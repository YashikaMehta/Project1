"""Multimodal Construction Intelligence Platform - Skill Wallet Capstone Project 1
Run: streamlit run app.py
"""
import json
import urllib.parse

import streamlit as st
from PIL import Image

try:
    from google import genai
    from google.genai import types
    GENAI_OK = True
except Exception:  # library missing -> demo mode only
    GENAI_OK = False

MODEL = "gemini-2.5-flash"

st.set_page_config(page_title="Construction Intelligence Platform", page_icon="🏗️", layout="wide")

# ---------------------------------------------------------------- styling
st.markdown("""
<style>
.hero{background:linear-gradient(120deg,#0f2027,#203a43,#2c5364);padding:1.4rem 1.8rem;border-radius:14px;color:#fff;margin-bottom:1rem}
.hero h1{margin:0;font-size:1.9rem}.hero p{margin:.3rem 0 0;opacity:.85}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:1rem 1.2rem;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.card .v{font-size:1.7rem;font-weight:700;color:#0f172a}.card .l{font-size:.8rem;color:#64748b;text-transform:uppercase;letter-spacing:.05em}
.pill{display:inline-block;padding:.2rem .75rem;border-radius:999px;font-weight:600;font-size:.82rem;color:#fff}
.green{background:#16a34a}.amber{background:#d97706}.orange{background:#ea580c}.red{background:#dc2626}.grey{background:#64748b}
.alert{border-left:6px solid;padding:.8rem 1rem;border-radius:8px;margin:.5rem 0;background:#f8fafc;color:#0f172a}
</style>""", unsafe_allow_html=True)

SEV_COLOR = {"low": "green", "medium": "amber", "high": "orange", "critical": "red"}


def pill(text, color=None):
    color = color or SEV_COLOR.get(str(text).lower(), "grey")
    return f'<span class="pill {color}">{text}</span>'


def card(label, value):
    return f'<div class="card"><div class="v">{value}</div><div class="l">{label}</div></div>'


def inr(v):
    """Format rupees as Lakhs / Crores."""
    return f"₹{v/1e7:,.2f} Cr" if v >= 1e7 else f"₹{v/1e5:,.2f} L"


# ---------------------------------------------------------------- Gemini helpers
def get_client():
    key = st.session_state.get("api_key", "").strip()
    if key and GENAI_OK:
        return genai.Client(api_key=key)
    return None


