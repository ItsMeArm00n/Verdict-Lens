"""Local HTTP API for VerdictLens.

Wraps the frozen `verdictlens` package so the Next.js site can run real audits.
This server is intended for local use only: it binds to 127.0.0.1 and holds no
credentials. Model artifacts stay on this side of the connection; the browser
only ever receives the structured decision and audit evidence.

Run it with:  python -m uvicorn api:app --reload --port 8000
Interactive API reference: http://127.0.0.1:8000/docs
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import Body, FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import store  # noqa: E402
from verdictlens import FEATURES  # noqa: E402
from verdictlens.case_import import parse_json_cases  # noqa: E402
from verdictlens.gemini_explanation import DEFAULT_MODEL as DEFAULT_GEMINI_MODEL  # noqa: E402
from verdictlens.gemini_explanation import generate_explanation, generate_primary_explanation, validate_api_key  # noqa: E402
from verdictlens.validation import COUNT_FIELDS, LATE_FIELDS  # noqa: E402

@asynccontextmanager
async def lifespan(_: FastAPI):
    store.initialize()
    yield


app = FastAPI(
    title="VerdictLens local API",
    version="1.0.0",
    lifespan=lifespan,
    description=(
        "Local audit API for the VerdictLens Next.js site. Deterministic, offline, "
        "and frozen: the primary decision is reported exactly as the model produced it "
        "and is never overridden by the audit."
    ),
)

# The site is served from a different dev port than this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)

# One auditor per process, loaded and integrity-checked on first use.
_auditor = None
_executor = ThreadPoolExecutor(max_workers=2)
GEMINI_TIMEOUT_SECONDS = 45.0


def auditor():
    global _auditor
    if _auditor is None:
        from verdictlens import Auditor

        _auditor = Auditor()
    return _auditor


# --- Presentation metadata for the ten fixed input features -------------------
# Labels and help text live here so the site form and the model schema cannot drift.
FIELD_META = {
    "RevolvingUtilizationOfUnsecuredLines": {
        "label": "Revolving credit utilization",
        "help": "Share of your revolving credit limit currently in use, as a fraction. 0.54 means 54%.",
        "step": 0.000001,
    },
    "age": {
        "label": "Age",
        "help": "Applicant age in years. Zero is treated as a missing value and imputed.",
        "step": 1,
    },
    "NumberOfTime30-59DaysPastDueNotWorse": {
        "label": "Times 30-59 days late",
        "help": "Number of 30-59 day late payments in the last 24 months. 96 and 98 are ambiguous codes.",
        "step": 1,
    },
    "DebtRatio": {
        "label": "Debt ratio",
        "help": "Monthly debt payments divided by monthly income, as a fraction. 0.69 means 69%.",
        "step": 0.000001,
    },
    "MonthlyIncome": {
        "label": "Monthly income",
        "help": "Gross monthly income in your currency. A null value is imputed and flagged.",
        "step": 0.01,
    },
    "NumberOfOpenCreditLinesAndLoans": {
        "label": "Open credit lines and loans",
        "help": "How many credit lines and loans are currently open.",
        "step": 1,
    },
    "NumberOfTimes90DaysLate": {
        "label": "Times 90+ days late",
        "help": "Number of 90+ day late payments. 96 and 98 are ambiguous codes, not real counts.",
        "step": 1,
    },
    "NumberRealEstateLoansOrLines": {
        "label": "Real-estate loans or lines",
        "help": "Number of real-estate loans or credit lines held.",
        "step": 1,
    },
    "NumberOfTime60-89DaysPastDueNotWorse": {
        "label": "Times 60-89 days late",
        "help": "Number of 60-89 day late payments. 96 and 98 are ambiguous codes.",
        "step": 1,
    },
    "NumberOfDependents": {
        "label": "Number of dependents",
        "help": "People financially dependent on the applicant. A null value is imputed and flagged.",
        "step": 1,
    },
}

# The reference site exposes explicit "unavailable" toggles for these two fields.
UNAVAILABLE_FIELDS = ["MonthlyIncome", "NumberOfDependents"]


@app.get("/api/health")
def health():
    """Report API readiness plus the frozen policy values the site displays."""
    config = auditor().config
    return {
        "status": "ok",
        "audit_version": config["audit_version"],
        "primary_threshold": config["primary_threshold"],
        "challenger_thresholds": config["challenger_thresholds"],
        "threshold_offsets": config["threshold_offsets"],
        "policy": config["policy"],
        "policy_status": config["policy_status"],
        "features": FEATURES,
        "counts": {
            "training_rows": config["training_rows"],
            "calibration_rows": config["calibration_rows"],
            "policy_rows": config["policy_rows"],
            "test_rows": config["test_rows"],
        },
    }


@app.get("/api/schema")
def schema():
    """Describe the ten input features, including training-data reference ranges."""
    config = auditor().config
    return {
        "features": [
            {
                "name": name,
                "label": FIELD_META[name]["label"],
                "help": FIELD_META[name]["help"],
                "step": FIELD_META[name]["step"],
                "integer": name in COUNT_FIELDS,
                "nullable": True,
                "late_count": name in LATE_FIELDS,
                "ambiguous_values": [96, 98] if name in LATE_FIELDS else [],
                "supports_unavailable_toggle": name in UNAVAILABLE_FIELDS,
                "reference": config["reference"][name],
            }
            for name in FEATURES
        ],
        "unavailable_fields": UNAVAILABLE_FIELDS,
    }


class PredictRequest(BaseModel):
    applicant: dict = Field(..., description="Exactly the ten named feature keys.")


class AuditRequest(BaseModel):
    case_ref: str | None = Field(None, description="An existing case to complete.")
    applicant: dict | None = Field(None, description="A new applicant, when no case exists yet.")


class ImportRequest(BaseModel):
    raw: str = Field(..., description="One applicant object or a list of applicant objects.")


class ExplainRequest(BaseModel):
    case_ref: str
    api_key: str = Field("", description="Optional per-request key; never stored on the server.")


class GeminiKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=1, description="Used for this request only; never stored.")


@app.post("/api/import")
def import_cases(payload: ImportRequest):
    """Validate pasted JSON applicant objects before they reach the form."""
    try:
        cases = parse_json_cases(payload.raw)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"count": len(cases), "cases": cases}


@app.post("/api/predict")
def predict(payload: PredictRequest):
    """Run only the primary model and open a case at the decision stage."""
    try:
        primary = auditor().primary_prediction(payload.applicant)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    case = store.create_case(payload.applicant, primary=primary)
    return {**case, "primary": primary}


@app.post("/api/gemini/validate")
def validate_gemini(payload: GeminiKeyRequest):
    """Require a working Gemini key before the browser starts the decision workflow."""
    try:
        _executor.submit(validate_api_key, payload.api_key).result(timeout=GEMINI_TIMEOUT_SECONDS)
    except TimeoutError as error:
        raise HTTPException(status_code=504, detail="Gemini did not respond in time. Please try again.") from error
    except Exception as error:
        raise HTTPException(status_code=422, detail=f"Gemini key validation failed: {error}") from error
    return {"valid": True, "model": DEFAULT_GEMINI_MODEL}


@app.post("/api/explain-primary")
def explain_primary(payload: ExplainRequest):
    """Explain the recorded primary result before the deterministic audit runs."""
    try:
        case = store.get_case(payload.case_ref)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"No case {error}.") from error
    if not case["primary"]:
        raise HTTPException(status_code=409, detail="This case has no primary result yet.")
    api_key = payload.api_key.strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=422, detail="A Gemini API key is required.")
    try:
        markdown = _executor.submit(
            generate_primary_explanation, case["primary"], api_key
        ).result(timeout=GEMINI_TIMEOUT_SECONDS)
    except TimeoutError as error:
        raise HTTPException(status_code=504, detail="Gemini did not respond in time.") from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Gemini explanation failed: {error}") from error
    return {"source": "gemini", "markdown": markdown, "model": DEFAULT_GEMINI_MODEL, "error": None}


@app.post("/api/audit")
def audit(payload: AuditRequest):
    """Run the deterministic evidence checks around an existing or new applicant."""
    try:
        if payload.case_ref:
            case = store.get_case(payload.case_ref)
            applicant = case["applicant"]
        elif payload.applicant is not None:
            applicant = payload.applicant
        else:
            raise HTTPException(
                status_code=400, detail="Provide either a case_ref or an applicant object."
            )
        result = auditor().run(applicant)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"No case {error}.") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    if payload.case_ref:
        saved = store.save_audit(payload.case_ref, result["primary"], result)
        return saved
    created = store.create_case(applicant)
    saved = store.save_audit(created["case_ref"], result["primary"], result)
    return saved


@app.post("/api/explain")
def explain(payload: ExplainRequest):
    """Add optional Gemini wording on top of a finished audit.

    The deterministic template explanation is always returned. Gemini only ever
    rewrites it, and a failure never invalidates the audit.
    """
    try:
        case = store.get_case(payload.case_ref)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"No case {error}.") from error
    if not case["audit"]:
        raise HTTPException(status_code=409, detail="This case has no audit result yet.")

    result = case["audit"]
    response = {
        "case_ref": payload.case_ref,
        "source": "template",
        "template": result["explanation"],
        "markdown": result["explanation"],
        "model": None,
        "error": None,
    }
    api_key = payload.api_key.strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        response["error"] = "Add a Gemini API key here or set GEMINI_API_KEY in the backend environment."
        return response
    try:
        text = _executor.submit(
            generate_explanation, result, api_key
        ).result(timeout=GEMINI_TIMEOUT_SECONDS)
    except TimeoutError as error:
        response["error"] = "Gemini did not respond in time. The audit result is unchanged."
        return response
    except Exception as error:  # surfaced to the UI, never fatal to the audit
        response["error"] = str(error)
        return response
    response.update({"source": "gemini", "markdown": text, "model": DEFAULT_GEMINI_MODEL})
    return response


@app.get("/api/cases")
def list_cases(
    search: str = Query("", description="Match against the case reference."),
    status: str = Query("all", pattern="^(all|review|stable)$"),
    decision: str = Query("all", pattern="^(all|approve|reject)$"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    return store.list_cases(search=search, status=status, decision=decision, limit=limit, offset=offset)


@app.get("/api/cases/{case_ref}")
def get_case(case_ref: str):
    try:
        return store.get_case(case_ref)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"No case {case_ref}.") from error


@app.delete("/api/cases/{case_ref}")
def delete_case(case_ref: str):
    try:
        return store.delete_case(case_ref)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"No case {case_ref}.") from error
