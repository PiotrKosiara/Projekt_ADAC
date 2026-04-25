import { useEffect, useRef, useState } from "react";

import {
  createSession,
  labelSession,
  PredictionResponse,
  requestPrediction,
  sendEventsBatch,
} from "./api/client";
import { InteractionPanel } from "./components/InteractionPanel";
import { PredictionPanel } from "./components/PredictionPanel";
import { TelemetryCollector } from "./telemetry/collector";
import { collectFingerprint } from "./telemetry/fingerprint";

function App() {
  const collectorRef = useRef<TelemetryCollector | null>(null);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [bufferedCount, setBufferedCount] = useState(0);
  const [acceptedCount, setAcceptedCount] = useState(0);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [loadingPrediction, setLoadingPrediction] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Inicjalizacja...");

  useEffect(() => {
    let active = true;

    const bootstrap = async () => {
      try {
        const fingerprint = collectFingerprint();
        const session = await createSession({
          source: "frontend_manual",
          client_fingerprint: fingerprint,
          environment: {
            ...fingerprint,
            page: window.location.pathname,
            referrer: document.referrer,
            started_at: new Date().toISOString(),
          },
        });

        if (!active) {
          return;
        }

        setSessionId(session.session_id);
        setStatusMessage("Sesja telemetryczna aktywna");

        const collector = new TelemetryCollector({
          batchSize: 35,
          flushIntervalMs: 2000,
          onBatch: async (events) => {
            await sendEventsBatch(session.session_id, events);
          },
          onBufferedCount: setBufferedCount,
          onAcceptedCount: (count) => setAcceptedCount((prev) => prev + count),
          onError: () => {
            setStatusMessage("Błąd wysyłki batcha - ponawianie");
          },
        });

        collector.start();
        collectorRef.current = collector;
      } catch (error) {
        setStatusMessage(`Błąd inicjalizacji: ${String(error)}`);
      }
    };

    void bootstrap();

    return () => {
      active = false;
      collectorRef.current?.stop();
      collectorRef.current = null;
    };
  }, []);

  const handlePredict = async () => {
    if (!sessionId) {
      return;
    }

    try {
      setLoadingPrediction(true);
      await collectorRef.current?.flush();
      const response = await requestPrediction(sessionId);
      setPrediction(response);
      setStatusMessage(`Decyzja: ${response.enforcement_action}`);
    } catch (error) {
      setStatusMessage(`Błąd predykcji: ${String(error)}`);
    } finally {
      setLoadingPrediction(false);
    }
  };

  const handleLabel = async (label: "human" | "bot") => {
    if (!sessionId) {
      return;
    }

    try {
      await collectorRef.current?.flush();
      await labelSession(sessionId, label);
      setStatusMessage(`Sesja oznaczona jako ${label}`);
    } catch (error) {
      setStatusMessage(`Błąd etykietowania: ${String(error)}`);
    }
  };

  return (
    <div className="layout">
      <header className="hero surface">
        <div>
          <h1>Bot czy człowiek? Behavioral Biometrics MVP</h1>
          <p>
            Demo collecting mouse dynamics + policy enforcement. Interact naturally,
            then trigger inference and action.
          </p>
        </div>

        <div className="status-grid">
          <div>
            <span>Session ID</span>
            <strong>{sessionId ?? "-"}</strong>
          </div>
          <div>
            <span>Zbuforowane eventy</span>
            <strong>{bufferedCount}</strong>
          </div>
          <div>
            <span>Wysłane eventy</span>
            <strong>{acceptedCount}</strong>
          </div>
          <div>
            <span>Status</span>
            <strong>{statusMessage}</strong>
          </div>
        </div>
      </header>

      <main className="content-grid">
        <InteractionPanel />
        <PredictionPanel
          prediction={prediction}
          loading={loadingPrediction}
          onPredict={handlePredict}
          onLabel={handleLabel}
        />
      </main>
    </div>
  );
}

export default App;
