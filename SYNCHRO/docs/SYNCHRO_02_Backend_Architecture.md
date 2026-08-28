# SYNCHRO — DOCUMENT 2: BACKEND ARCHITECTURE
### Step 2 of the development blueprint

---

## 2.1 Services to Build

1. **API Gateway** (FastAPI) — auth, user management, WebSocket push to dashboard
2. **Agent Engine** — the trading brain (M1+M2+M3), one worker per user account or shared pool
3. **Data Ingestion** — Deriv WebSocket tick/candle collector, news calendar fetcher
4. **Learning Worker** — nightly 02:00 GMT jobs (Celery beat): win-rate recalc, Kelly adjustment, pattern indexing
5. **Evolution Worker** — 48h cycle: generate variations → backtest → sandbox → deploy/rollback
6. **Telegram Bot Service** — approvals with 15-min timeout, crisis alerts, YES/NO inline buttons
7. **Billing Service** — Stripe subscriptions, plan gating
8. **Notification Service** — email, in-app, push

---

## 2.2 Communication Flow

```
Deriv WS ──► Data Ingestion ──► Redis Stream ──► Agent Engine ──► Decision
                                                                    │
                                              order instruction ◄────┘
                                                     │
User's Bridge (local) ◄── WebSocket ─────────────────┘
      │
      ▼
MT5 EA executes trade ──► confirmation back ──► trade record in DB
```

---

## 2.3 Tech Stack (final list)

| Purpose | Tool |
|---|---|
| Language | Python 3.12 |
| API framework | FastAPI + Uvicorn |
| Async tasks | Celery + Redis |
| Main DB | PostgreSQL 16 (Supabase) |
| Time-series | PostgreSQL with manual partitioning |
| Cache/pubsub | Redis 7 |
| ML | hmmlearn, stable-baselines3, XGBoost, pandas, numpy |
| Backtesting | vectorbt or custom event-driven engine |
| Realtime UI | React + WebSockets (Socket.IO or native WS) |
| Desktop app | Tauri (lighter than Electron) |
| Telegram | aiogram / python-telegram-bot |
| Billing | Stripe |
| Auth | JWT + refresh tokens |
| Containerization | Docker + docker-compose (K8s later) |

---

**Previous document:** `SYNCHRO_01_Core_Architecture.md`
**Next document:** `SYNCHRO_03_Database_Architecture.md`
