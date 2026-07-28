"""
Error generation script — trigger alerts via API.

Sends bursts of error logs to the FastAPI /generate-errors endpoint
to trigger Grafana alerts and test the alerting pipeline.

Usage:
    python -m scripts.generate_errors [--count 50] [--bursts 3] [--interval 10]
"""

import argparse
import time
import httpx


BASE_URL = "http://localhost:8000"


def generate_error_burst(count: int, service: str | None = None) -> dict:
    """Send a burst of error logs via the API."""
    payload = {
        "count": count,
        "severity": "ERROR",
    }
    if service:
        payload["service"] = service

    response = httpx.post(
        f"{BASE_URL}/api/v1/generate-errors",
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def main(count: int, bursts: int, interval: int, service: str | None) -> None:
    """Run multiple error bursts with configurable intervals."""
    print(f"{'='*60}")
    print(f"  Error Generation — Alert Trigger Test")
    print(f"{'='*60}")
    print(f"  Errors per burst: {count}")
    print(f"  Number of bursts: {bursts}")
    print(f"  Interval:         {interval}s")
    print(f"  Target service:   {service or 'random'}")
    print()

    total_generated = 0

    for i in range(bursts):
        print(f"  Burst {i + 1}/{bursts}...")

        try:
            result = generate_error_burst(count, service)
            data = result.get("data", {})
            generated = data.get("total_errors_generated", 0)
            total_generated += generated

            print(
                f"    Generated: {generated} errors | "
                f"DB: {data.get('stored_in_db', 0)} | "
                f"Kafka: {data.get('published_to_kafka', 0)}"
            )
        except Exception as e:
            print(f"    ERROR: {e}")

        if i < bursts - 1:
            print(f"    Waiting {interval}s before next burst...")
            time.sleep(interval)

    print()
    print(f"{'='*60}")
    print(f"  Total errors generated: {total_generated}")
    print(f"  Check Grafana for triggered alerts!")
    print(f"  Grafana: http://localhost:3000")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate error bursts to trigger alerts")
    parser.add_argument("--count", type=int, default=50, help="Errors per burst")
    parser.add_argument("--bursts", type=int, default=3, help="Number of bursts")
    parser.add_argument("--interval", type=int, default=10, help="Seconds between bursts")
    parser.add_argument("--service", type=str, default=None, help="Target service name")
    args = parser.parse_args()

    main(args.count, args.bursts, args.interval, args.service)
