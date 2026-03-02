"""
SignalFlow — LSTM Predictor (Phase 2B)
Probabilistic output: P(up), P(down), P(flat)
Input: returns + VIX + credit_spread (when available)
"""
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple, List

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# Threshold for label (forward return): |ret| > LABEL_THRESH = up/down, else flat
LABEL_THRESH_BPS = 10  # 10 bps = 0.001


def _label_from_forward_return(forward_ret: float) -> int:
    """0=down, 1=flat, 2=up"""
    if forward_ret > LABEL_THRESH_BPS / 10_000:
        return 2  # up
    if forward_ret < -LABEL_THRESH_BPS / 10_000:
        return 0  # down
    return 1  # flat


ML_FEATURE_COLS = ["returns", "vix", "credit_spread", "yield_curve"]
FEATURE_FALLBACKS = {"vix": 20.0, "credit_spread": 4.0, "yield_curve": 0.5}


def _get_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract ML-ready features. Fills missing external with fallbacks."""
    out = pd.DataFrame(index=df.index)
    out["returns"] = df["returns"]
    for col in ["vix", "credit_spread", "yield_curve"]:
        if col in df.columns:
            s = df[col].ffill()
            fallback = FEATURE_FALLBACKS.get(col, 0.0)
            out[col] = s.fillna(s.median() if s.notna().any() else fallback)
        else:
            out[col] = FEATURE_FALLBACKS.get(col, 0.0)
    return out.dropna(how="all").ffill().dropna()


def build_sequences(
    feat: np.ndarray,
    labels: np.ndarray,
    lookback: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Create (X, y) sequences. X: (n_samples, lookback, n_features). labels[i] = forward ret i→i+1."""
    X, y = [], []
    for i in range(lookback, len(feat) - 1):
        X.append(feat[i - lookback : i])
        y.append(labels[i])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


