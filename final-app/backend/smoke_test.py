"""Local API smoke test. Exercises every endpoint against a running uvicorn.

Usage:  python smoke_test.py            (server must already be on 127.0.0.1:8000)
"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api"
APP = {
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
failures = []


def call(method, path, body=None, expect=200):
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            status, payload = response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        status, payload = error.code, json.loads(error.read())
    ok = status == expect
    if not ok:
        failures.append(f"{method} {path} -> {status}, expected {expect}")
    print(f"  [{'ok' if ok else 'FAIL'}] {method} {path} -> {status}")
    return payload


def check(label, condition):
    print(f"  [{'ok' if condition else 'FAIL'}] {label}")
    if not condition:
        failures.append(label)


print("health")
health = call("GET", "/health")
check("threshold frozen at 0.178669735789299", health["primary_threshold"] == 0.178669735789299)
check("ten features", len(health["features"]) == 10)

print("schema")
schema = call("GET", "/schema")
check("ten described fields", len(schema["features"]) == 10)
check("age is an integer field", schema["features"][1]["integer"] is True)
check("income supports the unavailable toggle", schema["features"][4]["supports_unavailable_toggle"] is True)
check("reference ranges present", "q25" in schema["features"][0]["reference"])

print("import")
call("POST", "/import", {"raw": json.dumps(APP)}, 200)
call("POST", "/import", {"raw": json.dumps([APP, APP])}, 200)
call("POST", "/import", {"raw": '{"age": 40}'}, 422)
call("POST", "/import", {"raw": "[]"}, 422)
call("POST", "/import", {"raw": "{bad json}"}, 422)

print("predict then audit by case_ref")
predicted = call("POST", "/predict", {"applicant": APP})
check("case reference allocated", predicted["case_ref"].startswith("VL-"))
check("rejects near the boundary", predicted["primary"]["decision"] == "REJECT")
audited = call("POST", "/audit", {"case_ref": predicted["case_ref"]})
audit = audited["audit"]
check("stage advanced to audit", audited["stage"] == "audit")
check("review status", audit["status"] == "REVIEW")
check("two challengers", len(audit["challengers"]) == 2)
check("five threshold probes", len(audit["threshold_sensitivity"]) == 5)
check("input probes present", len(audit["input_sensitivity"]) > 0)
check("primary preserved through audit", audit["primary"]["risk_estimate"] == predicted["primary"]["risk_estimate"])
check("explanation present", bool(audit["explanation"]))
check("three limitations", len(audit["limitations"]) == 3)
check("payload is strictly JSON serialisable", json.dumps(audited, allow_nan=False) is not None)

print("audit for a brand new applicant")
low = dict(APP, age=80, DebtRatio=15.0, MonthlyIncome=0.0)
fresh = call("POST", "/audit", {"applicant": low})
check("new case created", fresh["case_ref"] != predicted["case_ref"])
check("low risk approved", fresh["audit"]["primary"]["decision"] == "APPROVE")

print("null inputs produce quality flags")
missing = dict(APP, MonthlyIncome=None, NumberOfDependents=None)
with_missing = call("POST", "/audit", {"applicant": missing})
check("imputed inputs flagged", any(q["code"] == "IMPUTED_INPUT" for q in with_missing["audit"]["input_quality"]))
check("review raised", with_missing["audit"]["status"] == "REVIEW")

print("ambiguous late count")
ambiguous = dict(APP, NumberOfTimes90DaysLate=98)
with_ambiguous = call("POST", "/audit", {"applicant": ambiguous})
check("ambiguous code flagged", any(q["code"] == "AMBIGUOUS_LATE_COUNT" for q in with_ambiguous["audit"]["input_quality"]))

print("validation errors")
for label, patch in [
    ("negative value", {"age": -1}),
    ("non-integer count", {"age": 45.5}),
    ("missing key", None),
    ("string value", {"MonthlyIncome": "6000"}),
    ("boolean value", {"age": True}),
]:
    broken = dict(APP) if patch is not None else {k: v for k, v in APP.items() if k != "age"}
    broken.update(patch or {})
    call("POST", "/predict", {"applicant": broken}, 422)
    print(f"       {label}")

print("audit requires a target")
call("POST", "/audit", {}, 400)

print("case listing")
listing = call("GET", "/cases")
check("cases persisted", listing["total"] >= 4)
only_review = call("GET", "/cases?status=review")
check("review filter narrows", all(c["status"] == "REVIEW" for c in only_review["cases"]))
only_reject = call("GET", "/cases?decision=reject")
check("decision filter applies", all(c["decision"] == "REJECT" for c in only_reject["cases"]))
search = call(f"GET", f"/cases?search={predicted['case_ref']}")
check("search matches one case", search["total"] == 1)

print("case detail and explain")
detail = call("GET", f"/cases/{predicted['case_ref']}")
check("applicant round-trips", len(detail["applicant"]) == 10)
explain = call("POST", "/explain", {"case_ref": predicted["case_ref"], "api_key": ""})
check("template explanation always returned", bool(explain["template"]))
check("no key reported as an error", explain["error"] is not None)
check("still template sourced", explain["source"] == "template")

print("delete")
call("DELETE", f"/cases/{fresh['case_ref']}")
call("GET", f"/cases/{fresh['case_ref']}", None, 404)
call("DELETE", f"/cases/{fresh['case_ref']}", None, 404)

print("not found")
call("GET", "/cases/VL-9999", None, 404)
call("POST", "/audit", {"case_ref": "VL-9999"}, 404)

print()
if failures:
    print(f"{len(failures)} FAILURES:")
    for failure in failures:
        print(f"  - {failure}")
    sys.exit(1)
print("all checks passed")
