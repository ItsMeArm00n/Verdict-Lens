"""Small local Streamlit interface for exercising the VerdictLens workflow."""
import json
import os

import pandas as pd
import streamlit as st

from verdictlens import Auditor
from verdictlens.case_import import parse_json_cases
from verdictlens.gemini_explanation import DEFAULT_MODEL, FLASH_MODELS, generate_explanation


st.set_page_config(page_title="VerdictLens", page_icon="🔎", layout="wide")
st.markdown(
    """
    <style>
    .block-container {max-width: 1100px; padding-top: 2rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {background: #18202b; border: 1px solid #344154;
        border-radius: 10px; padding: 0.9rem 1rem;}
    [data-testid="stMetric"] label,
    [data-testid="stMetric"] [data-testid="stMetricLabel"] {
        color: #b9c6d8 !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    .vl-note {color: #596579; font-size: .92rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_auditor():
    return Auditor()


LABELS = {
    "INPUT_QUALITY_REVIEW": "An input is missing, unusual, or outside the normal training range.",
    "MODEL_POLICY_DISAGREEMENT": "At least one challenger model reached a different decision using its own threshold.",
    "COMMON_THRESHOLD_DISAGREEMENT": "At least one challenger disagreed when all models used the primary threshold.",
    "THRESHOLD_SENSITIVE": "The decision changes under a nearby decision threshold.",
    "INPUT_SENSITIVE": "A small diagnostic input change flips the primary decision.",
}

DEFAULTS = {
    "RevolvingUtilizationOfUnsecuredLines": 0.536575875,
    "age": 35,
    "NumberOfTime30-59DaysPastDueNotWorse": 1,
    "DebtRatio": 0.692470557,
    "MonthlyIncome": 7556.0,
    "NumberOfOpenCreditLinesAndLoans": 16,
    "NumberOfTimes90DaysLate": 0,
    "NumberRealEstateLoansOrLines": 1,
    "NumberOfTime60-89DaysPastDueNotWorse": 0,
    "NumberOfDependents": 0,
}

JSON_EXAMPLE = json.dumps(DEFAULTS, indent=2)
FORM_KEYS = {
    "RevolvingUtilizationOfUnsecuredLines": "form_utilization",
    "age": "form_age",
    "NumberOfTime30-59DaysPastDueNotWorse": "form_late_30_59",
    "DebtRatio": "form_debt_ratio",
    "MonthlyIncome": "form_income",
    "NumberOfOpenCreditLinesAndLoans": "form_open_lines",
    "NumberOfTimes90DaysLate": "form_late_90",
    "NumberRealEstateLoansOrLines": "form_real_estate",
    "NumberOfTime60-89DaysPastDueNotWorse": "form_late_60_89",
    "NumberOfDependents": "form_dependents",
}


def result_signature(applicant):
    return json.dumps(applicant, sort_keys=True, separators=(",", ":"))


def clear_old_results(applicant):
    signature = result_signature(applicant)
    if st.session_state.get("applicant_signature") != signature:
        st.session_state.pop("prediction", None)
        st.session_state.pop("audit_result", None)
        st.session_state.pop("gemini_explanation", None)
    st.session_state["applicant_signature"] = signature


def load_case_into_form(case):
    for feature, key in FORM_KEYS.items():
        value = case[feature]
        if feature == "MonthlyIncome":
            st.session_state["form_income_missing"] = value is None
        if feature == "NumberOfDependents":
            st.session_state["form_dependents_missing"] = value is None
        if value is not None:
            st.session_state[key] = int(value) if feature in {
                "age", "NumberOfTime30-59DaysPastDueNotWorse",
                "NumberOfOpenCreditLinesAndLoans", "NumberOfTimes90DaysLate",
                "NumberRealEstateLoansOrLines", "NumberOfTime60-89DaysPastDueNotWorse",
                "NumberOfDependents",
            } else float(value)


def show_json_importer():
    with st.expander("Import applicant JSON"):
        st.write(
            "Paste either one applicant object or a JSON list of applicant objects. "
            "Every object must contain exactly these ten fields. Use `null` only for "
            "`MonthlyIncome` or `NumberOfDependents` when the value is unavailable."
        )
        st.code(JSON_EXAMPLE, language="json")
        raw = st.text_area(
            "Applicant JSON", key="json_import_text", height=190,
            placeholder="Paste one object or a list of objects here…",
        )
        if st.button("Validate and import JSON"):
            try:
                st.session_state["imported_cases"] = parse_json_cases(raw)
                st.session_state["imported_case_index"] = 0
                load_case_into_form(st.session_state["imported_cases"][0])
                st.success(f"Imported {len(st.session_state['imported_cases'])} valid case(s).")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        cases = st.session_state.get("imported_cases", [])
        if cases:
            case_number = st.selectbox(
                "Imported case", range(len(cases)),
                format_func=lambda index: f"Case {index + 1} of {len(cases)}",
                key="imported_case_index",
            )
            if st.button("Load selected case into form"):
                load_case_into_form(cases[case_number])
                st.session_state.pop("prediction", None)
                st.session_state.pop("audit_result", None)
                st.session_state.pop("gemini_explanation", None)
                st.rerun()
        st.download_button(
            "Download JSON template", JSON_EXAMPLE,
            file_name="verdictlens_applicant_template.json", mime="application/json",
        )


def collect_applicant():
    left, right = st.columns(2, gap="large")
    with left:
        utilization = st.number_input(
            "Revolving credit utilization",
            min_value=0.0,
            value=DEFAULTS["RevolvingUtilizationOfUnsecuredLines"],
            format="%.6f",
            help="Balance on revolving credit divided by the available credit limit.",
            key=FORM_KEYS["RevolvingUtilizationOfUnsecuredLines"],
        )
        age = st.number_input("Age", min_value=0, value=DEFAULTS["age"], step=1, key=FORM_KEYS["age"])
        late_30_59 = st.number_input(
            "Times 30–59 days late", min_value=0,
            value=DEFAULTS["NumberOfTime30-59DaysPastDueNotWorse"], step=1,
            key=FORM_KEYS["NumberOfTime30-59DaysPastDueNotWorse"],
        )
        debt_ratio = st.number_input(
            "Debt ratio", min_value=0.0, value=DEFAULTS["DebtRatio"], format="%.6f",
            key=FORM_KEYS["DebtRatio"],
        )
        income_missing = st.checkbox("Monthly income is unavailable", key="form_income_missing")
        income = st.number_input(
            "Monthly income", min_value=0.0, value=DEFAULTS["MonthlyIncome"],
            step=100.0, disabled=income_missing,
            key=FORM_KEYS["MonthlyIncome"],
        )
    with right:
        open_lines = st.number_input(
            "Open credit lines and loans", min_value=0,
            value=DEFAULTS["NumberOfOpenCreditLinesAndLoans"], step=1,
            key=FORM_KEYS["NumberOfOpenCreditLinesAndLoans"],
        )
        late_90 = st.number_input(
            "Times 90+ days late", min_value=0,
            value=DEFAULTS["NumberOfTimes90DaysLate"], step=1,
            key=FORM_KEYS["NumberOfTimes90DaysLate"],
        )
        real_estate = st.number_input(
            "Real-estate loans or lines", min_value=0,
            value=DEFAULTS["NumberRealEstateLoansOrLines"], step=1,
            key=FORM_KEYS["NumberRealEstateLoansOrLines"],
        )
        late_60_89 = st.number_input(
            "Times 60–89 days late", min_value=0,
            value=DEFAULTS["NumberOfTime60-89DaysPastDueNotWorse"], step=1,
            key=FORM_KEYS["NumberOfTime60-89DaysPastDueNotWorse"],
        )
        dependents_missing = st.checkbox("Number of dependents is unavailable", key="form_dependents_missing")
        dependents = st.number_input(
            "Number of dependents", min_value=0,
            value=DEFAULTS["NumberOfDependents"], step=1, disabled=dependents_missing,
            key=FORM_KEYS["NumberOfDependents"],
        )
    return {
        "RevolvingUtilizationOfUnsecuredLines": utilization,
        "age": age,
        "NumberOfTime30-59DaysPastDueNotWorse": late_30_59,
        "DebtRatio": debt_ratio,
        "MonthlyIncome": None if income_missing else income,
        "NumberOfOpenCreditLinesAndLoans": open_lines,
        "NumberOfTimes90DaysLate": late_90,
        "NumberRealEstateLoansOrLines": real_estate,
        "NumberOfTime60-89DaysPastDueNotWorse": late_60_89,
        "NumberOfDependents": None if dependents_missing else dependents,
    }


def show_primary(primary):
    st.subheader("Primary loan-risk model")
    decision_col, risk_col, threshold_col, margin_col = st.columns(4)
    decision_col.metric("Decision", primary["decision"])
    risk_col.metric("Estimated risk", f"{primary['risk_estimate']:.3%}")
    threshold_col.metric("Decision threshold", f"{primary['threshold']:.3%}")
    margin_col.metric(
        "Margin to threshold",
        f"{primary['signed_margin'] * 100:+.3f} pp",
        help="Estimated risk minus the decision threshold, measured in percentage points.",
    )
    st.caption(
        "Estimated risk is the model's output. The threshold is the fixed cutoff: "
        "risk at or above the threshold produces REJECT."
    )
    if primary["decision"] == "REJECT":
        st.error("The primary model rejects this application.")
    else:
        st.success("The primary model approves this application.")


def show_audit(result, gemini_api_key):
    st.divider()
    st.subheader("VerdictLens audit")
    if result["status"] == "REVIEW":
        st.warning("Review required — one or more configured checks raised a flag.")
    else:
        st.success("Stable under current checks — no configured check raised a flag.")

    st.write(result["explanation"])
    st.caption("VerdictLens reports diagnostic evidence. It does not reverse the primary decision.")

    st.markdown("#### Gemini explanation: primary decision and audit")
    st.caption(
        "Gemini receives the completed audit evidence, without the raw applicant form. "
        "It can explain the result but cannot alter it."
    )
    if st.button("Generate Gemini explanation", disabled=not bool(gemini_api_key), width="stretch"):
        try:
            with st.spinner("Asking Gemini to explain the audit…"):
                st.session_state["gemini_explanation"] = generate_explanation(
                    result, gemini_api_key
                )
        except Exception as error:
            st.error(f"Gemini explanation failed: {error}")
    if not gemini_api_key:
        st.info("Add a Gemini API key in the sidebar to enable the AI explanation.")
    if "gemini_explanation" in st.session_state:
        st.markdown(st.session_state["gemini_explanation"])

    st.markdown("#### Checks")
    if result["flags"]:
        for code in result["flags"]:
            st.markdown(f"⚠️ **{code.replace('_', ' ').title()}** — {LABELS.get(code, code)}")
    else:
        st.markdown("✅ No review flags in the configured checks.")

    model_rows = [{
        "Model": item["model"].replace("_", " ").title(),
        "Risk estimate": f"{item['risk_estimate']:.2%}",
        "Decision": item["own_policy_decision"],
        "Model threshold": f"{item['own_policy_threshold']:.2%}",
    } for item in result["challengers"]]
    with st.expander("Model comparison", expanded=True):
        st.dataframe(pd.DataFrame(model_rows), hide_index=True, width="stretch")

    with st.expander("Threshold and input sensitivity details"):
        threshold_rows = [{
            "Threshold": f"{item['threshold']:.2%}", "Decision": item["decision"]
        } for item in result["threshold_sensitivity"]]
        st.markdown("**Nearby thresholds**")
        st.dataframe(pd.DataFrame(threshold_rows), hide_index=True, width="stretch")
        flips = [item for item in result["input_sensitivity"] if item["decision_flipped"]]
        st.markdown("**Input probes that changed the decision**")
        if flips:
            st.dataframe(pd.DataFrame([{
                "Scenario": item["scenario"], "Risk": f"{item['risk_estimate']:.2%}",
                "Decision": item["decision"],
            } for item in flips]), hide_index=True, width="stretch")
        else:
            st.write("None of the configured local input probes changed the decision.")

    with st.expander("Input-quality details"):
        if result["input_quality"]:
            st.dataframe(pd.DataFrame(result["input_quality"]), hide_index=True, width="stretch")
        else:
            st.write("No input-quality flags.")

    with st.expander("Raw structured result"):
        st.json(result)
    st.download_button(
        "Download audit JSON", json.dumps(result, indent=2),
        file_name="verdictlens_audit.json", mime="application/json",
    )


st.title("VerdictLens")
st.markdown(
    "Test a loan-risk decision, then inspect deterministic audit signals from challenger models, "
    "nearby thresholds, input probes, and data-quality checks."
)
st.caption("Local core · Gemini is optional and used only for the plain-language explanation")

with st.sidebar:
    st.header("Optional Gemini explanation")
    st.caption("The decision and audit work without Gemini.")
    saved_key = os.getenv("GEMINI_API_KEY", "")
    try:
        saved_key = saved_key or st.secrets.get("GEMINI_API_KEY", "")
    except FileNotFoundError:
        pass
    entered_key = st.text_input(
        "Gemini API key",
        type="password",
        value="" if saved_key else st.session_state.get("temporary_gemini_key", ""),
        placeholder="Configured in environment" if saved_key else "Paste key for this session",
        help="Prefer the GEMINI_API_KEY environment variable. A pasted key stays only in this Streamlit session.",
    )
    if entered_key:
        st.session_state["temporary_gemini_key"] = entered_key
    gemini_api_key = saved_key or st.session_state.get("temporary_gemini_key", "")
    if gemini_api_key:
        st.success(f"Gemini enabled · starts with {DEFAULT_MODEL}")
        st.caption("Temporary capacity errors automatically try: " + " → ".join(FLASH_MODELS))
    else:
        st.info("Gemini is not configured.")

show_json_importer()

with st.form("application_form"):
    st.subheader("Applicant information")
    applicant = collect_applicant()
    run_primary, run_audit = st.columns(2)
    primary_clicked = run_primary.form_submit_button("Run loan decision", width="stretch")
    audit_clicked = run_audit.form_submit_button("Run VerdictLens audit", type="primary", width="stretch")

clear_old_results(applicant)
try:
    auditor = get_auditor()
    if primary_clicked:
        st.session_state["prediction"] = auditor.primary_prediction(applicant)
    if audit_clicked:
        st.session_state["audit_result"] = auditor.run(applicant)
        st.session_state["prediction"] = st.session_state["audit_result"]["primary"]
except ValueError as error:
    st.error(f"Could not evaluate this applicant: {error}")

if "prediction" in st.session_state:
    show_primary(st.session_state["prediction"])
if "audit_result" in st.session_state:
    show_audit(st.session_state["audit_result"], gemini_api_key)

st.divider()
st.markdown(
    '<p class="vl-note">Prototype only. A review flag is evidence to inspect, not proof that a decision is wrong, fair, or unfair.</p>',
    unsafe_allow_html=True,
)
