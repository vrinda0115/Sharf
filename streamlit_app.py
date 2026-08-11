from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
import altair as alt


ROOT = Path(__file__).resolve().parent
FINAL_DIR = ROOT / "data" / "final"
MEMORY_PATH = ROOT / "data" / "app_memory.json"

PALETTE = {
    "abyss": "#092C56",
    "lapis": "#225688",
    "slate": "#668CA9",
    "glacier": "#A9CBE0",
    "quartz": "#F0F5F4",
    "ink": "#102033",
    "warn": "#B7791F",
    "danger": "#B42318",
    "ok": "#1F7A5A",
}

st.set_page_config(page_title="SHARF Founder Risk Cockpit", layout="wide")

DIMENSION_NAMES = [
    "Runway",
    "Revenue",
    "Retention",
    "Growth Efficiency",
    "Customer Sentiment",
    "Team Capacity",
    "Governance",
]


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    profiles = pd.read_csv(FINAL_DIR / "startup_profiles.csv")
    metrics = pd.read_csv(FINAL_DIR / "sharf_monthly_metrics.csv", parse_dates=["month"])
    forecast = pd.read_csv(FINAL_DIR / "monte_carlo_risk_forecast.csv", parse_dates=["forecast_start_month"])
    validation = pd.read_csv(FINAL_DIR / "validation_summary.csv")
    return profiles, metrics, forecast, validation


def load_memory() -> dict[str, object]:
    if not MEMORY_PATH.exists():
        return {"users": {}}
    try:
        return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"users": {}}


def save_memory(memory: dict[str, object]) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(json.dumps(memory, indent=2), encoding="utf-8")


