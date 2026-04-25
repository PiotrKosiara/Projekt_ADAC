from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import (
    auc,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


def compute_metrics(y_true, y_pred, y_prob) -> dict:
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)
    y_prob_arr = np.asarray(y_prob)

    tn, fp, fn, tp = confusion_matrix(y_true_arr, y_pred_arr, labels=[0, 1]).ravel()

    metrics = {
        "precision": float(precision_score(y_true_arr, y_pred_arr, zero_division=0)),
        "recall": float(recall_score(y_true_arr, y_pred_arr, zero_division=0)),
        "f1": float(f1_score(y_true_arr, y_pred_arr, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true_arr, y_prob_arr)) if len(np.unique(y_true_arr)) > 1 else 0.0,
        "false_positive_rate_human": float(fp / max(fp + tn, 1)),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }
    return metrics


def save_confusion_matrix_plot(y_true, y_pred, output_path: str) -> None:
    cm = confusion_matrix(np.asarray(y_true), np.asarray(y_pred), labels=[0, 1])
    figure, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax)
    ax.set_xlabel("Predykcja")
    ax.set_ylabel("Rzeczywista etykieta")
    ax.set_xticklabels(["human", "bot"])
    ax.set_yticklabels(["human", "bot"])
    ax.set_title("Confusion matrix")
    figure.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path)
    plt.close(figure)


def save_roc_plot(y_true, y_prob, output_path: str) -> None:
    y_true_arr = np.asarray(y_true)
    y_prob_arr = np.asarray(y_prob)

    if len(np.unique(y_true_arr)) < 2:
        return

    fpr, tpr, _ = roc_curve(y_true_arr, y_prob_arr)
    roc_auc = auc(fpr, tpr)

    figure, ax = plt.subplots(figsize=(5, 4))
    ax.plot(fpr, tpr, label=f"ROC AUC = {roc_auc:.3f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC curve")
    ax.legend(loc="lower right")
    figure.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path)
    plt.close(figure)


def save_report(report: dict, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
