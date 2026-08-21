"""Test isolation.

Two separate problems are solved here.

Import time: `aeris.app.api` constructs a ProductStore as a module-level global, which
creates and migrates a database as soon as the module is imported. Pointing
AERIS_DB_PATH at a temporary directory *before* any test module is imported keeps the
suite from creating and mutating `artifacts/aeris_product.db` inside the working tree.
conftest.py is imported before the test modules, so this runs early enough.

Per test: the tests that exercise the API used the module-level store directly, so rows
created by one test were visible to the next and results depended on what a previous run
had left behind. Each test now gets a freshly seeded database.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP_ROOT = tempfile.mkdtemp(prefix="aeris-tests-")
os.environ.setdefault("AERIS_DB_PATH", str(Path(_TMP_ROOT) / "import_time.db"))

import pytest  # noqa: E402  - must follow the env var above

from aeris.app import api  # noqa: E402
from aeris.app.product_service import ProductStore  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_product_store(tmp_path, monkeypatch) -> ProductStore:
    """Give every test its own freshly seeded database."""
    store = ProductStore(tmp_path / "aeris_product.db")
    monkeypatch.setattr(api, "product_store", store)
    return store
