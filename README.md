# Yuclaw-Matrix — CRT Lock-Free Concurrent Scheduler

**High-performance task scheduler for parallel financial computation.**

15x faster than `threading` at 1,000+ concurrent instruments using lock-free CRT (Chinese Remainder Theorem) scheduling.

## Overview

Yuclaw-Matrix is the concurrency backbone of the YUCLAW ATROS system. It schedules parallel LLM inference, market data ingestion, and portfolio computations across heterogeneous hardware (GPU + CPU) without traditional locking.

## Key Features

- **Lock-free scheduling** — CRT-based work distribution eliminates mutex contention
- **15x throughput** — benchmarked vs Python `threading` at 1,000 instruments
- **GPU-aware** — routes compute to CUDA cores or CPU based on task type
- **Backpressure** — adaptive rate limiting prevents GPU OOM under burst load
- **Zero-copy IPC** — shared memory buffers between inference and post-processing

## Architecture

```
┌──────────────────────────────────────────┐
│           CRT Scheduler Core             │
│  ┌─────────┐ ┌─────────┐ ┌───────────┐  │
│  │ GPU Pool │ │ CPU Pool │ │ I/O Pool  │  │
│  └────┬────┘ └────┬────┘ └─────┬─────┘  │
│       └───────────┼────────────┘         │
│              Work Stealing               │
│           (lock-free queues)             │
└──────────────────────────────────────────┘
```

## Usage

```python
from yuclaw_matrix import Scheduler

sched = Scheduler(gpu_workers=1, cpu_workers=8)

async def analyze(ticker):
    return await llm.complete(f"Analyze {ticker}")

# Schedule 1000 instruments concurrently
results = await sched.map(analyze, tickers)
```

## Benchmarks

| Concurrency | threading (s) | Yuclaw-Matrix (s) | Speedup |
|-------------|--------------|-------------------|---------|
| 100         | 12.4         | 2.1               | 5.9x    |
| 500         | 58.7         | 4.8               | 12.2x   |
| 1,000       | 124.3        | 8.2               | 15.2x   |

## Part of YUCLAW ATROS

This is a component of the [YUCLAW ATROS](https://github.com/YuClawLab/yuclaw-brain) financial intelligence system.

## License

Proprietary — YuClawLab
