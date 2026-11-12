"""Measure warm, offline latency of the experimental 10-review candidate path.

This benchmark never enables serving and never writes the synthetic review text.
Run from scoring-service with ``python -m app.benchmark_phase1_latency``.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import platform
import statistics
import sys
import time
from pathlib import Path

from app.artifact_loader import load_artifact_bundle
from app.calibrate_explain import _organic_scores, apply_calibrator, explain_linear, trust_score_and_verdict

VERSION = "tl-text-1.1.0"
ROOT = Path(__file__).resolve().parents[1]
CONSTANTS_PATH = ROOT.parent / "contracts" / "v1" / "constants.json"
SYNTHETIC_BATCH = [
    "I have used this kettle every morning for three weeks and it boils enough water for two mugs.",
    "The handle stays comfortable to hold, although the lid takes a little effort to open.",
    "It heats quickly on my kitchen counter and shuts off after the water boils.",
    "After a month of daily use, the buttons still work and the cord reaches my outlet.",
    "This small kettle fits beside my coffee maker and is easy to rinse after use.",
    "The water reaches a boil in a few minutes, which is useful before work.",
    "I compared it with my old kettle and this one takes up less counter space.",
    "The lid feels stiff at first, but it became easier to open after several uses.",
    "It works well for tea in the evening, though the outside gets warm during use.",
    "I have used it for two weeks and the markings are clear when I fill it.",
]


def _system_memory_bytes() -> int | None:
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int(pages * page_size)
    except (AttributeError, OSError, ValueError):
        return None


def _limit_cpu_affinity(cpu_limit: int) -> tuple[int, str]:
    if hasattr(os, "sched_getaffinity") and hasattr(os, "sched_setaffinity"):
        allowed = sorted(os.sched_getaffinity(0))
        chosen = allowed[:cpu_limit]
        os.sched_setaffinity(0, chosen)
        return len(chosen), "process affinity limited"
    if os.name == "nt":
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        kernel.GetProcessAffinityMask.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)
        ]
        kernel.GetProcessAffinityMask.restype = ctypes.c_int
        kernel.SetProcessAffinityMask.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        kernel.SetProcessAffinityMask.restype = ctypes.c_int
        process = kernel.GetCurrentProcess()
        process_mask = ctypes.c_size_t()
        system_mask = ctypes.c_size_t()
        if not kernel.GetProcessAffinityMask(process, ctypes.byref(process_mask), ctypes.byref(system_mask)):
            raise RuntimeError("could not read process CPU affinity")
        available = int(process_mask.value)
        chosen_mask = 0
        for bit in range(available.bit_length()):
            if available & (1 << bit):
                chosen_mask |= 1 << bit
                if chosen_mask.bit_count() == cpu_limit:
                    break
        if not chosen_mask or not kernel.SetProcessAffinityMask(process, ctypes.c_size_t(chosen_mask)):
            raise RuntimeError("could not limit benchmark process CPU affinity")
        return chosen_mask.bit_count(), "process affinity limited"
    return min(cpu_limit, os.cpu_count() or 1), "affinity unavailable; processor count is informational"


def _percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _measure_batch(model, calibrator: dict, bands: list[dict]) -> None:
    raw = _organic_scores(model, SYNTHETIC_BATCH)
    probabilities = apply_calibrator(calibrator, raw)
    for text, probability in zip(SYNTHETIC_BATCH, probabilities):
        trust_score_and_verdict(float(probability), bands)
        explain_linear(model, text, numeric=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--warmups", type=int, default=20)
    parser.add_argument("--cpu-limit", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.iterations < 20 or args.warmups < 1 or not 1 <= args.cpu_limit <= 64:
        parser.error("iterations must be >=20, warmups >=1, and cpu-limit between 1 and 64")

    effective_cpus, affinity_note = _limit_cpu_affinity(args.cpu_limit)
    physical_memory = _system_memory_bytes()
    started = time.perf_counter()
    bundle = load_artifact_bundle(ROOT / "artifacts" / VERSION, VERSION)
    load_ms = (time.perf_counter() - started) * 1000
    constants = json.loads(CONSTANTS_PATH.read_text(encoding="utf-8"))
    bands = constants["bands"]
    calibrator = bundle["calibration"]

    for _ in range(args.warmups):
        _measure_batch(bundle["model"], calibrator, bands)
    durations = []
    for _ in range(args.iterations):
        before = time.perf_counter_ns()
        _measure_batch(bundle["model"], calibrator, bands)
        durations.append((time.perf_counter_ns() - before) / 1_000_000)

    target_memory = physical_memory is not None and 7 * 1024**3 <= physical_memory <= 8.5 * 1024**3
    profile_match = effective_cpus == 4 and target_memory
    p95 = _percentile95(durations)
    report = {
        "benchmark": "offline experimental candidate inference plus calibration, score mapping, and explanations",
        "servingEnabled": False,
        "modelVersion": bundle["manifest"]["modelVersion"],
        "batchSize": len(SYNTHETIC_BATCH),
        "syntheticInputsOnly": True,
        "inputTextRetained": False,
        "cpuOnly": True,
        "cpuAffinity": affinity_note,
        "effectiveCpuCount": effective_cpus,
        "physicalMemoryGiB": round(physical_memory / 1024**3, 2) if physical_memory else None,
        "targetProfile": "4 vCPU / 8 GB RAM, CPU-only, warm model",
        "targetProfileMatched": profile_match,
        "artifactLoadAndVerificationMs": round(load_ms, 3),
        "warmupBatches": args.warmups,
        "measuredBatches": args.iterations,
        "warmBatchLatencyMs": {
            "p50": round(statistics.median(durations), 3),
            "p95NearestRank": round(p95, 3),
            "max": round(max(durations), 3),
        },
        "targetP95Ms": 1500,
        "latencyTargetMetOnThisRun": p95 <= 1500,
        "phaseGateEvidenceEligible": profile_match and p95 <= 1500,
        "limitation": "Offline experimental candidate benchmark; it does not enable serving or measure Spring/HTTP/network overhead.",
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor() or "not reported",
    }
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
