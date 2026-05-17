from __future__ import annotations

import argparse
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from scenarios import run_named_scenario


CURSOR_OVERLAY_SCRIPT = r"""
(() => {
  if (window.__botCursorOverlayInstalled) return;
  window.__botCursorOverlayInstalled = true;

  const mount = () => {
    if (!document.body) {
      requestAnimationFrame(mount);
      return;
    }

    const cursor = document.createElement('div');
    cursor.id = '__bot_cursor_overlay';
    cursor.style.position = 'fixed';
    cursor.style.left = '0';
    cursor.style.top = '0';
    cursor.style.width = '14px';
    cursor.style.height = '14px';
    cursor.style.marginLeft = '-2px';
    cursor.style.marginTop = '-2px';
    cursor.style.border = '2px solid #00d4ff';
    cursor.style.borderRadius = '50%';
    cursor.style.background = 'rgba(0, 212, 255, 0.35)';
    cursor.style.pointerEvents = 'none';
    cursor.style.zIndex = '2147483647';
    cursor.style.transform = 'translate(-100px, -100px)';
    cursor.style.transition = 'transform 18ms linear';
    cursor.style.boxShadow = '0 0 0 2px rgba(0,0,0,0.15)';
    document.body.appendChild(cursor);

    document.addEventListener('mousemove', (event) => {
      cursor.style.transform = `translate(${event.clientX}px, ${event.clientY}px)`;
    }, true);

    document.addEventListener('mousedown', (event) => {
      const pulse = document.createElement('div');
      pulse.style.position = 'fixed';
      pulse.style.left = `${event.clientX - 8}px`;
      pulse.style.top = `${event.clientY - 8}px`;
      pulse.style.width = '16px';
      pulse.style.height = '16px';
      pulse.style.border = '2px solid #ff4d4d';
      pulse.style.borderRadius = '50%';
      pulse.style.pointerEvents = 'none';
      pulse.style.zIndex = '2147483647';
      pulse.style.opacity = '0.9';
      pulse.style.transform = 'scale(0.6)';
      pulse.style.transition = 'transform 180ms ease-out, opacity 180ms ease-out';
      document.body.appendChild(pulse);
      requestAnimationFrame(() => {
        pulse.style.transform = 'scale(1.8)';
        pulse.style.opacity = '0';
      });
      setTimeout(() => pulse.remove(), 220);
    }, true);
  };

  mount();
})();
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot runner for behavioral biometrics MVP")
    parser.add_argument(
        "--scenario",
        required=True,
        choices=["human_manual", "linear", "human_like", "adaptive", "replay"],
        help="Behavior scenario to execute",
    )
    parser.add_argument("--sessions", type=int, default=1)
    parser.add_argument("--target-url", default=os.getenv("BOT_TARGET_URL", "http://localhost:5173"))
    parser.add_argument("--replay-file", default="replay_sample.json")
    parser.add_argument("--manual-seconds", type=int, default=25)
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    parser.add_argument(
        "--slow-mo-ms",
        type=int,
        default=0,
        help="Delay each Playwright action by N ms (useful for live visualization)",
    )
    parser.add_argument(
        "--record-video",
        action="store_true",
        help="Record each session to MP4 for visualization",
    )
    parser.add_argument(
        "--show-cursor",
        action="store_true",
        help="Render synthetic cursor overlay in page (visible in recordings)",
    )
    parser.add_argument(
        "--video-dir",
        default=os.getenv("BOT_VIDEO_DIR", "/app/artifacts/videos"),
        help="Directory for Playwright video artifacts",
    )
    parser.add_argument(
        "--human-profile-url",
        default=os.getenv("HUMAN_PROFILE_URL", "http://backend:8000/api/v1/sessions/human-behavior-profile"),
        help="Backend endpoint with profile distilled from human sessions",
    )
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed, slow_mo=max(0, args.slow_mo_ms))
        try:
            for idx in range(args.sessions):
                context_kwargs: dict = {"viewport": {"width": 1366, "height": 768}}
                if args.record_video:
                    Path(args.video_dir).mkdir(parents=True, exist_ok=True)
                    context_kwargs["record_video_dir"] = args.video_dir
                    context_kwargs["record_video_size"] = {"width": 1366, "height": 768}

                context = browser.new_context(**context_kwargs)
                if args.show_cursor or args.record_video:
                    context.add_init_script(CURSOR_OVERLAY_SCRIPT)
                page = context.new_page()
                print(f"Running scenario={args.scenario} session={idx + 1}/{args.sessions}")
                run_named_scenario(
                    page=page,
                    scenario=args.scenario,
                    target_url=args.target_url,
                    replay_file=args.replay_file,
                    manual_seconds=args.manual_seconds,
                    human_profile_url=args.human_profile_url,
                )
                context.close()
                if args.record_video and page.video:
                    print(f"Video saved: {page.video.path()}")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
