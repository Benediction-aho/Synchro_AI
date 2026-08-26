"""M2 decision-making: Q-learning with a DQN upgrade path (Doc 4 item 14).

Tabular Q-learning stores state_key/action/q_value rows exactly like the
`q_values` database table. Linear-approximation Q and a bounded replay buffer
provide the migration path toward deep RL without scipy/native deps.
"""

import json
import random
from collections import deque
from pathlib import Path
from typing import Literal

import numpy as np

ACTIONS = ("BUY", "SELL", "WAIT")
Action = Literal["BUY", "SELL", "WAIT"]

_REGIMES = ("trend_up", "trend_down", "range", "high_vol", "crisis")
_TRENDS = ("bullish", "bearish", "none")
_MOMENTUM = ("neg", "flat", "pos")
_RSI_BANDS = ("oversold", "low", "mid", "high", "overbought")


def _rsi_band(rsi: float) -> str:
    if not np.isfinite(rsi):
        return "mid"
    if rsi <= 30:
        return "oversold"
    if rsi <= 45:
        return "low"
    if rsi < 55:
        return "mid"
    if rsi < 70:
        return "high"
    return "overbought"


def _momentum_bucket(score: float) -> str:
    if not np.isfinite(score) or abs(score) < 0.1:
        return "flat"
    return "pos" if score > 0 else "neg"


def encode_state(regime: str, trend_alignment: str | None, momentum_score: float, rsi: float) -> str:
    if regime not in _REGIMES:
        raise ValueError(f"unknown regime '{regime}'")
    trend = trend_alignment if trend_alignment in ("bullish", "bearish") else "none"
    return f"{regime}|{trend}|{_momentum_bucket(momentum_score)}|{_rsi_band(rsi)}"


def state_feature_vector(
    regime: str, trend_alignment: str | None, momentum_score: float, rsi: float
) -> np.ndarray:
    regime_onehot = np.array([1.0 if regime == r else 0.0 for r in _REGIMES])
    trend = trend_alignment if trend_alignment in ("bullish", "bearish") else "none"
    trend_onehot = np.array([1.0 if trend == t else 0.0 for t in _TRENDS])
    mom_onehot = np.array([1.0 if _momentum_bucket(momentum_score) == m else 0.0 for m in _MOMENTUM])
    band_onehot = np.array([1.0 if _rsi_band(rsi) == b else 0.0 for b in _RSI_BANDS])
    return np.concatenate([regime_onehot, trend_onehot, mom_onehot, band_onehot])


class QLearningAgent:
    def __init__(
        self,
        alpha: float = 0.1,
        gamma: float = 0.95,
        epsilon: float = 0.15,
        epsilon_min: float = 0.01,
        epsilon_decay: float = 0.995,
        seed: int = 42,
    ):
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        if not 0 <= gamma < 1:
            raise ValueError("gamma must be in [0, 1)")
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self._rng = random.Random(seed)
        self.q_table: dict[str, dict[str, float]] = {}

    def q_value(self, state_key: str, action: str) -> float:
        if action not in ACTIONS:
            raise ValueError(f"unknown action '{action}'")
        return self.q_table.get(state_key, {}).get(action, 0.0)

    def choose_action(self, state_key: str, explore: bool = True) -> Action:
        if explore and self._rng.random() < self.epsilon:
            return self._rng.choice(ACTIONS)
        row = self.q_table.get(state_key, {})
        best = max(ACTIONS, key=lambda a: row.get(a, 0.0))
        return best

    def update(self, state_key: str, action: str, reward: float, next_state_key: str | None) -> float:
        current = self.q_value(state_key, action)
        if next_state_key is None:
            target = reward
        else:
            next_row = self.q_table.get(next_state_key, {})
            target = reward + self.gamma * max(next_row.get(a, 0.0) for a in ACTIONS)
        td_error = target - current
        new_value = current + self.alpha * td_error
        self.q_table.setdefault(state_key, {})[action] = new_value
        self.decay_epsilon()
        return td_error

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def to_db_rows(self) -> list[tuple[str, str, float]]:
        return [
            (state, action, value)
            for state, row in self.q_table.items()
            for action, value in row.items()
        ]

    def load_db_rows(self, rows: list[tuple[str, str, float]]) -> None:
        self.q_table.clear()
        for state, action, value in rows:
            if action not in ACTIONS:
                raise ValueError(f"unknown action '{action}' in stored rows")
            self.q_table.setdefault(state, {})[action] = value

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps({"q": self.q_table, "epsilon": self.epsilon}))

    @classmethod
    def load(cls, path: str | Path, **kwargs) -> "QLearningAgent":
        payload = json.loads(Path(path).read_text())
        agent = cls(**kwargs)
        agent.q_table = {s: dict(row) for s, row in payload["q"].items()}
        agent.epsilon = float(payload["epsilon"])
        return agent


class ReplayBuffer:
    """Bounded FIFO experience replay (Doc 4: capacity 10k)."""

    MAX_CAPACITY = 100_000

    def __init__(self, capacity: int = 10_000, seed: int = 42):
        if not 1 <= capacity <= self.MAX_CAPACITY:
            raise ValueError(f"capacity must be in [1, {self.MAX_CAPACITY}]")
        self.buffer: deque = deque(maxlen=capacity)
        self._rng = np.random.default_rng(seed)

    def push(self, state: Any, action: Any, reward: float, next_state: Any, done: bool) -> None:
        self.buffer.append((state, action, float(reward), next_state, bool(done)))

    def sample(self, batch_size: int) -> list[tuple]:
        if batch_size > len(self.buffer):
            raise ValueError(f"cannot sample {batch_size} from {len(self.buffer)} items")
        indices = self._rng.integers(0, len(self.buffer), size=batch_size)
        return [self.buffer[i] for i in indices]

    def __len__(self) -> int:
        return len(self.buffer)


class LinearApproxQLearner:
    """Linear function approximation over state features - step before DQN."""

    def __init__(
        self,
        n_features: int,
        actions: tuple[str, ...] = ACTIONS,
        alpha: float = 0.01,
        gamma: float = 0.95,
        seed: int = 42,
    ):
        rng = np.random.default_rng(seed)
        self.weights = rng.normal(0, 0.01, size=(len(actions), n_features))
        self.actions = actions
        self.alpha = alpha
        self.gamma = gamma

    def q_values(self, features: np.ndarray) -> np.ndarray:
        return self.weights @ features

    def choose_action(self, features: np.ndarray, explore: bool = False, epsilon: float = 0.1) -> str:
        if explore and np.random.random() < epsilon:
            return self.actions[np.random.randint(len(self.actions))]
        return self.actions[int(np.argmax(self.q_values(features)))]

    def update(self, features: np.ndarray, action: str, reward: float, next_features: np.ndarray | None) -> float:
        a_idx = self.actions.index(action)
        current = float(self.weights[a_idx] @ features)
        if next_features is None:
            target = reward
        else:
            target = reward + self.gamma * float(np.max(self.weights @ next_features))
        td_error = target - current
        self.weights[a_idx] += self.alpha * td_error * features
        return td_error
