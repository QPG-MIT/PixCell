from __future__ import annotations

import sys
from pathlib import Path

import pyarrow.parquet as pq
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
for path in (REPO_ROOT / "src", REPO_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)


@pytest.fixture(scope="session")
def core_row() -> dict:
    path = REPO_ROOT / "dataset" / "data" / "l0" / "train-00000-of-00001.parquet"
    return pq.read_table(path).slice(0, 1).to_pylist()[0]
