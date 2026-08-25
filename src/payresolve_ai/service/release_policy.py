"""Non-autonomous W4 safe-degraded release wrapper."""

from __future__ import annotations

from typing import Any

from .contracts import RUNTIME_MODE

RELEASE = {
    "scope": "SAFE_DEGRADED_DEMO",
    "requires_human_review": True,
    "autonomous_action_allowed": False,
    "production_approved": False,
}


class ReleasePolicyError(RuntimeError):
    pass


def apply_safe_degraded_policy(
    *,
    request_id: str,
    core_output: dict[str, Any],
    intent_name: str,
    intent_confidence: float,
    versions: dict[str, str],
    latency: dict[str, float],
) -> dict[str, Any]:
    strategy = core_output.get("answer_strategy")
    if core_output.get("response_type") == "ABSTAIN_ESCALATE" and strategy == "ABSTAIN":
        response_type = "ABSTAIN_ESCALATE"
    elif core_output.get("response_type") == "ANSWER" and strategy == "STANDARD":
        response_type = "ANSWER_STANDARD"
    elif core_output.get("response_type") == "ANSWER" and strategy == "CORRECTIVE":
        response_type = "ANSWER_SAFE_CORRECTIVE"
    else:
        raise ReleasePolicyError("unrecognized candidate response taxonomy")

    reason_codes = (core_output.get("response_plan") or {}).get("reason_codes") or ["NO_REASON_CODE"]
    citations = list(core_output.get("citations") or [])
    evidence_key = "retrieved_evidence" if response_type == "ABSTAIN_ESCALATE" else "selected_evidence"
    evidence = list(core_output.get(evidence_key) or [])
    grounded = response_type != "ABSTAIN_ESCALATE" and bool(citations) and bool(evidence)
    if response_type != "ABSTAIN_ESCALATE" and not grounded:
        raise ReleasePolicyError("factual response lacks citations or selected evidence")
    return {
        "request_id": request_id,
        "runtime_mode": RUNTIME_MODE,
        "response_type": response_type,
        "intent": {"name": intent_name, "confidence": intent_confidence},
        "answer": str(core_output.get("answer_text") or ""),
        "reason": ";".join(str(item) for item in reason_codes),
        "grounded": grounded,
        "escalate": response_type == "ABSTAIN_ESCALATE",
        "citations": citations,
        "evidence": evidence,
        "release": dict(RELEASE),
        "versions": dict(versions),
        "latency": dict(latency),
    }
