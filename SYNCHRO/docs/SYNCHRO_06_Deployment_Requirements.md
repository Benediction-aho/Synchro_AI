# SYNCHRO — DOCUMENT 6: DEPLOYMENT REQUIREMENTS
### Step 6 of the development blueprint — complete functional checklist

---

## 6.1 Infrastructure
- [ ] Production server(s): 4 vCPU/8GB min, autoscaling group
- [ ] Managed PostgreSQL with TimescaleDB
- [ ] Redis instance
- [ ] Object storage (backups, model versions, PDF reports)
- [ ] CDN + WAF: Cloudflare
- [ ] Domain + SSL certificates
- [ ] Separate VPS region choice: low latency to Deriv servers (test ping!)

---

## 6.2 DevOps
- [ ] Docker images + registry
- [ ] CI/CD: GitHub Actions → staging → prod (manual approval gate)
- [ ] Monitoring: Prometheus + Grafana dashboards (latency, error rate, agent health per user)
- [ ] Error tracking: Sentry
- [ ] Uptime alerts: UptimeRobot/PagerDuty
- [ ] Secrets manager (never hardcode tokens)
- [ ] Daily DB backups + tested restore procedure

---

## 6.3 Business/Legal (required to be a real SaaS)
- [ ] Terms of Service with explicit risk disclaimer ("capital protection ≠ no losses")
- [ ] Privacy policy (GDPR if EU users)
- [ ] Refund policy
- [ ] Stripe live account
- [ ] Support channel (email/Discord)
- [ ] Marketing site explaining the agent in non-technical language

---

## 6.4 User-Facing Deliverables
- [ ] Downloadable installer (Windows .exe via Tauri; Mac optional phase 2)
- [ ] Auto-setup wizard (detects MT4/MT5, installs EA, connects)
- [ ] Quick-start guide (PDF/video, non-technical)
- [ ] In-app help center mapping every dashboard element to plain-language explanation
- [ ] Email sequence for first-week guided experience

---

**Previous document:** `SYNCHRO_05_Testing_Plan.md`
**Next document:** `SYNCHRO_07_UIUX_Specification.md`
