from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

BOT_SEARCH_PHRASES = (
    "vault",
    "router",
    "kamera ip",
    "fido2",
    "securemesh",
    "zero trust",
    "siem alerts",
    "incident response",
    "threat intel",
)


@dataclass(frozen=True)
class BehaviorProfile:
    move_step_mean_px: float = 22.0
    move_step_std_px: float = 11.0
    move_dt_mean_ms: float = 17.0
    move_dt_p90_ms: float = 33.0
    speed_mean_px_s: float = 980.0
    speed_p90_px_s: float = 2400.0
    click_interval_mean_ms: float = 680.0
    click_interval_p90_ms: float = 1600.0
    scroll_delta_mean: float = 260.0
    scroll_delta_p90: float = 620.0
    pause_prob: float = 0.08
    pause_mean_ms: float = 280.0
    pause_p90_ms: float = 720.0


def open_testbed(page: Page, target_url: str) -> None:
    page.goto(target_url, wait_until="networkidle")
    page.wait_for_timeout(1000)


def scenario_human_manual(page: Page, target_url: str, duration_seconds: int = 25) -> None:
    open_testbed(page, target_url)
    print(
        "Manual baseline: wykonuj interakcje myszką ręcznie w otwartym oknie przeglądarki "
        f"przez {duration_seconds} sekund."
    )
    page.wait_for_timeout(duration_seconds * 1000)


def scenario_linear(page: Page, target_url: str) -> None:
    open_testbed(page, target_url)
    start_points = [(80, 120), (280, 140), (520, 170), (780, 190), (980, 220)]

    for x, y in start_points:
        page.mouse.move(x, y, steps=12)
        time.sleep(0.02)

    selectors = [
        "#menu-products",
        "#filter-network",
        "#product-3-cart",
        "#newsletter-toggle",
        "#agree-toggle",
        "#cta-buy",
    ]

    for selector in selectors:
        locator = page.locator(selector)
        box = locator.bounding_box()
        if not box:
            continue
        target_x = box["x"] + box["width"] / 2
        target_y = box["y"] + box["height"] / 2
        page.mouse.move(target_x, target_y, steps=18)
        page.mouse.click(target_x, target_y)
        time.sleep(0.03)

    for y in [120, 260, 420, 580, 320, 140]:
        page.mouse.wheel(0, y)
        time.sleep(0.025)

    _type_random_search_phrase(page, min_delay=10, max_delay=35)

    if _click_if_present(page, "#label-bot"):
        page.wait_for_timeout(200)


def _bezier(p0, p1, p2, p3, t):
    return (
        (1 - t) ** 3 * p0
        + 3 * (1 - t) ** 2 * t * p1
        + 3 * (1 - t) * t**2 * p2
        + t**3 * p3
    )


def _move_bezier(page: Page, start: tuple[float, float], end: tuple[float, float], steps: int = 40):
    x0, y0 = start
    x3, y3 = end

    cp1 = (x0 + (x3 - x0) * 0.3 + random.uniform(-80, 80), y0 + random.uniform(-90, 90))
    cp2 = (x0 + (x3 - x0) * 0.7 + random.uniform(-80, 80), y3 + random.uniform(-90, 90))

    for i in range(1, steps + 1):
        t = i / steps
        x = _bezier(x0, cp1[0], cp2[0], x3, t) + random.uniform(-1.1, 1.1)
        y = _bezier(y0, cp1[1], cp2[1], y3, t) + random.uniform(-1.1, 1.1)
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.004, 0.02))


def _safe_bounding_box(page: Page, selector: str, timeout_ms: int = 3000):
    try:
        return page.locator(selector).bounding_box(timeout=timeout_ms)
    except PlaywrightTimeoutError:
        return None


def _click_if_present(page: Page, selector: str, timeout_ms: int = 3000) -> bool:
    box = _safe_bounding_box(page, selector, timeout_ms=timeout_ms)
    if not box:
        return False
    target_x = box["x"] + box["width"] / 2
    target_y = box["y"] + box["height"] / 2
    page.mouse.click(target_x, target_y)
    return True


def _type_random_search_phrase(page: Page, min_delay: int, max_delay: int) -> None:
    phrase = random.choice(BOT_SEARCH_PHRASES)
    if not _click_if_present(page, "#search-input", timeout_ms=2500):
        return
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.keyboard.type(phrase, delay=random.randint(min_delay, max_delay))


