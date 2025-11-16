import json
import os
import time
from dataclasses import dataclass
from typing import Any

import yaml
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

POLICIES_DIR = os.environ.get("POLICIES_DIR", "/app/policies")
AIBOM_PUBLIC_KEY_PATH = os.environ.get("AIBOM_PUBLIC_KEY_PATH", "/app/keys/aibom_public_key.pem")
AIBOM_REQUIRED = os.environ.get("AIBOM_REQUIRED", "false").lower() == "true"
GATE_SLA_MS = int(os.environ.get("GATE_SLA_MS", "1500"))


@dataclass
class GateResult:
    allowed: bool
    reasons: list[str]
    risk_score: float
    within_sla: bool
    elapsed_ms: int


def _load_yaml(name: str) -> dict[str, Any]:
    path = os.path.join(POLICIES_DIR, name)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_policies() -> tuple[dict[str, Any], dict[str, Any]]:
    model_policy = _load_yaml("model-policy.yml")
    risk_matrix = _load_yaml("risk-matrix.yml")
    return model_policy, risk_matrix


def _verify_aibom(payload: dict[str, Any]) -> tuple[bool, str]:
    """Optional AIBOM verification using Ed25519 public key.
    Expected structure:
    payload["aibom"] = {"data": <object>, "signature": <hex/base64>}
    We canonicalize JSON for verification; signature is assumed hex-encoded.
    """
    aibom = payload.get("aibom")
    if not aibom:
        return (
            not AIBOM_REQUIRED,
            "aibom_missing_allowed" if not AIBOM_REQUIRED else "aibom_missing_denied",
        )

    try:
        with open(AIBOM_PUBLIC_KEY_PATH, "rb") as f:
            pub_bytes = f.read()
        public_key = serialization.load_pem_public_key(pub_bytes)
        if not isinstance(public_key, Ed25519PublicKey):
            return False, "aibom_public_key_not_ed25519"

        data_canonical = json.dumps(
            aibom.get("data"), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        sig_hex = aibom.get("signature")
        if not isinstance(sig_hex, str):
            return (False, "aibom_signature_missing")
        try:
            sig = bytes.fromhex(sig_hex)
        except ValueError:
            return (False, "aibom_signature_not_hex")
        public_key.verify(sig, data_canonical)
        return True, "aibom_verified"
    except FileNotFoundError:
        # If required, deny; otherwise allow with note
        return (not AIBOM_REQUIRED, "aibom_pubkey_not_found")
    except InvalidSignature:
        return False, "aibom_signature_invalid"
    except Exception as e:
        return False, f"aibom_error:{e}"


def _compute_risk(payload: dict[str, Any], risk_matrix: dict[str, Any]) -> tuple[float, list[str]]:
    """Compute a simple risk score.
    Supports two schemas:
    1) risk-matrix with 'weights' and optional 'thresholds'. Expects payload['risk'] to contain numeric factors.
    2) legacy 'class_base' / 'use_case_base' style maps.
    """
    reasons: list[str] = []
    score = 0.0

    # Newer schema: weights * factors
    weights = risk_matrix.get("weights")
    if isinstance(weights, dict):
        factors = payload.get("risk", {}) or {}
        if isinstance(factors, dict):
            for k, w in weights.items():
                try:
                    v = float(factors.get(k, 0))
                    score += float(w) * v
                    if v:
                        reasons.append(f"risk:{k}*{w}={v*w}")
                except Exception:
                    continue
            return score, reasons

    # Legacy schema fallback
    model_class = payload.get("model_class") or payload.get("model_type") or "unknown"
    use_case = payload.get("use_case", "unknown")
    region = payload.get("region", "global")

    class_map = risk_matrix.get("class_base") or {}
    use_map = risk_matrix.get("use_case_base") or {}
    region_map = risk_matrix.get("region_modifiers") or {}

    if model_class in class_map:
        score += float(class_map[model_class])
        reasons.append(f"class:{model_class}")
    if use_case in use_map:
        score += float(use_map[use_case])
        reasons.append(f"use_case:{use_case}")
    if region in region_map:
        score += float(region_map[region])
        reasons.append(f"region:{region}")
    return score, reasons


def evaluate(payload: dict[str, Any]) -> GateResult:
    t0 = time.perf_counter_ns()
    policies, risk_matrix = _load_policies()

    # 1) AIBOM verification (optional)
    aibom_ok, aibom_reason = _verify_aibom(payload)

    reasons: list[str] = []
    if not aibom_ok:
        reasons.append(aibom_reason)
    else:
        if aibom_reason:
            reasons.append(aibom_reason)

    # 2) Risk computation
    score, risk_reasons = _compute_risk(payload, risk_matrix)
    reasons.extend(risk_reasons)

    # 3) Threshold evaluation from model-policy.yml
    # Expected keys: required/deny lists, max_risk
    max_risk = float(policies.get("max_risk", 5.0))

    # Explicit deny rules (simple contains checks)
    deny_rules = policies.get("deny", []) or []
    for rule in deny_rules:
        # rule example: { field: "use_case", equals: "ads-targeting" }
        field = rule.get("field")
        equals = rule.get("equals")
        if field and equals is not None and str(payload.get(field)) == str(equals):
            reasons.append(f"deny:{field}={equals}")
            allowed = False
            elapsed_ms = int((time.perf_counter_ns() - t0) / 1_000_000)
            return GateResult(
                allowed=allowed,
                reasons=reasons,
                risk_score=score,
                within_sla=(elapsed_ms <= GATE_SLA_MS),
                elapsed_ms=elapsed_ms,
            )

    # Required fields
    req_fields = policies.get("required", []) or []
    missing = [f for f in req_fields if payload.get(f) in (None, "")]
    if missing:
        reasons.append("missing:" + ",".join(missing))
        allowed = False
        elapsed_ms = int((time.perf_counter_ns() - t0) / 1_000_000)
        return GateResult(
            allowed=allowed,
            reasons=reasons,
            risk_score=score,
            within_sla=(elapsed_ms <= GATE_SLA_MS),
            elapsed_ms=elapsed_ms,
        )

    # Risk threshold
    allowed = aibom_ok and (score <= max_risk)
    if not allowed and score > max_risk:
        reasons.append(f"risk_exceeds:{score}>{max_risk}")

    elapsed_ms = int((time.perf_counter_ns() - t0) / 1_000_000)
    return GateResult(
        allowed=allowed,
        reasons=reasons,
        risk_score=score,
        within_sla=(elapsed_ms <= GATE_SLA_MS),
        elapsed_ms=elapsed_ms,
    )
