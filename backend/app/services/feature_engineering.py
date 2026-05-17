from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

import numpy as np


FEATURE_COLUMNS = [
    "event_count",
    "window_duration_ms",
    "mousemove_count",
    "click_count",
    "scroll_count",
    "focus_blur_transitions",
    "viewport_enter_count",
    "viewport_leave_count",
    "path_length",
    "displacement",
    "path_efficiency",
    "speed_mean",
    "speed_std",
    "speed_max",
    "acc_mean",
    "acc_std",
    "acc_max",
    "jerk_mean",
    "jerk_std",
    "jerk_max",
    "curvature_mean",
    "curvature_std",
    "angle_change_mean",
    "angle_change_std",
    "micro_pause_count",
    "correction_rhythm",
    "click_interval_mean",
    "click_interval_std",
    "hover_before_click_mean",
    "dwell_time_mean",
    "overshoot_count",
    "target_revisit_count",
    "scroll_velocity_mean",
    "scroll_velocity_std",
    "unique_event_types",
    "event_type_entropy",
    "webdriver_flag",
    "headless_flag",
    "viewport_area",
    "screen_area",
    "viewport_screen_ratio",
    "hardware_concurrency",
    "device_memory",
]

ENVIRONMENT_FEATURE_COLUMNS = [
    "webdriver_flag",
    "headless_flag",
    "viewport_area",
    "screen_area",
    "viewport_screen_ratio",
    "hardware_concurrency",
    "device_memory",
]

BEHAVIORAL_FEATURE_COLUMNS = [
    column for column in FEATURE_COLUMNS if column not in ENVIRONMENT_FEATURE_COLUMNS
]


@dataclass
class SimpleEvent:
    event_type: str
    ts_ms: int
    x: float | None = None
    y: float | None = None
    scroll_x: float | None = None
    scroll_y: float | None = None
    target_id: str | None = None
    in_viewport: bool | None = None


def _safe_mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def _safe_std(values: list[float]) -> float:
    return float(np.std(values)) if values else 0.0


def _safe_max(values: list[float]) -> float:
    return float(np.max(values)) if values else 0.0


def _vector_angle(dx: float, dy: float) -> float:
    return math.atan2(dy, dx)


def _angle_diff(a1: float, a2: float) -> float:
    diff = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
    return abs(diff)


def _entropy(counter: Counter[str]) -> float:
    total = sum(counter.values())
    if total == 0:
        return 0.0
    probabilities = [count / total for count in counter.values()]
    return float(-sum(p * math.log2(p) for p in probabilities if p > 0))


def _coerce_event(event: object) -> SimpleEvent:
    return SimpleEvent(
        event_type=getattr(event, "event_type"),
        ts_ms=int(getattr(event, "ts_ms")),
        x=getattr(event, "x", None),
        y=getattr(event, "y", None),
        scroll_x=getattr(event, "scroll_x", None),
        scroll_y=getattr(event, "scroll_y", None),
        target_id=getattr(event, "target_id", None),
        in_viewport=getattr(event, "in_viewport", None),
    )