def scenario_human_like(page: Page, target_url: str) -> None:
    open_testbed(page, target_url)

    selectors = [
        "#menu-home",
        "#filter-software",
        "#product-4-details",
        "#product-4-cart",
        "#search-input",
        "#menu-products",
        "#newsletter-toggle",
        "#agree-toggle",
        "#cta-buy",
    ]

    current = (130.0, 120.0)
    for selector in selectors:
        box = _safe_bounding_box(page, selector)
        if not box:
            print(f"[human_like] Pomijam brakujący element: {selector}")
            continue

        target = (
            box["x"] + box["width"] * random.uniform(0.35, 0.65),
            box["y"] + box["height"] * random.uniform(0.35, 0.65),
        )
        _move_bezier(page, current, target, steps=random.randint(20, 50))

        should_click = selector in {"#search-input", "#filter-software"} or random.random() < 0.75
        if should_click:
            page.mouse.click(target[0], target[1])
            time.sleep(random.uniform(0.02, 0.18))

        if selector == "#search-input":
            _type_random_search_phrase(page, min_delay=40, max_delay=120)

        if random.random() < 0.3:
            page.mouse.wheel(0, random.randint(-250, 420))

        current = target

    _type_random_search_phrase(page, min_delay=25, max_delay=90)

    if _click_if_present(page, "#label-bot"):
        page.wait_for_timeout(200)


