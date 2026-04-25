import { TelemetryEvent } from "./types";

type CollectorOptions = {
  batchSize?: number;
  flushIntervalMs?: number;
  onBatch: (events: TelemetryEvent[]) => Promise<void>;
  onBufferedCount?: (count: number) => void;
  onAcceptedCount?: (count: number) => void;
  onError?: (error: unknown) => void;
};

export class TelemetryCollector {
  private readonly batchSize: number;
  private readonly flushIntervalMs: number;
  private readonly onBatch: (events: TelemetryEvent[]) => Promise<void>;
  private readonly onBufferedCount?: (count: number) => void;
  private readonly onAcceptedCount?: (count: number) => void;
  private readonly onError?: (error: unknown) => void;

  private sequenceNo = 0;
  private bufferedEvents: TelemetryEvent[] = [];
  private flushTimer: number | null = null;
  private isFlushing = false;
  private lastScrollY = window.scrollY;

  private listeners: Array<() => void> = [];

  constructor(options: CollectorOptions) {
    this.batchSize = options.batchSize ?? 35;
    this.flushIntervalMs = options.flushIntervalMs ?? 2000;
    this.onBatch = options.onBatch;
    this.onBufferedCount = options.onBufferedCount;
    this.onAcceptedCount = options.onAcceptedCount;
    this.onError = options.onError;
  }

  start() {
    this.attachListeners();
    this.flushTimer = window.setInterval(() => {
      void this.flush();
    }, this.flushIntervalMs);
  }

  stop() {
    this.listeners.forEach((removeListener) => removeListener());
    this.listeners = [];
    if (this.flushTimer !== null) {
      window.clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
    void this.flush();
  }

  private attachListeners() {
    const onMouseMove = (event: MouseEvent) => {
      this.record({
        event_type: "mousemove",
        x: event.clientX,
        y: event.clientY,
        pointer_type: "mouse",
        in_viewport: !document.hidden,
        payload: {},
      });
    };

    const onClick = (event: MouseEvent) => {
      const target = this.extractTargetInfo(event.target);
      this.record({
        event_type: "click",
        x: event.clientX,
        y: event.clientY,
        target_id: target.target_id,
        target_tag: target.target_tag,
        target_class: target.target_class,
        pointer_type: "mouse",
        in_viewport: !document.hidden,
        payload: { button: event.button },
      });
    };

    const onScroll = () => {
      const deltaY = window.scrollY - this.lastScrollY;
      this.lastScrollY = window.scrollY;
      this.record({
        event_type: "scroll",
        scroll_x: window.scrollX,
        scroll_y: window.scrollY,
        pointer_type: "mouse",
        in_viewport: !document.hidden,
        payload: { deltaY },
      });
    };

    const onFocus = () => {
      this.record({
        event_type: "focus",
        in_viewport: true,
        payload: {},
      });
    };

    const onBlur = () => {
      this.record({
        event_type: "blur",
        in_viewport: false,
        payload: {},
      });
    };

    const onVisibility = () => {
      this.record({
        event_type: document.hidden ? "viewport_leave" : "viewport_enter",
        in_viewport: !document.hidden,
        payload: { visibilityState: document.visibilityState },
      });
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("click", onClick, { passive: true });
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("focus", onFocus);
    window.addEventListener("blur", onBlur);
    document.addEventListener("visibilitychange", onVisibility);

    this.listeners.push(() => window.removeEventListener("mousemove", onMouseMove));
    this.listeners.push(() => window.removeEventListener("click", onClick));
    this.listeners.push(() => window.removeEventListener("scroll", onScroll));
    this.listeners.push(() => window.removeEventListener("focus", onFocus));
    this.listeners.push(() => window.removeEventListener("blur", onBlur));
    this.listeners.push(() => document.removeEventListener("visibilitychange", onVisibility));
  }

  private extractTargetInfo(target: EventTarget | null): {
    target_id?: string;
    target_tag?: string;
    target_class?: string;
  } {
    const element = target as HTMLElement | null;
    if (!element) {
      return {};
    }
    return {
      target_id: element.id || undefined,
      target_tag: element.tagName?.toLowerCase() || undefined,
      target_class: element.className || undefined,
    };
  }

  private record(event: Omit<TelemetryEvent, "sequence_no" | "ts_ms">) {
    this.sequenceNo += 1;
    this.bufferedEvents.push({
      sequence_no: this.sequenceNo,
      ts_ms: Date.now(),
      ...event,
    });

    this.onBufferedCount?.(this.bufferedEvents.length);

    if (this.bufferedEvents.length >= this.batchSize) {
      void this.flush();
    }
  }

  async flush() {
    if (this.isFlushing || this.bufferedEvents.length === 0) {
      return;
    }

    this.isFlushing = true;
    const batch = [...this.bufferedEvents];
    this.bufferedEvents = [];
    this.onBufferedCount?.(0);

    try {
      await this.onBatch(batch);
      this.onAcceptedCount?.(batch.length);
    } catch (error) {
      this.bufferedEvents = [...batch, ...this.bufferedEvents].slice(0, 300);
      this.onBufferedCount?.(this.bufferedEvents.length);
      this.onError?.(error);
    } finally {
      this.isFlushing = false;
    }
  }
}
