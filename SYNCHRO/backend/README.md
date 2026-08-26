# SYNCHRO Backend

Cloud backend monorepo for the SYNCHRO trading agent (see `../docs/` for the full blueprint).

## Structure

```
backend/
├── src/synchro/
│   ├── core/            config (env-driven), logging, security (bcrypt + JWT)
│   ├── db/
│   │   ├── base.py      declarative base, naming conventions, JSON/JSONB helper
│   │   ├── models/      all Doc 3 tables: users, accounts, api_credentials,
│   │   │                subscriptions, configurations, trades, signals, patterns,
│   │   │                q_values, model_versions, evolution_logs, alerts, audit_log
│   │   └── session.py   engine + session factory
│   ├── api/v1/          versioned routes: /health, /auth/*
│   ├── schemas/         pydantic request/response models
│   ├── domain/          trade lifecycle state machine + audit log service
│   └── services/
│       ├── api_gateway/        FastAPI app (entry point)
│       ├── data_ingestion/     Deriv WS client + tick publishers (+ runnable main)
│       ├── agent_engine/       M1+M2+M3 brain; intelligence/regime.py = HMM regime detector
│       │                       (pure-NumPy Baum-Welch HMM, no scipy needed)
│       ├── learning_worker/    nightly Celery jobs
│       ├── evolution_worker/   48h evolution cycle
│       ├── telegram_bot/       approvals / crisis alerts
│       └── notification_service/
├── alembic/             migrations (initial schema covers all tables)
└── tests/               pytest suite (17 tests)
```

## Run locally (no Docker)

```powershell
cd SYNCHRO\backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -e ".[dev]"

copy .env.example .env

uvicorn synchro.services.api_gateway.main:app --reload
```

Then open:

- App root: http://127.0.0.1:8000
- Interactive docs (Swagger): http://127.0.0.1:8000/docs — use the Authorize button for protected routes
- Health check: http://127.0.0.1:8000/api/v1/health

## Auth API

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | create account, returns access + refresh tokens |
| POST | `/api/v1/auth/login` | email + password → tokens |
| POST | `/api/v1/auth/refresh` | rotate tokens |
| GET  | `/api/v1/auth/me` | current user (Bearer token required) |

Access tokens live 30 min, refresh tokens 14 days (configurable via `.env`).

## Migrations

```powershell
alembic upgrade head                                   apply all migrations
alembic revision --autogenerate -m "description"       generate a new migration after model changes
alembic downgrade -1                                   roll back last migration
```

## Data ingestion (Deriv WebSocket)

```powershell
python -m synchro.services.data_ingestion.main --symbols R_75,frxEURUSD --duration 30
```

- Uses Deriv's **current platform** (`api.derivws.com/trading/v1/options/ws/public`);
  market data needs no authentication.
- Publisher backend is selected via `PUBLISHER_BACKEND` (`memory` locally,
  `redis` for the Redis Streams pipeline described in Doc 2).
- Symbol codes: `R_75` (Volatility 75), `1HZ100V` (V100 1s), `frxEURUSD`, ...
- A PAT bearer token (from https://api.deriv.com) is only needed later for
  account/trade endpoints, stored encrypted in `api_credentials`.
- Tests: offline suite uses a fake Deriv server; one test streams live ticks.

## Tests

```powershell
pytest
```

## Notes

- Local dev defaults to SQLite so nothing else needs to be installed.
  Switch `DATABASE_URL` in `.env` to PostgreSQL when ready:
  `postgresql+psycopg://user:pass@localhost:5432/synchro`
  (`psycopg[binary]` is already installed.)
- Doc 3 references `account_id` on several tables without defining an `accounts`
  table; we added one. Each account belongs to a user and holds its configuration;
  `api_credentials` links user + account to broker credentials (token encryption
  at rest comes with the secrets-manager step).
- Docker/docker-compose comes later per the roadmap (Phase 0 item 2).
