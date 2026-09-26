"""JSON parsing for one or more applicant test cases."""
import json

from .validation import validate


def parse_json_cases(raw):
    """Parse one applicant object or a non-empty list of applicant objects."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON near line {error.lineno}, column {error.colno}.") from error
    cases = data if isinstance(data, list) else [data]
    if not cases:
        raise ValueError("The JSON list is empty.")
    return [validate(case) for case in cases]
