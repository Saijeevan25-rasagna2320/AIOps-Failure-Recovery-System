import streamlit as st
import pandas as pd
import requests
import time
import os
from datetime import datetime, timedelta

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="AIOps Control Center",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state ─────────────────────────────────────────────
for k, v in [("dark_mode", True), ("refresh_enabled", True), ("refresh_interval", 5)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Palette ───────────────────────────────────────────────────
dark = st.session_state.dark_mode
if dark:
    C = dict(
        bg       = "#0b0d12",
        surface  = "#111318",
        surface2 = "#181c24",
        border   = "#21263a",
        text     = "#dde1ed",
        muted    = "#5c6380",
        blue     = "#5b9cf6",
        green    = "#34d17a",
        yellow   = "#f5c542",
        red      = "#f55252",
        purple   = "#9d72f5",
    )
else:
    C = dict(
        bg       = "#f2f4f9",
        surface  = "#ffffff",
        surface2 = "#f7f8fc",
        border   = "#dce0ee",
        text     = "#0f1623",
        muted    = "#7b82a0",
        blue     = "#2563eb",
        green    = "#16a34a",
        yellow   = "#d97706",
        red      = "#dc2626",
        purple   = "#7c3aed",
    )

# ── CSS ───────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{
  font-family: 'Inter', sans-serif;
  background: {C['bg']} !important;
  color: {C['text']} !important;
}}
.stApp {{ background: {C['bg']} !important; }}
.block-container {{ padding: 1.2rem 2rem 2rem !important; max-width: 1500px !important; }}
#MainMenu, footer, header {{ visibility: hidden; }}

/* Sidebar */
section[data-testid="stSidebar"] {{
  background: {C['surface']} !important;
  border-right: 1px solid {C['border']} !important;
}}
section[data-testid="stSidebar"] * {{ color: {C['text']} !important; }}

/* Tabs */
.stTabs [role="tablist"] {{ border-bottom: 1px solid {C['border']}; gap: 4px; }}
.stTabs [role="tab"] {{
  font-size: 12.5px; font-weight: 600; padding: 7px 18px;
  color: {C['muted']} !important; border-bottom: 2px solid transparent;
  border-radius: 0; letter-spacing: 0.02em;
}}
.stTabs [aria-selected="true"] {{
  color: {C['blue']} !important;
  border-bottom: 2px solid {C['blue']} !important;
  background: transparent !important;
}}

/* Buttons */
.stButton > button {{
  font-family: 'Inter', sans-serif; font-weight: 600; font-size: 13px;
  border-radius: 6px; border: 1px solid {C['border']};
  background: {C['surface2']}; color: {C['text']}; padding: 7px 18px;
  transition: all 0.15s ease;
}}
.stButton > button:hover {{ border-color: {C['blue']}; color: {C['blue']}; background: {C['blue']}10; }}
.stButton > button:disabled {{ opacity: 0.35; cursor: not-allowed; }}

/* Inputs */
.stTextInput input, .stTextArea textarea {{
  background: {C['surface2']} !important; border: 1px solid {C['border']} !important;
  border-radius: 6px !important; color: {C['text']} !important;
  font-family: 'Inter', sans-serif !important; font-size: 13px !important;
}}
.stSelectbox div[data-baseweb="select"] > div {{
  background: {C['surface2']} !important; border: 1px solid {C['border']} !important;
  border-radius: 6px !important; color: {C['text']} !important;
}}

/* Slider track and thumb */
[data-testid="stSlider"] > div > div > div > div,
[data-testid="stSelectSlider"] > div > div > div > div {{
  background: {C['blue']} !important;
}}
[data-testid="stSlider"] [role="slider"],
[data-testid="stSelectSlider"] [role="slider"] {{
  background: {C['surface']} !important;
  border: 2.5px solid {C['blue']} !important;
  box-shadow: 0 0 0 3px {C['blue']}35 !important;
  width: 15px !important; height: 15px !important;
}}
[data-testid="stSlider"] > div > div > div:first-child,
[data-testid="stSelectSlider"] > div > div > div:first-child {{
  background: {C['border']} !important;
}}
[data-testid="stSlider"] .st-emotion-cache-1dp5vir,
[data-testid="stSelectSlider"] .st-emotion-cache-1dp5vir {{
  background: {C['blue']} !important;
}}

