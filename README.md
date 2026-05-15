<div align="center">

# YUCLAW-MATRIX

**CRT-Based Concurrent Scheduler — Research Preview**

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Hardware](https://img.shields.io/badge/hardware-DGX_Spark_GB10-green)
![Algorithm](https://img.shields.io/badge/algorithm-CRT_scheduling-purple)
![Status](https://img.shields.io/badge/status-research_preview-orange)
![License](https://img.shields.io/badge/license-MIT-red)

> Concurrent task scheduler for financial tick processing. Uses the Chinese
> Remainder Theorem (Sun Zi's *Suanjing*, ~279 CE) to route work across
> instruments without mutexes. Includes an arXiv-style paper and a simulated
> benchmark on NVIDIA DGX Spark.

</div>

---

> **Status — research preview**
> This repository contains the scheduling algorithm, a simulated benchmark,
> and a working paper. The scheduler is **not currently used in the active
> YUCLAW production cron**; the live pipeline in
> [yuclaw-brain](https://github.com/YuClawLab/yuclaw-brain) uses a simpler
> sequential engine refresh. This repo is published as research output and as
> a reference implementation for the paper.

---

## What this repo contains

| File | Purpose | LOC |
|---|---|---:|
| `yuclaw_matrix/scheduler.py` | CRT scheduler + benchmark harness | 395 |
| `yuclaw_matrix/live_feed.py` | Finnhub websocket + yfinance polling adapters | 235 |
| `paper/crt_arxiv.tex` + `crt_arxiv.md` | Working paper (LaTeX + Markdown) | — |
| `paper/submission/main.pdf` | Compiled 60 KB PDF | — |
| `docs/benchmark_weekend.json` | Raw benchmark data | — |
| `docs/benchmark_dgx_spark.md` | Benchmark write-up | — |

Total: **633 lines of Python** + working paper.

---

## The algorithm

The Chinese Remainder Theorem guarantees that for pairwise coprime moduli
`m_1, m_2, ..., m_k`, the system of congruences `x ≡ a_i (mod m_i)` has a
unique solution modulo `M = m_1 · m_2 · ... · m_k`.

**Applied to scheduling**: each instrument gets a unique prime modulus. Two
instruments A (mod `p`) and B (mod `q`) are co-active only when `t ≡ 0 (mod
p·q)`. Since `p·q >> max(p, q)`, simultaneous activations are rare, and
because each instrument only ever writes its own state, no mutex is needed.

```python
# scheduler.py:117 — the entire scheduling decision per tick per instrument
def is_active(self, tick: int) -> bool:
    return tick % self.prime == 0
```

Expected number of active instruments at any tick `t`:

```
E[active(t)] = Σ 1/p_i  ≈  N / ln(p_N)    (Mertens' theorem)
```

At `N=1000` (so `p_1000 = 7919`): `E[active] ≈ 111` per tick — about 11% of
the universe at any given moment.

---

## Benchmark — simulated workload

> **Methodology disclosure**
> The benchmark in `scheduler.py:312-355` simulates each instrument fetch with
> a hardcoded `await asyncio.sleep(0.001)` — a fixed 1 ms fake network round
> trip. **The measured latencies are scheduling overhead on top of that
> simulated 1 ms, not end-to-end production trading latency.** Real-world
> performance depends on the actual data feed, broker, and downstream pipeline.

### Single-machine NVIDIA DGX Spark (GB10 Grace Blackwell, 128 GB unified memory, ARM64)

Raw data in [`docs/benchmark_weekend.json`](docs/benchmark_weekend.json):

| Instruments | p50 latency (ms) | p95 (ms) | p99 (ms) |
|---:|---:|---:|---:|
| 50 | 1.08 | 1.12 | 1.99 |
| 100 | 1.08 | 1.15 | 2.00 |
| 300 | 1.09 | 1.33 | 3.12 |
| 1,000 | 1.11 | 1.12 | 2.00 |
| 3,000 | 1.18 | 1.20 | 2.00 |
| 10,000 | 1.41 | 2.32 | 3.91 |

**Observation**: scheduling overhead stays at roughly 1.1–1.4 ms p50 from
N=50 to N=10,000. That is the cost of the CRT dispatch loop itself,
*not* the cost of doing real work for each instrument. This demonstrates
that the scheduler adds **O(1) overhead per active instrument** — it does
not become the bottleneck as the universe grows.

It does **not** mean a real trading system reaches the market in 1.4 ms.

---

## Usage

```python
from yuclaw_matrix import CRTScheduler
import asyncio

async def fetch_price(ticker: str) -> float:
    # Your real price fetch goes here
    ...

sched = CRTScheduler(["AAPL", "MSFT", "NVDA", "..."])
await sched.run(fetch_price, max_ticks=1000)
```

Reproduce the benchmark yourself:

```bash
git clone https://github.com/YuClawLab/yuclaw-matrix
cd yuclaw-matrix
python3 yuclaw_matrix/scheduler.py
```

---

## Working paper

`paper/crt_arxiv.tex` is a draft paper (~10 pages) covering:

1. Mathematical foundation (CRT, prime sieve)
2. Algorithm and proof of lock-freedom
3. Simulated benchmark on DGX Spark
4. Discussion of related scheduling approaches

Compiled PDF: `paper/submission/main.pdf` (60 KB).

The paper has not been formally submitted to arXiv at the time of writing
this README. SSRN abstract [#6461418](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6461418)
is the related preprint covering the broader YUCLAW system.

---

## Ecosystem

| | |
|:---|:---|
| Production pipeline | [yuclaw-brain](https://github.com/YuClawLab/yuclaw-brain) |
| Live dashboard | [yuclawlab.github.io/yuclaw-brain](https://yuclawlab.github.io/yuclaw-brain) |
| PyPI | [pypi.org/project/yuclaw](https://pypi.org/project/yuclaw) |
| GitHub | [YuClawLab](https://github.com/YuClawLab) |

---

## Disclaimer

YUCLAW is open-source research and educational software. **It is NOT financial
advice or a recommendation to buy or sell any security.** Numbers in this
README come from a simulated benchmark on a single machine and do not
constitute a claim about real-world trading latency. Past performance — of
either the algorithm or any trading strategy built on it — does not predict
future results.

For educational and research purposes only. MIT Licensed.

---

<div align="center">

*Built on NVIDIA DGX Spark GB10 · MIT*

</div>