def password_hash(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    _, candidate = password_hash(password, salt_hex)
    return hmac.compare_digest(candidate, digest_hex)


def ensure_user_record(username: str) -> dict[str, object]:
    memory = load_memory()
    users = memory.setdefault("users", {})
    user = users.setdefault(username, {"score_runs": [], "action_rows": []})
    save_memory(memory)
    return user


def persist_user_memory() -> None:
    username = st.session_state.get("authenticated_user")
    if not username:
        return
    memory = load_memory()
    users = memory.setdefault("users", {})
    user = users.setdefault(username, {})
    user["score_runs"] = st.session_state.get("score_runs", [])
    user["action_rows"] = st.session_state.get("action_rows", [])
    save_memory(memory)


def login_panel() -> None:
    inject_css()
    st.title("SHARF Founder Login")
    st.caption("Sign in to keep your monthly SHARF scores and action-plan notes saved on this computer.")
    tab_login, tab_register = st.tabs(["Login", "Create account"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username").strip().lower()
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            memory = load_memory()
            user = memory.get("users", {}).get(username)
            if user and verify_password(password, user["salt"], user["password_hash"]):
                st.session_state.authenticated_user = username
                st.session_state.score_runs = user.get("score_runs", [])
                st.session_state.action_rows = user.get("action_rows", [])
                st.success("Login successful. The app will open now.")
                st.rerun()
            else:
                st.error("That username or password did not match.")

    with tab_register:
        with st.form("register_form"):
            new_username = st.text_input("New username").strip().lower()
            new_password = st.text_input("New password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            registered = st.form_submit_button("Create account", use_container_width=True)
        if registered:
            memory = load_memory()
            users = memory.setdefault("users", {})
            if not new_username:
                st.error("Enter a username.")
            elif new_username in users:
                st.error("That username already exists.")
            elif len(new_password) < 4:
                st.error("Use at least 4 characters for this prototype password.")
            elif new_password != confirm_password:
                st.error("The two passwords do not match.")
            else:
                salt, digest = password_hash(new_password)
                users[new_username] = {
                    "salt": salt,
                    "password_hash": digest,
                    "score_runs": [],
                    "action_rows": [],
                }
                save_memory(memory)
                st.session_state.authenticated_user = new_username
                st.session_state.score_runs = []
                st.session_state.action_rows = []
                st.success("Account created. The app will open now.")
                st.rerun()


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {PALETTE["quartz"]};
            color: {PALETTE["ink"]};
        }}
        [data-testid="stSidebar"] {{
            background: {PALETTE["abyss"]};
        }}
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] > div > div > div > div > label,
        [data-testid="stSidebar"] .stSelectbox > label,
        [data-testid="stSidebar"] .stSelectbox > label *,
        [data-testid="stSidebar"] .stRadio > label,
        [data-testid="stSidebar"] .stRadio > label *,
        [data-testid="stSidebar"] .stRadio label,
        [data-testid="stSidebar"] .stRadio p {{
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            background-color: transparent !important;
        }}
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span {{
            color: inherit;
        }}
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea,
        [data-testid="stSidebar"] select,
        [data-testid="stSidebar"] [data-baseweb="select"],
        [data-testid="stSidebar"] [data-baseweb="select"] *,
        [data-testid="stSidebar"] [data-baseweb="input"],
        [data-testid="stSidebar"] [data-baseweb="input"] * {{
            color: {PALETTE["ink"]} !important;
            background-color: #FFFFFF !important;
            -webkit-text-fill-color: {PALETTE["ink"]} !important;
        }}
        [data-testid="stSidebar"] [data-baseweb="select"] svg {{
            fill: {PALETTE["ink"]} !important;
            color: {PALETTE["ink"]} !important;
            background-color: transparent !important;
        }}
        h1, h2, h3 {{
            color: {PALETTE["abyss"]};
            letter-spacing: 0;
        }}
        p, li, label, span, div {{
            color: {PALETTE["ink"]};
        }}
        input, textarea, select {{
            color: {PALETTE["ink"]} !important;
            background-color: #FFFFFF !important;
            -webkit-text-fill-color: {PALETTE["ink"]} !important;
        }}
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="select"] div,
        [data-baseweb="select"] span,
        [data-baseweb="select"] input {{
            color: {PALETTE["ink"]} !important;
            -webkit-text-fill-color: {PALETTE["ink"]} !important;
        }}
        [data-baseweb="popover"],
        [data-baseweb="popover"] *,
        [role="listbox"],
        [role="listbox"] *,
        [role="option"],
        [role="option"] * {{
            color: {PALETTE["ink"]} !important;
            background-color: #FFFFFF !important;
            -webkit-text-fill-color: {PALETTE["ink"]} !important;
        }}
        [role="option"]:hover,
        [role="option"][aria-selected="true"] {{
            background-color: {PALETTE["glacier"]} !important;
            color: {PALETTE["abyss"]} !important;
        }}
        [data-testid="stMarkdownContainer"] {{
            color: {PALETTE["ink"]};
        }}
        [data-testid="stDataFrame"],
        [data-testid="stDataFrame"] * {{
            color: {PALETTE["ink"]} !important;
        }}
        [data-testid="stAlert"],
        [data-testid="stAlert"] *,
        [data-testid="stNotification"],
        [data-testid="stNotification"] * {{
            color: {PALETTE["ink"]} !important;
        }}
        .stButton button,
        [data-testid="stFormSubmitButton"] button {{
            background-color: {PALETTE["lapis"]} !important;
            color: #FFFFFF !important;
            border: 1px solid {PALETTE["abyss"]} !important;
            border-radius: 8px !important;
        }}
        .stButton button *,
        [data-testid="stFormSubmitButton"] button * {{
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
        }}
        .block-container {{
            padding-top: 2rem;
        }}
        div[data-testid="stMetric"] {{
            background: white;
            border: 1px solid {PALETTE["glacier"]};
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 12px 30px rgba(9, 44, 86, 0.08);
        }}
        div[data-testid="stMetric"] * {{
            color: {PALETTE["ink"]} !important;
        }}
        .sharf-card {{
            background: white;
            border: 1px solid {PALETTE["glacier"]};
            border-radius: 8px;
            padding: 18px;
            box-shadow: 0 12px 30px rgba(9, 44, 86, 0.08);
            min-height: 120px;
            color: {PALETTE["ink"]};
        }}
        .sharf-card *,
        .option-card *,
        .purpose *,
        .why-box *,
        .explain-box * {{
            color: {PALETTE["ink"]} !important;
        }}
        .purpose {{
            background: {PALETTE["glacier"]};
            border: 1px solid {PALETTE["slate"]};
            border-radius: 8px;
            padding: 14px 18px;
            color: {PALETTE["abyss"]};
            font-weight: 700;
        }}
        .risk-pill {{
            display: inline-block;
            border-radius: 999px;
            padding: 7px 12px;
            font-weight: 800;
            background: {PALETTE["glacier"]};
            color: {PALETTE["abyss"]};
        }}
        .option-card {{
            background: white;
            border: 1px solid {PALETTE["slate"]};
            border-radius: 8px;
            padding: 18px;
            min-height: 260px;
            color: {PALETTE["ink"]};
        }}
        .bar-shell {{
            background: #DDEAF2;
            border-radius: 999px;
            height: 18px;
            overflow: hidden;
            border: 1px solid {PALETTE["glacier"]};
        }}
        .bar-fill {{
            height: 100%;
            border-radius: 999px;
            background: {PALETTE["lapis"]};
        }}
        .why-box {{
            background: #EEF6FA;
            border-left: 5px solid {PALETTE["slate"]};
            padding: 10px 12px;
            border-radius: 6px;
            font-size: 0.95rem;
            color: {PALETTE["ink"]};
        }}
        .small-muted {{
            color: #496071;
            font-size: 0.92rem;
        }}
        .explain-box {{
            background: #FFFFFF;
            border: 1px solid {PALETTE["glacier"]};
            border-radius: 8px;
            padding: 16px;
            margin: 10px 0 18px 0;
            color: {PALETTE["ink"]};
        }}
        .data-box {{
            background: #EAF3F8;
            border: 1px solid {PALETTE["glacier"]};
            border-radius: 8px;
            padding: 14px;
            color: {PALETTE["abyss"]};
        }}
        .data-box,
        .data-box * {{
            color: {PALETTE["abyss"]} !important;
            -webkit-text-fill-color: {PALETTE["abyss"]} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def scaled(value: float, low: float, high: float, inverse: bool = False) -> float:
    score = clamp(100 * (value - low) / (high - low), 0, 100)
    return 100 - score if inverse else score


def risk_tier(score: float) -> str:
    if score < 50:
        return "Critical"
    if score < 70:
        return "Watch"
    return "Stable"


def score_inputs(values: dict[str, float], previous_revenue: float) -> dict[str, object]:
    runway = values["cash_balance_usd"] / max(values["monthly_burn_usd"], 1)
    mom_growth = values["mom_revenue_growth"]
    if mom_growth is None:
        mom_growth = (values["monthly_revenue_usd"] - previous_revenue) / previous_revenue if previous_revenue > 0 else 0

    scores = {
        "Runway": scaled(runway, 3, 18),
        "Revenue": scaled(mom_growth, -0.08, 0.16),
        "Retention": scaled(values["monthly_churn_rate"], 0, 0.12, inverse=True),
        "Growth Efficiency": scaled(values["cac_payback_months"], 3, 24, inverse=True),
        "Customer Sentiment": scaled(values["nps"], -20, 70),
        "Team Capacity": scaled(values["avg_time_to_fill_days"], 20, 90, inverse=True),
        "Governance": values["governance_score"],
    }
    weights = {
        "Runway": 0.24,
        "Revenue": 0.18,
        "Retention": 0.16,
        "Growth Efficiency": 0.14,
        "Customer Sentiment": 0.10,
        "Team Capacity": 0.08,
        "Governance": 0.10,
    }
    score = sum(scores[name] * weight for name, weight in weights.items())
    weakest = min(scores.items(), key=lambda item: item[1])[0]
    return {
        "runway_months": round(runway, 1),
        "mom_revenue_growth": mom_growth,
        "dimension_scores": {name: round(value, 1) for name, value in scores.items()},
        "sharf_score": round(score, 1),
        "risk_tier": risk_tier(score),
        "weakest_dimension": weakest,
    }


def burn_sentence(runway: float, growth: float) -> str:
    if runway < 6:
        return "Your runway is under six months, so the safest move is to reduce spending now and protect cash."
    if runway < 12 or growth < 0:
        return "Your runway or growth is not strong enough yet, so keep spending tight and review cash every month."
    return "Your runway is in a healthier range, so you can maintain the current plan while watching growth and churn."


def fundraising_sentence(score: float, runway: float, churn: float) -> str:
    if score >= 75 and runway >= 12 and churn <= 0.06:
        return "You look ready to prepare investor outreach because the health score, runway, and churn are all in a stronger range."
    if score >= 60 and runway >= 6:
        return "You can prepare fundraising materials, but you should fix the weakest area before pushing hard for investor meetings."
    return "You should delay fundraising outreach for now and focus on fixing the biggest operating risk first."


def risk_reason(result: dict[str, object], values: dict[str, float]) -> str:
    score = float(result["sharf_score"])
    runway = float(result["runway_months"])
    weakest = str(result["weakest_dimension"])
    churn = values["monthly_churn_rate"]
    if score < 50:
        return f"The startup is in the Critical range because the overall score is low and the weakest area is {weakest.lower()}. In simple terms, the company should focus on survival and fixing the biggest blocker before taking on new risk."
    if score < 70:
        return f"The startup is in the Watch range. It is not automatically in trouble, but {weakest.lower()} is pulling down the score and should be reviewed in the next 30 days."
    return f"The startup is in the Stable range. The company looks healthier overall, but it should still monitor {weakest.lower()}, runway of {runway:.1f} months, and churn of {churn * 100:.1f}%."


def improvement_sentence(score_change: float, runway_change: float, growth_change: float, churn_change: float) -> str:
    if score_change >= 3 and runway_change >= 0:
        return "Yes, the startup appears to be improving because the health score increased and runway did not get worse."
    if score_change <= -3 or runway_change < -1.5:
        return "No, the startup appears to be getting riskier because the health score or runway moved in the wrong direction."
    if growth_change > 0 and churn_change <= 0:
        return "Review, but there are positive signs because growth improved and churn did not rise."
    return "Review. The startup looks mostly steady, so one more month of data would make the trend clearer."


def trend_summary(df: pd.DataFrame) -> dict[str, object]:
    df = df.sort_values("run_date")
    first = df.iloc[0]
    last = df.iloc[-1]
    score_change = round(float(last["sharf_score"]) - float(first["sharf_score"]), 1)
    best = df.loc[df["sharf_score"].idxmax()]
    worst = df.loc[df["sharf_score"].idxmin()]
    if score_change >= 5:
        direction = "improving"
    elif score_change <= -5:
        direction = "declining"
    else:
        direction = "roughly stable"
    return {
        "months_logged": len(df),
        "first_date": first["run_date"],
        "first_score": first["sharf_score"],
        "last_date": last["run_date"],
        "last_score": last["sharf_score"],
        "score_change": score_change,
        "avg_score": round(float(df["sharf_score"].mean()), 1),
        "best_date": best["run_date"],
        "best_score": best["sharf_score"],
        "worst_date": worst["run_date"],
        "worst_score": worst["sharf_score"],
        "volatility": round(float(df["sharf_score"].std(ddof=0)), 1) if len(df) > 1 else 0.0,
        "direction": direction,
        "latest_tier": last["risk_tier"],
        "latest_weakest": last["weakest_dimension"],
    }


def trend_recommendation(summary: dict[str, object]) -> str:
    direction = summary["direction"]
    tier = summary["latest_tier"]
    weakest = str(summary["latest_weakest"]).lower()
    if direction == "improving" and tier == "Stable":
        return f"The trend is positive and the startup is now in the Stable range. Keep the current plan, but keep watching {weakest} since it is still the weakest area."
    if direction == "improving":
        return f"The trend is positive, but the startup has not reached the Stable range yet. Keep the current plan and prioritize {weakest} to push the score higher."
    if direction == "declining" and tier == "Critical":
        return f"The trend is negative and the startup is now in the Critical range. Conserve cash immediately and fix {weakest} before taking on any new spending decisions."
    if direction == "declining":
        return f"The trend is negative. Before it becomes urgent, review spending this month and address {weakest} in the next 30 days."
    return f"The score has been roughly stable over the logged months. Use this steady period to proactively improve {weakest} rather than waiting for a downturn."


def get_startup_actions(startup_name: str) -> pd.DataFrame:
    """Action plan rows belonging to this startup. Older rows saved before the Startup
    field existed are treated as belonging to whichever startup is currently selected,
    so existing data isn't silently dropped from the analysis."""
    rows = st.session_state.get("action_rows", [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if "Startup" in df.columns:
        df = df[df["Startup"].fillna(startup_name) == startup_name]
    return df


def action_impact_table(startup_runs: pd.DataFrame, startup_name: str) -> pd.DataFrame:
    """For each action logged for this startup, find the SHARF score at the closest run
    before (or at) the action's date, and the score at the next run after it, so the
    change can be attributed to that specific decision."""
    actions = get_startup_actions(startup_name)
    if actions.empty:
        return pd.DataFrame()

    actions = actions.copy()
    date_source = actions["Logged Date"] if "Logged Date" in actions.columns else actions.get("Due Date")
    actions["_event_date"] = pd.to_datetime(date_source, errors="coerce")
    actions = actions.dropna(subset=["_event_date"]).sort_values("_event_date")
    if actions.empty:
        return pd.DataFrame()

    records = []
    for _, action in actions.iterrows():
        event_date = action["_event_date"]
        prior = startup_runs[startup_runs["run_date"] <= event_date]
        after = startup_runs[startup_runs["run_date"] > event_date]
        before_score = float(prior.iloc[-1]["sharf_score"]) if not prior.empty else None
        before_label = prior.iloc[-1]["run_label"] if not prior.empty else None
        after_score = float(after.iloc[0]["sharf_score"]) if not after.empty else None
        after_label = after.iloc[0]["run_label"] if not after.empty else None
        anchor_label = before_label if before_label is not None else after_label
        if anchor_label is None:
            continue
        change = round(after_score - before_score, 1) if before_score is not None and after_score is not None else None
        if change is None:
            category = "Pending"
        elif change > 1:
            category = "Improved"
        elif change < -1:
            category = "Declined"
        else:
            category = "Neutral"
        records.append(
            {
                "Decision": action.get("Decision", ""),
                "Status": action.get("Status", ""),
                "Logged Date": event_date.date(),
                "Anchor Run": anchor_label,
                "Score Before": before_score,
                "Score After": after_score,
                "Score Change": change,
                "Self-Reported Outcome": action.get("Score Improved?", ""),
                "Outcome Category": category,
            }
        )
    return pd.DataFrame(records)


def action_impact_insight(impact_df: pd.DataFrame) -> str:
    valid = impact_df.dropna(subset=["Score Change"])
    if valid.empty:
        return (
            "None of the logged actions yet have both a scoring run before and after them, so there isn't "
            "enough data to compare statistically. Run scoring again after enough time has passed since the action."
        )
    agg = valid.groupby("Decision")["Score Change"].agg(["mean", "count"]).reset_index().sort_values("mean", ascending=False)
    if len(agg) == 1:
        row = agg.iloc[0]
        return (
            f"Across {int(row['count'])} logged action(s) categorized as '{row['Decision']}', the SHARF score changed "
            f"by an average of {row['mean']:+.1f} points afterward. Log actions with different decisions to compare which approach works best."
        )
    best = agg.iloc[0]
    worst = agg.iloc[-1]
    return (
        f"Comparing {len(valid)} action(s) with a score before and after: decisions logged as '{best['Decision']}' were "
        f"followed by the largest average score change ({best['mean']:+.1f} points, n={int(best['count'])}), while "
        f"'{worst['Decision']}' saw the smallest average change ({worst['mean']:+.1f} points, n={int(worst['count'])}). "
        "This is a simple before/after average, not a controlled experiment, so treat it as a starting point for reasoning about what worked rather than proof of cause and effect."
    )


def build_annotated_trend_chart(startup_runs: pd.DataFrame, impact_df: pd.DataFrame) -> alt.Chart:
    run_order = list(startup_runs["run_label"])
    line = (
        alt.Chart(startup_runs)
        .mark_line(point=alt.OverlayMarkDef(size=60, filled=True), color=PALETTE["lapis"])
        .encode(
            x=alt.X("run_label:N", sort=run_order, title="Run (order logged)"),
            y=alt.Y("sharf_score:Q", title="SHARF Score", scale=alt.Scale(domain=[0, 100])),
            tooltip=[alt.Tooltip("run_label:N", title="Run"), alt.Tooltip("sharf_score:Q", title="Score")],
        )
    )
    if impact_df.empty:
        return line.properties(height=380).interactive()

    outcome_domain = ["Improved", "Declined", "Neutral", "Pending"]
    outcome_range = [PALETTE["ok"], PALETTE["danger"], PALETTE["warn"], PALETTE["slate"]]
    rules = (
        alt.Chart(impact_df)
        .mark_rule(strokeDash=[5, 3], size=2, opacity=0.85)
        .encode(
            x=alt.X("Anchor Run:N", sort=run_order),
            color=alt.Color(
                "Outcome Category:N",
                scale=alt.Scale(domain=outcome_domain, range=outcome_range),
                legend=alt.Legend(title="Action outcome"),
            ),
            tooltip=[
                alt.Tooltip("Decision:N", title="Decision"),
                alt.Tooltip("Status:N", title="Status"),
                alt.Tooltip("Logged Date:N", title="Logged"),
                alt.Tooltip("Score Change:Q", title="Score change after"),
            ],
        )
    )
    return (line + rules).properties(height=380).interactive()


def page_trend_section(startup_name: str) -> None:
    st.subheader("Trend, Summary, and Recommendation")
    runs_df = pd.DataFrame(st.session_state.get("score_runs", []))
    if runs_df.empty:
        st.info("No scoring runs logged yet. Run scoring on Page 1 for at least two different months to see a trend.")
        return

    startup_runs = runs_df[runs_df["startup"] == startup_name].copy()
    if len(startup_runs) < 2:
        st.info(
            f"Only {len(startup_runs)} scoring run(s) logged for {startup_name}. "
            "Log at least two months (run scoring on Page 1 more than once, on different dates) to see a trend graph, summary, and recommendation."
        )
        return

    startup_runs["run_date"] = pd.to_datetime(startup_runs["run_date"])
    # Sort oldest -> newest by date, and for same-day runs preserve the order they were
    # originally logged in (score_runs is stored newest-first, so we reverse before sorting).
    startup_runs = startup_runs.iloc[::-1].sort_values("run_date", kind="stable").reset_index(drop=True)
    startup_runs["run_order"] = range(1, len(startup_runs) + 1)
    startup_runs["run_label"] = startup_runs["run_order"].astype(str) + " (" + startup_runs["run_date"].dt.strftime("%b %d, %Y") + ")"

    explain_box(
        "What is happening in this section?",
        "This chart and summary look across every logged scoring run for this startup, not just the latest one. "
        "The x-axis is the order the runs were logged in (labeled with the date), so multiple test runs on the same day "
        "still show up as separate points instead of stacking on top of each other. Dashed vertical lines mark when an "
        "action plan entry was logged, color-coded by whether the score improved, declined, or stayed flat afterward — "
        "hover over a line to see which decision it was and the resulting score change.",
    )

    impact_df = action_impact_table(startup_runs, startup_name)
    st.altair_chart(build_annotated_trend_chart(startup_runs, impact_df), use_container_width=True)

    summary = trend_summary(startup_runs)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Months logged", summary["months_logged"])
    c2.metric("Score change (first to latest)", summary["last_score"], delta=summary["score_change"])
    c3.metric("Average score", summary["avg_score"])
    c4.metric("Volatility (std dev)", summary["volatility"])

    st.markdown(
        f'<div class="sharf-card">'
        f'<p class="small-muted">Summary</p>'
        f"<p>Across {summary['months_logged']} logged runs for {startup_name}, the SHARF score moved from "
        f"{summary['first_score']} on {pd.to_datetime(summary['first_date']).date()} to {summary['last_score']} on "
        f"{pd.to_datetime(summary['last_date']).date()} ({'+' if summary['score_change'] >= 0 else ''}{summary['score_change']} points). "
        f"The best month was {pd.to_datetime(summary['best_date']).date()} at {summary['best_score']}, and the weakest month was "
        f"{pd.to_datetime(summary['worst_date']).date()} at {summary['worst_score']}. The overall trend is <strong>{summary['direction']}</strong>."
        f"</p></div>",
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        f'<div class="why-box"><strong>Recommendation:</strong> {trend_recommendation(summary)}</div>',
        unsafe_allow_html=True,
    )

    st.write("")
    with st.expander("Action Impact Analysis (statistical breakdown by decision)"):
        if impact_df.empty:
            st.info(
                "No action plan entries are tied to this startup with a usable date yet. Log a decision on the "
                "Log New Entry tab, and it will show up here compared against the score before and after."
            )
        else:
            display_df = impact_df.drop(columns=["Anchor Run", "Outcome Category"])
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            st.markdown(f'<div class="why-box">{action_impact_insight(impact_df)}</div>', unsafe_allow_html=True)

    with st.expander("Per-dimension trends (Runway, Retention, Churn, etc.)"):
        dim_records = []
        for _, run_row in startup_runs.iterrows():
            dims = run_row.get("dimension_scores")
            dims = dims if isinstance(dims, dict) else {}
            dim_records.append({name: dims.get(name) for name in DIMENSION_NAMES})
        dims_df = pd.DataFrame(dim_records)
        dims_df.index = startup_runs["run_label"]

        if dims_df.dropna(how="all").empty:
            st.info(
                "No per-dimension history is available yet. This shows up for runs logged after this feature was added — "
                "log a new scoring run on Page 1 to start tracking individual dimensions like churn (Retention) or runway over time."
            )
        else:
            default_dims = [str(summary["latest_weakest"])] if str(summary["latest_weakest"]) in DIMENSION_NAMES else DIMENSION_NAMES[:2]
            chosen_dims = st.multiselect(
                "Choose which dimensions to plot (defaults to the current weakest area)",
                DIMENSION_NAMES,
                default=default_dims,
            )
            if not chosen_dims:
                st.caption("Select at least one dimension above to see its trend.")
            else:
                st.line_chart(dims_df[chosen_dims], use_container_width=True)

                dim_notes = []
                for dim_name in chosen_dims:
                    series = dims_df[dim_name].dropna()
                    if len(series) < 2:
                        continue
                    change = round(float(series.iloc[-1]) - float(series.iloc[0]), 1)
                    if change >= 5:
                        dim_notes.append(f"**{dim_name}** is improving ({'+' if change >= 0 else ''}{change} points since the first logged run).")
                    elif change <= -5:
                        dim_notes.append(f"**{dim_name}** is declining ({change} points since the first logged run) — worth a closer look.")
                    else:
                        dim_notes.append(f"**{dim_name}** has stayed roughly flat ({'+' if change >= 0 else ''}{change} points since the first logged run).")
                if dim_notes:
                    st.markdown("  \n".join(dim_notes))


def require_scoring() -> bool:
    if "current_result" not in st.session_state:
        st.warning("Go to Page 1 and click Run scoring first.")
        return False
    return True


def explain_box(title: str, body: str) -> None:
    st.markdown(
        f'<div class="explain-box"><strong>{title}</strong><br>{body}</div>',
        unsafe_allow_html=True,
    )


def action_log_manager() -> None:
    """Action plan log table with the ability to edit or delete a single entry."""
    rows = st.session_state.get("action_rows", [])
    st.subheader("Action plan log")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if not rows:
        st.caption("No entries yet.")
        return

    with st.expander("Edit or delete an action plan entry"):
        options = [
            f"Entry {i + 1}: {row.get('Due Date', '')} — {row.get('Decision', '')} ({row.get('Status', '')})"
            for i, row in enumerate(rows)
        ]
        choice = st.selectbox("Select the entry", options, key="action_log_select")
        idx = options.index(choice)
        row = rows[idx]

        status_options = ["Not started", "In progress", "Done", "Review"]
        outcome_options = ["Yes", "No", "Review"]

        with st.form(f"edit_action_row_{idx}"):
            startup_input = st.text_input("Startup", row.get("Startup", ""))
            try:
                logged_default = pd.to_datetime(row.get("Logged Date", row.get("Due Date"))).date()
            except (TypeError, ValueError):
                logged_default = date.today()
            logged_date_input = st.date_input("Logged Date (when this action was actually taken)", logged_default)
            decision = st.text_input("Decision", row.get("Decision", ""))
            owner = st.text_input("Owner", row.get("Owner", ""))
            target = st.text_input("Metric Target", row.get("Metric Target", ""))
            try:
                due_default = pd.to_datetime(row.get("Due Date")).date()
            except (TypeError, ValueError):
                due_default = date.today()
            due = st.date_input("Due Date", due_default)
            status = st.selectbox(
                "Status", status_options,
                index=status_options.index(row["Status"]) if row.get("Status") in status_options else 0,
            )
            outcome = st.selectbox(
                "Score Improved?", outcome_options,
                index=outcome_options.index(row["Score Improved?"]) if row.get("Score Improved?") in outcome_options else 2,
            )
            notes = st.text_area("Outcome Notes", row.get("Outcome Notes", ""))

            save_col, delete_col = st.columns(2)
            save_clicked = save_col.form_submit_button("Save changes", use_container_width=True)
            delete_clicked = delete_col.form_submit_button("Delete this entry", use_container_width=True)

        if save_clicked:
            rows[idx] = {
                "Startup": startup_input,
                "Logged Date": str(logged_date_input),
                "Decision": decision,
                "Owner": owner,
                "Metric Target": target,
                "Due Date": str(due),
                "Status": status,
                "Outcome Notes": notes,
                "Score Improved?": outcome,
            }
            st.session_state.action_rows = rows
            persist_user_memory()
            st.success("Entry updated.")
            st.rerun()
        if delete_clicked:
            rows.pop(idx)
            st.session_state.action_rows = rows
            persist_user_memory()
            st.success("Entry deleted.")
            st.rerun()


def score_log_manager() -> None:
    """Saved score memory table with the ability to edit or delete a single logged run."""
    rows = st.session_state.get("score_runs", [])
    st.subheader("Saved score memory")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if not rows:
        st.caption("No entries yet.")
        return

    with st.expander("Edit or delete a saved score run"):
        options = [
            f"Entry {i + 1}: {row.get('run_date', '')} — {row.get('startup', '')}: {row.get('sharf_score', '')} ({row.get('risk_tier', '')})"
            for i, row in enumerate(rows)
        ]
        choice = st.selectbox("Select the entry", options, key="score_log_select")
        idx = options.index(choice)
        row = rows[idx]
        dims = row.get("dimension_scores") or {}

        risk_tier_options = ["Critical", "Watch", "Stable"]

        with st.form(f"edit_score_row_{idx}"):
            try:
                run_date_default = pd.to_datetime(row.get("run_date")).date()
            except (TypeError, ValueError):
                run_date_default = date.today()
            run_date_input = st.date_input("Run date", run_date_default)
            startup_input = st.text_input("Startup", row.get("startup", ""))
            sharf_score_input = st.number_input(
                "SHARF score", min_value=0.0, max_value=100.0, value=float(row.get("sharf_score", 0.0)), step=0.1
            )
            risk_tier_input = st.selectbox(
                "Risk tier", risk_tier_options,
                index=risk_tier_options.index(row["risk_tier"]) if row.get("risk_tier") in risk_tier_options else 1,
            )
            runway_input = st.number_input(
                "Runway months", min_value=0.0, value=float(row.get("runway_months", 0.0)), step=0.1
            )

            st.caption("Per-dimension scores (0-100). Only correct these if you know why the original run was wrong.")
            dim_inputs = {}
            dim_cols = st.columns(3)
            for i, dim_name in enumerate(DIMENSION_NAMES):
                dim_inputs[dim_name] = dim_cols[i % 3].number_input(
                    dim_name, min_value=0.0, max_value=100.0, value=float(dims.get(dim_name, 0.0)), step=0.1,
                    key=f"dim_edit_{dim_name}_{idx}",
                )

            weakest_input = st.selectbox(
                "Weakest dimension", DIMENSION_NAMES,
                index=DIMENSION_NAMES.index(row["weakest_dimension"]) if row.get("weakest_dimension") in DIMENSION_NAMES else 0,
            )

            save_col, delete_col = st.columns(2)
            save_clicked = save_col.form_submit_button("Save changes", use_container_width=True)
            delete_clicked = delete_col.form_submit_button("Delete this entry", use_container_width=True)

        if save_clicked:
            rows[idx] = {
                "startup": startup_input,
                "run_date": str(run_date_input),
                "sharf_score": round(float(sharf_score_input), 1),
                "risk_tier": risk_tier_input,
                "runway_months": round(float(runway_input), 1),
                "weakest_dimension": weakest_input,
                "dimension_scores": {name: round(float(value), 1) for name, value in dim_inputs.items()},
            }
            st.session_state.score_runs = rows
            persist_user_memory()
            st.success("Entry updated.")
            st.rerun()
        if delete_clicked:
            rows.pop(idx)
            st.session_state.score_runs = rows
            persist_user_memory()
            st.success("Entry deleted.")
            st.rerun()


def page_input(selected: pd.Series) -> None:
    st.header("Page 1: Monthly Input Review")
    st.markdown(
        '<div class="purpose">Purpose: confirm or edit monthly startup inputs before scoring.</div>',
        unsafe_allow_html=True,
    )
    explain_box(
        "What is happening on this page?",
        "This is where the founder enters the current month of operating data. "
        "The default numbers come from the validated SHARF dataset, but the user can replace them with their own monthly values. "
        "When Run scoring is clicked, the app calculates runway, converts each metric into a 0-100 score, and creates the overall SHARF health score.",
    )
    st.write("")

    with st.form("founder_input"):
        c1, c2, c3, c4 = st.columns(4)
        revenue = c1.number_input("Revenue input", min_value=0.0, value=float(selected["monthly_revenue_usd"]), step=100.0)
        mom_growth_pct = c2.number_input("MoM growth input (%)", value=float(selected["mom_revenue_growth"]) * 100, step=0.5)
        cash = c3.number_input("Cash input", min_value=0.0, value=float(selected["cash_balance_usd"]), step=100.0)
        burn = c4.number_input("Burn input", min_value=1.0, value=float(selected["monthly_burn_usd"]), step=100.0)

        c5, c6, c7, c8 = st.columns(4)
        churn_pct = c5.number_input("Churn input (%)", min_value=0.0, max_value=100.0, value=float(selected["monthly_churn_rate"]) * 100, step=0.1)
        cac = c6.number_input("CAC input", min_value=0.0, value=float(selected["customer_acquisition_cost_usd"]), step=100.0)
        payback = c7.number_input("Payback input", min_value=0.0, max_value=60.0, value=float(selected["cac_payback_months"]), step=0.1)
        nps = c8.number_input("NPS input", min_value=-100.0, max_value=100.0, value=float(selected["nps"]), step=1.0)

        c9, c10, c11 = st.columns(3)
        headcount = c9.number_input("Headcount input", min_value=1, value=int(selected["headcount"]), step=1)
        time_to_fill = c10.number_input("Time to fill input", min_value=1.0, max_value=180.0, value=float(selected["avg_time_to_fill_days"]), step=1.0)
        board = c11.selectbox("Board? input", ["Yes", "No"], index=0 if bool(selected["board_or_advisory_group"]) else 1)

        submitted = st.form_submit_button("Run scoring", use_container_width=True)

    missing_or_risky = []
    if cash / max(burn, 1) < 6:
        missing_or_risky.append("Runway is below six months.")
    if churn_pct > 8:
        missing_or_risky.append("Churn is high.")
    if payback > 18:
        missing_or_risky.append("CAC payback is slow.")
    if nps < 0:
        missing_or_risky.append("NPS is negative.")
    if time_to_fill > 75:
        missing_or_risky.append("Hiring is taking a long time.")

    if submitted:
        values = {
            "monthly_revenue_usd": revenue,
            "mom_revenue_growth": mom_growth_pct / 100,
            "cash_balance_usd": cash,
            "monthly_burn_usd": burn,
            "monthly_churn_rate": churn_pct / 100,
            "customer_acquisition_cost_usd": cac,
            "cac_payback_months": payback,
            "nps": nps,
            "headcount": float(headcount),
            "avg_time_to_fill_days": time_to_fill,
            "governance_score": 100.0 if board == "Yes" else 45.0,
        }
        result = score_inputs(values, float(selected["monthly_revenue_usd"]))
        st.session_state.current_values = values
        st.session_state.current_result = result
        st.session_state.current_startup = selected["startup_name"]
        st.session_state.score_runs.insert(
            0,
            {
                "startup": selected["startup_name"],
                "run_date": str(date.today()),
                "sharf_score": result["sharf_score"],
                "risk_tier": result["risk_tier"],
                "runway_months": result["runway_months"],
                "weakest_dimension": result["weakest_dimension"],
                "dimension_scores": result["dimension_scores"],
            },
        )
        persist_user_memory()
        st.success("Scoring complete. Go to Page 2 to see the health score and risk explanation.")

    st.subheader("Missing or high-risk fields")
    if missing_or_risky:
        for item in missing_or_risky:
            st.warning(item)
    else:
        st.info("No missing fields or obvious high-risk input warnings were found.")


def page_score() -> None:
    st.header("Page 2: Health Score and Risk Explanation")
    if not require_scoring():
        return
    result = st.session_state.current_result
    values = st.session_state.current_values
    explain_box(
        "What is happening on this page?",
        "This page shows the result of the monthly scoring. The composite SHARF score is the overall health score from 0 to 100. "
        "The risk tier turns that score into a simple label: Stable, Watch, or Critical. "
        "The bars explain which business areas are strong or weak, and the right-side text explains why each area matters in plain language.",
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Composite SHARF Score 0-100", result["sharf_score"])
    c2.markdown(
        f'<div class="sharf-card"><p class="small-muted">Risk Tier</p><h2>{result["risk_tier"]}</h2><span class="risk-pill">Low / Watch / Critical</span></div>',
        unsafe_allow_html=True,
    )
    c3.markdown(
        f'<div class="sharf-card"><p class="small-muted">Plain-language reason</p><p>{risk_reason(result, values)}</p></div>',
        unsafe_allow_html=True,
    )

    st.write("")
    why = {
        "Runway": "Runway matters because it tells the founder how long the company can keep operating before cash becomes urgent.",
        "Revenue": "Revenue matters because stronger growth gives the startup more room to spend and improves fundraising credibility.",
        "Retention": "Retention matters because high churn means customers are leaving and future revenue is less reliable.",
        "Growth Efficiency": "Growth efficiency matters because a long CAC payback means sales are too expensive for the current cash position.",
        "Customer Sentiment": "Customer sentiment matters because unhappy customers can become churn before revenue drops.",
        "Team Capacity": "Team capacity matters because slow hiring can block product, sales, and customer support work.",
        "Governance": "Governance matters because advisors or a board can improve accountability and fundraising readiness.",
    }
    for name, score in result["dimension_scores"].items():
        left, middle, right = st.columns([1.2, 2.4, 1.4])
        left.markdown(f"**{name}**")
        middle.markdown(
            f'<div class="bar-shell"><div class="bar-fill" style="width:{score}%"></div></div>',
            unsafe_allow_html=True,
        )
        right.markdown(f'<div class="why-box">{why[name]}</div>', unsafe_allow_html=True)


def option_copy(option: str, result: dict[str, object], values: dict[str, float]) -> dict[str, str]:
    runway = float(result["runway_months"])
    score = float(result["sharf_score"])
    weakest = str(result["weakest_dimension"]).lower()
    if option == "Conserve Cash":
        return {
            "effect": f"This option is expected to protect runway. If burn is cut by 15%, runway could move from about {runway:.1f} months to about {runway / 0.85:.1f} months.",
            "tradeoff": "The tradeoff is slower hiring, slower growth experiments, or delayed product work.",
            "action": f"Reduce discretionary spend this month and focus the saved cash on fixing {weakest}.",
        }
    if option == "Maintain Plan":
        return {
            "effect": f"This option keeps runway near {runway:.1f} months unless revenue improves next month.",
            "tradeoff": "The risk is that weak metrics continue without a cash cushion getting better.",
            "action": "Maintain the current plan only if the founder reviews score movement again next month.",
        }
    return {
        "effect": "This option uses time and attention to prepare investor materials rather than only cutting costs.",
        "tradeoff": "The risk is that investors may react poorly if the health score and weakest dimension are not improved first.",
        "action": "Prepare the story and data room, but do outreach only after the weakest operating metric improves.",
    }


def page_decisions() -> None:
    st.header("Page 3: Decision Options")
    if not require_scoring():
        return
    result = st.session_state.current_result
    values = st.session_state.current_values
    explain_box(
        "What is happening on this page?",
        "This page turns the score into decision choices. Instead of only showing a dashboard number, SHARF compares three founder actions: conserve cash, maintain the plan, or prepare to fundraise. "
        "Pick an option below to see its expected effect on runway, the tradeoff, and the next practical action. You can peek at the other two options for comparison before deciding.",
    )

    options = ["Conserve Cash", "Maintain Plan", "Prepare Fundraise"]
    selected_option = st.selectbox("Choose an option to review", options)
    copy = option_copy(selected_option, result, values)

    st.markdown(f'<div class="option-card"><h3>{selected_option}</h3>', unsafe_allow_html=True)
    st.write("**Expected effect on runway**")
    st.write(copy["effect"])
    st.write("**Tradeoffs and risk flags**")
    st.write(copy["tradeoff"])
    st.write("**Recommended next action**")
    st.write(copy["action"])
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Compare the other options"):
        for other_option in options:
            if other_option == selected_option:
                continue
            other_copy = option_copy(other_option, result, values)
            st.markdown(f"**{other_option}**")
            st.write(f"Effect: {other_copy['effect']}")
            st.write(f"Tradeoff: {other_copy['tradeoff']}")
            st.write(f"Next action: {other_copy['action']}")
            st.divider()

    st.write("")
    note = st.text_area("Founder note", placeholder="Example: Cut paid ads by 15% and review churn weekly.")
    if st.button("Send selected option to action plan", use_container_width=True):
        st.session_state.selected_decision = {
            "decision": selected_option,
            "metric_target": f"Improve {result['weakest_dimension']} and keep SHARF score above {result['sharf_score']}",
            "next_action": copy["action"],
            "note": note,
        }
        st.success("Decision saved. Go to Page 4 to complete the action plan.")


def page_action_plan(selected: pd.Series) -> None:
    st.header("Page 4: Action Plan and Outcome Log")
    st.markdown(
        '<div class="purpose">Purpose: convert recommendation into a 30-day operating decision.</div>',
        unsafe_allow_html=True,
    )

    tab_new, tab_log, tab_scores, tab_trends = st.tabs(
        ["Log New Entry", "Action Plan Log", "Score Memory", "Trends & Insights"]
    )

    with tab_new:
        if not require_scoring():
            st.info(
                "You can still review old action-log entries, saved score memory, and trend history in the other tabs. "
                "Run scoring only when you want to create a new action-plan entry from a fresh score."
            )
        else:
            explain_box(
                "What is happening on this tab?",
                "This is where the founder records the decision, owner, target metric, due date, and status. "
                "The outcome section compares the new SHARF score with the latest validated score and says whether the score improved, declined, or needs review.",
            )

            saved = st.session_state.get("selected_decision", {})
            decision_default = saved.get("decision", "Conserve Cash")
            target_default = saved.get("metric_target", f"Improve {st.session_state.current_result['weakest_dimension']}")

            c1, c2, c3, c4, c5 = st.columns(5)
            decision = c1.text_input("Decision", decision_default)
            owner = c2.text_input("Owner", "Founder")
            target = c3.text_input("Metric Target", target_default)
            due = c4.date_input("Due Date", date.today())
            status = c5.selectbox("Status", ["Not started", "In progress", "Done", "Review"])

            notes = st.text_area("Next month outcome notes", value=saved.get("note", ""))

            previous_score = float(selected["sharf_score"])
            new_score = float(st.session_state.current_result["sharf_score"])
            score_change = round(new_score - previous_score, 1)
            outcome = "Yes" if score_change > 1 else "No" if score_change < -1 else "Review"
            st.metric("Did score improve? Yes / No / Review", outcome, delta=score_change)

            if st.button("Add entry to outcome log", use_container_width=True):
                st.session_state.action_rows.insert(
                    0,
                    {
                        "Startup": st.session_state.get("current_startup", selected["startup_name"]),
                        "Logged Date": str(date.today()),
                        "Decision": decision,
                        "Owner": owner,
                        "Metric Target": target,
                        "Due Date": str(due),
                        "Status": status,
                        "Outcome Notes": notes,
                        "Score Improved?": outcome,
                    },
                )
                persist_user_memory()
                st.success("Action plan entry added. See it under the Action Plan Log tab.")

    with tab_log:
        action_log_manager()

    with tab_scores:
        score_log_manager()

    with tab_trends:
        page_trend_section(st.session_state.get("current_startup", selected["startup_name"]))


profiles, metrics, forecast, validation = load_data()
latest = metrics.sort_values("month").groupby("startup_id").tail(1)
app = profiles.merge(latest, on="startup_id").merge(forecast, on="startup_id")
for base_col in ["industry", "stage", "region", "board_or_advisory_group"]:
    if base_col not in app.columns:
        for candidate in [f"{base_col}_x", f"{base_col}_y"]:
            if candidate in app.columns:
                app[base_col] = app[candidate]
                break

if "authenticated_user" not in st.session_state:
    login_panel()
    st.stop()

user_memory = ensure_user_record(st.session_state.authenticated_user)
if "score_runs" not in st.session_state:
    st.session_state.score_runs = user_memory.get("score_runs", [])
if "action_rows" not in st.session_state:
    st.session_state.action_rows = user_memory.get("action_rows", [])

inject_css()

st.sidebar.title("SHARF")
st.sidebar.caption(f"Signed in as {st.session_state.authenticated_user}")
if st.sidebar.button("Logout"):
    persist_user_memory()
    for key in ["authenticated_user", "score_runs", "action_rows", "current_values", "current_result", "current_startup", "selected_decision"]:
        st.session_state.pop(key, None)
    st.rerun()
page = st.sidebar.radio(
    "Pages",
    [
        "1. Founder Input",
        "2. Health Score and Risk",
        "3. Decision Options",
        "4. Action Plan and Outcome Log",
    ],
)
startup_name = st.sidebar.selectbox("Startup profile defaults", app["startup_name"])
selected = app.loc[app["startup_name"] == startup_name].iloc[0]

passed = int(validation["passed"].astype(str).str.lower().eq("true").sum())
st.sidebar.success(f"{passed}/{len(validation)} validation checks passed")
st.sidebar.markdown(
    f"""
    <div class="data-box">
    <strong>About the data</strong><br>
    The app uses the validated SHARF final datasets from the previous deliverable.
    The startup records are synthetic so no private founder, customer, or investor data is exposed.
    The fields and ranges are based on the project plan, research-backed assumptions, and a sourced company employment/payroll benchmark.
    Validation checks passed for schema, missing values, identifiers, ranges, formulas, referential integrity, and Monte Carlo outputs.
    This makes the data fit for testing this prototype, but not universally valid for real startup investment decisions.
    </div>
    """,
    unsafe_allow_html=True,
)

st.title("SHARF Founder Decision Support")
st.caption("A Streamlit prototype using validated SHARF data, health scoring, Monte Carlo risk context, and founder-entered monthly inputs.")

if page == "1. Founder Input":
    page_input(selected)
elif page == "2. Health Score and Risk":
    page_score()
elif page == "3. Decision Options":
    page_decisions()
else:
    page_action_plan(selected)
