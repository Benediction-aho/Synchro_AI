import numpy as np
import pytest

from synchro.services.agent_engine.intelligence.hmm_numpy import GaussianHMMDiag
from synchro.services.agent_engine.intelligence.regime import (
    MarketRegime,
    RegimeDetector,
    candles_to_features,
)


def _synthetic_candles() -> list[dict]:
    rng = np.random.default_rng(7)
    segments = [
        (600, 0.0004, 0.0005),
        (400, -0.0030, 0.0080),
        (500, 0.0000, 0.0003),
        (300, -0.0006, 0.0012),
    ]
    closes = []
    price = 100.0
    for length, drift, vol in segments:
        returns = rng.normal(drift, vol, size=length)
        for r in returns:
            price *= float(np.exp(r))
            closes.append(price)
    return [{"epoch": i, "close": c} for i, c in enumerate(closes)]


def _segment_regimes(detector: RegimeDetector, candles, start: int, end: int) -> list[MarketRegime]:
    regimes = detector.predict_regimes(candles)
    offset = detector.vol_window - 1
    return regimes[start + offset : end + offset]


def test_features_shape_and_short_input_error():
    candles = [{"epoch": i, "close": 100 + i} for i in range(25)]
    with pytest.raises(ValueError):
        candles_to_features(candles, vol_window=20)

    candles_ok = [{"epoch": i, "close": 100 * float(np.exp(0.0001 * i))} for i in range(60)]
    X = candles_to_features(candles_ok, vol_window=20)
    assert X.shape[1] == 2


def test_detector_separates_synthetic_regimes():
    candles = _synthetic_candles()
    detector = RegimeDetector(n_states=5).fit(candles)

    up = _segment_regimes(detector, candles, 0, 600)
    crash = _segment_regimes(detector, candles, 600, 1000)
    flat = _segment_regimes(detector, candles, 1000, 1500)

    up_majority = max(set(up), key=up.count)
    flat_majority = max(set(flat), key=flat.count)
    crash_majority = max(set(crash), key=crash.count)

    assert up_majority == MarketRegime.TREND_UP
    assert flat_majority == MarketRegime.RANGE
    assert crash_majority in {MarketRegime.CRISIS, MarketRegime.HIGH_VOL}


def test_current_regime_returns_valid_enum():
    candles = _synthetic_candles()
    detector = RegimeDetector().fit(candles)
    regime = detector.current_regime(candles[-120:])
    assert isinstance(regime, MarketRegime)


def test_save_load_roundtrip(tmp_path):
    candles = _synthetic_candles()
    detector = RegimeDetector().fit(candles)
    path = tmp_path / "regimes.pkl"
    detector.save(path)

    loaded = RegimeDetector.load(path)
    original = detector.predict_regimes(candles)
    restored = loaded.predict_regimes(candles)
    assert original == restored


def test_predict_before_fit_raises():
    detector = RegimeDetector()
    candles = [{"epoch": i, "close": 100 + i} for i in range(50)]
    with pytest.raises(RuntimeError):
        detector.predict_regimes(candles)


def test_em_log_likelihood_monotonically_improves():
    candles = _synthetic_candles()
    X = candles_to_features(candles, vol_window=20)
    model = GaussianHMMDiag(n_states=4, n_iter=40, random_state=1).fit(X)
    lls = model.log_likelihoods_
    assert len(lls) >= 2
    diffs = np.diff(lls)
    assert (diffs >= -1e-6 * np.abs(lls[:-1])).all(), f"EM decreased: {diffs.min()}"
