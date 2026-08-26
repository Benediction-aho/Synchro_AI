# SYNCHRO — DOCUMENT 1: CORE ARCHITECTURE
### Step 1 of the development blueprint (from Part III of the logbook)

---

## 1.1 The Best Core Architecture for Your Product

Your product has **two parts** that must be physically separated:

```
╔══════════════════════════════════════╗   ╔═══════════════════════════════╗
║        CLOUD (SaaS Backend)           ║   ║   USER'S COMPUTER (Local)     ║
╠══════════════════════════════════════╣   ╠═══════════════════════════════╣
║ • Brain: M1 Consciousness (HMM/NLP)  ║   ║ • Desktop App (installer)     ║
║ • M2 Decision-Making (RL)            ║◄──►║ • Bridge Service              ║
║ • M3 Execution Logic (5/5 Score)     ║ W ║ • MT4/MT5 Expert Advisor      ║
║ • M4 Learning Engine                 ║ S ║   (.ex5/.ex4 file)            ║
║ • M5 Telegram Bot                    ║   ║ • Local fallback protections  ║
║ • M6 Evolution Engine                ║   ║ • Offline kill-switch         ║
║ • Web Dashboard (React)              ║   ╚═══════════════════════════════╝
║ • API Gateway + Auth + Billing       ║
╚══════════════════════════════════════╝
```

**Why this split is the "best core architecture":**
- Intelligence stays in YOUR cloud → you control updates, learning, and IP protection
- Execution lives locally → MT4/MT5 can only be controlled by an EA running inside the terminal
- If internet drops → local EA keeps breakeven/trailing alive (Commandment II survives outages)
- Scaling: thousands of users share one brain infrastructure

---

## 1.2 The 9 APEX Layers → Implementation Mapping

| Layer | Your Doc | Technology | Runs On |
|---|---|---|---|
| ① REGIME | HMM 5 states | Python `hmmlearn`, Baum-Welch | Cloud |
| ② SENTIMENT | News NLP | FinBERT / economic calendar API | Cloud |
| ③ MACRO | Context engine | DXY feed, correlation matrix | Cloud |
| ④ STRUCTURE | OB/FVG/BOS scanner | Custom candle-structure library | Cloud |
| ⑤ TREND | Multi-TF EMA validator | pandas/numpy on OHLCV | Cloud |
| ⑥ MOMENTUM | RSI/Stoch/MACD/BB | `ta` library | Cloud |
| ⑦ ENTRY | Trigger candle gate | Pattern detector functions | Cloud |
| ⑧ RISK | Kelly+Bayes+CLT sizing | Pure math module | Cloud + EA mirror |
| ⑨ EXECUTE | 15 filters | Filter chain | Cloud + EA mirror |

---

**Next document:** `SYNCHRO_02_Backend_Architecture.md`
