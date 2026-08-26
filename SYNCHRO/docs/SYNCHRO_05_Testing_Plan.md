# SYNCHRO — DOCUMENT 5: TESTING PLAN
### Step 5 of the development blueprint

---

## 5.1 Test Types Required

| Level | What | Tool |
|---|---|---|
| Unit tests | Every filter, scorer, sizing formula | pytest, ≥85% coverage |
| Property tests | Risk never exceeds limits under any input | Hypothesis |
| Backtesting | Historical V75/V100/FX, walk-forward validation | custom/vectorbt |
| Monte Carlo | 10,000 simulated equity paths — verify drawdown claims | numpy |
| Integration | Cloud ↔ EA ↔ Deriv demo round-trip | pytest + staging env |
| Latency tests | Signal-to-execution time <500ms target | Locust |
| Chaos tests | Kill cloud mid-trade → EA protective mode works | manual scripts |
| Security | OWASP top 10, token encryption, injection | ZAP/Burp |
| UX testing | 10 non-technical users complete onboarding unaided | usability sessions |
| Beta | 30 days minimum on demo accounts, multiple users | Commandment VIII |

---

## 5.2 Acceptance Criteria Before Launch

- [ ] Walk-forward Sharpe > 1.0 on out-of-sample data
- [ ] Max observed backtest drawdown within claimed limits
- [ ] EA survives 24h total cloud outage without unprotected exposure
- [ ] Breakeven fires correctly in 100% of test scenarios
- [ ] Rollback works after deliberately bad evolution cycle
- [ ] Non-technical user installs and goes live in <10 min without support

---

**Previous document:** `SYNCHRO_04_Development_Steps.md`
**Next document:** `SYNCHRO_06_Deployment_Requirements.md`
