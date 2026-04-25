import { FingerprintPayload } from "./types";

export function collectFingerprint(): FingerprintPayload {
  const nav = window.navigator as Navigator & {
    webdriver?: boolean;
    deviceMemory?: number;
  };

  const webdriver = Boolean(nav.webdriver);
  const userAgent = nav.userAgent || "unknown";
  const headlessHint = /Headless|PhantomJS|bot/i.test(userAgent);

  return {
    user_agent: userAgent,
    language: nav.language || "unknown",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "unknown",
    screen_width: window.screen.width,
    screen_height: window.screen.height,
    viewport_width: window.innerWidth,
    viewport_height: window.innerHeight,
    platform: nav.platform || "unknown",
    pointer_type: window.matchMedia("(pointer:fine)").matches ? "mouse" : "coarse",
    webdriver,
    headless_hint: headlessHint,
    hardware_concurrency: nav.hardwareConcurrency || 0,
    device_memory: nav.deviceMemory || 0,
  };
}