def build_feature_vector(events: Iterable[object], environment: dict | None = None) -> dict[str, float]:
    ordered_events = sorted((_coerce_event(ev) for ev in events), key=lambda e: e.ts_ms)
    environment = environment or {}

    if not ordered_events:
        return {column: 0.0 for column in FEATURE_COLUMNS}

    event_counter = Counter(event.event_type for event in ordered_events)

    speeds: list[float] = []
    accelerations: list[float] = []
    jerks: list[float] = []
    curvatures: list[float] = []
    angle_changes: list[float] = []
    scroll_velocities: list[float] = []

    click_times: list[int] = []
    dwell_durations: list[float] = []
    hover_before_click: list[float] = []

    path_length = 0.0
    displacement = 0.0
    micro_pause_count = 0
    correction_rhythm = 0
    overshoot_count = 0
    target_revisit_count = 0

    last_move = None
    last_speed = None
    last_acc = None
    last_angle = None

    target_click_counter: Counter[str] = Counter()

    for event in ordered_events:
        if event.event_type == "click":
            click_times.append(event.ts_ms)
            if event.target_id:
                target_click_counter[event.target_id] += 1
            if last_move is not None and event.x is not None and event.y is not None:
                dt_hover_ms = max(0, event.ts_ms - int(last_move.ts_ms))
                if (
                    last_move.x is not None
                    and last_move.y is not None
                    and math.dist((event.x, event.y), (last_move.x, last_move.y)) < 35
                ):
                    hover_before_click.append(float(dt_hover_ms))

    if target_click_counter:
        target_revisit_count = sum(1 for count in target_click_counter.values() if count > 1)

    for prev, cur in zip(ordered_events[:-1], ordered_events[1:]):
        dt_ms = max(1, cur.ts_ms - prev.ts_ms)
        dt_s = dt_ms / 1000.0

        if cur.event_type == "scroll" and prev.scroll_y is not None and cur.scroll_y is not None:
            scroll_velocities.append(abs(cur.scroll_y - prev.scroll_y) / dt_s)

        if prev.x is None or prev.y is None or cur.x is None or cur.y is None:
            continue

        dx = cur.x - prev.x
        dy = cur.y - prev.y
        distance = math.hypot(dx, dy)
        path_length += distance

        speed = distance / dt_s
        speeds.append(speed)

        if speed < 40:
            micro_pause_count += 1

        angle = _vector_angle(dx, dy)
        if last_angle is not None:
            angle_diff = _angle_diff(last_angle, angle)
            angle_changes.append(angle_diff)
            curvatures.append(angle_diff / max(distance, 1.0))
            if angle_diff > 1.1:
                correction_rhythm += 1
        last_angle = angle

        if last_speed is not None:
            acc = (speed - last_speed) / dt_s
            accelerations.append(acc)
            if last_acc is not None:
                jerks.append((acc - last_acc) / dt_s)
            last_acc = acc
        last_speed = speed

        if prev.event_type == "mousemove":
            last_move = cur

    first = ordered_events[0]
    last = ordered_events[-1]
    if (
        first.x is not None
        and first.y is not None
        and last.x is not None
        and last.y is not None
    ):
        displacement = math.dist((first.x, first.y), (last.x, last.y))

    if speeds:
        dwell_durations = [1000.0 / max(speed, 1.0) for speed in speeds]

    for click_ts in click_times:
        prior_moves = [
            event for event in ordered_events if event.event_type == "mousemove" and event.ts_ms < click_ts
        ]
        if len(prior_moves) >= 4:
            recent = prior_moves[-4:]
            reversal_count = 0
            previous_sign = None
            for prev, cur in zip(recent[:-1], recent[1:]):
                if prev.x is None or cur.x is None:
                    continue
                sign = 1 if cur.x - prev.x >= 0 else -1
                if previous_sign is not None and sign != previous_sign:
                    reversal_count += 1
                previous_sign = sign
            if reversal_count >= 2:
                overshoot_count += 1

    click_intervals = [
        float(cur - prev) for prev, cur in zip(click_times[:-1], click_times[1:]) if cur - prev > 0
    ]

    window_duration_ms = max(1, ordered_events[-1].ts_ms - ordered_events[0].ts_ms)

    viewport_width = float(environment.get("viewport_width") or 0)
    viewport_height = float(environment.get("viewport_height") or 0)
    screen_width = float(environment.get("screen_width") or 0)
    screen_height = float(environment.get("screen_height") or 0)

    vector = {
        "event_count": float(len(ordered_events)),
        "window_duration_ms": float(window_duration_ms),
        "mousemove_count": float(event_counter.get("mousemove", 0)),
        "click_count": float(event_counter.get("click", 0)),
        "scroll_count": float(event_counter.get("scroll", 0)),
        "focus_blur_transitions": float(event_counter.get("focus", 0) + event_counter.get("blur", 0)),
        "viewport_enter_count": float(event_counter.get("viewport_enter", 0)),
        "viewport_leave_count": float(event_counter.get("viewport_leave", 0)),
        "path_length": float(path_length),
        "displacement": float(displacement),
        "path_efficiency": float(displacement / max(path_length, 1.0)),
        "speed_mean": _safe_mean(speeds),
        "speed_std": _safe_std(speeds),
        "speed_max": _safe_max(speeds),
        "acc_mean": _safe_mean(accelerations),
        "acc_std": _safe_std(accelerations),
        "acc_max": _safe_max(accelerations),
        "jerk_mean": _safe_mean(jerks),
        "jerk_std": _safe_std(jerks),
        "jerk_max": _safe_max(jerks),
        "curvature_mean": _safe_mean(curvatures),
        "curvature_std": _safe_std(curvatures),
        "angle_change_mean": _safe_mean(angle_changes),
        "angle_change_std": _safe_std(angle_changes),
        "micro_pause_count": float(micro_pause_count),
        "correction_rhythm": float(correction_rhythm),
        "click_interval_mean": _safe_mean(click_intervals),
        "click_interval_std": _safe_std(click_intervals),
        "hover_before_click_mean": _safe_mean(hover_before_click),
        "dwell_time_mean": _safe_mean(dwell_durations),
        "overshoot_count": float(overshoot_count),
        "target_revisit_count": float(target_revisit_count),
        "scroll_velocity_mean": _safe_mean(scroll_velocities),
        "scroll_velocity_std": _safe_std(scroll_velocities),
        "unique_event_types": float(len(event_counter)),
        "event_type_entropy": _entropy(event_counter),
        "webdriver_flag": float(bool(environment.get("webdriver"))),
        "headless_flag": float(bool(environment.get("headless_hint"))),
        "viewport_area": viewport_width * viewport_height,
        "screen_area": screen_width * screen_height,
        "viewport_screen_ratio": (viewport_width * viewport_height)
        / max(screen_width * screen_height, 1.0),
        "hardware_concurrency": float(environment.get("hardware_concurrency") or 0),
        "device_memory": float(environment.get("device_memory") or 0),
    }

    for column in FEATURE_COLUMNS:
        vector.setdefault(column, 0.0)

    return vector


def to_feature_array(vector: dict[str, float]) -> list[float]:
    return [float(vector.get(column, 0.0)) for column in FEATURE_COLUMNS]
