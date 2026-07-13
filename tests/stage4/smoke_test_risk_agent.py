#!/usr/bin/env python
"""
smoke_test_risk_agent.py — end-to-end smoke test for the Stage 4 Risk Agent.

Exercises the REAL running service over HTTP (GET /health, POST /risk-score) and
prints a clear PASS/FAIL per check, like the Stage 1 spine test. Exit code is 0
only if every check passes, so it doubles as a CI gate and a demo-day check.

Usage
-----
    # against an already-running server (default http://localhost:8001)
    python "TESTING FILES/stage4/smoke_test_risk_agent.py"

    # point at a different URL
    python "TESTING FILES/stage4/smoke_test_risk_agent.py" --url http://localhost:8001

    # start the server automatically, test it, then shut it down
    python "TESTING FILES/stage4/smoke_test_risk_agent.py" --start

Env: RISK_AGENT_URL overrides the default base URL.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RISK_AGENT_DIR = os.path.join(ROOT, "risk-agent")
SHARED = os.path.join(ROOT, "shared")

CORRIDORS = ("hormuz", "redsea", "cape", "domestic")
ALERT_LEVELS = {"low", "elevated", "high", "critical"}
SEVERITIES = {"low", "medium", "high", "critical"}

PASS, FAIL = "✅", "❌"
_results = []


def check(label, ok, detail=""):
    _results.append(bool(ok))
    mark = PASS if ok else FAIL
    print(f"  {mark} {label}" + (f"  ({detail})" if detail else ""))
    return ok


def _valid_response_shape(body):
    """Validate against the frozen contract if importable; else structural checks."""
    try:
        sys.path.insert(0, SHARED)
        from schemas.risk_score import RiskScoreResponse
        RiskScoreResponse(**body)
        return True, "validates against frozen RiskScoreResponse"
    except ImportError:
        required = {"corridor", "score", "confidence", "alert_level",
                    "reasoning_trail", "key_events", "computed_at", "data_sources"}
        missing = required - set(body)
        if missing:
            return False, f"missing fields: {missing}"
        if not (0.0 <= body["score"] <= 100.0):
            return False, f"score out of range: {body['score']}"
        if not (0.0 <= body["confidence"] <= 1.0):
            return False, f"confidence out of range: {body['confidence']}"
        if body["alert_level"] not in ALERT_LEVELS:
            return False, f"bad alert_level: {body['alert_level']}"
        for ev in body["key_events"]:
            if ev.get("severity") not in SEVERITIES:
                return False, f"bad key_event severity: {ev.get('severity')}"
        return True, "structural checks passed"
    except Exception as e:
        return False, f"contract validation failed: {type(e).__name__}: {e}"


def wait_for_health(url, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(f"{url}/health", timeout=2).status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def run_checks(url):
    print(f"\nRisk Agent smoke test -> {url}\n" + "-" * 52)

    # 1. health
    print("[1] GET /health")
    try:
        r = requests.get(f"{url}/health", timeout=5)
        check("returns 200", r.status_code == 200, f"HTTP {r.status_code}")
        check('body is {"status":"ok"}', r.json() == {"status": "ok"}, str(r.json()))
    except requests.RequestException as e:
        check("server reachable", False, str(e))
        return

    # 2. /risk-score for every corridor -> valid contract
    print("[2] POST /risk-score for each corridor")
    for corridor in CORRIDORS:
        payload = {"corridor": corridor, "as_of": datetime.now(timezone.utc).isoformat()}
        try:
            r = requests.post(f"{url}/risk-score", json=payload, timeout=30)
            if not check(f"{corridor}: 200", r.status_code == 200, f"HTTP {r.status_code}"):
                continue
            body = r.json()
            ok, detail = _valid_response_shape(body)
            check(f"{corridor}: valid contract", ok, detail)
            check(f"{corridor}: score {body.get('score')} / alert {body.get('alert_level')}",
                  body.get("corridor") == corridor,
                  f"sources={body.get('data_sources')}")
        except requests.RequestException as e:
            check(f"{corridor}: request ok", False, str(e))

    # 3. validation: non-canonical corridor must be rejected
    print("[3] POST /risk-score validation")
    bad = {"corridor": "HORMUZ", "as_of": datetime.now(timezone.utc).isoformat()}
    try:
        r = requests.post(f"{url}/risk-score", json=bad, timeout=10)
        check("uppercase 'HORMUZ' -> 422", r.status_code == 422, f"HTTP {r.status_code}")
    except requests.RequestException as e:
        check("uppercase corridor rejected", False, str(e))

    missing = {"as_of": datetime.now(timezone.utc).isoformat()}  # no corridor
    try:
        r = requests.post(f"{url}/risk-score", json=missing, timeout=10)
        check("missing 'corridor' -> 422", r.status_code == 422, f"HTTP {r.status_code}")
    except requests.RequestException as e:
        check("missing field rejected", False, str(e))


def main():
    ap = argparse.ArgumentParser(description="Smoke test the Stage 4 Risk Agent.")
    ap.add_argument("--url", default=os.environ.get("RISK_AGENT_URL", "http://localhost:8001"))
    ap.add_argument("--start", action="store_true",
                    help="Launch uvicorn (risk-agent) on port 8001, test it, then stop it.")
    args = ap.parse_args()

    proc = None
    try:
        if args.start:
            print("Starting risk-agent (uvicorn main:app --port 8001) ...")
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "main:app", "--port", "8001"],
                cwd=RISK_AGENT_DIR,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if not wait_for_health(args.url):
                print(f"{FAIL} server did not become healthy in time")
                return 1
        run_checks(args.url)
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    passed = sum(_results)
    total = len(_results)
    print("-" * 52)
    print(f"{passed}/{total} checks passed  " + (PASS if passed == total else FAIL))
    return 0 if passed == total and total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
