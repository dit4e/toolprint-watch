# Charts

Generated from this repo's own data — `observations.csv` (daily counts) and
`findings/*.json` (rule classification) — by `generate_charts.py`.

| File | What it shows |
|---|---|
| `daily-changes.svg` / `.png` | Tool-definition changes per day; median 3/day, spikes on vendor-release days |
| `rule-distribution.svg` / `.png` | The 277 classified drift events by rule; the capability-increase signals (DRIFT-001/002) sit at zero |

Pinned to the Sep–Oct 2026 write-up window:

```
python3 charts/generate_charts.py --as-of 2026-10-04
```

SVGs are the source of truth; PNGs are rendered from them with headless Chrome:

```
<chrome> --headless --force-device-scale-factor=2 --window-size=1040,470 \
  --screenshot=charts/daily-changes.png file://<wrapped svg>
```
