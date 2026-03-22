"""
Texter Archetype Classifier — Synthetic Prototype Training

Generates synthetic feature vectors for each archetype based on defined
prototype ranges, then trains a GradientBoostingClassifier.

Usage:
    cd backend
    python -m training.train_texter_type
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.ml.features import FEATURE_COLS  # noqa: E402

SAMPLES_PER_CLASS = 200
RANDOM_SEED = 42

# ── Baseline ranges (what a "normal" user looks like) ─────────────────────
BASELINE = {
    "voice_note_rate":  (0.00, 0.05),
    "photo_rate":       (0.01, 0.10),
    "gif_rate":         (0.00, 0.04),
    "video_rate":       (0.00, 0.04),
    "document_rate":    (0.00, 0.03),
    "link_rate":        (0.00, 0.06),
    "music_rate":       (0.00, 0.02),
    "avg_length":       (20, 80),
    "length_variance":  (15, 50),
    "type_token_ratio": (0.10, 0.40),
    "cap_rate":         (0.01, 0.06),
    "question_rate":    (0.005, 0.020),
    "ellipsis_rate":    (0.000, 0.005),
    "forward_rate":     (0.00, 0.08),
    "late_night_rate":  (0.02, 0.15),
    "sticker_rate":     (0.00, 0.05),
}

# ── Archetype prototypes (override specific features) ─────────────────────
# Only features that deviate from baseline need to be specified.

PROTOTYPES: dict[str, dict[str, tuple[float, float]]] = {
    "voice_note_hostage_taker": {
        "voice_note_rate":  (0.15, 0.55),
        "avg_length":       (3, 30),
    },
    "gif_archaeologist": {
        "gif_rate":         (0.12, 0.45),
    },
    "snap_happy": {
        "photo_rate":       (0.15, 0.50),
    },
    "video_virtuoso": {
        "video_rate":       (0.10, 0.40),
    },
    "file_fiend": {
        "document_rate":    (0.10, 0.45),
    },
    "link_lobbyist": {
        "link_rate":        (0.15, 0.50),
    },
    "forwarding_machine": {
        "forward_rate":     (0.25, 0.70),
    },
    "sticker_merchant": {
        "sticker_rate":     (0.15, 0.55),
    },
    "novelist": {
        "avg_length":       (150, 500),
        "length_variance":  (60, 200),
        "voice_note_rate":  (0.00, 0.02),
    },
    "k_person": {
        "avg_length":       (1, 8),
        "length_variance":  (0, 5),
    },
    "midnight_dropper": {
        "late_night_rate":  (0.30, 0.70),
    },
    "normal": {
        # Uses baseline ranges as-is
    },
}


def generate_synthetic_data(
    rng: np.random.Generator,
) -> tuple[np.ndarray, list[str]]:
    """Generate synthetic feature vectors for all archetypes."""
    X_rows: list[np.ndarray] = []
    y_labels: list[str] = []

    for archetype, overrides in PROTOTYPES.items():
        for _ in range(SAMPLES_PER_CLASS):
            row = []
            for feat in FEATURE_COLS:
                lo, hi = overrides.get(feat, BASELINE[feat])
                row.append(rng.uniform(lo, hi))
            X_rows.append(np.array(row))
            y_labels.append(archetype)

    return np.array(X_rows), y_labels


def main() -> None:
    rng = np.random.default_rng(RANDOM_SEED)

    print(f"Generating {SAMPLES_PER_CLASS} synthetic samples per class "
          f"({len(PROTOTYPES)} classes)...")
    X, y_str = generate_synthetic_data(rng)
    print(f"Total samples: {len(X)}")

    le = LabelEncoder()
    y = le.fit_transform(y_str)

    print(f"\nClasses: {list(le.classes_)}")
    print(f"Features: {FEATURE_COLS}")

    model = GradientBoostingClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.1,
        random_state=RANDOM_SEED,
    )

    print("\nCross-validating (5-fold)...")
    scores = cross_val_score(model, X, y, cv=5, scoring="f1_weighted")
    print(f"F1 (weighted): {scores.mean():.3f} +/- {scores.std():.3f}")

    print("\nTraining final model on all data...")
    model.fit(X, y)

    # Feature importances
    print("\nFeature importances:")
    for feat, imp in sorted(
        zip(FEATURE_COLS, model.feature_importances_),
        key=lambda x: -x[1],
    ):
        print(f"  {feat:25s} {imp:.4f}")

    # Save artifacts
    models_dir = Path(__file__).resolve().parent.parent / "app" / "ml" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / "texter_type.pkl"
    encoder_path = models_dir / "label_encoder.pkl"

    joblib.dump(model, model_path)
    joblib.dump(le, encoder_path)

    print(f"\nSaved model  -> {model_path}")
    print(f"Saved encoder -> {encoder_path}")
    print("Done.")


if __name__ == "__main__":
    main()
