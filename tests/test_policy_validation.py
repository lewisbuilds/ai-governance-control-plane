import base64
import sys
from pathlib import Path

POLICY_SERVICE = Path(__file__).resolve().parents[1] / "services" / "mcp-policy"
sys.path.insert(0, str(POLICY_SERVICE))

import validators  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402


def _write_policies(directory: Path) -> None:
    (directory / "model-policy.yml").write_text(
        """
thresholds:
  minimum_accuracy: 0.85
  critical_accuracy: 0.95
  maximum_risk: 40
require:
  - field: flags.contains_forbidden_data
    op: eq
    value: false
  - field: metrics.accuracy
    op: gte
    value_from: thresholds.minimum_accuracy
  - when:
      field: context.safety_critical
      op: eq
      value: true
    field: metrics.accuracy
    op: gte
    value_from: thresholds.critical_accuracy
  - field: risk.score
    op: lte
    value_from: thresholds.maximum_risk
deny:
  - field: flags.contains_forbidden_data
    op: eq
    value: true
    reason: Forbidden data detected.
notes:
  - Include lineage evidence.
""",
        encoding="utf-8",
    )
    (directory / "risk-matrix.yml").write_text(
        "weights:\n  data_sensitivity: 3\n  model_complexity: 2\n  deployment_impact: 4\n  monitoring_maturity: -2\n",
        encoding="utf-8",
    )


def _payload(**overrides):
    payload = {
        "flags": {"contains_forbidden_data": False},
        "metrics": {"accuracy": 0.96},
        "context": {"safety_critical": True},
        "risk": {
            "data_sensitivity": 1,
            "model_complexity": 1,
            "deployment_impact": 1,
            "monitoring_maturity": 3,
        },
    }
    payload.update(overrides)
    return payload


def test_yaml_policy_allows_compliant_payload_and_uses_computed_score(tmp_path, monkeypatch):
    _write_policies(tmp_path)
    monkeypatch.setattr(validators, "POLICIES_DIR", str(tmp_path))
    monkeypatch.setattr(validators, "AIBOM_REQUIRED", False)

    result = validators.evaluate(_payload())

    assert result.allowed is True
    assert result.risk_score == 3
    assert result.within_sla is True
    assert result.notes == ["Include lineage evidence."]


def test_yaml_policy_denies_forbidden_data_with_human_readable_reason(tmp_path, monkeypatch):
    _write_policies(tmp_path)
    monkeypatch.setattr(validators, "POLICIES_DIR", str(tmp_path))
    monkeypatch.setattr(validators, "AIBOM_REQUIRED", False)

    result = validators.evaluate(_payload(flags={"contains_forbidden_data": True}))

    assert result.allowed is False
    assert "Forbidden data detected." in result.reasons


def test_yaml_policy_applies_conditional_safety_threshold(tmp_path, monkeypatch):
    _write_policies(tmp_path)
    monkeypatch.setattr(validators, "POLICIES_DIR", str(tmp_path))
    monkeypatch.setattr(validators, "AIBOM_REQUIRED", False)

    result = validators.evaluate(_payload(metrics={"accuracy": 0.94}))

    assert result.allowed is False
    assert "required_failed:metrics.accuracy" in result.reasons


def test_yaml_policy_blocks_computed_risk_above_threshold(tmp_path, monkeypatch):
    _write_policies(tmp_path)
    monkeypatch.setattr(validators, "POLICIES_DIR", str(tmp_path))
    monkeypatch.setattr(validators, "AIBOM_REQUIRED", False)
    payload = _payload(
        risk={
            "score": 0,
            "data_sensitivity": 5,
            "model_complexity": 5,
            "deployment_impact": 5,
            "monitoring_maturity": 0,
        }
    )

    result = validators.evaluate(payload)

    assert result.allowed is False
    assert result.risk_score == 45
    assert "required_failed:risk.score" in result.reasons


def test_yaml_policy_denies_missing_risk_factor(tmp_path, monkeypatch):
    _write_policies(tmp_path)
    monkeypatch.setattr(validators, "POLICIES_DIR", str(tmp_path))
    monkeypatch.setattr(validators, "AIBOM_REQUIRED", False)
    risk = _payload()["risk"]
    risk.pop("data_sensitivity")

    result = validators.evaluate(_payload(risk=risk))

    assert result.allowed is False
    assert "invalid_risk_factor:data_sensitivity" in result.reasons


def test_yaml_policy_denies_risk_factor_outside_documented_range(tmp_path, monkeypatch):
    _write_policies(tmp_path)
    monkeypatch.setattr(validators, "POLICIES_DIR", str(tmp_path))
    monkeypatch.setattr(validators, "AIBOM_REQUIRED", False)
    risk = _payload()["risk"]
    risk["data_sensitivity"] = 6

    result = validators.evaluate(_payload(risk=risk))

    assert result.allowed is False
    assert "invalid_risk_factor:data_sensitivity" in result.reasons


def test_aibom_verifies_signature_over_digest_string(tmp_path, monkeypatch):
    _write_policies(tmp_path)
    key_path = tmp_path / "aibom-public.pem"
    private_key = Ed25519PrivateKey.generate()
    key_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    monkeypatch.setattr(validators, "POLICIES_DIR", str(tmp_path))
    monkeypatch.setattr(validators, "AIBOM_PUBLIC_KEY_PATH", str(key_path))
    monkeypatch.setattr(validators, "AIBOM_REQUIRED", True)
    digest = "sha256:example-digest"
    signature = base64.b64encode(private_key.sign(digest.encode("utf-8"))).decode("ascii")

    result = validators.evaluate(_payload(aibom={"digest": digest, "signature_b64": signature}))

    assert result.allowed is True
    assert "aibom_verified" in result.reasons


def test_aibom_required_denies_missing_signature(tmp_path, monkeypatch):
    _write_policies(tmp_path)
    monkeypatch.setattr(validators, "POLICIES_DIR", str(tmp_path))
    monkeypatch.setattr(validators, "AIBOM_REQUIRED", True)

    result = validators.evaluate(_payload())

    assert result.allowed is False
    assert "aibom_missing_denied" in result.reasons
