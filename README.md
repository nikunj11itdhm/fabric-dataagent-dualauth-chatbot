# Fabric Data Agent — Dual Auth Chatbot 🏭🔐

A production-ready **Streamlit chatbot** that queries **Microsoft Fabric data** using the **Fabric Data Agent** directly. Supports both **Service Principal (SPN)** and **Entra User (Device Code)** authentication — switchable from the sidebar at runtime.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?logo=streamlit&logoColor=white)
![Fabric](https://img.shields.io/badge/Microsoft_Fabric-Data_Agent-F25022?logo=microsoft&logoColor=white)
![Auth](https://img.shields.io/badge/Auth-SPN_+_Entra_User-5C2D91)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🏗️ Architecture

This solution connects directly to a **Microsoft Fabric Data Agent** using the OpenAI Assistants-compatible API, supporting both SPN and user-identity authentication.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Streamlit App (app.py)                                                     │
│  ┌──────────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  Auth Selector        │  │  Rich Chat UI     │  │  Session Management  │  │
│  │  ┌─ 🔐 SPN           │  │  (Multi-turn)     │  │  • New Chat          │  │
│  │  └─ 👤 Entra User    │  │  • Avatars        │  │  • Disconnect        │  │
│  │     (Device Code)     │  │  • Suggestions    │  │  • Export Chat       │  │
│  └──────────┬───────────┘  └────────┬─────────┘  └──────────────────────┘  │
└─────────────┼──────────────────────┼───────────────────────────────────────┘
              │ SPN token /          │
              │ User token           │
              ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Fabric Client (fabric_client.py)                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  FabricAgentClient                                                    │  │
│  │  ├── SPN Auth (ClientSecretCredential)                               │  │
│  │  ├── Device Code Auth (MSAL PublicClientApplication)                  │  │
│  │  ├── Workspace/Agent Resolution (Fabric REST API)                    │  │
│  │  ├── OpenAI Assistants API (Threads, Messages, Runs)                 │  │
│  │  └── Retry with exponential back-off                                 │  │
│  └──────────────────────────────────┬──────────────────────────────────┘  │
└────────────────────────────────────┼─────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Microsoft Fabric Data Agent (OpenAI-compatible API)                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────────┐  ┌──────────────────┐    │
│  │ 🏠        │  │ 🏗️        │  │ 📊            │  │ ⚡               │    │
│  │ Lakehouse │  │ Warehouse │  │ Power BI      │  │ KQL Database    │    │
│  │ Delta/SQL │  │ T-SQL     │  │ DAX/Semantic  │  │ (Coming Soon)   │    │
│  └───────────┘  └───────────┘  └───────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### Dual Authentication
- **🔐 Service Principal (SPN)** — Non-interactive `ClientSecretCredential` for production/automated scenarios
- **👤 Entra User (Device Code)** — Interactive MSAL device code flow with user identity passthrough
- **🔄 Runtime Switching** — Toggle between auth modes from the sidebar without restarting

### Rich UI
- **🎨 Azure-branded design** — Gradient header banner, dark sidebar, custom SVG icons
- **💬 Multi-turn chat** — Context preserved across messages via persistent threads
- **💡 Suggestion cards** — Pre-built query suggestions for quick start
- **📊 Feature chips** — Visual indicators for capabilities and auth mode
- **👤 User/SPN identity card** — Shows connected identity in the sidebar
- **🔢 Message counter** — Tracks conversation length
- **📥 Export** — Download chat history as JSON or Markdown
- **⏱️ Response time** — Shows query latency for each response

### Data Sources
| Source | Status | Description |
|--------|--------|-------------|
| 🏠 **Lakehouse** | ✅ Available | Delta Lake / SQL queries |
| 🏗️ **Warehouse** | ✅ Available | T-SQL queries |
| 📊 **Power BI** | ✅ Available | DAX / Semantic Models |
| ⚡ **KQL Database** | 🔜 Coming Soon | Kusto Query Language |

---

## 🔐 SPN vs Entra User — When to Use Which

| Feature | 🔐 SPN | 👤 Entra User (Device Code) |
|---|---|---|
| **Login required** | ❌ No | ✅ Yes (device code) |
| **Headless / automated** | ✅ Yes | ❌ No |
| **Fabric Data Agent** | ✅ Supported (Preview) | ✅ Supported |
| **User-level RLS** | ❌ No user context | ✅ Enforced |
| **Multi-user backend** | ✅ Ideal | ❌ Per-user token |
| **Best for** | Production APIs, internal tools, automation | End-user facing apps needing user identity |

---

## 📋 Prerequisites

| Resource | Requirement |
|---|---|
| **Microsoft Fabric** | A workspace with a published Data Agent |
| **Service Principal** | An Entra ID app registration with client secret |
| **Fabric Workspace** | SPN granted access to the workspace containing the data agent |

### Step 1: Register Application & Create Service Principal

```bash
az ad sp create-for-rbac \
  --name "fabric-data-agent-spn" \
  --output json
```

### Step 2: Grant SPN Access to Fabric Workspace

1. Go to **Microsoft Fabric** → your workspace → **Manage access**
2. Add the Service Principal (by app name or client ID)
3. Assign at minimum **Contributor** role

---

## 🚀 Setup

### 1. Clone the repo

```bash
git clone https://github.com/nikunj11itdhm/fabric-dataagent-dualauth-chatbot.git
cd fabric-dataagent-dualauth-chatbot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your values
```

| Variable | Description | Where to Find |
|---|---|---|
| `AZURE_TENANT_ID` | Microsoft Entra tenant ID | Azure Portal → Entra ID → Overview |
| `AZURE_CLIENT_ID` | App registration client ID | Azure Portal → App registrations → your app |
| `AZURE_CLIENT_SECRET` | Client secret (SPN only) | Azure Portal → App registrations → Certificates & secrets |
| `DATA_AGENT_URL` | Published Data Agent URL | Fabric Portal → Data Agent → Settings → Published URL |
| `WORKSPACE_NAME` | Workspace name (if no URL) | Fabric Portal → Workspace name |
| `AGENT_NAME` | Agent name (if no URL) | Fabric Portal → Data Agent name |

### 4. Run the app

```bash
streamlit run app.py
```

Open `http://localhost:8501` — select your auth mode from the sidebar and connect!

---

## 📁 Project Structure

```
fabric-dataagent-dualauth-chatbot/
├── app.py                  # Streamlit app with dual auth + rich UI
├── fabric_client.py        # Fabric Data Agent client (SPN + Device Code)
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template (no secrets)
├── .gitignore              # Excludes .env, __pycache__, .venv
├── LICENSE                 # MIT License
├── README.md               # This file
└── docs/
    └── images/             # Screenshots and architecture diagrams
```

---

## 🛠️ Troubleshooting

| Error | Cause | Solution |
|---|---|---|
| `Unauthorized (401)` | SPN missing workspace access | Grant SPN Contributor role on workspace |
| `AADSTS7000215: Invalid client_secret` | Secret expired or incorrect | Regenerate in Azure Portal |
| `AADSTS700016: Application not found` | Wrong client ID or tenant | Verify `AZURE_CLIENT_ID` and `AZURE_TENANT_ID` |
| `Workspace not found` | Name mismatch or no access | Verify workspace name and SPN permissions |
| `Agent not found` | Agent not published | Publish the Data Agent in Fabric portal |

---

## 🔒 Security Best Practices

- 🔒 **Never commit `.env`** — excluded via `.gitignore`
- 🔒 **Rotate secrets regularly** — regenerate client secrets periodically
- 🔒 **Least privilege** — assign minimum required roles
- 🔒 **Use Azure Key Vault** — for production deployments

---

## 📚 References

- [Service Principal Support for Data Agents in Fabric (Preview)](https://community.fabric.microsoft.com/t5/Fabric-Updates-Blog/Service-Principal-Support-for-Data-Agents-in-Fabric-Preview/ba-p/5181634)
- [Service Principal for Fabric Data Agent — Setup Guide](https://aka.ms/Fabric/Data-Agent-Service-Principal)
- [MSAL Python — Device Code Flow](https://learn.microsoft.com/entra/msal/python/)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
