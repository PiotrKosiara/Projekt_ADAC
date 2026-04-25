import { PredictionResponse } from "../api/client";

type PredictionPanelProps = {
  prediction: PredictionResponse | null;
  loading: boolean;
  onPredict: () => void;
  onLabel: (label: "human" | "bot") => void;
};

export function PredictionPanel({ prediction, loading, onPredict, onLabel }: PredictionPanelProps) {
  const risk = prediction?.risk_score ?? 0;

  return (
    <aside className="panel surface sticky">
      <header className="panel-header">
        <h2>Silnik Ochrony</h2>
        <p>Uruchom klasyfikację i decyzję policy engine dla bieżącej sesji.</p>
      </header>

      <div className="prediction-actions">
        <button id="run-prediction" className="primary-btn" onClick={onPredict} disabled={loading}>
          {loading ? "Analiza..." : "Analizuj sesję"}
        </button>
        <button id="label-human" className="secondary-btn" onClick={() => onLabel("human")}>
          Oznacz jako human
        </button>
        <button id="label-bot" className="secondary-btn" onClick={() => onLabel("bot")}>
          Oznacz jako bot
        </button>
      </div>

      <div className="risk-card">
        <p>Risk score</p>
        <strong>{risk.toFixed(1)} / 100</strong>
        <div className="risk-bar">
          <div className="risk-bar-fill" style={{ width: `${Math.min(100, risk)}%` }} />
        </div>
      </div>

      <dl className="prediction-grid">
        <div>
          <dt>Predykcja</dt>
          <dd>{prediction?.predicted_label ?? "-"}</dd>
        </div>
        <div>
          <dt>Prawd. bot</dt>
          <dd>{prediction ? prediction.probability_bot.toFixed(3) : "-"}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{prediction ? prediction.confidence.toFixed(3) : "-"}</dd>
        </div>
        <div>
          <dt>Decyzja</dt>
          <dd>{prediction?.enforcement_action ?? "-"}</dd>
        </div>
      </dl>

      <p className="muted">{prediction?.enforcement_reason ?? "Brak predykcji dla tej sesji"}</p>
    </aside>
  );
}
