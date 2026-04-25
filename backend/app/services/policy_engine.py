from dataclasses import dataclass


@dataclass
class PolicyDecision:
    action: str
    reason: str


class PolicyEngine:
    def __init__(
        self,
        low_risk_threshold: float = 25.0,
        moderate_risk_threshold: float = 50.0,
        high_risk_threshold: float = 75.0,
        critical_risk_threshold: float = 90.0,
    ) -> None:
        self.low_risk_threshold = low_risk_threshold
        self.moderate_risk_threshold = moderate_risk_threshold
        self.high_risk_threshold = high_risk_threshold
        self.critical_risk_threshold = critical_risk_threshold

    def decide(self, risk_score: float) -> PolicyDecision:
        if risk_score < self.low_risk_threshold:
            return PolicyDecision(action="allow", reason="Niskie ryzyko zachowania botowego")
        if risk_score < self.moderate_risk_threshold:
            return PolicyDecision(action="observe", reason="Umiarkowane ryzyko, zwiększamy monitoring")
        if risk_score < self.high_risk_threshold:
            return PolicyDecision(action="throttle", reason="Wysokie ryzyko, ograniczamy tempo żądań")
        if risk_score < self.critical_risk_threshold:
            return PolicyDecision(action="challenge", reason="Bardzo wysokie ryzyko, wymagamy dodatkowej weryfikacji")
        return PolicyDecision(action="block", reason="Krytyczne ryzyko, sesja została zablokowana")