def _load_behavior_profile(profile_url: str | None) -> BehaviorProfile:
    if not profile_url:
        return BehaviorProfile()

    try:
        with urlopen(profile_url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return BehaviorProfile(
            move_step_mean_px=float(payload.get("move_step_mean_px", 22.0)),
            move_step_std_px=float(payload.get("move_step_std_px", 11.0)),
            move_dt_mean_ms=float(payload.get("move_dt_mean_ms", 17.0)),
            move_dt_p90_ms=float(payload.get("move_dt_p90_ms", 33.0)),
            speed_mean_px_s=float(payload.get("speed_mean_px_s", 980.0)),
            speed_p90_px_s=float(payload.get("speed_p90_px_s", 2400.0)),
            click_interval_mean_ms=float(payload.get("click_interval_mean_ms", 680.0)),
            click_interval_p90_ms=float(payload.get("click_interval_p90_ms", 1600.0)),
            scroll_delta_mean=float(payload.get("scroll_delta_mean", 260.0)),
            scroll_delta_p90=float(payload.get("scroll_delta_p90", 620.0)),
            pause_prob=float(payload.get("pause_prob", 0.08)),
            pause_mean_ms=float(payload.get("pause_mean_ms", 280.0)),
            pause_p90_ms=float(payload.get("pause_p90_ms", 720.0)),
        )
    except (URLError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"[adaptive] Nie udało się pobrać profilu human ({exc}), używam domyślnego.")
        return BehaviorProfile()


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _sample_gaussian(mean: float, std: float, lower: float, upper: float) -> float:
    value = random.gauss(mean, max(0.001, std))
    return _clamp(value, lower, upper)


def _sleep_move_dt(profile: BehaviorProfile, dt_scale: float = 1.0) -> None:
    dt_std = max(2.0, (profile.move_dt_p90_ms - profile.move_dt_mean_ms) / 1.4)
    dt_ms = _sample_gaussian(profile.move_dt_mean_ms, dt_std, 3.0, 45.0)
    dt_ms *= _clamp(dt_scale, 0.05, 4.5)
    time.sleep(dt_ms / 1000.0)


def _adaptive_move(
    page: Page,
    start: tuple[float, float],
    end: tuple[float, float],
    profile: BehaviorProfile,
    viewport: tuple[int, int],
) -> None:
    distance = math.hypot(end[0] - start[0], end[1] - start[1])
    step_mean = max(5.0, profile.move_step_mean_px)
    step_std = max(2.0, profile.move_step_std_px * 0.9)
    sampled_step = _sample_gaussian(step_mean * random.uniform(1.15, 2.7), step_std, 7.0, 120.0)
    steps = int(_clamp((distance / sampled_step) + random.uniform(2, 11), 6, 52))

    x0, y0 = start
    x3, y3 = end
    cp_jitter = _clamp(profile.move_step_std_px * 2.8, 14.0, 85.0)
    cp1 = (x0 + (x3 - x0) * 0.3 + random.uniform(-cp_jitter, cp_jitter), y0 + random.uniform(-cp_jitter, cp_jitter))
    cp2 = (x0 + (x3 - x0) * 0.7 + random.uniform(-cp_jitter, cp_jitter), y3 + random.uniform(-cp_jitter, cp_jitter))

    burst_enabled = random.random() < 0.96
    burst_start = int(steps * random.uniform(0.35, 0.62))
    burst_len = random.randint(2, 8)
    burst_end = min(steps, burst_start + burst_len)
    impulse_boost = random.uniform(0.2, 0.5)

    max_x, max_y = float(viewport[0] - 4), float(viewport[1] - 4)
    if distance > 140 and random.random() < 0.97:
        slow_anchor = (
            _clamp(x0 + (x3 - x0) * random.uniform(0.015, 0.045), 2.0, max_x),
            _clamp(y0 + (y3 - y0) * random.uniform(0.015, 0.045), 2.0, max_y),
        )
        page.mouse.move(slow_anchor[0], slow_anchor[1])
        time.sleep(random.uniform(0.18, 0.34))

        impulse = (
            _clamp(
                x0 + (x3 - x0) * random.uniform(0.65, 0.95) + random.uniform(-6.0, 6.0),
                2.0,
                max_x,
            ),
            _clamp(
                y0 + (y3 - y0) * random.uniform(0.65, 0.95) + random.uniform(-6.0, 6.0),
                2.0,
                max_y,
            ),
        )
        page.mouse.move(impulse[0], impulse[1])
        time.sleep(random.uniform(0.001, 0.003))
        page.mouse.move(
            _clamp(impulse[0] + random.uniform(-2.5, 2.5), 2.0, max_x),
            _clamp(impulse[1] + random.uniform(-2.5, 2.5), 2.0, max_y),
        )
        time.sleep(random.uniform(0.03, 0.08))
        page.mouse.move(
            _clamp(impulse[0] + (x3 - x0) * random.uniform(0.08, 0.16), 2.0, max_x),
            _clamp(impulse[1] + (y3 - y0) * random.uniform(0.08, 0.16), 2.0, max_y),
        )
        time.sleep(random.uniform(0.001, 0.004))
        x0, y0 = impulse
        distance = math.hypot(x3 - x0, y3 - y0)
        steps = int(_clamp((distance / sampled_step) + random.uniform(2, 8), 5, 36))

    for i in range(1, steps + 1):
        t = i / steps
        jitter = _clamp(profile.move_step_std_px / 9.0, 0.3, 2.4)
        x = _bezier(x0, cp1[0], cp2[0], x3, t)
        y = _bezier(y0, cp1[1], cp2[1], y3, t)

        dt_scale = 1.0
        if burst_enabled and burst_start <= i <= burst_end:
            phase = (i - burst_start) / max(1, burst_len)
            jitter *= random.uniform(1.35, 2.1)
            local_boost = impulse_boost * (1.05 - phase * 0.75)
            x += (x3 - x0) * local_boost
            y += (y3 - y0) * local_boost
            if i == burst_start:
                dt_scale = random.uniform(0.02, 0.06)
            else:
                dt_scale = random.uniform(0.03, 0.12)
        elif burst_enabled and i == burst_start - 1:
            x += random.uniform(-0.8, 0.8)
            y += random.uniform(-0.8, 0.8)
            dt_scale = random.uniform(2.7, 4.4)
        elif burst_enabled and i == burst_end + 1:
            dt_scale = random.uniform(2.2, 4.0)
        elif random.random() < 0.025:
            dt_scale = random.uniform(0.09, 0.24)

        x += random.uniform(-jitter, jitter)
        y += random.uniform(-jitter, jitter)
        page.mouse.move(_clamp(x, 2.0, max_x), _clamp(y, 2.0, max_y))
        _sleep_move_dt(profile, dt_scale=dt_scale)

    if random.random() < _clamp(profile.pause_prob, 0.01, 0.08):
        pause_std = max(16.0, (profile.pause_p90_ms - profile.pause_mean_ms) / 2.6)
        pause_ms = _sample_gaussian(profile.pause_mean_ms * 0.45, pause_std, 40.0, 420.0)
        time.sleep(pause_ms / 1000.0)


def _adaptive_scroll(page: Page, profile: BehaviorProfile) -> None:
    scroll_std = max(35.0, (profile.scroll_delta_p90 - profile.scroll_delta_mean) / 1.35)
    delta = _sample_gaussian(profile.scroll_delta_mean, scroll_std, 60.0, 900.0)
    if random.random() < 0.22:
        delta = -delta * random.uniform(0.35, 0.85)
    page.mouse.wheel(0, int(delta))


def scenario_adaptive(page: Page, target_url: str, human_profile_url: str | None = None) -> None:
    open_testbed(page, target_url)
    profile = _load_behavior_profile(human_profile_url)
    viewport = page.viewport_size or {"width": 1366, "height": 768}
    viewport_pair = (int(viewport["width"]), int(viewport["height"]))

    selectors = [
        "#menu-products",
        "#filter-network",
        "#product-3-details",
        "#product-3-cart",
        "#filter-software",
        "#product-4-details",
        "#product-4-cart",
        "#search-input",
        "#newsletter-toggle",
        "#agree-toggle",
        "#cta-buy",
    ]

    current = (random.uniform(80.0, 180.0), random.uniform(90.0, 170.0))
    char_delay_base = _clamp(profile.move_dt_mean_ms * 1.7, 18.0, 75.0)
    char_delay_jitter = max(10.0, (profile.click_interval_p90_ms - profile.click_interval_mean_ms) / 30.0)

    for selector in selectors:
        box = _safe_bounding_box(page, selector)
        if not box:
            print(f"[adaptive] Pomijam brakujący element: {selector}")
            continue

        target = (
            box["x"] + box["width"] * random.uniform(0.28, 0.72),
            box["y"] + box["height"] * random.uniform(0.28, 0.72),
        )

        if random.random() < 0.12:
            overshoot = (
                target[0] + random.uniform(-14.0, 14.0),
                target[1] + random.uniform(-12.0, 12.0),
            )
            _adaptive_move(page, current, overshoot, profile, viewport_pair)
            current = overshoot

        _adaptive_move(page, current, target, profile, viewport_pair)
        current = target

        click_prob = 0.92 if selector in {"#search-input", "#cta-buy", "#agree-toggle"} else 0.82
        if random.random() < click_prob:
            page.mouse.click(target[0], target[1])
            inter_click = _sample_gaussian(
                profile.click_interval_mean_ms / 8.0,
                max(16.0, (profile.click_interval_p90_ms - profile.click_interval_mean_ms) / 7.0),
                18.0,
                260.0,
            )
            time.sleep(inter_click / 1000.0)
            if random.random() < 0.15:
                page.mouse.click(
                    target[0] + random.uniform(-4.0, 4.0),
                    target[1] + random.uniform(-4.0, 4.0),
                )
                time.sleep(random.uniform(0.03, 0.16))

        if selector == "#search-input":
            phrase_count = random.randint(1, 2)
            for _ in range(phrase_count):
                phrase_delay = int(
                    _sample_gaussian(
                        char_delay_base,
                        char_delay_jitter,
                        20.0,
                        180.0,
                    )
                )
                _type_random_search_phrase(page, min_delay=max(8, phrase_delay - 12), max_delay=phrase_delay + 12)
                if random.random() < 0.45:
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                time.sleep(random.uniform(0.03, 0.16))

        if random.random() < 0.66:
            _adaptive_scroll(page, profile)
            time.sleep(random.uniform(0.02, 0.12))

    if random.random() < 0.18:
        neutral = (
            random.uniform(40.0, viewport_pair[0] - 40.0),
            random.uniform(40.0, viewport_pair[1] - 40.0),
        )
        _adaptive_move(page, current, neutral, profile, viewport_pair)

    if _click_if_present(page, "#label-bot"):
        page.wait_for_timeout(220)




def run_named_scenario(
    page: Page,
    scenario: str,
    target_url: str,
    replay_file: str,
    manual_seconds: int,
    human_profile_url: str | None = None,
) -> None:
    if scenario == "human_manual":
        scenario_human_manual(page, target_url, duration_seconds=manual_seconds)
        return
    if scenario == "linear":
        scenario_linear(page, target_url)
        return
    if scenario == "human_like":
        scenario_human_like(page, target_url)
        return
    if scenario == "adaptive":
        scenario_adaptive(page, target_url, human_profile_url=human_profile_url)
        return
    raise ValueError(f"Unknown scenario: {scenario}")
