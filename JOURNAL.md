# Kraken Adaptive Bot — Journal

## Todos
- [ ] Download 1h candles for the matrix assets (`scripts/download_ohlcv.py`) → `data/`
- [ ] Run `backtest/run_matrix.py --config configs/shared_baseline.json` and READ the ranking CSV (first real edge check — nothing proves an edge yet)
- [ ] Benchmark every window against buy-and-hold BTC; strategy must beat holding *after fees* to count as edge
- [ ] Fix timeframe mismatch: `bot/config.py` hardcodes `TIMEFRAME="5m"` but all research is 1h
- [ ] Decide realistic fee rate — `0.0026`/side (0.52% round-trip) is high; Kraken Pro maker/volume tiers are far lower
- [ ] Live loop ignores `bot/risk.py` sizing (flat `TRADE_USD`); wire risk-based sizing + trailing/EMA20 exit before any live use
- [ ] Fix EC2 systemd unit (`status=217/USER` crash loop) if cloud deploy is still wanted
- [ ] No real-order code exists anywhere — remains paper-only until walk-forward proves positive expectancy across assets AND regimes

## Entries

### 2026-11-24 — Repo review: "can it make money?"
Read the whole repo end to end (code, configs, notes, journal01.txt, git history). Verdict: **not as-is, and the gap is evidence not code.**
- Live loop (`bot/main.py`) is paper-only via `PaperTrader`; grep for `create_order`/`add_order` across repo = zero hits. Cannot touch real balance.
- `journal01.txt` (460KB) is entirely the EC2 service crash-looping on `status=217/USER` — never ran a successful iteration.
- No `data/`, no result CSVs; git history opens with "Failed first back test" then ~12 commits adding filters/gates = overfitting search. The walk-forward ranking the repo is built to produce has never been generated.
- Config/code smells: 5m-vs-1h timeframe mismatch; risk sizing in `risk.py` unused by live loop; live exit stop/target only; 0.52% round-trip fee is both a brutal hurdle and pessimistic vs real Kraken Pro fees.
- Strategy template (EMA-stack trend pullback breakout) is legitimate, just unproven.
- Offered to download candles + run the matrix as the free, highest-value next step. Awaiting user answer.
No code changes this session (review only).
