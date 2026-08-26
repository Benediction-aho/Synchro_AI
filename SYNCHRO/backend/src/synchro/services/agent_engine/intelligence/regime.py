import enum
import pickle
from pathlib import Path
from typing import Any

import numpy as np

from synchro.services.agent_engine.intelligence.hmm_numpy import GaussianHMMDiag


class MarketRegime(str, enum.Enum):
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    RANGE = "range"
    HIGH_VOL = "high_vol"
    CRISIS = "crisis"


def candles_to_features(candles: list[dict[str, Any]], vol_window: int = 20) -> np.ndarray:
    closes = np.array([float(c["close"]) for c in candles], dtype=float)
    if closes.size < vol_window + 10:
        raise ValueError(f"need at least {vol_window + 10} candles, got {closes.size}")
    log_returns = np.diff(np.log(closes))
    vols = np.empty_like(log_returns)
    for i in range(log_returns.size):
        start = max(0, i - vol_window + 1)
        vols[i] = log_returns[start : i + 1].std()
    features = np.column_stack([log_returns, vols])
    return features[vols > 0]


class RegimeDetector:
    def __init__(
        self,
        n_states: int = 5,
        vol_window: int = 20,
        n_iter: int = 200,
        random_state: int = 42,
    ):
        self.n_states = n_states
        self.vol_window = vol_window
        self.n_iter = n_iter
        self.random_state = random_state
        self.model: GaussianHMMDiag | None = None
        self._state_labels: list[MarketRegime] | None = None

    def fit(self, candles: list[dict[str, Any]]) -> "RegimeDetector":
        X = candles_to_features(candles, self.vol_window)
        model = GaussianHMMDiag(
            n_states=self.n_states,
            n_iter=self.n_iter,
            random_state=self.random_state,
        )
        model.fit(X)
        self.model = model
        self._state_labels = self._label_states(X)
        return self

    def _require_model(self) -> tuple[GaussianHMMDiag, list[MarketRegime]]:
        if self.model is None or self._state_labels is None:
            raise RuntimeError("Detector not fitted; call fit() first")
        return self.model, self._state_labels

    def _label_states(self, X: np.ndarray) -> list[MarketRegime]:
        assert self.model is not None
        states = self.model.predict(X)
        mus = []
        sigmas = []
        for s in range(self.n_states):
            values = X[states == s, 0]
            mus.append(float(values.mean()) if values.size else 0.0)
            sigmas.append(float(values.std()) if values.size else 0.0)
        mus_arr = np.array(mus)
        sigmas_arr = np.array(sigmas)
        positive_sigmas = sigmas_arr[sigmas_arr > 0]
        median_sigma = float(np.median(positive_sigmas)) if positive_sigmas.size else 1e-9
        crisis_mu = float(mus_arr.min())

        labels: list[MarketRegime] = []
        for mu, sigma in zip(mus_arr, sigmas_arr):
            drift_ratio = mu / max(sigma, 1e-12)
            if sigma >= 2.2 * median_sigma and abs(mu - crisis_mu) < 1e-12:
                labels.append(MarketRegime.CRISIS)
            elif sigma >= 1.6 * median_sigma:
                labels.append(MarketRegime.HIGH_VOL)
            elif drift_ratio > 0.4:
                labels.append(MarketRegime.TREND_UP)
            elif drift_ratio < -0.4:
                labels.append(MarketRegime.TREND_DOWN)
            else:
                labels.append(MarketRegime.RANGE)
        return labels

    def predict_regimes(self, candles: list[dict[str, Any]]) -> list[MarketRegime]:
        model, state_labels = self._require_model()
        X = candles_to_features(candles, self.vol_window)
        states = model.predict(X)
        return [state_labels[s] for s in states]

    def current_regime(
        self, candles: list[dict[str, Any]], lookback: int = 5
    ) -> MarketRegime:
        regimes = self.predict_regimes(candles)[-lookback:]
        counts: dict[MarketRegime, int] = {}
        for r in regimes:
            counts[r] = counts.get(r, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def save(self, path: str | Path) -> None:
        payload = {
            "n_states": self.n_states,
            "vol_window": self.vol_window,
            "n_iter": self.n_iter,
            "random_state": self.random_state,
            "model": self.model,
            "state_labels": self._state_labels,
        }
        Path(path).write_bytes(pickle.dumps(payload))

    @classmethod
    def load(cls, path: str | Path) -> "RegimeDetector":
        payload = pickle.loads(Path(path).read_bytes())
        detector = cls(
            n_states=payload["n_states"],
            vol_window=payload["vol_window"],
            n_iter=payload["n_iter"],
            random_state=payload["random_state"],
        )
        detector.model = payload["model"]
        detector._state_labels = payload["state_labels"]
        return detector
