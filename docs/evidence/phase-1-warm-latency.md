# Phase 1 warm latency check

The reproducible command is run from `scoring-service`:

```powershell
.\.venv\Scripts\python.exe -m app.benchmark_phase1_latency --iterations 100 --warmups 10 --cpu-limit 4 --output ..\docs\evidence\phase-1-warm-latency-local.json
```

The benchmark loads and verifies the versioned experimental bundle, constrains
the benchmark process to four logical CPUs, warms the model, then measures 100
synthetic batches of 10 through candidate inference, calibration, score and band
mapping, and explanation generation. It retains no input text and does not
enable model serving. The JSON file records the host profile and measurements.

## Current local result

- Warm p50: **174.751 ms**
- Warm p95 (nearest rank): **211.911 ms**
- Maximum: **237.792 ms**
- Artifact load and verification: **145.041 ms**
- Host memory: **23.7 GiB**; benchmark process affinity: **4 CPUs**
- Measured p95 is below the frozen **1,500 ms** threshold.

This is a local performance result, **not a Phase 1 latency-gate pass**. The
frozen profile is 4 vCPU / 8 GB RAM, CPU-only; this host has more memory, so the
profile does not match. It also measures the offline experimental candidate
path only, not HTTP, Spring, or network overhead. The artifact remains
`EXPERIMENTAL_NOT_FOR_SERVING` with production decision `UNKNOWN`; nothing here
approves it for live scoring.

To close the latency evidence, run the same command on a 4-vCPU / 8-GB CPU-only
environment and retain its JSON output. The scorer should continue to return
honest `UNKNOWN` results until each language's manual in-domain gate is passed
or its documented fallback is selected.