/* Toggle */
[data-testid="stToggle"] > label > div[data-checked="true"] {{
  background: {C['blue']} !important;
}}

/* DataFrames */
.stDataFrame {{ border-radius: 8px; overflow: hidden; border: 1px solid {C['border']}; }}

/* Download button */
.stDownloadButton > button {{
  font-family: 'Inter', sans-serif; font-weight: 600; font-size: 12px;
  border-radius: 6px; border: 1px solid {C['border']};
  background: {C['surface2']}; color: {C['muted']}; padding: 6px 16px;
}}

/* ── Custom HTML components ── */
.kpi-card {{
  background: {C['surface']};
  border: 1px solid {C['border']};
  border-radius: 10px;
  padding: 14px 16px 12px;
  position: relative; overflow: hidden;
  height: 100%;
}}
.kpi-card .kpi-bar {{
  position: absolute; top: 0; left: 0; width: 3px; height: 100%;
  border-radius: 10px 0 0 10px;
}}
.kpi-card .kpi-label {{
  font-size: 10.5px; font-weight: 600; letter-spacing: 0.1em;
  text-transform: uppercase; color: {C['muted']}; margin-bottom: 7px;
}}
.kpi-card .kpi-val {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 22px; font-weight: 600; color: {C['text']}; line-height: 1;
}}
.kpi-card .kpi-sub {{
  font-size: 11px; color: {C['muted']}; margin-top: 5px;
}}

.row-hdr {{
  display: flex; align-items: center; justify-content: space-between;
  margin: 4px 0 12px;
}}
.row-title {{
  font-size: 11px; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: {C['muted']};
}}

.pill {{
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px 4px 9px; border-radius: 20px;
  font-size: 12px; font-weight: 600; letter-spacing: 0.03em;
}}
.pill-dot {{
  width: 7px; height: 7px; border-radius: 50%;
  animation: blink 2s infinite;
}}
@keyframes blink {{
  0%,100% {{ opacity:1; transform:scale(1); }}
  50% {{ opacity:.4; transform:scale(1.4); }}
}}

.notice {{
  border-radius: 7px; padding: 10px 14px;
  font-size: 13px; font-weight: 500; border-left: 3px solid;
  margin-bottom: 10px;
}}
.n-info    {{ background:{C['blue']}12;   border-color:{C['blue']};   color:{C['blue']};   }}
.n-warn    {{ background:{C['yellow']}14; border-color:{C['yellow']}; color:{C['yellow']}; }}
.n-error   {{ background:{C['red']}12;    border-color:{C['red']};    color:{C['red']};    }}
.n-success {{ background:{C['green']}12;  border-color:{C['green']};  color:{C['green']};  }}

.mbar-track {{
  height: 5px; border-radius: 3px;
  background: {C['border']}; overflow: hidden; margin: 5px 0 14px;
}}
.mbar-fill {{ height: 100%; border-radius: 3px; }}

.sdiv {{ height:1px; background:{C['border']}; margin: 16px 0; }}

.card {{
  background: {C['surface']}; border: 1px solid {C['border']};
  border-radius: 10px; padding: 18px 20px; margin-bottom: 14px;
}}
.mono {{ font-family: 'IBM Plex Mono', monospace; font-size: 13px; line-height: 1.7; }}
.page-title {{ font-size: 20px; font-weight: 700; color: {C['text']}; letter-spacing: -0.02em; margin: 0; }}
.page-sub {{ font-size: 12.5px; color: {C['muted']}; margin: 2px 0 0; }}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────
API_BASE = "http://localhost:8010"
HEAL_LOG = "phase3_aiops/data/raw/healing_history.csv"

