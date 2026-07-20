from typing import TypedDict, Optional, Any
from datetime import datetime

class IncidentWindow(TypedDict):
    start: datetime
    end: datetime

    metrics: dict[str, Any]

    alerts: list[dict]

class Candidate(TypedDict):
    metric: str

    # Candidate ranking from detector
    confidence: float
    prior: float
    corr: float
    onset_rank: float

    # Underlying anomaly
    onset: datetime
    offset: datetime
    peak_score: float

    explains: list[str]


class DiagnosisState(TypedDict):
    incident_window: IncidentWindow
    # detector output
    ranked_candidates: list[Candidate]
    evidence_gathered: list[dict[str, Any]]
    # current LLM-generated explanation
    hypothesis: Optional[str]
    # LLM confidence
    confidence: float 
    iterations: int
    remediation_action: Optional[str]
    requires_approval: bool