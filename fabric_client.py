"""
Fabric Data Agent Client — Dual Authentication (SPN + Entra User)

Supports:
  • Service Principal (ClientSecretCredential) for non-interactive / automated scenarios
  • Entra User (Device Code via MSAL) for interactive user-identity passthrough
  • Retry logic with exponential back-off
  • Persistent-thread support for multi-turn conversations
"""

import logging
import time
import uuid
import warnings
import requests
import msal
from datetime import datetime, timezone
from typing import Optional

from azure.identity import ClientSecretCredential
from azure.core.credentials import AccessToken, TokenCredential
from openai import OpenAI

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=r".*Assistants API is deprecated.*"
)

log = logging.getLogger("fabric_agent")

FABRIC_API = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
FABRIC_USER_SCOPE = "https://api.fabric.microsoft.com/Dataagent.Execute.All"

MAX_RETRIES = 3
RETRY_BACKOFF = 2


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


class MsalTokenCredential(TokenCredential):
    """Wraps an MSAL access token for use with Azure SDK clients."""

    def __init__(self, access_token: str, expires_on: int):
        self._token = AccessToken(access_token, expires_on)

    def get_token(self, *scopes, **kwargs):
        return self._token


def _retry_request(method: str, url: str, **kwargs) -> requests.Response:
    """HTTP request with exponential-backoff retry on transient errors."""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code == 429:
                wait = RETRY_BACKOFF ** attempt
                log.warning("Rate-limited (429). Retrying in %ss…", wait)
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = RETRY_BACKOFF ** attempt
                log.warning("Server error %s. Retrying in %ss…", resp.status_code, wait)
                time.sleep(wait)
                continue
            return resp
        except requests.ConnectionError as exc:
            last_exc = exc
            wait = RETRY_BACKOFF ** attempt
            log.warning("Connection error (attempt %s/%s): %s", attempt, MAX_RETRIES, exc)
            time.sleep(wait)
    raise requests.ConnectionError(
        f"Failed after {MAX_RETRIES} retries: {last_exc}"
    ) from last_exc


