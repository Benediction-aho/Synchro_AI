# SYNCHRO — DOCUMENT 4: DEVELOPMENT STEPS (ORDERED)
### Step 4 of the development blueprint (from logbook Roadmap, Section 26)

Total estimated duration: **~22 weeks** (consistent with the 18–26 week logbook estimate)

---

## Phase 0 — Foundations (Weeks 1–2)
1. Git repo, monorepo structure, CI/CD pipelines (GitHub Actions)
2. Docker environments (dev/staging/prod)
3. PostgreSQL schema + Alembic migrations
4. FastAPI skeleton: registration, login, JWT
5. Stripe integration (sandbox)

---

## Phase 1 — Data & Execution (Weeks 3–5)
6. Deriv API connector (WebSocket: ticks, candles, account info)
7. **MQL5 EA development** — ⚠️ *missing from the original roadmap, critical addition*:
   - WebSocket client inside EA (or bridge via ZeroMQ/file pipe)
   - Order execution: open/modify/close, partial close (TP1 = 50%)
   - Local breakeven (+10 pips → SL to entry) and trailing logic
   - Heartbeat: if cloud unreachable >60s → protective mode only
8. Trade lifecycle state machine + audit logging

---

## Phase 2 — Intelligence (Weeks 6–11) — corresponds to Modules M1–M3
9. HMM regime detector trained on historical V75/V100/EURUSD data
10. News NLP filter + macro context engine (Forex markets)
11. Structure scanner: OB, FVG, BOS detection functions
12. Multi-TF EMA validator + oscillator confluence engine
13. 5/5 Score evaluator + all 15 filters (unit-testable pure functions)
14. RL agent: Q-learning first, DQN upgrade path; replay buffer 10k
15. **Backtesting harness** — must exist before any live code

---

## Phase 3 — Learning & Safety (Weeks 12–14) — corresponds to Modules M4–M6
16. Pattern database writes after every closed trade
17. Nightly 02:00 GMT Celery job (win rates, Kelly, thresholds)
18. Evolution engine: variation generator → backtester → 24h demo sandbox → auto-rollback
19. Telegram bot: approval cards, 15-min timeout, CRISIS broadcast, mobile kill-switch

---

## Phase 4 — Product (Weeks 15–20) — corresponds to Module M7
20. React dashboard — 7 pages (Dashboard, Charts, History, Settings, Alerts, Reports, Onboarding)
21. Plain-language layer: translate technical states into user-friendly wording
22. Tauri desktop wrapper + **auto-installer**: downloads EA, detects MT4/MT5 data folder, copies `.ex5`, launches terminal, verifies connection
23. Onboarding wizard: Token → Capital → Markets → Telegram → Launch (<2 min target)

---

## Phase 5 — Integration (Weeks 21–22) — corresponds to the FINAL phase
24. End-to-end assembly M1→M7
25. Staging deployment, load testing
26. Security audit (penetration test, token handling review)
27. Closed beta: the 30-day demo rule applied to the product itself

---

**Previous document:** `SYNCHRO_03_Database_Architecture.md`
**Next document:** `SYNCHRO_05_Testing_Plan.md`
