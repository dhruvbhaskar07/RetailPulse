"""Load testing script for RetailPulse API endpoints"""
import requests
import time
import statistics
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"
CONCURRENT_USERS = [1, 5, 10, 20]
REQUESTS_PER_USER = 50

def get_token():
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": USERNAME, "password": PASSWORD})
    resp.raise_for_status()
    return resp.json()["access_token"]

def test_endpoint(endpoint, method="GET", json_data=None, headers=None):
    start = time.time()
    try:
        if method == "GET":
            resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
        else:
            resp = requests.post(f"{BASE_URL}{endpoint}", json=json_data, headers=headers, timeout=10)
        duration = time.time() - start
        return {
            "endpoint": endpoint,
            "status": resp.status_code,
            "duration": duration,
            "success": 200 <= resp.status_code < 500,
        }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "status": 0,
            "duration": time.time() - start,
            "success": False,
            "error": str(e),
        }

def run_load_test(concurrent: int, total_requests: int):
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoints = [
        ("GET", "/health"),
        ("GET", "/models/status"),
        ("POST", "/forecast", {"store_id": 1, "product_id": 1, "horizon": 7}),
        ("POST", "/churn-risk", {"customer_id": 1}),
        ("POST", "/segment", {"customer_id": 1}),
        ("POST", "/inventory", {"store_id": 1, "top_n": 10}),
        ("POST", "/what-if", {"store_id": 1, "product_id": 1, "promo_lift_pct": 20, "price_change_pct": -10}),
    ]
    
    tasks = []
    for i in range(total_requests):
        method, endpoint, *data = endpoints[i % len(endpoints)]
        json_data = data[0] if data else None
        if method == "GET":
            tasks.append((endpoint, method, None, headers))
        else:
            tasks.append((endpoint, method, json_data, headers))
    
    results = []
    with ThreadPoolExecutor(max_workers=concurrent) as executor:
        futures = [executor.submit(test_endpoint, *t) for t in tasks]
        for f in as_completed(futures):
            results.append(f.result())
    
    return results

def print_report(results, concurrent):
    durations = [r["duration"] for r in results]
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    
    print(f"\n{'='*60}")
    print(f"LOAD TEST REPORT: {concurrent} Concurrent Users")
    print(f"{'='*60}")
    print(f"Total Requests:     {len(results)}")
    print(f"Successful:         {len(successes)} ({len(successes)/len(results)*100:.1f}%)")
    print(f"Failed:             {len(failures)} ({len(failures)/len(results)*100:.1f}%)")
    print(f"Avg Duration:       {statistics.mean(durations)*1000:.1f}ms")
    print(f"Median Duration:    {statistics.median(durations)*1000:.1f}ms")
    print(f"P95 Duration:       {sorted(durations)[int(len(durations)*0.95)]*1000:.1f}ms")
    print(f"P99 Duration:       {sorted(durations)[int(len(durations)*0.99)]*1000:.1f}ms")
    print(f"Max Duration:       {max(durations)*1000:.1f}ms")
    print(f"Min Duration:       {min(durations)*1000:.1f}ms")
    print(f"Requests/sec:       {len(results)/sum(durations):.1f}")
    
    # By endpoint
    print(f"\nPer-Endpoint Breakdown:")
    by_endpoint = {}
    for r in results:
        ep = r["endpoint"]
        if ep not in by_endpoint:
            by_endpoint[ep] = {"durations": [], "success": 0, "fail": 0}
        by_endpoint[ep]["durations"].append(r["duration"])
        if r["success"]:
            by_endpoint[ep]["success"] += 1
        else:
            by_endpoint[ep]["fail"] += 1
    
    for ep, data in sorted(by_endpoint.items()):
        durs = data["durations"]
        print(f"  {ep}:")
        print(f"    Success: {data['success']}, Fail: {data['fail']}")
        print(f"    Avg: {statistics.mean(durs)*1000:.1f}ms, P95: {sorted(durs)[int(len(durs)*0.95)]*1000:.1f}ms")
    
    # Error details
    if failures:
        print(f"\nError Details:")
        for f in failures[:5]:
            print(f"  {f['endpoint']}: Status={f['status']}, Error={f.get('error', 'N/A')}")
    
    return {
        "concurrent_users": concurrent,
        "total_requests": len(results),
        "success_rate": len(successes) / len(results) * 100,
        "avg_duration_ms": statistics.mean(durations) * 1000,
        "p95_duration_ms": sorted(durations)[int(len(durations)*0.95)] * 1000,
        "requests_per_sec": len(results) / sum(durations),
    }


if __name__ == "__main__":
    print("RetailPulse API Load Test")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print(f"User: {USERNAME}")
    print(f"Concurrent users: {CONCURRENT_USERS}")
    print(f"Requests per test: {REQUESTS_PER_USER}")
    print("=" * 60)
    
    # Verify API is up
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"\nAPI Health: {resp.json()['status']}")
    except Exception as e:
        print(f"\nERROR: API not reachable at {BASE_URL}: {e}")
        print("Start the API first with: uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    all_reports = []
    for concurrent in CONCURRENT_USERS:
        print(f"\nRunning test with {concurrent} concurrent users...")
        results = run_load_test(concurrent, max(REQUESTS_PER_USER, concurrent * 5))
        report = print_report(results, concurrent)
        all_reports.append(report)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"LOAD TEST SUMMARY")
    print(f"{'='*60}")
    print(f"{'Users':<10} {'Requests':<12} {'Success':<10} {'Avg (ms)':<12} {'P95 (ms)':<12} {'RPS':<10}")
    print(f"{'-'*10} {'-'*12} {'-'*10} {'-'*12} {'-'*12} {'-'*10}")
    for r in all_reports:
        print(f"{r['concurrent_users']:<10} {r['total_requests']:<12} {r['success_rate']:<9.1f}% {r['avg_duration_ms']:<11.1f} {r['p95_duration_ms']:<11.1f} {r['requests_per_sec']:<9.1f}")
    
    print(f"\n{'='*60}")
    print("Load test complete!")
    print(f"{'='*60}")
