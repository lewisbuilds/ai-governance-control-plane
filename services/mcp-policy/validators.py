"""Policy and risk evaluation for the YAML driven governance gate."""

from __future__ import annotations

import base64
import binascii
import math
import os
import time
from collections.abc import Callable
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
    notes: list[str]


def _load_yaml(name: str) -> dict[str, Any]:
    path = os.path.join(POLICIES_DIR, name)
    with open(path, encoding="utf-8") as policy_file:
        return yaml.safe_load(policy_file) or {}


def _load_policies() -> tuple[dict[str, Any], dict[str, Any]]:
    return _load_yaml("model-policy.yml"), _load_yaml("risk-matrix.yml")


def _verify_aibom(payload: dict[str, Any]) -> tuple[bool, str]:
    """Verify an Ed25519 signature over the exact UTF-8 AIBOM digest string."""
    aibom = payload.get("aibom")
    if not aibom:
        return (
            not AIBOM_REQUIRED,
            "aibom_missing_allowed" if not AIBOM_REQUIRED else "aibom_missing_denied",
        )
    if not isinstance(aibom, dict):
        return False, "aibom_must_be_object"

    digest = aibom.get("digest")
    signature_b64 = aibom.get("signature_b64")
    if not isinstance(digest, str) or not digest:
        return False, "aibom_digest_missing"
    if not isinstance(signature_b64, str):
        return False, "aibom_signature_missing"

    try:
        with open(AIBOM_PUBLIC_KEY_PATH, "rb") as key_file:
            public_key = serialization.load_pem_public_key(key_file.read())
        if not isinstance(public_key, Ed25519PublicKey):
            return False, "aibom_public_key_not_ed25519"
        signature = base64.b64decode(signature_b64, validate=True)
        public_key.verify(signature, digest.encode("utf-8"))
    except FileNotFoundError:
        return False, "aibom_public_key_not_found"
    except (ValueError, binascii.Error):
        return False, "aibom_signature_not_base64"
    except InvalidSignature:
        return False, "aibom_signature_invalid"
    except (OSError, TypeError) as exc:
        return False, f"aibom_verification_error:{type(exc).__name__}"
    return True, "aibom_verified"


def _compute_risk(payload: dict[str, Any], risk_matrix: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    weights = risk_matrix.get("weights", {})
    factors = payload.get("risk", {})
    if not isinstance(weights, dict) or not isinstance(factors, dict):
        return score, reasons
    for name, weight in weights.items():
        raw_value = factors.get(name)
        if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
            reasons.append(f"invalid_risk_factor:{name}")
            continue
        value = float(raw_value)
        try:
            numeric_weight = float(weight)
        except (TypeError, ValueError):
            reasons.append(f"invalid_risk_weight:{name}")
            continue
        if not math.isfinite(value) or not math.isfinite(numeric_weight) or not 0 <= value <= 5:
            reasons.append(f"invalid_risk_factor:{name}")
            continue
        contribution = numeric_weight * value
        score += contribution
        if value:
            reasons.append(f"risk:{name}*{weight}={contribution}")
    return score, reasons


def _dot_get(data: Any, path: str) -> Any:
    value = data
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _resolve_value(rule: dict[str, Any], policy: dict[str, Any]) -> Any:
    if "value_from" in rule:
        return _dot_get(policy, str(rule["value_from"]))
    return rule.get("value")


_OPS: dict[str, Callable[[Any, Any], bool]] = {
    "eq": lambda actual, expected: actual == expected,
    "ne": lambda actual, expected: actual != expected,
    "gt": lambda actual, expected: actual is not None and actual > expected,
    "gte": lambda actual, expected: actual is not None and actual >= expected,
    "lt": lambda actual, expected: actual is not None and actual < expected,
    "lte": lambda actual, expected: actual is not None and actual <= expected,
    "in": lambda actual, expected: actual in expected,
    "not_in": lambda actual, expected: actual not in expected,
    "contains": lambda actual, expected: expected in actual,
}


def _matches(rule: dict[str, Any], payload: dict[str, Any], policy: dict[str, Any]) -> bool:
    field = rule.get("field")
    operation = _OPS.get(str(rule.get("op", "eq")))
    if not isinstance(field, str) or operation is None:
        return False
    actual = _dot_get(payload, field)
    expected = _resolve_value(rule, policy)
    try:
        return operation(actual, expected)
    except (TypeError, ValueError):
        return False


def _condition_applies(
    rule: dict[str, Any], payload: dict[str, Any], policy: dict[str, Any]
) -> bool:
    condition = rule.get("when")
    return not isinstance(condition, dict) or _matches(condition, payload, policy)


def evaluate(payload: dict[str, Any]) -> GateResult:
    start = time.perf_counter_ns()
    policies, risk_matrix = _load_policies()
    risk = payload.get("risk", {})
    invalid_risk_type = not isinstance(risk, dict)
    risk = {} if invalid_risk_type else risk
    score, reasons = _compute_risk({**payload, "risk": risk}, risk_matrix)
    if invalid_risk_type:
        reasons.append("invalid_risk_factor:risk_must_be_object")
    aibom_ok, aibom_reason = _verify_aibom(payload)
    reasons.append(aibom_reason)

    # The policy always evaluates the score computed from the configured risk factors.
    evaluated_payload = {**payload, "risk": {**risk, "score": score}}

    required_failures: list[str] = []
    for rule in policies.get("require", []) or []:
        if (
            isinstance(rule, dict)
            and _condition_applies(rule, evaluated_payload, policies)
            and not _matches(rule, evaluated_payload, policies)
        ):
            required_failures.append(str(rule.get("field", "unknown")))
    if required_failures:
        reasons.extend(f"required_failed:{field}" for field in required_failures)

    denied: list[str] = []
    for rule in policies.get("deny", []) or []:
        if (
            isinstance(rule, dict)
            and _condition_applies(rule, evaluated_payload, policies)
            and _matches(rule, evaluated_payload, policies)
        ):
            denied.append(str(rule.get("reason") or f"denied:{rule.get('field', 'unknown')}"))
    reasons.extend(denied)

    notes = [str(note) for note in policies.get("notes", []) or []]
    has_invalid_risk = any(reason.startswith("invalid_risk_") for reason in reasons)
    allowed = aibom_ok and not has_invalid_risk and not required_failures and not denied
    elapsed_ms = int((time.perf_counter_ns() - start) / 1_000_000)
    within_sla = elapsed_ms <= GATE_SLA_MS
    if not within_sla:
        reasons.append(f"warn:gate_sla_exceeded:{elapsed_ms}ms>{GATE_SLA_MS}ms")
    return GateResult(allowed, reasons, score, within_sla, elapsed_ms, notes)
