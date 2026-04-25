from app.services.policy_engine import PolicyEngine


def test_policy_thresholds():
    engine = PolicyEngine()

    assert engine.decide(10).action == "allow"
    assert engine.decide(35).action == "observe"
    assert engine.decide(65).action == "throttle"
    assert engine.decide(85).action == "challenge"
    assert engine.decide(95).action == "block"
