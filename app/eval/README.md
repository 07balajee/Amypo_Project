# Evaluation

## Router: how `optimal_route` labels are derived

`data/synthetic/router_scenarios.jsonl` labels each (prompt, scenario, t_sec) with the route a
well-behaved router should pick. The labels come from this rule table
(`scripts/synth/benchmarks.py::optimal_route`), using the prompt's **true** complexity label (not its
hint) and the thresholds in `config.yaml` (`router.thresholds`):

| Feasibility | Rule |
|---|---|
| local feasible | `ram_available_mb >= local_min_ram_mb` (1500) and `cpu_load_pct < local_max_cpu_pct` (90) |
| remote feasible | `bandwidth_kbps >= remote_min_bw_kbps` (64) and `api_quota_remaining > 0` |

| Complexity | Preference order (first feasible wins) | Why |
|---|---|---|
| low | local_model → cloud_api → offline_fallback | local quality (3) meets required (1) at zero cost |
| medium | local_model → cloud_api → offline_fallback | local quality (2) meets required (2) at zero cost |
| high | cloud_api → local_model → offline_fallback | only remote quality (3) meets required (3) |

Notes:

- **Cold cache.** Labels assume every request is evaluated on its own with `dry_run: true`, so `cache`
  is never the optimal label. Cache behaviour is measured separately with the repeat/paraphrase
  prompts (`repeat_of` in `router_prompts.jsonl`).
- **Flapping is excluded from the labels.** In `flapping.csv` the bandwidth oscillates around the
  64 kbps floor. Hysteresis (CLAUDE.md §7) should deliberately *lag* the raw threshold, so we score
  that scenario by the number of route flips instead of accuracy.
- **Offline fallback** is labelled only when no model tier is feasible (the `ram_squeeze` window at
  t=160–200 s, where the link also drops).
- **Don't overfit.** These labels come from the same rules the decision engine encodes. Tune
  weights on router accuracy *and* the cost and latency baselines, not on this accuracy alone.

## Scenario traces (`data/synthetic/scenarios/*.csv`)

Columns: `t_sec, bandwidth_kbps, ram_available_mb, cpu_load_pct, api_quota_remaining`, every 5 s from 0 to 300 s.

| Scenario | What happens |
|---|---|
| steady | healthy: about 900 kbps, about 3.2 GB free RAM, 30% CPU, quota slowly decreasing |
| bandwidth_drop | bandwidth falls to about 40 kbps for t = 90–210 s |
| quota_exhaustion | quota drains linearly from 60 to 0 by t = 240 s |
| ram_squeeze | free RAM falls to about 900 MB for t = 90–210 s; bandwidth also drops for t = 160–200 s |
| flapping | bandwidth alternates between 58 and 72 kbps every 10 s |
| remote_down | bandwidth is 0 (remote unreachable) for t = 60–240 s |
