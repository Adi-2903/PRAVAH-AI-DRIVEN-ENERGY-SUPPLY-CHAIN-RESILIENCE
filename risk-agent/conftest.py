"""Make both this folder and the repo root importable during tests, so
`from scoring... import` / `from ingestion... import` and `from shared.contracts
... import` all resolve regardless of the working directory pytest runs from.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, _REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
