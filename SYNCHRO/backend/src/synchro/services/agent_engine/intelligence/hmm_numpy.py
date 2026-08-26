import numpy as np


def _logsumexp(a: np.ndarray, axis: int) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.max(a, axis=axis, keepdims=True)
        m_safe = np.where(np.isfinite(m), m, 0.0)
        result = m + np.log(np.sum(np.exp(a - m_safe), axis=axis, keepdims=True))
        return np.squeeze(result, axis=axis)


def _normalize_rows(matrix: np.ndarray, floor: float = 1e-8) -> np.ndarray:
    matrix = np.maximum(matrix, floor)
    return matrix / matrix.sum(axis=1, keepdims=True)


class GaussianHMMDiag:
    """Gaussian HMM with diagonal covariance, trained via Baum-Welch EM.

    Pure NumPy implementation (no scipy dependency).
    """

    def __init__(
        self,
        n_states: int = 5,
        n_iter: int = 100,
        tol: float = 1e-6,
        random_state: int = 42,
        min_covar: float = 1e-8,
    ):
        self.n_states = n_states
        self.n_iter = n_iter
        self.tol = tol
        self.random_state = random_state
        self.min_covar = min_covar
        self.pi_: np.ndarray | None = None
        self.A_: np.ndarray | None = None
        self.means_: np.ndarray | None = None
        self.variances_: np.ndarray | None = None
        self.log_likelihoods_: list[float] = []

    def _log_emission(self, X: np.ndarray) -> np.ndarray:
        T, D = X.shape
        diff = X[None, :, :] - self.means_[:, None, :]
        prec = 1.0 / self.variances_
        maha = np.sum(diff * diff * prec[:, None, :], axis=2)
        log_det = np.sum(np.log(self.variances_), axis=1)
        return -0.5 * (D * np.log(2.0 * np.pi) + log_det[:, None] + maha)

    def _forward_log(self, logB: np.ndarray) -> tuple[np.ndarray, float]:
        K, T = logB.shape
        logA = np.log(self.A_)
        alpha = np.empty((T, K))
        alpha[0] = np.log(self.pi_) + logB[:, 0]
        for t in range(1, T):
            alpha[t] = logB[:, t] + _logsumexp(alpha[t - 1][:, None] + logA, axis=0)
        total = _logsumexp(alpha[-1], axis=0)
        return alpha, float(total)

    def _backward_log(self, logB: np.ndarray) -> np.ndarray:
        K, T = logB.shape
        logA = np.log(self.A_)
        beta = np.zeros((T, K))
        for t in range(T - 2, -1, -1):
            beta[t] = _logsumexp(logA + (logB[:, t + 1] + beta[t + 1])[None, :], axis=1)
        return beta

    def _init_params(self, X: np.ndarray) -> None:
        rng = np.random.default_rng(self.random_state)
        T, D = X.shape
        K = self.n_states
        quantiles = np.quantile(X[:, 0], (np.arange(K) + 0.5) / K)
        distances = np.abs(X[:, 0][:, None] - quantiles[None, :])
        labels = np.argmin(distances, axis=1)

        weights = np.full((T, K), 1e-6)
        weights[np.arange(T), labels] += 1.0
        weight_sums = weights.sum(axis=0) + 1e-12

        self.means_ = (weights.T @ X) / weight_sums[:, None]
        centered = X[None, :, :] - self.means_[:, None, :]
        var = np.einsum("kt,ktd->kd", weights.T, centered**2) / weight_sums[:, None]
        self.variances_ = np.maximum(var, self.min_covar)

        starts = np.bincount(labels[: max(1, T // 100)], minlength=K).astype(float) + 0.5
        self.pi_ = starts / starts.sum()

        counts = np.full((K, K), 0.5)
        np.add.at(counts, (labels[:-1], labels[1:]), 1.0)
        counts += rng.random((K, K)) * 1e-3
        self.A_ = counts / counts.sum(axis=1, keepdims=True)

    def fit(self, X: np.ndarray) -> "GaussianHMMDiag":
        X = np.asarray(X, dtype=float)
        if X.ndim != 2 or X.shape[0] < 10 * self.n_states:
            raise ValueError(f"need >= {10 * self.n_states} samples, got {X.shape[0]}")
        self._init_params(X)
        self.log_likelihoods_ = []
        previous = -np.inf
        var_floor = np.maximum(1e-4 * X.var(axis=0), self.min_covar)

        for _ in range(self.n_iter):
            logB = self._log_emission(X)
            alpha, ll = self._forward_log(logB)
            self.log_likelihoods_.append(ll)
            beta = self._backward_log(logB)

            gamma = np.exp(alpha + beta - ll)
            gamma /= gamma.sum(axis=1, keepdims=True)

            logA = np.log(self.A_)
            m = (
                alpha[:-1][:, :, None]
                + logA[None, :, :]
                + (logB[:, 1:].T + beta[1:])[:, None, :]
            )
            xi = np.exp(_logsumexp(m, axis=0) - ll)

            weight_sums = gamma.sum(axis=0) + 1e-300
            self.pi_ = _normalize_rows(gamma[0][None, :])[0]
            self.A_ = _normalize_rows(xi / weight_sums[:, None])
            self.means_ = (gamma.T @ X) / weight_sums[:, None]
            centered = X[None, :, :] - self.means_[:, None, :]
            var = np.einsum("kt,ktd->kd", gamma.T, centered**2) / weight_sums[:, None]
            self.variances_ = np.maximum(var, var_floor)

            if abs(ll - previous) < self.tol * max(1.0, abs(previous)):
                break
            previous = ll

        return self

    def score(self, X: np.ndarray) -> float:
        logB = self._log_emission(np.asarray(X, dtype=float))
        _, ll = self._forward_log(logB)
        return ll

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        logB = self._log_emission(X)
        K, T = logB.shape
        logA = np.log(self.A_)
        delta = np.log(self.pi_) + logB[:, 0]
        psi = np.zeros((T, K), dtype=int)
        for t in range(1, T):
            candidates = delta[:, None] + logA
            psi[t] = candidates.argmax(axis=0)
            delta = logB[:, t] + candidates.max(axis=0)
        path = np.zeros(T, dtype=int)
        path[-1] = int(delta.argmax())
        for t in range(T - 2, -1, -1):
            path[t] = psi[t + 1][path[t + 1]]
        return path
