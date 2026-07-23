import json
import re
from agent.state import DiagnosisState
from agent.llm import call_llm
from agent.utils import DIAGNOSIS_PROMPT


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {text[:200]}")
    return json.loads(match.group(0))

def diagnose(state: DiagnosisState) -> DiagnosisState:
    prompt = DIAGNOSIS_PROMPT.format(
        candidates=json.dumps(state["ranked_candidates"], indent=2, default=str),
        evidence=json.dumps(state["evidence_gathered"], indent=2, default=str),
        # metric_behavior=json.dumps(state["metric_behavior"], indent=2, default=str),
        candidate_confidence=json.dumps(state["phase3_confidence_gap"], indent=2, default=str),
    )
    response = call_llm(prompt)

    try:
        result = _extract_json(response)
    except (ValueError, json.JSONDecodeError) as e:
        # Fail safe rather than crashing the graph — surface it as a low-confidence,
        # no-action diagnosis so the loop-guard/human review path still triggers.
        state["hypothesis"] = f"LLM output could not be parsed: {e}"
        state["confidence"] = 0.0
        state["remediation_action"] = "none"
        state["needs_more_evidence"] = True
        state["diagnosed_root_cause"] = state["ranked_candidates"][0]["metric"] if state["ranked_candidates"] else None
        state["iterations"] += 1
        return state


    candidate_confidence = (
        state["ranked_candidates"][0]["confidence"]
        if state["ranked_candidates"]
        else 0
    )
    llm_confidence = float(result.get("confidence",0))

    state["confidence"] = min(candidate_confidence + 0.15, llm_confidence)

    state["hypothesis"] = result.get("hypothesis", "")

    # Update the remediation action only if the LLM suggests a new one. If it returns "none", we keep the existing action (if any) to avoid overwriting a previously determined safe action.
    new_action = result.get("recommended_action", "none")
    if new_action != "none":
        state["remediation_action"] = new_action

    state["diagnosed_root_cause"] = result.get("root_cause")
    state["needs_more_evidence"] = bool(result.get("needs_more_evidence", False))
    state["reasoning"] = result.get("reasoning", "")
    state["iterations"] += 1

    # print("Escalation decision:", state["needs_more_evidence"], "confidence:", state["confidence"])

    return state

def confidence_check(state: DiagnosisState) -> str:

    # hard safety limit
    if state["iterations"] >= 3:
        return "finalize"

    # confident diagnosis
    if state["confidence"] >= 0.6:
        return "finalize"

    if not state["needs_more_evidence"]:
        return "finalize"

    # uncertain diagnosis
    return "gather_evidence"
