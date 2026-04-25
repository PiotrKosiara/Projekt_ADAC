from __future__ import annotations

import argparse
import os

from playwright.sync_api import sync_playwright

from scenarios import run_named_scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot runner for behavioral biometrics MVP")
    parser.add_argument(
        "--scenario",
        required=True,
        choices=["human_manual", "linear", "human_like", "replay"],
        help="Behavior scenario to execute",
    )
    parser.add_argument("--sessions", type=int, default=1)
    parser.add_argument("--target-url", default=os.getenv("BOT_TARGET_URL", "http://localhost:5173"))
    parser.add_argument("--replay-file", default="replay_sample.json")
    parser.add_argument("--manual-seconds", type=int, default=25)
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        try:
            for idx in range(args.sessions):
                context = browser.new_context(viewport={"width": 1366, "height": 768})
                page = context.new_page()
                print(f"Running scenario={args.scenario} session={idx + 1}/{args.sessions}")
                run_named_scenario(
                    page=page,
                    scenario=args.scenario,
                    target_url=args.target_url,
                    replay_file=args.replay_file,
                    manual_seconds=args.manual_seconds,
                )
                context.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