def analyze_image(prompt, image, demo):
    """Run a multimodal JSON analysis; fall back to demo data on any failure."""
    client = get_client()
    if client is None:
        st.info("🧪 Demonstration mode - showing sample output (add a Gemini API key for live analysis).")
        return demo
    try:
        resp = client.models.generate_content(
            model=MODEL, contents=[prompt, image],
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
        return json.loads(resp.text)
    except Exception as e:
        st.error(f"Gemini request failed ({type(e).__name__}): {e}. Showing demo output instead.")
        return demo


def chat_reply(history, system):
    client = get_client()
    if client is None:
        return ("🧪 *Demo mode:* For live answers add a Gemini API key in the sidebar. "
                "Meanwhile: always verify with the structural engineer of record, follow IS 456 for "
                "concrete (min. M20 for RCC), and maintain 7 days of curing for OPC.")
    try:
        contents = [types.Content(role="user" if m["role"] == "user" else "model",
                                  parts=[types.Part.from_text(text=m["content"])]) for m in history]
        resp = client.models.generate_content(
            model=MODEL, contents=contents,
            config=types.GenerateContentConfig(system_instruction=system, temperature=0.4))
        return resp.text
    except Exception as e:
        return f"⚠️ Assistant error ({type(e).__name__}): {e}"


def load_image(file):
    try:
        img = Image.open(file).convert("RGB")
        img.thumbnail((1600, 1600))
        return img
    except Exception as e:
        st.error(f"Could not read image: {e}")
        return None


# ---------------------------------------------------------------- prompts & demo data
PPE_PROMPT = """You are a certified construction safety officer. Analyze this construction site photo for worker PPE
compliance (hard helmet, high-visibility vest, steel-toe boots, safety harness) and site hazards under OSHA 1926 and
relevant Indian standards (IS 456 for concrete works, IS 3696 for scaffolding). Return ONLY JSON:
{"safety_score": int 0-100, "overall_status": "Compliant|Needs Improvement|Non-Compliant",
 "workers_detected": int,
 "ppe_detection": {"helmet": {"detected": bool, "note": str}, "high_vis_vest": {...}, "steel_toe_boots": {...}, "safety_harness": {...}},
 "hazards": [{"hazard": str, "severity": "Low|Medium|High|Critical", "remedy": str}],
 "summary": str}"""

PPE_DEMO = {
    "safety_score": 62, "overall_status": "Needs Improvement", "workers_detected": 3,
    "ppe_detection": {
        "helmet": {"detected": True, "note": "2 of 3 workers wearing helmets"},
        "high_vis_vest": {"detected": True, "note": "All workers visible in vests"},
        "steel_toe_boots": {"detected": False, "note": "Footwear not verifiable / sneakers observed"},
        "safety_harness": {"detected": False, "note": "No harness while working at height"}},
    "hazards": [
        {"hazard": "Worker at height without fall arrest", "severity": "Critical", "remedy": "Stop work; install guardrails and provide full-body harness anchored to a rated point (OSHA 1926.502)."},
        {"hazard": "Unsecured scaffold planks", "severity": "High", "remedy": "Fully plank and tie scaffolding; inspect per IS 3696 before each shift."},
        {"hazard": "Loose rebar ends exposed", "severity": "Medium", "remedy": "Fit rebar caps on all protruding bars."},
        {"hazard": "Debris on walkways", "severity": "Low", "remedy": "Daily housekeeping and designated waste zones."}],
    "summary": "Partial PPE compliance with a critical fall-protection gap. Immediate corrective action required."}

CRACK_PROMPT = """You are a structural engineer. Analyze this concrete/wall surface photo. Classify the defect as one of:
Hairline, Settlement, Structural Shear, Thermal Expansion, Spalling. Return ONLY JSON:
{"defect_type": str, "confidence": float 0-1, "estimated_crack_width_mm": float, "pattern": str,
 "root_causes": [str], "recommended_repairs": [{"method": str, "detail": str}],
 "urgency": "Low|Medium|High|Critical", "monitoring_advice": str, "summary": str}
Reference IS 456 crack-width limits (0.3 mm typical limit for moderate exposure)."""

CRACK_DEMO = {
    "defect_type": "Settlement", "confidence": 0.78, "estimated_crack_width_mm": 2.5,
    "pattern": "Diagonal stair-step crack widening toward one corner",
    "root_causes": ["Differential foundation settlement", "Poor soil compaction / moisture variation", "Possible drainage leakage near footing"],
    "recommended_repairs": [
        {"method": "Epoxy injection", "detail": "Clean crack, install ports, inject low-viscosity epoxy after settlement has stabilised."},
        {"method": "Structural re-grouting", "detail": "Pressure-grout underpinning voids; consider micro-piles if movement continues."}],
    "urgency": "High", "monitoring_advice": "Install tell-tale crack gauges and log readings weekly for 8 weeks.",
    "summary": "Likely settlement-induced crack exceeding IS 456 serviceability limits; needs engineering inspection."}

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("🏗️ CIP Control Panel")
    st.session_state["api_key"] = st.text_input("Google Gemini API Key", type="password",
                                                help="Leave empty to use demonstration mode.")
    live = bool(st.session_state["api_key"].strip()) and GENAI_OK
    st.markdown(pill("LIVE MODE" if live else "DEMO MODE", "green" if live else "amber"), unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("Architecture")
    st.markdown("""
- **UI:** Streamlit (single file, no DB)
- **Vision/LLM:** Gemini multimodal, JSON output
- **Calc engine:** rule-of-thumb cost model (Python)
- **Rendering:** Pollinations AI image URL
- **State:** `st.session_state` only
""")
    st.subheader("Navigation")
    st.markdown("1. Safety & PPE Audit\n2. Crack Diagnostics\n3. Planning & Valuation\n4. Site Assistant")
    st.caption("Skill Wallet Capstone · Project 1")

st.markdown('<div class="hero"><h1>🏗️ Multimodal Construction Intelligence Platform</h1>'
            '<p>AI-powered safety audits, structural diagnostics, valuation and daily site advisory</p></div>',
            unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🦺 Safety & PPE Audit", "🧱 Crack Diagnostics",
                                  "💰 Planning & Valuation", "🌦️ Site Assistant"])

# ---------------------------------------------------------------- Tab 1
with tab1:
    st.subheader("Site Safety & PPE Audit")
    up = st.file_uploader("Upload construction site photo", type=["jpg", "jpeg", "png"], key="ppe_up")
    if up:
        img = load_image(up)
        if img:
            c1, c2 = st.columns([1, 1.4])
            c1.image(img, caption="Uploaded site photo", use_container_width=True)
            if c2.button("🔍 Run Safety Audit", type="primary", key="ppe_btn"):
                with st.spinner("Analyzing site..."):
                    st.session_state["ppe"] = analyze_image(PPE_PROMPT, img, PPE_DEMO)
    r = st.session_state.get("ppe")
    if r:
        try:
            score = int(r.get("safety_score", 0))
            status = r.get("overall_status", "N/A")
            scol = "green" if score >= 80 else "amber" if score >= 60 else "red"
            m = st.columns(3)
            m[0].markdown(card("Safety Score", f"{score}/100"), unsafe_allow_html=True)
            m[1].markdown(card("Workers Detected", r.get("workers_detected", "-")), unsafe_allow_html=True)
            m[2].markdown(card("Status", pill(status, scol)), unsafe_allow_html=True)
            st.progress(min(max(score, 0), 100) / 100)
            st.write(r.get("summary", ""))
            st.markdown("##### PPE Checklist")
            for k, v in r.get("ppe_detection", {}).items():
                icon = "✅" if v.get("detected") else "❌"
                st.markdown(f"{icon} **{k.replace('_', ' ').title()}** - {v.get('note', '')}")
            st.markdown("##### Identified Hazards")
            for h in r.get("hazards", []):
                sev = h.get("severity", "Low")
                st.markdown(f'<div class="alert" style="border-color:var(--c)">{pill(sev)} <b>{h.get("hazard")}</b>'
                            f'<br>🛠️ {h.get("remedy")}</div>', unsafe_allow_html=True)
            st.download_button("⬇️ Download JSON report", json.dumps(r, indent=2),
                               "safety_report.json", "application/json")
        except Exception as e:
            st.error(f"Could not render report: {e}")
    elif not up:
        st.info("Upload a photo to begin. Demo mode works without an API key.")

# ---------------------------------------------------------------- Tab 2
with tab2:
    st.subheader("Crack Diagnostics & Structural Integrity")
    up2 = st.file_uploader("Upload concrete / wall surface photo", type=["jpg", "jpeg", "png"], key="crack_up")
    if up2:
        img2 = load_image(up2)
        if img2:
            c1, c2 = st.columns([1, 1.4])
            c1.image(img2, caption="Surface under inspection", use_container_width=True)
            if c2.button("🔬 Diagnose Defect", type="primary", key="crack_btn"):
                with st.spinner("Diagnosing..."):
                    st.session_state["crack"] = analyze_image(CRACK_PROMPT, img2, CRACK_DEMO)
    d = st.session_state.get("crack")
    if d:
        try:
            m = st.columns(4)
            m[0].markdown(card("Defect Type", d.get("defect_type", "-")), unsafe_allow_html=True)
            m[1].markdown(card("Crack Width", f'{d.get("estimated_crack_width_mm", "-")} mm'), unsafe_allow_html=True)
            m[2].markdown(card("Confidence", f'{float(d.get("confidence", 0)) * 100:.0f}%'), unsafe_allow_html=True)
            m[3].markdown(card("Urgency", pill(d.get("urgency", "Low"))), unsafe_allow_html=True)
            st.write(f"**Pattern:** {d.get('pattern', '-')}")
            st.write(d.get("summary", ""))
            a, b = st.columns(2)
            with a:
                st.markdown("##### Root Causes")
                for c in d.get("root_causes", []):
                    st.markdown(f"- {c}")
            with b:
                st.markdown("##### Recommended Repairs")
                for rp in d.get("recommended_repairs", []):
                    st.markdown(f"- **{rp.get('method')}** - {rp.get('detail')}")
            st.info(f"📈 Monitoring: {d.get('monitoring_advice', '-')}")
            st.download_button("⬇️ Download JSON report", json.dumps(d, indent=2),
                               "crack_report.json", "application/json")
        except Exception as e:
            st.error(f"Could not render diagnosis: {e}")
    elif not up2:
        st.info("Upload a surface photo to classify cracks and get repair guidance.")

# ---------------------------------------------------------------- Tab 3
COST_SQFT = {"Residential (RCC)": 2000, "Commercial": 2800, "Industrial": 1800, "Luxury Villa": 3800}
TIER_MULT = {"Tier 1 (Mumbai, Delhi, Bengaluru)": 1.25, "Tier 2 (Indore, Pune, Jaipur)": 1.0,
             "Tier 3 (Smaller cities)": 0.8}
MARKET_SQFT = {"Tier 1": 9000, "Tier 2": 5000, "Tier 3": 3000}  # market value per sqft (INR)
STAGES = [(10, "Site prep & excavation"), (25, "Foundation"), (45, "Superstructure / columns & slabs"),
          (65, "Masonry & roofing"), (85, "MEP & plastering"), (100, "Finishing & handover")]

with tab3:
    st.subheader("Planning & Real Estate Valuation")
    c1, c2 = st.columns(2)
    stype = c1.selectbox("Structure type", list(COST_SQFT))
    tier = c2.selectbox("Location tier", list(TIER_MULT))
    sqft = c1.number_input("Built-up area (sq ft)", 200, 500000, 2000, step=100)
    pct = c2.slider("Completion %", 0, 100, 40)

    budget = sqft * COST_SQFT[stype] * TIER_MULT[tier]
    capex = budget * pct / 100
    market_rate = MARKET_SQFT[tier.split()[0] + " " + tier.split()[1]] * (1.3 if stype == "Luxury Villa" else 1)
    # asset value: land+structure market value scaled by completion (min 30% land share)
    full_value = sqft * market_rate
    asset = full_value * (0.3 + 0.7 * pct / 100)
    steel_kg = sqft * 4.0
    cement_bags = sqft * 0.4

    m = st.columns(4)
    m[0].markdown(card("Total Budget", inr(budget)), unsafe_allow_html=True)
    m[1].markdown(card("CapEx Incurred", inr(capex)), unsafe_allow_html=True)
    m[2].markdown(card("Current Asset Value", inr(asset)), unsafe_allow_html=True)
    m[3].markdown(card("Projected Value @100%", inr(full_value)), unsafe_allow_html=True)
    m = st.columns(2)
    m[0].markdown(card("Steel Required", f"{steel_kg/1000:,.1f} tonnes"), unsafe_allow_html=True)
    m[1].markdown(card("Cement Required", f"{cement_bags:,.0f} bags (50 kg)"), unsafe_allow_html=True)
    st.caption("Estimates use rule-of-thumb rates (steel ≈ 4 kg/sq ft, cement ≈ 0.4 bags/sq ft). Verify with a quantity surveyor.")

    st.markdown("##### Milestone Progress")
    st.progress(pct / 100)
    stage = next(n for lim, n in STAGES if pct <= lim)
    st.write(f"Current stage: **{stage}**")

    st.markdown("##### 🎨 Conceptual 3D Rendering (Pollinations AI)")
    style = st.text_input("Architectural style", "modern minimalist with large glass facade")
    prompt = (f"photorealistic 3D architectural rendering of a {stype.lower()} building, {int(sqft)} sq ft, "
              f"{style}, Indian context, golden hour, ultra detailed")
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) + "?width=1024&height=640&nologo=true"
    if st.button("Generate rendering", key="render_btn"):
        st.session_state["render_url"] = url
    if st.session_state.get("render_url"):
        st.image(st.session_state["render_url"], caption="AI concept render (illustrative only)",
                 use_container_width=True)
    with st.expander("Image prompt"):
        st.code(prompt)