class FabricAgentClient:
    """Fabric Data Agent client with dual authentication.

    Auth Modes
    ----------
    * ``spn`` — Service Principal (ClientSecretCredential). Non-interactive.
    * ``device_code`` — MSAL Device Code flow with user identity passthrough.
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: Optional[str] = None,
        workspace_name: str = "",
        agent_name: str = "",
        data_agent_url: Optional[str] = None,
        auth_mode: str = "spn",
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.workspace_name = workspace_name
        self.agent_name = agent_name
        self.data_agent_url = data_agent_url if data_agent_url else None
        self.auth_mode = auth_mode
        self.token = None
        self._device_msg: Optional[str] = None
        self._device_code: Optional[str] = None
        self._device_url: Optional[str] = None
        self._workspace_id: Optional[str] = None
        self._agent_id: Optional[str] = None
        self._user_name: Optional[str] = None
        self._user_email: Optional[str] = None

    # ── Authentication ────────────────────────────────────────────────
    def authenticate(self) -> str:
        """Perform authentication based on auth_mode. Returns a status message."""
        if self.auth_mode == "spn":
            return self._auth_spn()
        return self._auth_device_code()

    def _auth_spn(self) -> str:
        if not self.client_secret:
            raise ConfigError("AZURE_CLIENT_SECRET is required for SPN authentication.")
        credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )
        token = credential.get_token(FABRIC_SCOPE)
        self.token = AccessToken(token.token, token.expires_on)
        return "✅ Authenticated via Service Principal"

    def _auth_device_code(self) -> str:
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        app = msal.PublicClientApplication(client_id=self.client_id, authority=authority)
        flow = app.initiate_device_flow(scopes=[FABRIC_USER_SCOPE])
        if "user_code" not in flow:
            raise ConfigError(
                f"Failed to initiate device flow: "
                f"{flow.get('error_description', 'Unknown error')}"
            )

        self._device_code = flow["user_code"]
        self._device_url = flow["verification_uri"]
        self._device_msg = flow.get("message", "")

        result = app.acquire_token_by_device_flow(flow)

        if "access_token" not in result:
            error = result.get("error", "unknown_error")
            desc = result.get("error_description", "No details.")
            raise ConfigError(f"Sign-in failed: {error}\n{desc}")

        claims = result.get("id_token_claims", {})
        self._user_name = claims.get("name", "User")
        self._user_email = claims.get("preferred_username", "")

        self.token = AccessToken(
            result["access_token"],
            int(time.time()) + result.get("expires_in", 3600),
        )
        return "✅ Authenticated via Entra ID (Device Code)"

    @property
    def device_code_info(self) -> Optional[dict]:
        if self._device_code:
            return {"code": self._device_code, "url": self._device_url,
                    "message": self._device_msg}
        return None

    @property
    def user_name(self) -> Optional[str]:
        return self._user_name

    @property
    def user_email(self) -> Optional[str]:
        return self._user_email

    @property
    def token_expiry(self) -> Optional[datetime]:
        if self.token:
            return datetime.fromtimestamp(self.token.expires_on, tz=timezone.utc)
        return None

    def _ensure_token(self):
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        if self.token.expires_on <= time.time() + 300:
            log.info("Token expiring soon — re-authentication may be required.")

    def _headers(self) -> dict:
        self._ensure_token()
        return {
            "Authorization": f"Bearer {self.token.token}",
            "Content-Type": "application/json",
        }

    # ── Workspace / Agent resolution ──────────────────────────────────
    def resolve(self) -> str:
        """Resolve workspace & agent names → IDs, or validate published URL."""
        if self.data_agent_url:
            return "✅ Using published agent URL"

        self._workspace_id = self._find_workspace()
        self._agent_id = self._find_agent(self._workspace_id)
        self.data_agent_url = (
            f"{FABRIC_API}/workspaces/{self._workspace_id}"
            f"/dataagents/{self._agent_id}/aiassistant/openai"
        )
        return (
            f"✅ Workspace: `{self._workspace_id}`\n"
            f"✅ Agent: `{self._agent_id}`"
        )

    def _find_workspace(self) -> str:
        r = _retry_request("GET", f"{FABRIC_API}/workspaces",
                           headers=self._headers(), timeout=30)
        r.raise_for_status()
        names = []
        for ws in r.json().get("value", []):
            names.append(ws["displayName"])
            if ws["displayName"].lower() == self.workspace_name.lower():
                return ws["id"]
        raise ValueError(
            f"Workspace '{self.workspace_name}' not found.\n"
            f"Available: {', '.join(names[:10])}"
        )

    def _find_agent(self, wid: str) -> str:
        r = _retry_request(
            "GET", f"{FABRIC_API}/workspaces/{wid}/items",
            headers=self._headers(), params={"type": "DataAgent"}, timeout=30,
        )
        r.raise_for_status()
        names = []
        for item in r.json().get("value", []):
            names.append(item["displayName"])
            if item["displayName"].lower() == self.agent_name.lower():
                return item["id"]
        hint = (f"Available: {', '.join(names)}" if names
                else "No Data Agent items found.")
        raise ValueError(
            f"Agent '{self.agent_name}' not found in workspace "
            f"'{self.workspace_name}'.\n{hint}"
        )

    # ── OpenAI Assistants helpers ─────────────────────────────────────
    def _oai(self) -> OpenAI:
        self._ensure_token()
        return OpenAI(
            api_key="n/a",
            base_url=self.data_agent_url,
            default_query={"api-version": "2024-05-01-preview"},
            default_headers={
                "Authorization": f"Bearer {self.token.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "ActivityId": str(uuid.uuid4()),
            },
        )

    def _thread(self, name: Optional[str] = None) -> dict:
        name = name or f"chat-{uuid.uuid4()}"
        base = self.data_agent_url.removesuffix("/openai").replace(
            "/aiassistant", "/__private/aiassistant"
        )
        r = _retry_request(
            "GET",
            f'{base}/threads/fabric?tag="{name}"',
            headers={
                "Authorization": f"Bearer {self.token.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "ActivityId": str(uuid.uuid4()),
            },
            timeout=30,
        )
        r.raise_for_status()
        t = r.json()
        t["name"] = name
        return t

    # ── Chat ──────────────────────────────────────────────────────────
    def ask(
        self,
        question: str,
        thread_name: Optional[str] = None,
        timeout: int = 120,
    ) -> str:
        """Send a question to the Data Agent and return the answer."""
        if not self.data_agent_url:
            raise RuntimeError("Call resolve() before asking questions.")
        if not question or not question.strip():
            raise ValueError("Question cannot be empty.")

        client = self._oai()
        assistant = client.beta.assistants.create(model="n/a")
        thread = self._thread(thread_name)

        client.beta.threads.messages.create(
            thread_id=thread["id"], role="user", content=question
        )
        run = client.beta.threads.runs.create(
            thread_id=thread["id"], assistant_id=assistant.id
        )

        t0 = time.time()
        while run.status in ("queued", "in_progress"):
            if time.time() - t0 > timeout:
                return "⏱️ Timed out — try a simpler question or increase the timeout."
            time.sleep(2)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread["id"], run_id=run.id
            )

        if run.status == "failed":
            err = getattr(run, "last_error", None)
            detail = f" ({err.message})" if err and hasattr(err, "message") else ""
            return (f"⚠️ Agent run failed{detail}. Check that the agent is published "
                    f"and data sources are accessible.")

        if run.status != "completed":
            return f"⚠️ Run ended with status: {run.status}"

        msgs = client.beta.threads.messages.list(thread_id=thread["id"], order="asc")
        out: list[str] = []
        for m in msgs.data:
            if m.role == "assistant":
                try:
                    c = m.content[0]
                    text = (
                        c.text.value
                        if hasattr(c, "text") and hasattr(c.text, "value")
                        else str(c)
                    )
                    out.append(text)
                except (IndexError, AttributeError):
                    out.append(str(m.content))

        if thread_name is None:
            try:
                client.beta.threads.delete(thread_id=thread["id"])
            except Exception:
                pass

        return "\n".join(out) if out else "No response received from the agent."