class LSTMModule(nn.Module):
    """LSTM for sequence → 3-class probability."""

    def __init__(self, n_features: int, hidden: int = 64, n_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.lstm = nn.LSTM(n_features, hidden, n_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden, 3)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


class LSTMPredictor:
    """
    LSTM predictor: returns + VIX + credit_spread → P(up), P(down), P(flat).
    Fallback: returns None when torch unavailable or model not trained.
    """

    def __init__(
        self,
        lookback: int = 40,
        hidden: int = 64,
        n_layers: int = 2,
        model_path: Optional[Path] = None,
    ):
        self.lookback = lookback
        self.hidden = hidden
        self.n_layers = n_layers
        self._model: Optional[nn.Module] = None
        self._n_features: Optional[int] = None
        self._scaler_mean: Optional[np.ndarray] = None
        self._scaler_std: Optional[np.ndarray] = None
        self._model_path = model_path or Path(__file__).parent.parent.parent / "storage" / "lstm_model.pt"

    def _ensure_storage(self) -> Path:
        p = Path(self._model_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def is_available(self) -> bool:
        """Can predict? Requires torch + trained model."""
        return TORCH_AVAILABLE and self._model is not None

    def fit(
        self,
        df: pd.DataFrame,
        epochs: int = 50,
        lr: float = 0.001,
        batch_size: int = 32,
        val_frac: float = 0.2,
        device: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Train on pipeline DataFrame. Uses forward returns for labels.
        Returns dict with train_loss, val_loss (last epoch).
        """
        if not TORCH_AVAILABLE:
            return {"error": "torch not available"}

        ml_df = _get_ml_features(df)
        if len(ml_df) < self.lookback + 50:
            return {"error": f"Need at least {self.lookback + 50} rows"}

        returns = ml_df["returns"].values
        labels = np.array(
            [_label_from_forward_return(returns[i + 1]) for i in range(len(returns) - 1)],
            dtype=np.int64,
        )

        cols = [c for c in ML_FEATURE_COLS if c in ml_df.columns]
        self._feature_cols = cols
        feat = ml_df[cols].values.astype(np.float32)
        self._n_features = feat.shape[1]

        # Scale
        self._scaler_mean = np.nanmean(feat, axis=0)
        self._scaler_std = np.nanstd(feat, axis=0)
        self._scaler_std[self._scaler_std < 1e-8] = 1.0
        feat = (feat - self._scaler_mean) / self._scaler_std

        X, y = build_sequences(feat, labels, self.lookback)
        n_val = int(len(X) * val_frac)
        X_train, X_val = X[:-n_val], X[-n_val:]
        y_train, y_val = y[:-n_val], y[-n_val:]

        dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
        model = LSTMModule(
            n_features=self._n_features,
            hidden=self.hidden,
            n_layers=self.n_layers,
        ).to(dev)
        opt = torch.optim.Adam(model.parameters(), lr=lr)
        crit = nn.CrossEntropyLoss()

        for ep in range(epochs):
            model.train()
            perm = np.random.permutation(len(X_train))
            train_loss = 0.0
            for i in range(0, len(X_train), batch_size):
                idx = perm[i : i + batch_size]
                bx = torch.from_numpy(X_train[idx]).to(dev)
                by = torch.from_numpy(y_train[idx]).to(dev)
                opt.zero_grad()
                logits = model(bx)
                loss = crit(logits, by)
                loss.backward()
                opt.step()
                train_loss += loss.item()
            train_loss /= (len(X_train) // batch_size + 1)

            model.eval()
            with torch.no_grad():
                vx = torch.from_numpy(X_val).to(dev)
                vy = torch.from_numpy(y_val).to(dev)
                val_loss = crit(model(vx), vy).item()

        self._model = model
        self._save()
        return {"train_loss": train_loss, "val_loss": val_loss}

    def _save(self) -> None:
        if self._model is None:
            return
        path = self._ensure_storage()
        cols = getattr(self, "_feature_cols", ML_FEATURE_COLS)
        meta = {
            "lookback": self.lookback,
            "n_features": self._n_features,
            "feature_cols": cols,
            "scaler_mean": self._scaler_mean.tolist() if self._scaler_mean is not None else None,
            "scaler_std": self._scaler_std.tolist() if self._scaler_std is not None else None,
        }
        torch.save({"state_dict": self._model.state_dict(), "meta": meta}, path)
        meta_path = path.with_suffix(".json")
        with open(meta_path, "w") as f:
            json.dump({k: v for k, v in meta.items() if v is not None}, f, indent=2)

    def load(self) -> bool:
        """Load from storage. Returns True if successful."""
        if not TORCH_AVAILABLE:
            return False
        path = Path(self._model_path)
        if not path.exists():
            return False
        try:
            ckpt = torch.load(path, map_location="cpu", weights_only=True)
            meta = ckpt.get("meta", {})
            self.lookback = meta.get("lookback", self.lookback)
            self._n_features = meta.get("n_features", 3)
            self._feature_cols = meta.get("feature_cols", ["returns", "vix", "credit_spread"])
            self._scaler_mean = np.array(meta["scaler_mean"]) if meta.get("scaler_mean") else None
            self._scaler_std = np.array(meta["scaler_std"]) if meta.get("scaler_std") else None
            self._model = LSTMModule(
                n_features=self._n_features,
                hidden=self.hidden,
                n_layers=self.n_layers,
            )
            self._model.load_state_dict(ckpt["state_dict"])
            self._model.eval()
            return True
        except Exception:
            return False

    def predict_proba(self, df: pd.DataFrame) -> Optional[Dict[str, float]]:
        """
        Predict P(up), P(down), P(flat) for the last row.
        Returns None if not available (no model, insufficient data).
        """
        if not TORCH_AVAILABLE or self._model is None:
            return None
        ml_df = _get_ml_features(df)
        if len(ml_df) < self.lookback:
            return None

        cols = getattr(self, "_feature_cols", ML_FEATURE_COLS)
        cols = [c for c in cols if c in ml_df.columns]
        if not cols:
            return None
        feat = ml_df[cols].values.astype(np.float32)
        if feat.shape[1] != self._n_features:
            return None
        if self._scaler_mean is not None and self._scaler_std is not None:
            feat = (feat - self._scaler_mean) / self._scaler_std

        last_seq = feat[-self.lookback :].reshape(1, self.lookback, -1)
        with torch.no_grad():
            x = torch.from_numpy(last_seq).float()
            logits = self._model(x)
            probs = torch.softmax(logits, dim=1).numpy()[0]

        return {
            "P_down": float(probs[0]),
            "P_flat": float(probs[1]),
            "P_up": float(probs[2]),
        }