# ── Helpers ───────────────────────────────────────────────────
def get_json(route, fallback=None):
    try:
        r = requests.get(f"{API_BASE}{route}", timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception:
        return fallback if fallback is not None else {}

def post_json(route, payload):
    try:
        r = requests.post(f"{API_BASE}{route}", json=payload, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def check_api():
    try:
        requests.get(f"{API_BASE}/health", timeout=2)
        return True
    except Exception:
        return False

def load_logs():
    if os.path.exists(HEAL_LOG):
        try:
            return pd.read_csv(HEAL_LOG)
        except Exception:
            pass
    return pd.DataFrame()

def kpi(label, value, sub="", accent=None):
    a = accent or C['blue']
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-bar" style="background:{a}"></div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-val">{value}</div>
      {sub_html}
    </div>""", unsafe_allow_html=True)

def pill(label, color):
    st.markdown(f"""
    <span class="pill" style="background:{color}18; color:{color};">
      <span class="pill-dot" style="background:{color}"></span>{label}
    </span>""", unsafe_allow_html=True)

def notice(kind, msg):
    st.markdown(f'<div class="notice n-{kind}">{msg}</div>', unsafe_allow_html=True)

def hbar(pct, color):
    p = min(max(float(pct), 0.0), 1.0) * 100
    st.markdown(
        f'<div class="mbar-track"><div class="mbar-fill" style="width:{p:.1f}%;background:{color}"></div></div>',
        unsafe_allow_html=True,
    )

def row_title(title):
    st.markdown(f'<div class="row-hdr"><span class="row-title">{title}</span></div>', unsafe_allow_html=True)

def sdiv():
    st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)

def tcolor(val, warn, crit, invert=False):
    if invert:
        return C['red'] if val < crit else C['yellow'] if val < warn else C['green']
    return C['red'] if val >= crit else C['yellow'] if val >= warn else C['green']

# ── Fetch ─────────────────────────────────────────────────────
connected    = check_api()
status_data  = get_json("/status")
predict_data = get_json("/predict")
explain_data = get_json("/predict/explain")
runtime_data = get_json("/runtime")
services_data = get_json("/services", fallback=[])

metrics    = status_data.get("live_metrics", {})
controller = status_data.get("controller", {})
mode       = predict_data.get("mode", "UNKNOWN")
conf       = float(predict_data.get("confidence", 0))
pred_count = runtime_data.get("prediction_count", 0)
heal_count = runtime_data.get("heal_count", 0)
uptime_sec = runtime_data.get("uptime_seconds", 0)
high_risk_count = runtime_data.get("high_risk_count", 0)
incident_active = bool(controller.get("incident_active", False))

is_shadow    = mode == "SHADOW"
is_high_risk = mode == "HIGH_RISK"
is_normal    = not is_shadow and not is_high_risk and mode != "UNKNOWN"

shadow_service = (
    controller.get("last_action", "").split(":")[-1].strip()
    if controller.get("last_action") else ""
)
shadow_action = "restart_container"
shadow_ready  = is_shadow and bool(shadow_service)

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="page-title">AIOps</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Control Center</div>', unsafe_allow_html=True)
    sdiv()

    row_title("Connection")
    pill("API Connected" if connected else "API Unreachable",
         C['green'] if connected else C['red'])
    if not connected:
        st.markdown("<br>", unsafe_allow_html=True)
        notice("error", f"Cannot reach {API_BASE}")

    st.markdown("<br>", unsafe_allow_html=True)
    row_title("System Mode")
    pill(mode,
         C['yellow'] if is_shadow else C['red'] if is_high_risk else
         C['green'] if is_normal else C['muted'])

    sdiv()
    row_title("Appearance")
    if st.button("Switch to Light Mode" if dark else "Switch to Dark Mode",
                 use_container_width=True):
        st.session_state.dark_mode = not dark
        st.rerun()

    sdiv()
    row_title("Auto Refresh")
    st.session_state.refresh_enabled = st.toggle(
        "Live Refresh", value=st.session_state.refresh_enabled
    )
    if st.session_state.refresh_enabled:
        st.session_state.refresh_interval = st.select_slider(
            "Interval",
            options=[3, 5, 10, 15, 30],
            value=st.session_state.refresh_interval,
            format_func=lambda x: f"{x}s",
        )

    sdiv()
    st.markdown(
        f'<span style="font-family:\'IBM Plex Mono\',monospace;font-size:11px;color:{C["muted"]};">'
        f'Updated {datetime.now().strftime("%H:%M:%S")}</span>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Refresh Now", use_container_width=True):
        st.rerun()

# ── Page header ───────────────────────────────────────────────
hcol, bcol = st.columns([5, 1])
with hcol:
    st.markdown('<div class="page-title">Autonomous AIOps Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="page-sub">Observe &mdash; Predict &mdash; Reason &mdash; Act &mdash; Verify</div>',
        unsafe_allow_html=True,
    )
with bcol:
    if incident_active:
        notice("error", "INCIDENT ACTIVE")

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────
t1, t2, t3, t4, t5 = st.tabs([
    "Overview", "Live Metrics", "AI Reasoning", "Services", "Healing History"
])

# ═══════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ═══════════════════════════════════════════════
with t1:
    uptime_disp = str(timedelta(seconds=int(uptime_sec))) if uptime_sec else "N/A"

    row_title("Key Performance Indicators")
    cols = st.columns(5)
    tiles = [
        ("Mode",            mode if mode != "UNKNOWN" else "N/A",  "Operation mode",
         C['yellow'] if is_shadow else C['red'] if is_high_risk else C['green']),
        ("Confidence",      f"{conf:.1%}",                          "Prediction score",
         C['green'] if conf > 0.8 else C['yellow'] if conf > 0.5 else C['red']),
        ("Predictions",     f"{pred_count:,}",                      "Total predictions",   C['blue']),
        ("Healing Actions", f"{heal_count:,}",                      "Remediations run",    C['purple']),
        ("Uptime",          uptime_disp,                            "Since last restart",  C['green']),
    ]
    for col, (lbl, val, sub, ac) in zip(cols, tiles):
        with col:
            kpi(lbl, val, sub, ac)

    sdiv()
    row_title("Risk and Incident Summary")
    r1, r2, r3 = st.columns(3)
    with r1:
        kpi("High Risk Events", f"{high_risk_count:,}", "Total detections", C['red'])
    with r2:
        kpi("Incident Active",
            "YES" if incident_active else "NO",
            "Current status",
            C['red'] if incident_active else C['green'])
    with r3:
        kpi("API Status",
            "Online" if connected else "Offline",
            API_BASE, C['green'] if connected else C['red'])

    sdiv()

    # Inline confidence bar — no extra column waste
    conf_c = C['green'] if conf > 0.8 else C['yellow'] if conf > 0.5 else C['red']
    st.markdown(
        f'<div class="row-hdr">'
        f'<span class="row-title">Prediction Confidence</span>'
        f'<span style="font-family:\'IBM Plex Mono\',monospace;font-size:12px;color:{conf_c};">'
        f'{conf:.4f}</span></div>',
        unsafe_allow_html=True,
    )
    hbar(conf, conf_c)

    sdiv()
    row_title("Operator Decision Panel")

    if not is_shadow:
        notice("info", "No pending decisions — operator controls activate only in SHADOW mode.")
    elif not shadow_ready:
        notice("warn", "SHADOW MODE active. No service action queued — buttons disabled until a target service is resolved.")
    else:
        notice("warn",
            f"SHADOW MODE &mdash; Suggested: <strong>{shadow_action}</strong> on "
            f"<strong>{shadow_service}</strong> &nbsp;|&nbsp; Confidence: {conf:.1%}")

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("Approve Action",
                     disabled=not shadow_ready,
                     use_container_width=True,
                     type="primary" if shadow_ready else "secondary"):
            _, err = post_json("/shadow/approve", {
                "service": shadow_service, "action": shadow_action, "confidence": conf
            })
            notice("error" if err else "success",
                   f"Approval failed: {err}" if err else
                   f"Action executed on '{shadow_service}'.")
    with bc2:
        if st.button("Ignore Recommendation",
                     disabled=not shadow_ready,
                     use_container_width=True):
            _, err = post_json("/shadow/ignore", {
                "service": shadow_service, "action": shadow_action, "confidence": conf
            })
            notice("error" if err else "info",
                   f"Request failed: {err}" if err else
                   "Recommendation ignored. System continues monitoring.")

    if is_high_risk:
        notice("error", "HIGH RISK MODE — Autonomous remediation is active without operator approval.")
    elif is_normal:
        notice("success", "System operating normally. No action required.")

    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# TAB 2 — LIVE METRICS
# ═══════════════════════════════════════════════
with t2:
    cpu_val    = float(metrics.get("cpu", 0))
    mem_val    = float(metrics.get("memory", 0))
    lat_val    = float(metrics.get("latency", 0))
    err_val    = float(metrics.get("error_rate", 0))
    req_val    = float(metrics.get("request_rate", 0))
    svc_health = float(metrics.get("service_health", 0))

    if all(v == 0 for v in [cpu_val, mem_val, lat_val, err_val, req_val]):
        notice("info", "No live data available. Metrics appear once the API is reporting.")

    row_title("Infrastructure Metrics")
    m1, m2, m3 = st.columns(3)

    with m1:
        cpu_c = tcolor(cpu_val, 60, 85)
        kpi("CPU Usage", f"{cpu_val:.1f}%", "Warn >60%  Crit >85%", cpu_c)
        hbar(cpu_val / 100, cpu_c)

        mem_c = tcolor(mem_val, 60, 80)
        kpi("Memory", f"{int(mem_val)} MB", "Warn >60%  Crit >80%", mem_c)
        hbar(min(mem_val / 1024, 1.0), mem_c)

    with m2:
        lat_c = tcolor(lat_val, 200, 500)
        kpi("Latency", f"{lat_val:.1f} ms", "Warn >200ms  Crit >500ms", lat_c)
        hbar(min(lat_val / 1000, 1.0), lat_c)

        err_c = tcolor(err_val, 0.01, 0.05)
        kpi("Error Rate", f"{err_val:.4f}", "Warn >1%  Crit >5%", err_c)
        hbar(min(err_val / 0.1, 1.0), err_c)

    with m3:
        kpi("Request Rate", f"{req_val:.2f} /s", "Requests per second", C['blue'])

        sh_c = tcolor(svc_health, 0.9, 0.7, invert=True)
        kpi("Service Health", f"{svc_health:.4f}", "1.0 = fully healthy", sh_c)
        hbar(svc_health, sh_c)

    sdiv()
    row_title("Metric Status Summary")
    health_rows = [
        ("CPU Usage",      f"{cpu_val:.1f}%",       "CRITICAL" if cpu_val >= 85    else "WARNING" if cpu_val >= 60    else "OK"),
        ("Memory",         f"{int(mem_val)} MB",     "CRITICAL" if mem_val >= 80    else "WARNING" if mem_val >= 60    else "OK"),
        ("Latency",        f"{lat_val:.1f} ms",      "CRITICAL" if lat_val >= 500   else "WARNING" if lat_val >= 200   else "OK"),
        ("Error Rate",     f"{err_val:.4f}",         "CRITICAL" if err_val >= 0.05  else "WARNING" if err_val >= 0.01  else "OK"),
        ("Request Rate",   f"{req_val:.2f} /s",      "OK"),
        ("Service Health", f"{svc_health:.4f}",      "CRITICAL" if svc_health < 0.7 else "WARNING" if svc_health < 0.9 else "OK"),
    ]
    df_h = pd.DataFrame(health_rows, columns=["Metric", "Value", "Status"])

    def style_status(val):
        return (
            f"color:{C['red']};font-weight:700" if val == "CRITICAL" else
            f"color:{C['yellow']};font-weight:600" if val == "WARNING" else
            f"color:{C['green']}"
        )

    st.dataframe(
        df_h.style.applymap(style_status, subset=["Status"]),
        use_container_width=True, hide_index=True,
    )

# ═══════════════════════════════════════════════
# TAB 3 — AI REASONING
# ═══════════════════════════════════════════════
with t3:
    reason      = explain_data.get("reason", "")
    last_action = explain_data.get("last_action", "")

    if not reason and not last_action:
        notice("info", "No AI reasoning data yet. The /predict/explain endpoint is not returning data.")

    row_title("Decision Engine")
    re1, re2 = st.columns(2)

    with re1:
        st.markdown(f'<div class="row-title" style="margin-bottom:10px;">Prediction Reason</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="mono" style="color:{C["text"]}">'
            f'{reason or "No reason provided."}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with re2:
        st.markdown(f'<div class="row-title" style="margin-bottom:10px;">Last Executed Action</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="mono" style="color:{C["text"]}">'
            f'{last_action or "No action recorded."}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    if controller:
        sdiv()
        row_title("Controller State")
        ctrl_rows = [{"Field": k, "Value": str(v)} for k, v in controller.items()]
        st.dataframe(pd.DataFrame(ctrl_rows), use_container_width=True, hide_index=True)

    if explain_data:
        sdiv()
        row_title("Raw Explain Payload")
        st.json(explain_data, expanded=False)

# ═══════════════════════════════════════════════
# TAB 4 — SERVICES
# ═══════════════════════════════════════════════
with t4:
    row_title("Registered Services")

    if services_data:
        if isinstance(services_data, list):
            st.dataframe(pd.DataFrame(services_data), use_container_width=True, hide_index=True)
        else:
            st.json(services_data, expanded=False)
    else:
        notice("info", "No data from /services. Implement this endpoint to list registered services.")

    sdiv()
    row_title("Manual Remediation")

    if not connected:
        notice("error", "API unreachable — manual triggers disabled.")
    else:
        trigger_service = st.text_input("Target Service", placeholder="e.g. payment-service")
        trigger_action  = st.selectbox("Action", [
            "restart_container", "scale_up", "scale_down",
            "flush_cache", "reroute_traffic",
        ])
        trigger_reason = st.text_area("Notes (optional)", height=70,
                                      placeholder="Reason for manual action...")

        if st.button("Execute Action", type="primary"):
            if not trigger_service.strip():
                notice("warn", "Enter a target service name.")
            else:
                _, err = post_json("/manual/trigger", {
                    "service": trigger_service.strip(),
                    "action":  trigger_action,
                    "reason":  trigger_reason,
                })
                notice(
                    "error" if err else "success",
                    f"Trigger failed: {err}" if err else
                    f"'{trigger_action}' triggered on '{trigger_service.strip()}'."
                )

    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# TAB 5 — HEALING HISTORY
# ═══════════════════════════════════════════════
with t5:
    logs = load_logs()

    if logs.empty:
        notice("info",
            f"No healing logs at {HEAL_LOG}. Events appear here after autonomous remediations.")
    else:
        cols_lower = [c.lower() for c in logs.columns]
        total = len(logs)

        row_title("Log Summary")
        s1, s2, s3 = st.columns(3)
        with s1:
            kpi("Total Events", f"{total:,}", "All records", C['blue'])
        with s2:
            if "status" in cols_lower:
                sc = logs.columns[cols_lower.index("status")]
                ok = logs[sc].str.lower().str.contains("success", na=False).sum()
                kpi("Successful", f"{ok:,}", "Resolved", C['green'])
            else:
                kpi("Successful", "N/A", "", C['green'])
        with s3:
            if "status" in cols_lower:
                sc = logs.columns[cols_lower.index("status")]
                fail = logs[sc].str.lower().str.contains("fail", na=False).sum()
                kpi("Failed", f"{fail:,}", "Failed remediations", C['red'])
            else:
                kpi("Failed", "N/A", "", C['red'])

        sdiv()

        # Filters side by side — no wasted empty columns
        f1, f2 = st.columns(2)
        with f1:
            row_limit = st.select_slider(
                "Rows to show",
                options=[10, 20, 50, 100, 500],
                value=20,
                format_func=lambda x: f"{x} rows",
            )
        with f2:
            if "status" in cols_lower:
                sc = logs.columns[cols_lower.index("status")]
                statuses = ["All"] + sorted(logs[sc].dropna().unique().tolist())
                filter_status = st.selectbox("Filter by Status", statuses)
            else:
                filter_status = "All"

        filtered = logs.copy()
        if filter_status != "All" and "status" in cols_lower:
            sc = logs.columns[cols_lower.index("status")]
            filtered = filtered[filtered[sc] == filter_status]

        st.dataframe(filtered.tail(row_limit), use_container_width=True, hide_index=True)

        st.download_button(
            "Export as CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"healing_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

# ── Footer ────────────────────────────────────────────────────
st.markdown(
    f'<div style="text-align:center;color:{C["muted"]};font-size:11px;'
    f'border-top:1px solid {C["border"]};padding-top:14px;margin-top:10px;">'
    f'Phase 3 &mdash; Autonomous Failure Prediction and Self-Healing Platform'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Auto-refresh ──────────────────────────────────────────────
if st.session_state.refresh_enabled:
    time.sleep(st.session_state.refresh_interval)
    st.rerun()