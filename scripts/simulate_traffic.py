"""
Traffic simulation script — hit FastAPI endpoints continuously.

Sends HTTP requests to the FastAPI service to simulate realistic
traffic patterns. Useful for populating Grafana dashboards and
testing Prometheus metrics.

Usage:
    python -m scripts.simulate_traffic [--duration 60] [--rps 5]
"""

import argparse
import asyncio
import random
import time
import sys

import httpx

BASE_URL = "http://localhost:8000"

# Endpoints to hit with relative weights
ENDPOINTS = [
    ("GET",  "/api/v1/logs",                        30),
    ("GET",  "/api/v1/logs?service=auth-service",    10),
    ("GET",  "/api/v1/logs?level=ERROR",             10),
    ("GET",  "/api/v1/logs/service/payment-service",  8),
    ("GET",  "/api/v1/logs/level/WARNING",            8),
    ("GET",  "/api/v1/stats",                        15),
    ("GET",  "/api/v1/health",                       10),
    ("GET",  "/metrics",                              5),
    ("POST", "/api/v1/simulate",                      4),
]


async def send_request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
) -> dict:
    """Send a single HTTP request and return stats."""
    url = f"{BASE_URL}{path}"
    start = time.perf_counter()

    try:
        if method == "GET":
            response = await client.get(url, timeout=10.0)
        else:
            body = {"count": random.randint(5, 20)}
            response = await client.post(url, json=body, timeout=10.0)

        duration_ms = (time.perf_counter() - start) * 1000

        return {
            "method": method,
            "path": path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "success": response.status_code < 400,
        }
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        return {
            "method": method,
            "path": path,
            "status": 0,
            "duration_ms": round(duration_ms, 2),
            "success": False,
            "error": str(e),
        }


async def run_simulation(duration_seconds: int, requests_per_second: float) -> None:
    """Run the traffic simulation for a given duration."""
    print(f"{'='*60}")
    print(f"  Traffic Simulation")
    print(f"  Duration: {duration_seconds}s | Target RPS: {requests_per_second}")
    print(f"  Base URL: {BASE_URL}")
    print(f"{'='*60}")
    print()

    # Extract weights for random selection
    methods = [e[0] for e in ENDPOINTS]
    paths = [e[1] for e in ENDPOINTS]
    weights = [e[2] for e in ENDPOINTS]

    stats = {
        "total": 0,
        "success": 0,
        "errors": 0,
        "total_duration_ms": 0.0,
    }

    interval = 1.0 / requests_per_second
    start_time = time.time()

    async with httpx.AsyncClient() as client:
        while time.time() - start_time < duration_seconds:
            # Pick a random endpoint based on weights
            idx = random.choices(range(len(ENDPOINTS)), weights=weights, k=1)[0]
            method = methods[idx]
            path = paths[idx]

            result = await send_request(client, method, path)

            stats["total"] += 1
            stats["total_duration_ms"] += result["duration_ms"]
            if result["success"]:
                stats["success"] += 1
            else:
                stats["errors"] += 1

            # Progress indicator every 10 requests
            if stats["total"] % 10 == 0:
                elapsed = time.time() - start_time
                actual_rps = stats["total"] / elapsed if elapsed > 0 else 0
                print(
                    f"  [{elapsed:6.1f}s] Requests: {stats['total']:5d} | "
                    f"Success: {stats['success']:5d} | "
                    f"Errors: {stats['errors']:3d} | "
                    f"RPS: {actual_rps:.1f}"
                )

            # Wait to maintain target RPS
            await asyncio.sleep(interval)

    # Final summary
    elapsed = time.time() - start_time
    avg_latency = stats["total_duration_ms"] / max(stats["total"], 1)

    print()
    print(f"{'='*60}")
    print(f"  Simulation Complete")
    print(f"{'='*60}")
    print(f"  Duration:       {elapsed:.1f}s")
    print(f"  Total Requests: {stats['total']}")
    print(f"  Successful:     {stats['success']}")
    print(f"  Errors:         {stats['errors']}")
    print(f"  Avg Latency:    {avg_latency:.2f}ms")
    print(f"  Actual RPS:     {stats['total'] / elapsed:.1f}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate traffic to FastAPI")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--rps", type=float, default=5.0, help="Requests per second")
    args = parser.parse_args()

    asyncio.run(run_simulation(args.duration, args.rps))
