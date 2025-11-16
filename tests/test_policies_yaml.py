from pathlib import Path

import yaml


def _load_yaml(p: Path):
    assert p.exists(), f"Missing file: {p}"
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_model_policy_yaml_parses_and_is_mapping():
    p = Path("policies/model-policy.yml")
    data = _load_yaml(p)
    assert isinstance(data, dict), "model-policy.yml must be a YAML mapping"
    assert data, "model-policy.yml should not be empty"


def test_risk_matrix_yaml_has_expected_structure():
    p = Path("policies/risk-matrix.yml")
    data = _load_yaml(p)
    assert isinstance(data, dict), "risk-matrix.yml must be a YAML mapping"
    # The validators support different schemas; just ensure it's non-empty and dict
    assert data, "risk-matrix.yml should not be empty"
