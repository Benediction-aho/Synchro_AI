# SYNCHRO Phase 5: Integration & Production Deployment

## Overview
Phase 5 completes the SYNCHRO trading agent system with:
- MQL5 EA + External Bridge (file-based polling, HMAC signing)
- Tauri Desktop Auto-Installer (MT5 detection, EA deployment, verification)
- AWS Infrastructure (Terraform: ECS Fargate, Supabase, ElastiCache, Secrets Manager)
- CI/CD Pipeline (GitHub Actions: test → build → security scan → deploy)
- 30-day Closed Beta (25 users, demo-rule enforcement)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLOUD (AWS)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ API Gateway │  │ Learning    │  │ Evolution   │             │
│  │ (FastAPI)   │  │ Worker      │  │ Worker      │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Supabase (PostgreSQL + TimescaleDB)        │   │
│  │  • Users, Accounts, Trades, Signals, Patterns           │   │
│  │  • RLS per user                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│         ┌────────────────┼────────────────┐                   │
│         ▼                ▼                ▼                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   Redis     │  │  Secrets    │  │   S3        │           │
│  │ (ElastiCache)│  │  Manager    │  │ (Backups)   │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ mTLS / HMAC
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL BRIDGE (Python)                     │
│  C:\SynchroBridge\                                              │
│  ├── commands/ (Cloud→EA)                                       │
│  ├── responses/ (EA→Cloud)                                      │
│  ├── heartbeat/                                                 │
│  ├── state/                                                     │
│  └── config/                                                    │
└─────────────────────────────────────────────────────────────────┘
                          │
                          │ File Polling (500ms)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MQL5 EA (Windows)                          │
│  • File polling (500ms)                                         │
│  • HMAC-SHA256 signing                                          │
│  • Heartbeat every 5s                                           │
│  • Protective mode (60s cloud timeout)                          │
│  • Order execution: OPEN/MODIFY/CLOSE/PARTIAL/BE/TRAIL          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security Model

| Layer | Implementation |
|-------|----------------|
| **Secrets** | AWS Secrets Manager (Deriv tokens, JWT, HMAC key, DB URL) |
| **Transport** | mTLS (Cloud↔Bridge), File permissions (Bridge↔EA) |
| **Signing** | HMAC-SHA256 on every command/response (32-byte key from Secrets Manager) |
| **Replay Protection** | UUID v4 nonces + 5-min timestamp window |
| **Database** | Supabase RLS per user |
| **Network** | Cloudflare WAF, VPC private subnets, Security Groups |
| **EA** | Code-signed binary, no network access, file-only comms |
| **Bridge** | Runs as restricted Windows service |

---

## Quick Start

### Prerequisites
- AWS Account with admin permissions
- Supabase project (PostgreSQL + TimescaleDB)
- Deriv API tokens (demo for beta)
- Windows 10/11 with MetaTrader 5 installed

### 1. Configure AWS Secrets
```bash
# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret --name synchro/database-url \
  --secret-string 'postgresql://user:pass@host:5432/db?sslmode=require'

aws secretsmanager create-secret --name synchro/jwt-secret \
  --secret-string 'your-256-bit-secret-key'

aws secretsmanager create-secret --name synchro/encryption-key \
  --secret-string 'your-32-byte-encryption-key'

aws secretsmanager create-secret --name synchro/redis-url \
  --secret-string 'rediss://user:pass@host:6379'

aws secretsmanager create-secret --name synchro/deriv-ws-url \
  --secret-string 'wss://api.derivws.com/trading/v1/options/ws/public'

aws secretsmanager create-secret --name synchro/bridge/hmac-key \
  --secret-string '{"hmac_key": "your-32-byte-hmac-key"}'
```

### 2. Deploy Infrastructure
```bash
cd SYNCHRO/infra/terraform
terraform init
terraform plan -var="environment=staging" -var="image_tag=latest"
terraform apply
```

### 3. Deploy Application (CI/CD)
Push to `main` branch triggers:
1. Backend tests (194 tests)
2. Frontend build + type check
3. Bridge tests
4. Security scans (Trivy, OWASP ZAP)
5. Docker build & push to ECR
6. Terraform plan
7. **Manual approval** → Deploy staging
8. **Manual approval** → Deploy production