# ---------------------------------------------------------------- Tab 4
WEATHER = {
    "Normal": ("green", ["✅ Standard operations permitted.", "Continue routine PPE and toolbox talk.",
                         "Maintain concrete curing: keep surfaces moist for 7+ days (IS 456)."]),
    "High Wind": ("red", ["🚫 Suspend crane and hoisting operations above wind speeds of ~35 km/h.",
                          "Secure loose materials, formwork sheets and scaffolding sheeting.",
                          "Halt work at height; check scaffold ties after the event."]),
    "Heavy Rain": ("orange", ["⚡ Electrical hazard: de-energise temporary power, check earthing and RCCBs.",
                              "Cover fresh concrete; avoid pouring during downpour.",
                              "Pump out excavations; inspect shoring for soil collapse risk.",
                              "Anti-slip measures on ramps and walkways."]),
    "Extreme Heat": ("amber", ["🌡️ Schedule heavy work before 11 AM / after 4 PM; enforce hydration and shaded rest breaks.",
                               "Concrete curing protocol: pour at night/early morning, use chilled water or ice, "
                               "wet-cure with hessian and begin curing immediately to limit plastic shrinkage cracks.",
                               "Monitor workers for heat-stroke symptoms."]),
}

with tab4:
    st.subheader("Daily Site Assistant & Weather-Aware Advisory")
    w = st.selectbox("Today's weather condition", list(WEATHER), key="weather")
    col, items = WEATHER[w]
    html = "".join(f"<li>{i}</li>" for i in items)
    st.markdown(f'<div class="alert" style="border-color:{ {"green":"#16a34a","red":"#dc2626","orange":"#ea580c","amber":"#d97706"}[col] }">'
                f'{pill(w, col)}<ul style="margin:.5rem 0 0">{html}</ul></div>', unsafe_allow_html=True)

    st.markdown("##### 💬 Construction Engineering Assistant")
    if "chat" not in st.session_state:
        st.session_state["chat"] = [{"role": "assistant",
            "content": "Hello! I'm your site engineering assistant. Ask about concrete mix, curing, safety, scheduling or materials."}]
    for msg in st.session_state["chat"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    if q := st.chat_input("Ask a construction question..."):
        st.session_state["chat"].append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        system = (f"You are an expert Indian civil/construction engineer assistant. Current weather on site: {w}. "
                  "Give concise, practical, standards-aware (IS codes, OSHA) answers and recommend consulting "
                  "a licensed engineer for structural decisions.")
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                ans = chat_reply(st.session_state["chat"], system)
            st.markdown(ans)
        st.session_state["chat"].append({"role": "assistant", "content": ans})
    if st.button("🗑️ Clear chat"):
        st.session_state.pop("chat", None)
        st.rerun()
