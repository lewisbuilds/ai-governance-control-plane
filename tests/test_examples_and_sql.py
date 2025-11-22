import json
from pathlib import Path


def test_register_model_example_is_valid_and_has_required_fields():
    p = Path("examples/register_model.json")
    assert p.exists(), "examples/register_model.json is missing"
    with p.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    assert isinstance(payload, dict)
    # Minimal required fields per docs/examples; keep flexible to avoid churn
    for key in ("model_id", "version"):
        assert key in payload, f"Missing field '{key}' in register_model example"


def test_init_sql_exists_and_contains_schema_statements():
    p = Path("infra/init.sql")
    assert p.exists(), "infra/init.sql is missing"
    text = p.read_text(encoding="utf-8")
    assert any(
        kw in text.upper() for kw in ("CREATE TABLE", "CREATE SCHEMA")
    ), "Expected CREATE statements in init.sql"
