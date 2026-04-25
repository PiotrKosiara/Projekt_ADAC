from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path

from playwright.sync_api import Page


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


def scenario_human_like(page: Page, target_url: str) -> None:
    open_testbed(page, target_url)

    selectors = [
        "#menu-home",
        "#search-input",
        "#filter-software",
        "#product-4-details",
        "#product-4-cart",
        "#newsletter-toggle",
        "#agree-toggle",
        "#cta-buy",
    ]

    current = (130.0, 120.0)
    for selector in selectors:
        box = page.locator(selector).bounding_box()
        if not box:
            continue

        target = (
            box["x"] + box["width"] * random.uniform(0.35, 0.65),
            box["y"] + box["height"] * random.uniform(0.35, 0.65),
        )
        _move_bezier(page, current, target, steps=random.randint(20, 50))

        if random.random() < 0.75:
            page.mouse.click(target[0], target[1])
            time.sleep(random.uniform(0.02, 0.18))

        if selector == "#search-input":
            page.keyboard.type("router secure", delay=random.randint(40, 120))

        if random.random() < 0.3:
            page.mouse.wheel(0, random.randint(-250, 420))

        current = target


def scenario_replay(page: Page, target_url: str, replay_file: str) -> None:
    open_testbed(page, target_url)

    replay_path = Path(replay_file)
    data = json.loads(replay_path.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise RuntimeError("Replay file must contain a list of points")

    for point in data:
        x = float(point.get("x", 0))
        y = float(point.get("y", 0))
        delay_ms = max(1, int(point.get("delay_ms", 20)))
        page.mouse.move(x, y)
        if point.get("click"):
            page.mouse.click(x, y)
        page.wait_for_timeout(delay_ms)

    page.wait_for_timeout(700)


def run_named_scenario(page: Page, scenario: str, target_url: str, replay_file: str, manual_seconds: int) -> None:
    if scenario == "human_manual":
        scenario_human_manual(page, target_url, duration_seconds=manual_seconds)
        return
    if scenario == "linear":
        scenario_linear(page, target_url)
        return
    if scenario == "human_like":
        scenario_human_like(page, target_url)
        return
    if scenario == "replay":
        scenario_replay(page, target_url, replay_file)
        return
    raise ValueError(f"Unknown scenario: {scenario}")
