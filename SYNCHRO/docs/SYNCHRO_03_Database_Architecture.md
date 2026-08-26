# SYNCHRO — DOCUMENT 3: DATABASE ARCHITECTURE
### Step 3 of the development blueprint

---

## 3.1 Complete Schema

**SaaS layer:**
```sql
users(id PK, email UNIQUE, password_hash, telegram_chat_id, locale, created_at)
subscriptions(id FK→users, plan[free/pro/elite], status, stripe_id, renews_at)
devices(id FK→users, device_name, os, last_seen, status)
api_credentials(id FK→users, deriv_token_encrypted, broker_type, account_login,
                account_type[demo/live], encrypted_at_rest ✓)
```

**Trading layer:**
```sql
configurations(id FK→accounts, allocated_capital, active_markets JSONB,
               risk_phase INT 0-5, min_score FIXED=5, demo_lock_until DATE)
trades(id, account_id, symbol, direction, entry_price, exit_price, sl_initial,
       sl_current, tp, lots, pnl, status[open/be/trailing/closed],
       score_components JSONB, filters_snapshot JSONB, opened_at, closed_at)
signals(id, account_id, symbol, timestamp, apex_layer_results JSONB,
        decision[BUY/SELL/WAIT], reason_text)   -- Commandment IX transparency
patterns(id FK→trades, features JSONB, hmm_state, session, outcome, is_win)
q_values(state_key TEXT, action, q_value REAL, updated_at)
model_versions(id, version, params JSONB, backtest_metrics JSONB,
               deployed_at, rolled_back BOOL)
evolution_logs(id, cycle_date, variations_tested, winner, improvement_pct,
               demo_validated, human_approved)
alerts(id, user_id, type[approval/crisis/info], payload JSONB,
       expires_at, response[yes/no/timeout])
audit_log(id, actor[agent/human/system], action, reason, created_at)
equity_snapshots(account_id, timestamp, balance, equity, daily_pnl)
```

---

## 3.2 Data Policies

- Retention: ticks 90 days hot, then aggregated; trades/patterns forever
- Encryption: AES-256 at rest for tokens; TLS 1.3 in transit
- Backup: daily automated snapshots + point-in-time recovery
- Indexing: `trades(account_id, opened_at)`, `patterns(features GIN index)`

---

**Previous document:** `SYNCHRO_02_Backend_Architecture.md`
**Next document:** `SYNCHRO_04_Development_Steps.md`
