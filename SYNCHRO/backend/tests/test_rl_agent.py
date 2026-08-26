import numpy as np
import pytest

from synchro.services.agent_engine.rl.qlearning import (
    ACTIONS,
    LinearApproxQLearner,
    QLearningAgent,
    ReplayBuffer,
    encode_state,
    state_feature_vector,
)


class TestStateEncoding:
    def test_tabular_key_format(self):
        key = encode_state("trend_up", "bullish", 0.5, 60.0)
        assert key == "trend_up|bullish|pos|high"

    def test_unknown_regime_rejected(self):
        with pytest.raises(ValueError):
            encode_state("moon_phase", None, 0.0, 50.0)

    def test_feature_vector_shape_and_onehot(self):
        v = state_feature_vector("crisis", None, -0.8, 25.0)
        assert v.shape == (16,)
        assert v.sum() == pytest.approx(4.0)
        assert v[4] == 1.0

    def test_rsi_bands(self):
        assert encode_state("range", "none", 0.0, 20.0).endswith("oversold")
        assert encode_state("range", "none", 0.0, 50.0).endswith("mid")
        assert encode_state("range", "none", 0.0, 85.0).endswith("overbought")


class TestQLearning:
    def test_learns_optimal_action_in_toy_mdp(self):
        agent = QLearningAgent(alpha=0.5, gamma=0.9, epsilon=0.2, seed=1)
        for _ in range(400):
            agent.update("s0", "BUY", 10.0, "s1")
            agent.update("s0", "WAIT", 1.0, "s1")
            agent.update("s0", "SELL", -10.0, "s1")
            agent.update("s1", "WAIT", 0.0, None)
        assert agent.q_value("s0", "BUY") > agent.q_value("s0", "WAIT")
        assert agent.q_value("s0", "BUY") > agent.q_value("s0", "SELL")
        assert agent.choose_action("s0", explore=False) == "BUY"

    def test_greedy_follows_q_table(self):
        agent = QLearningAgent(seed=3)
        agent.q_table["x"] = {"BUY": 0.1, "SELL": 5.0, "WAIT": 0.0}
        assert agent.choose_action("x", explore=False) == "SELL"

    def test_epsilon_decays_to_floor(self):
        agent = QLearningAgent(epsilon=0.5, epsilon_min=0.01, epsilon_decay=0.9)
        for _ in range(100):
            agent.decay_epsilon()
        assert agent.epsilon == pytest.approx(agent.epsilon_min)

    def test_invalid_hyperparams_rejected(self):
        with pytest.raises(ValueError):
            QLearningAgent(alpha=0)
        with pytest.raises(ValueError):
            QLearningAgent(gamma=1.5)

    def test_invalid_action_rejected(self):
        agent = QLearningAgent()
        with pytest.raises(ValueError):
            agent.q_value("s", "HODL")

    def test_terminal_update_no_bootstrap(self):
        agent = QLearningAgent(alpha=0.6, gamma=0.9, seed=1)
        td = agent.update("end", "SELL", 4.0, None)
        assert td == pytest.approx(4.0)
        assert agent.q_value("end", "SELL") == pytest.approx(0.6 * 4.0)

    def test_db_rows_roundtrip(self):
        agent = QLearningAgent(seed=2)
        agent.update("a|b|c|d", "BUY", 2.0, None)
        rows = agent.to_db_rows()
        restored = QLearningAgent()
        restored.load_db_rows(rows)
        assert restored.q_value("a|b|c|d", "BUY") == agent.q_value("a|b|c|d", "BUY")

    def test_load_db_rows_rejects_bad_action(self):
        with pytest.raises(ValueError):
            QLearningAgent.load_db_rows(QLearningAgent(), [("s", "MOON", 1.0)])

    def test_save_load_roundtrip(self, tmp_path):
        agent = QLearningAgent(seed=2)
        agent.update("state1", "BUY", 3.0, None)
        path = tmp_path / "q.json"
        agent.save(path)
        loaded = QLearningAgent.load(path)
        assert loaded.q_value("state1", "BUY") == agent.q_value("state1", "BUY")
        assert loaded.epsilon == agent.epsilon


class TestReplayBuffer:
    def test_fifo_bound_at_capacity(self):
        buffer = ReplayBuffer(capacity=10_000)
        for i in range(10_500):
            buffer.push(f"s{i}", "BUY", float(i), f"s{i+1}", False)
        assert len(buffer) == 10_000
        first_state = buffer.buffer[0][0]
        assert first_state == "s500"

    def test_capacity_bounds_enforced(self):
        with pytest.raises(ValueError):
            ReplayBuffer(capacity=200_000)

    def test_sample_shapes(self):
        buffer = ReplayBuffer(capacity=100, seed=1)
        for i in range(50):
            buffer.push(i, "WAIT", i * 0.1, i + 1, False)
        batch = buffer.sample(10)
        assert len(batch) == 10
        assert all(len(item) == 5 for item in batch)

    def test_oversample_rejected(self):
        buffer = ReplayBuffer(capacity=10)
        with pytest.raises(ValueError):
            buffer.sample(5)


class TestLinearApprox:
    def test_converges_on_repeated_transition(self):
        features = state_feature_vector("trend_up", "bullish", 0.7, 60.0)
        learner = LinearApproxQLearner(n_features=len(features), alpha=0.05, seed=1)
        initial_err = None
        for _ in range(300):
            err = abs(learner.update(features, "BUY", 5.0, None))
            if initial_err is None:
                initial_err = err
        final_err = abs(learner.update(features, "BUY", 5.0, None))
        assert final_err < initial_err

    def test_greedy_picks_max_q(self):
        features = np.zeros(16)
        features[0] = 1.0
        learner = LinearApproxQLearner(n_features=16, seed=2)
        learner.weights[1, :] = 1.0
        assert learner.choose_action(features) == "SELL"

    def test_all_actions_present(self):
        assert set(ACTIONS) == {"BUY", "SELL", "WAIT"}
