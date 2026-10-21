"""Guard the job package layout against import-path regressions.

Jobs run from the API project root (``services/api``) as
``python -m jobs.<job>.<module>`` and import the application as ``app``.
Importing through ``services.api.app`` (or any other prefix) loads a second
copy of the application and fails at runtime, so these tests catch it early
without needing a database.
"""

from __future__ import annotations

import ast
import importlib
import os
import subprocess
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
JOB_MODULES = ["jobs.ingest_places.importer"]


def _python_files(*dirs: str) -> list[Path]:
    return [p for d in dirs for p in sorted((API_ROOT / d).rglob("*.py"))]


def test_no_module_imports_through_services_prefix() -> None:
    offenders: list[str] = []
    for path in _python_files("app", "jobs"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            offenders += [
                f"{path.relative_to(API_ROOT)}: {n}" for n in names if n.split(".")[0] == "services"
            ]
    assert offenders == [], f"Import the API as 'app', not via 'services.': {offenders}"


def test_job_modules_import_in_process() -> None:
    for name in JOB_MODULES:
        module = importlib.import_module(name)
        assert callable(module.main), f"{name} must expose main()"


def test_job_modules_import_from_documented_working_directory() -> None:
    """Mirror ``python -m`` resolution: a fresh interpreter whose cwd is the API root."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    for name in JOB_MODULES:
        result = subprocess.run(
            [sys.executable, "-c", f"import {name}"],
            cwd=API_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{name} failed to import:\n{result.stderr}"