### 4. Build Desktop Installer
```bash
cd SYNCHRO/tauri_installer
npm install
npm run tauri build
# Output: SYNCHRO_1.0.0_x64.msi
```

### 5. Install on User Machine
1. Run `SYNCHRO_1.0.0_x64.msi` as Administrator
2. Installer auto-detects MT5, deploys EA to `MQL5/Experts/SYNCHRO`
3. Creates `C:\SynchroBridge\` with secure permissions
3. Installs bridge as Windows service
4. Launches SYNCHRO app → Onboarding wizard (Token → Capital → Markets → Telegram → Launch)

---

## Beta Program (30 Days, 25 Users)

### Enrollment
1. User signs up at `https://synchro.trade/beta`
2. Receives invite email with download link
3. Runs installer → Onboarding wizard
4. Connects Deriv demo account
5. Sets capital, selects markets, links Telegram

### Demo Rule Enforcement
- **All beta accounts start in demo mode**
- 30 consecutive demo days required before live eligibility
- Daily equity snapshots tracked in Supabase
- Automatic demo-lock if rules violated

### Monitoring
- **Grafana Cloud**: ECS CPU/Memory, ALB latency, Redis, ECS health
- **Sentry**: Error tracking
- **CloudWatch**: Custom metrics (trades/day, win rate, PnL)
- **Alerts**: PagerDuty for critical errors

---

## File Structure (Phase 5 Additions)

```
SYNCHRO/
├── mql5_bridge/
│   ├── PROTOCOL.md              # Bridge protocol specification
│   ├── ea/
│   │   └── SYNCHRO_Bridge_EA.mq5    # MQL5 Expert Advisor
│   └── bridge/
│       ├── config.py            # AWS Secrets Manager integration
│       ├── crypto.py            # HMAC signing/verification
│       ├── main.py              # File polling bridge service
│       ├── requirements.txt
│       └── test_bridge.py       # Unit tests
├── tauri_installer/
│   ├── tauri.conf.json          # Tauri config
│   ├── installer.nsi            # NSIS installer script
│   ├── src-tauri/               # Rust backend
│   └── icons/                   # App icons
├── infra/
│   └── terraform/
│       ├── main.tf              # AWS infrastructure
│       ├── variables.tf
│       └── outputs.tf
├── .github/workflows/
│   └── ci-cd.yml                # Complete CI/CD pipeline
└── docs/phase5/
    └── DEPLOYMENT_GUIDE.md
```

---

## Testing Checklist

### Pre-Deploy
- [ ] Backend: 194 tests pass
- [ ] Frontend: TypeScript compiles, build succeeds
- [ ] Bridge: Unit tests pass
- [ ] Security: Trivy scan clean, no CRITICAL/HIGH vulns
- [ ] Terraform: `fmt`, `validate`, `plan` pass

### Staging Validation
- [ ] Health endpoints return 200
- [ ] Deriv WS connection established
- [ ] Bridge processes commands → EA executes
- [ ] EA heartbeat received every 5s
- [ ] Protective mode triggers at 60s timeout
- [ ] Telegram approvals work (15-min timeout)
- [ ] Reports generate PDF/CSV

### Production Go/No-Go
- [ ] Load test: 100 concurrent users, <500ms p99
- [ ] Pen-test report reviewed (no CRITICAL/HIGH)
- [ ] Legal: ToS, Privacy Policy published
- [ ] Backup/restore tested (RPO < 1hr, RTO < 4hr)
- [ ] Beta agreement signed by 25 users

---

## Rollback Procedure

1. **ECS**: `aws ecs update-service --task-definition previous-revision`
2. **Terraform**: `terraform apply -replace=aws_ecs_task_definition.services["api-gateway"]`
3. **Database**: Supabase point-in-time recovery (RPO < 5min)
4. **Bridge**: Stop service, restore `C:\SynchroBridge\config\` from backup

---

## Support

- **Documentation**: `https://docs.synchro.trade`
- **Beta Support**: `beta-support@synchro.trade`
- **Security Issues**: `security@synchro.trade`
- **Status Page**: `https://status.synchro.trade`