from types import SimpleNamespace

from app.services.feature_engineering import FEATURE_COLUMNS, build_feature_vector


def test_feature_vector_contains_required_columns():
    events = [
        SimpleNamespace(event_type="mousemove", ts_ms=1000, x=10.0, y=20.0, scroll_x=0.0, scroll_y=0.0, target_id=None, in_viewport=True),
        SimpleNamespace(event_type="mousemove", ts_ms=1020, x=30.0, y=40.0, scroll_x=0.0, scroll_y=0.0, target_id=None, in_viewport=True),
        SimpleNamespace(event_type="click", ts_ms=1200, x=30.0, y=40.0, scroll_x=0.0, scroll_y=0.0, target_id="cta-buy", in_viewport=True),
        SimpleNamespace(event_type="scroll", ts_ms=1300, x=None, y=None, scroll_x=0.0, scroll_y=240.0, target_id=None, in_viewport=True),
        SimpleNamespace(event_type="blur", ts_ms=1400, x=None, y=None, scroll_x=0.0, scroll_y=240.0, target_id=None, in_viewport=False),
    ]

    env = {
        "viewport_width": 1200,
        "viewport_height": 700,
        "screen_width": 1920,
        "screen_height": 1080,
        "webdriver": False,
        "headless_hint": False,
    }

    vector = build_feature_vector(events, env)

    for column in FEATURE_COLUMNS:
        assert column in vector

    assert vector["event_count"] == 5
    assert vector["click_count"] >= 1
    assert vector["path_length"] > 0
    assert vector["speed_mean"] >= 0
