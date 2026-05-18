"""
Fabric Data Agent — Streamlit Chatbot (Dual Auth)

Natural language queries over Microsoft Fabric data using Fabric Data Agent.
Supports both Service Principal (SPN) and Entra User (Device Code) authentication.
"""

import os
import time
import json
import base64 as _b64
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

from fabric_client import FabricAgentClient, ConfigError

load_dotenv()

# ── Configuration ───────────────────────────────────────────────────────────
TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
WORKSPACE_NAME = os.getenv("WORKSPACE_NAME", "")
AGENT_NAME = os.getenv("AGENT_NAME", "")
DATA_AGENT_URL = os.getenv("DATA_AGENT_URL", "")

# ── SVG Assets ──────────────────────────────────────────────────────────────
AZURE_AI_LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="40" height="40">
  <defs>
    <linearGradient id="azGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0078D4;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#5C2D91;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="48" height="48" rx="10" fill="url(#azGrad)"/>
  <text x="24" y="32" text-anchor="middle" fill="white" font-size="22"
        font-family="Segoe UI,sans-serif" font-weight="bold">AI</text>
</svg>
"""

BOT_AVATAR_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="32" height="32">
  <defs>
    <linearGradient id="botGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0078D4;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#50E6FF;stop-opacity:1" />
    </linearGradient>
  </defs>
  <circle cx="24" cy="24" r="22" fill="url(#botGrad)"/>
  <circle cx="17" cy="20" r="3" fill="white" opacity="0.9"/>
  <circle cx="31" cy="20" r="3" fill="white" opacity="0.9"/>
  <path d="M16 30 Q24 37 32 30" stroke="white" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <circle cx="24" cy="6" r="3" fill="#50E6FF"/>
  <line x1="24" y1="9" x2="24" y2="14" stroke="#50E6FF" stroke-width="2"/>
</svg>
"""

FABRIC_ICON_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="32" height="32">
  <rect x="4" y="8" width="18" height="14" rx="3" fill="#F25022"/>
  <rect x="26" y="8" width="18" height="14" rx="3" fill="#7FBA00"/>
  <rect x="4" y="26" width="18" height="14" rx="3" fill="#00A4EF"/>
  <rect x="26" y="26" width="18" height="14" rx="3" fill="#FFB900"/>
</svg>
"""

AZURE_AI_LOGO_BASE64 = "data:image/svg+xml;base64," + _b64.b64encode(AZURE_AI_LOGO_SVG.encode()).decode()
BOT_AVATAR_BASE64 = "data:image/svg+xml;base64," + _b64.b64encode(BOT_AVATAR_SVG.encode()).decode()
FABRIC_ICON_BASE64 = "data:image/svg+xml;base64," + _b64.b64encode(FABRIC_ICON_SVG.encode()).decode()


# ── Custom CSS ──────────────────────────────────────────────────────────────
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');

    .stApp {
        background: linear-gradient(165deg, #f8faff 0%, #eef2ff 40%, #f0f4ff 100%);
    }

    /* ── Header banner ── */
    .azure-header {
        background: linear-gradient(135deg, #0078D4 0%, #005A9E 50%, #5C2D91 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        box-shadow: 0 8px 32px rgba(0, 120, 212, 0.25);
        position: relative;
        overflow: hidden;
    }
    .azure-header::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%);
        border-radius: 50%;
    }
    .azure-header-logo {
        width: 52px;
        height: 52px;
        border-radius: 12px;
        background: rgba(255,255,255,0.15);
        padding: 6px;
        backdrop-filter: blur(10px);
        flex-shrink: 0;
    }
    .azure-header-text h1 {
        color: white;
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.3px;
        font-family: 'Segoe UI', sans-serif;
    }
    .azure-header-text p {
        color: rgba(255,255,255,0.8);
        font-size: 0.85rem;
        margin: 4px 0 0 0;
        font-family: 'Segoe UI', sans-serif;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1f36 0%, #0d1117 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown span,
    section[data-testid="stSidebar"] .stMarkdown label {
        color: #e0e6f0 !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.1);
    }

    /* ── Sidebar brand ── */
    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 0.5rem 0 1rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 1rem;
    }
    .sidebar-brand img {
        width: 36px;
        height: 36px;
        border-radius: 8px;
    }
    .sidebar-brand-text {
        color: #e0e6f0;
        font-size: 0.9rem;
        font-weight: 600;
        font-family: 'Segoe UI', sans-serif;
    }
    .sidebar-brand-sub {
        color: rgba(255,255,255,0.5);
        font-size: 0.7rem;
        font-family: 'Segoe UI', sans-serif;
    }

    /* ── Auth selector card ── */
    .auth-selector {
        background: linear-gradient(135deg, rgba(0,120,212,0.12), rgba(92,45,145,0.08));
        border: 1px solid rgba(0,120,212,0.2);
        border-radius: 12px;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0 0.5rem 0;
    }
    .auth-selector-title {
        color: rgba(255,255,255,0.5);
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0px;
        font-family: 'Segoe UI', sans-serif;
    }

    /* ── User card ── */
    .user-card {
        background: linear-gradient(135deg, rgba(0,120,212,0.15), rgba(92,45,145,0.1));
        border: 1px solid rgba(0,120,212,0.2);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .user-card .user-name {
        color: #58a6ff;
        font-weight: 600;
        font-size: 0.95rem;
    }
    .user-card .user-detail {
        color: rgba(255,255,255,0.5);
        font-size: 0.75rem;
        margin-top: 2px;
    }

    /* ── Status pill ── */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(46,160,67,0.15);
        border: 1px solid rgba(46,160,67,0.3);
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.75rem;
        color: #3fb950;
        margin: 0.5rem 0;
    }
    .status-pill-spn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(0,120,212,0.15);
        border: 1px solid rgba(0,120,212,0.3);
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.75rem;
        color: #58a6ff;
        margin: 0.5rem 0;
    }
    .status-dot {
        width: 8px;
        height: 8px;
        background: #3fb950;
        border-radius: 50%;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    .status-dot-blue {
        width: 8px;
        height: 8px;
        background: #58a6ff;
        border-radius: 50%;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    /* ── Sidebar buttons ── */
    section[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease;
        font-family: 'Segoe UI', sans-serif;
    }

    /* ── Sign-in card ── */
    .signin-card {
        background: white;
        border-radius: 20px;
        padding: 3rem 2.5rem;
        text-align: center;
        box-shadow: 0 4px 24px rgba(0,0,0,0.06);
        border: 1px solid rgba(0,120,212,0.1);
        max-width: 500px;
        margin: 2rem auto;
    }
    .signin-card h2 {
        color: #1a1f36;
        font-family: 'Segoe UI', sans-serif;
        margin-bottom: 0.5rem;
    }
    .signin-card p {
        color: #6b7280;
        font-size: 0.95rem;
    }

    /* ── Device code card ── */
    .device-code-card {
        background: linear-gradient(135deg, #f0f7ff, #f5f0ff);
        border: 2px solid #0078D4;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    .device-code {
        font-size: 2.2rem;
        font-weight: 700;
        font-family: 'Consolas', 'Courier New', monospace;
        color: #0078D4;
        letter-spacing: 4px;
        background: white;
        padding: 0.5rem 1.5rem;
        border-radius: 10px;
        display: inline-block;
        margin: 0.75rem 0;
        box-shadow: 0 2px 8px rgba(0,120,212,0.15);
    }

    /* ── Chat area ── */
    .stChatMessage {
        border-radius: 16px !important;
        margin-bottom: 0.75rem !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    }

    /* ── Feature chips ── */
    .feature-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 1rem 0;
        justify-content: center;
    }
    .chip {
        background: rgba(0,120,212,0.08);
        border: 1px solid rgba(0,120,212,0.15);
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 0.8rem;
        color: #0078D4;
        font-family: 'Segoe UI', sans-serif;
    }

    /* ── Welcome message ── */
    .welcome-box {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        border: 1px solid rgba(0,0,0,0.06);
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        margin: 1rem 0;
    }
    .welcome-box h3 {
        color: #1a1f36;
        font-family: 'Segoe UI', sans-serif;
    }
    .welcome-box p {
        color: #4b5563;
        line-height: 1.6;
    }

    /* ── Suggestion cards ── */
    .suggestion-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin: 1rem 0;
    }
    .suggestion-card {
        background: linear-gradient(135deg, #f8faff, #f0f4ff);
        border: 1px solid rgba(0,120,212,0.12);
        border-radius: 12px;
        padding: 1rem;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.85rem;
        color: #374151;
        font-family: 'Segoe UI', sans-serif;
    }
    .suggestion-card:hover {
        border-color: #0078D4;
        box-shadow: 0 4px 12px rgba(0,120,212,0.12);
        transform: translateY(-1px);
    }
    .suggestion-icon {
        font-size: 1.3rem;
        margin-bottom: 6px;
    }

    /* ── Response time ── */
    .response-time {
        font-size: 0.75rem;
        color: #888;
        margin-top: 4px;
    }

    /* Hide default Streamlit header/footer */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)


# ── Header banner ──────────────────────────────────────────────────────────
def render_header():
    st.markdown(f"""
    <div class="azure-header">
        <img class="azure-header-logo" src="{AZURE_AI_LOGO_BASE64}" alt="Azure AI">
        <div class="azure-header-text">
            <h1>Fabric Data Agent</h1>
            <p>Natural language queries over Microsoft Fabric · Dual Authentication</p>
        </div>
        <img src="{FABRIC_ICON_BASE64}" alt="Fabric"
             style="width:36px; height:36px; margin-left:auto; opacity:0.7; position:relative; z-index:1;">
    </div>
    """, unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        # Brand
        st.markdown(f"""
        <div class="sidebar-brand">
            <img src="{AZURE_AI_LOGO_BASE64}" alt="Azure AI">
            <div>
                <div class="sidebar-brand-text">Microsoft Fabric</div>
                <div class="sidebar-brand-sub">Data Agent · Dual Auth</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Auth method selector ──
        st.markdown("""
        <div class="auth-selector">
            <div class="auth-selector-title">🔑 Authentication Method</div>
        </div>
        """, unsafe_allow_html=True)

        auth_mode = st.radio(
            "Choose authentication:",
            options=["🔐 Service Principal (SPN)", "👤 Entra User (Device Code)"],
            index=0 if st.session_state.get("auth_mode", "spn") == "spn" else 1,
            label_visibility="collapsed",
        )

        new_mode = "spn" if "Service Principal" in auth_mode else "entra"
        if new_mode != st.session_state.get("auth_mode"):
            for key in ("messages", "client", "connected",
                        "thread_name", "msg_count"):
                st.session_state.pop(key, None)
            st.session_state["auth_mode"] = new_mode
            st.rerun()

        st.markdown("---")

        current_mode = st.session_state.get("auth_mode", "spn")
        is_connected = st.session_state.get("connected", False)

        if is_connected:
            client: FabricAgentClient = st.session_state["client"]

            if current_mode == "spn":
                st.markdown("""
                <div class="status-pill-spn">
                    <span class="status-dot-blue"></span> Connected via SPN
                </div>
                """, unsafe_allow_html=True)
                st.markdown("""
                <div class="user-card">
                    <div class="user-name">🔐 Service Principal</div>
                    <div class="user-detail">Non-interactive authentication</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                user_name = client.user_name or "User"
                user_email = client.user_email or ""
                st.markdown("""
                <div class="status-pill">
                    <span class="status-dot"></span> Connected
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f"""
                <div class="user-card">
                    <div class="user-name">👤 {user_name}</div>
                    <div class="user-detail">{user_email}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")

            # Agent info
            agent_label = AGENT_NAME or "Data Agent"
            st.markdown(f"""
            <div style="padding:0.5rem 0;">
                <p style="color:rgba(255,255,255,0.4); font-size:0.7rem; text-transform:uppercase;
                          letter-spacing:1px; margin-bottom:8px;">Agent Configuration</p>
                <div style="display:flex; align-items:center; gap:8px; margin:4px 0;">
                    <img src="{BOT_AVATAR_BASE64}" style="width:24px; height:24px;">
                    <span style="color:#e0e6f0; font-size:0.85rem; font-weight:600;">{agent_label}</span>
                </div>
                <p style="color:rgba(255,255,255,0.5); font-size:0.8rem; margin:4px 0 0 34px;">
                    Workspace: {WORKSPACE_NAME or 'Published URL'}</p>
            </div>
            """, unsafe_allow_html=True)

            # Token expiry
            expiry = client.token_expiry
            if expiry:
                st.markdown(f"""
                <p style="color:rgba(255,255,255,0.5); font-size:0.75rem; margin-top:8px;">
                    🕐 Token expires: {expiry:%H:%M:%S UTC}</p>
                """, unsafe_allow_html=True)

            st.markdown("---")

            # Message counter
            msg_count = st.session_state.get("msg_count", 0)
            st.markdown(f"""
            <p style="color:rgba(255,255,255,0.5); font-size:0.8rem;">
                💬 {msg_count} message{'s' if msg_count != 1 else ''} in conversation</p>
            """, unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 New Chat", use_container_width=True):
                    st.session_state["messages"] = []
                    st.session_state["msg_count"] = 0
                    st.session_state["thread_name"] = f"session-{datetime.now():%Y%m%d-%H%M%S}"
                    st.rerun()
            with col2:
                label = "🚪 Sign Out" if current_mode == "entra" else "🔌 Disconnect"
                if st.button(label, use_container_width=True):
                    for key in ("messages", "client", "connected",
                                "thread_name", "msg_count"):
                        st.session_state.pop(key, None)
                    st.rerun()

            # Export chat
            messages = st.session_state.get("messages", [])
            if messages:
                st.markdown("---")
                st.markdown("""
                <p style="color:rgba(255,255,255,0.4); font-size:0.7rem; text-transform:uppercase;
                          letter-spacing:1px; margin-bottom:8px;">📥 Export Chat</p>
                """, unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    json_str = json.dumps(messages, indent=2)
                    st.download_button(
                        "JSON", json_str, "chat_history.json",
                        mime="application/json", use_container_width=True,
                    )
                with col2:
                    md_lines = []
                    for m in messages:
                        role = "**You**" if m["role"] == "user" else "**Agent**"
                        ts = m.get("timestamp", "")
                        md_lines.append(f"{role} ({ts}):\n{m['content']}\n")
                    md_str = "\n---\n\n".join(md_lines)
                    st.download_button(
                        "Markdown", md_str, "chat_history.md",
                        mime="text/markdown", use_container_width=True,
                    )

        else:
            st.markdown("""
            <div style="padding:0.5rem 0;">
                <p style="color:rgba(255,255,255,0.6); font-size:0.85rem; line-height:1.6;">
                    Connect to query Fabric data using natural language.
                </p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")

            st.markdown("""
            <p style="color:rgba(255,255,255,0.4); font-size:0.7rem; text-transform:uppercase;
                      letter-spacing:1px; margin-bottom:8px;">Supported Data Sources</p>
            """, unsafe_allow_html=True)

            sources = [
                ("🏠", "Lakehouse", "Delta Lake / SQL"),
                ("🏗️", "Warehouse", "T-SQL"),
                ("📊", "Power BI", "DAX / Semantic Models"),
                ("⚡", "KQL Database", "Coming Soon"),
            ]
            for icon, name, desc in sources:
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:10px; padding:6px 0;">
                    <span style="font-size:1.2rem;">{icon}</span>
                    <div>
                        <span style="color:#e0e6f0; font-size:0.85rem; font-weight:600;">{name}</span>
                        <br><span style="color:rgba(255,255,255,0.4); font-size:0.72rem;">{desc}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Footer
        st.markdown("---")
        auth_label = ("SPN Auth" if st.session_state.get("auth_mode", "spn") == "spn"
                      else "Device Code Auth · User Identity")
        st.markdown(f"""
        <div style="text-align:center; padding:0.5rem 0;">
            <div style="display:flex; justify-content:center; gap:8px; margin-bottom:6px;">
                <img src="{AZURE_AI_LOGO_BASE64}"
                     style="width:20px; height:20px; border-radius:4px; opacity:0.5;">
                <img src="{FABRIC_ICON_BASE64}"
                     style="width:20px; height:20px; border-radius:4px; opacity:0.5;">
            </div>
            <p style="color:rgba(255,255,255,0.25); font-size:0.65rem; margin:0;">
                Fabric Data Agent v1.0</p>
            <p style="color:rgba(255,255,255,0.2); font-size:0.6rem; margin:2px 0 0 0;">
                {auth_label}</p>
        </div>
        """, unsafe_allow_html=True)


# ── Welcome / empty state ──────────────────────────────────────────────────
def render_welcome():
    auth_mode = st.session_state.get("auth_mode", "spn")
    auth_chips = (
        '<span class="chip">🔐 Service Principal Auth</span>'
        if auth_mode == "spn"
        else '<span class="chip">🔐 Identity Passthrough (Device Code)</span>'
    )

    st.markdown(f"""
    <div class="welcome-box">
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
            <img src="{BOT_AVATAR_BASE64}" style="width:40px; height:40px;">
            <h3 style="margin:0;">Welcome! Ask me anything about your Fabric data.</h3>
        </div>
        <p>I can query your Lakehouses, Warehouses, Power BI Semantic Models,
           and KQL Databases (coming soon) using natural language. Just type your question below.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="feature-chips">
        {auth_chips}
        <span class="chip">💬 Multi-turn Conversations</span>
        <span class="chip">📊 SQL · DAX · KQL (Coming Soon)</span>
        <span class="chip">🛡️ Row-Level Security</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 💡 Try asking:")
    st.markdown("""
    <div class="suggestion-grid">
        <div class="suggestion-card">
            <div class="suggestion-icon">📈</div>
            Show me total revenue by region for this quarter
        </div>
        <div class="suggestion-card">
            <div class="suggestion-icon">🔍</div>
            What are the top 10 products by sales volume?
        </div>
        <div class="suggestion-card">
            <div class="suggestion-icon">📊</div>
            Compare year-over-year growth across departments
        </div>
        <div class="suggestion-card">
            <div class="suggestion-icon">🏗️</div>
            List all tables in my warehouse with row counts
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── SPN connection page ────────────────────────────────────────────────────
def render_spn_connect():
    st.markdown(f"""
    <div class="signin-card">
        <div style="display:flex; justify-content:center; gap:12px; margin-bottom:1.2rem;">
            <img src="{AZURE_AI_LOGO_BASE64}" style="width:48px; height:48px; border-radius:12px;">
            <div style="font-size:2rem; line-height:48px; color:#ccc;">⟷</div>
            <img src="{FABRIC_ICON_BASE64}" style="width:48px; height:48px; border-radius:12px;">
        </div>
        <h2>Connect with Service Principal</h2>
        <p>Authenticate using your configured Service Principal credentials
           from the <code>.env</code> file. No interactive sign-in required.</p>
        <div style="display:flex; justify-content:center; gap:16px; margin-top:1.2rem;">
            <div style="text-align:center;">
                <div style="font-size:1.5rem;">🏠</div>
                <div style="font-size:0.7rem; color:#6b7280;">Lakehouse</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:1.5rem;">🏗️</div>
                <div style="font-size:0.7rem; color:#6b7280;">Warehouse</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:1.5rem;">📊</div>
                <div style="font-size:0.7rem; color:#6b7280;">Power BI</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:1.5rem;">⚡</div>
                <div style="font-size:0.7rem; color:#6b7280;">KQL DB (Coming Soon)</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _, col_btn, _ = st.columns([1, 2, 1])
    with col_btn:
        return st.button("🔐  Connect with SPN",
                         use_container_width=True, type="primary")


# ── Entra User sign-in page ────────────────────────────────────────────────
def render_signin():
    st.markdown(f"""
    <div class="signin-card">
        <div style="display:flex; justify-content:center; gap:12px; margin-bottom:1.2rem;">
            <img src="{AZURE_AI_LOGO_BASE64}" style="width:48px; height:48px; border-radius:12px;">
            <div style="font-size:2rem; line-height:48px; color:#ccc;">⟷</div>
            <img src="{FABRIC_ICON_BASE64}" style="width:48px; height:48px; border-radius:12px;">
        </div>
        <h2>Sign in to get started</h2>
        <p>Use your Microsoft account to securely connect to your Fabric data.
           Your identity is passed through to enforce row-level security.</p>
        <div style="display:flex; justify-content:center; gap:16px; margin-top:1.2rem;">
            <div style="text-align:center;">
                <div style="font-size:1.5rem;">🏠</div>
                <div style="font-size:0.7rem; color:#6b7280;">Lakehouse</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:1.5rem;">🏗️</div>
                <div style="font-size:0.7rem; color:#6b7280;">Warehouse</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:1.5rem;">📊</div>
                <div style="font-size:0.7rem; color:#6b7280;">Power BI</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:1.5rem;">⚡</div>
                <div style="font-size:0.7rem; color:#6b7280;">KQL DB (Coming Soon)</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _, col_btn, _ = st.columns([1, 2, 1])
    with col_btn:
        return st.button("🔑  Sign in with Microsoft",
                         use_container_width=True, type="primary")


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Fabric Data Agent — Dual Auth",
        page_icon="🏭",
        layout="centered",
        initial_sidebar_state="expanded",
    )

    inject_custom_css()

    # Set defaults
    if "auth_mode" not in st.session_state:
        st.session_state["auth_mode"] = "spn"

    # Validate env vars
    missing = []
    if not TENANT_ID or TENANT_ID.startswith("<"):
        missing.append("AZURE_TENANT_ID")
    if not CLIENT_ID or CLIENT_ID.startswith("<"):
        missing.append("AZURE_CLIENT_ID")
    if st.session_state["auth_mode"] == "spn":
        if not CLIENT_SECRET or CLIENT_SECRET.startswith("<"):
            missing.append("AZURE_CLIENT_SECRET")
    if not DATA_AGENT_URL or DATA_AGENT_URL.startswith("<"):
        if not WORKSPACE_NAME or WORKSPACE_NAME.startswith("<"):
            missing.append("WORKSPACE_NAME")
        if not AGENT_NAME or AGENT_NAME.startswith("<"):
            missing.append("AGENT_NAME")

    if missing:
        render_header()
        render_sidebar()
        st.error(f"Missing environment variables: **{', '.join(missing)}**. "
                 f"Check your `.env` file.")
        st.code(open(".env.example").read() if os.path.exists(".env.example") else
                "See .env.example for required variables", language="ini")
        st.stop()

    current_mode = st.session_state.get("auth_mode", "spn")
    is_connected = st.session_state.get("connected", False)

    # ── Not connected ──
    if not is_connected:
        render_header()
        render_sidebar()

        if current_mode == "spn":
            if render_spn_connect():
                with st.spinner("🔐 Connecting with Service Principal..."):
                    try:
                        client = FabricAgentClient(
                            tenant_id=TENANT_ID,
                            client_id=CLIENT_ID,
                            client_secret=CLIENT_SECRET,
                            workspace_name=WORKSPACE_NAME,
                            agent_name=AGENT_NAME,
                            data_agent_url=DATA_AGENT_URL or None,
                            auth_mode="spn",
                        )
                        auth_msg = client.authenticate()
                        st.success(auth_msg)

                        with st.spinner("Resolving agent..."):
                            resolve_msg = client.resolve()
                        st.success(resolve_msg)

                        st.session_state["client"] = client
                        st.session_state["connected"] = True
                        st.session_state["messages"] = []
                        st.session_state["msg_count"] = 0
                        st.session_state["thread_name"] = f"session-{datetime.now():%Y%m%d-%H%M%S}"
                        st.balloons()
                        st.rerun()
                    except ConfigError as e:
                        st.error(f"⚙️ Config error:\n\n{e}")
                    except Exception as e:
                        st.error(f"❌ Connection failed")
                        with st.expander("Error details"):
                            st.code(str(e))
        else:
            if render_signin():
                with st.spinner("🔑 Starting device code flow..."):
                    try:
                        client = FabricAgentClient(
                            tenant_id=TENANT_ID,
                            client_id=CLIENT_ID,
                            workspace_name=WORKSPACE_NAME,
                            agent_name=AGENT_NAME,
                            data_agent_url=DATA_AGENT_URL or None,
                            auth_mode="device_code",
                        )
                        auth_msg = client.authenticate()
                        st.success(auth_msg)

                        with st.spinner("Resolving agent..."):
                            resolve_msg = client.resolve()
                        st.success(resolve_msg)

                        st.session_state["client"] = client
                        st.session_state["connected"] = True
                        st.session_state["messages"] = []
                        st.session_state["msg_count"] = 0
                        st.session_state["thread_name"] = f"session-{datetime.now():%Y%m%d-%H%M%S}"
                        st.balloons()
                        st.rerun()
                    except ConfigError as e:
                        st.error(f"⚙️ Config error:\n\n{e}")
                    except Exception as e:
                        st.error(f"❌ Connection failed")
                        with st.expander("Error details"):
                            st.code(str(e))
        st.stop()

    # ── Connected → Chat ──
    render_header()
    render_sidebar()

    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "msg_count" not in st.session_state:
        st.session_state["msg_count"] = 0

    if not st.session_state["messages"]:
        render_welcome()

    # Render chat history
    for msg in st.session_state["messages"]:
        avatar = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if msg.get("response_time"):
                st.markdown(
                    f'<div class="response-time">⏱ {msg["response_time"]:.1f}s</div>',
                    unsafe_allow_html=True,
                )

    # User input
    if prompt := st.chat_input("Ask about your Fabric data..."):
        st.session_state["messages"].append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("🧠 Querying your data..."):
                t0 = time.time()
                try:
                    thread = st.session_state.get("thread_name")
                    answer = st.session_state["client"].ask(prompt, thread_name=thread)
                except Exception as e:
                    answer = f"❌ Error: {e}"
                elapsed = time.time() - t0
            st.markdown(answer)
            st.markdown(
                f'<div class="response-time">⏱ {elapsed:.1f}s</div>',
                unsafe_allow_html=True,
            )

        st.session_state["messages"].append({
            "role": "assistant",
            "content": answer,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "response_time": elapsed,
        })
        st.session_state["msg_count"] = st.session_state.get("msg_count", 0) + 1
        st.rerun()


if __name__ == "__main__":
    main()
