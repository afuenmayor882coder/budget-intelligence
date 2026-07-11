"""JSON-based model registry."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REGISTRY_DIR = Path(__file__).parent.parent.parent / "data" / "models"
REGISTRY_FILE = REGISTRY_DIR / "registry.json"


def _ensure_dir():
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_FILE.exists():
        REGISTRY_FILE.write_text("[]", encoding="utf-8")


def load_registry() -> list[dict]:
    _ensure_dir()
    try:
        return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_registry(entries: list[dict]):
    _ensure_dir()
    REGISTRY_FILE.write_text(json.dumps(entries, indent=2, default=str), encoding="utf-8")


def register_run(
    model_name: str,
    layer: str,
    target: str,
    hyperparams: dict | None = None,
    metrics: dict | None = None,
    artifact_path: str | None = None,
    conn=None,
) -> dict:
    """Register a model run in JSON registry and optionally SQLite."""
    entry = {
        "id": len(load_registry()) + 1,
        "model_name": model_name,
        "layer": layer,
        "target": target,
        "hyperparams": hyperparams or {},
        "metrics": metrics or {},
        "artifact_path": artifact_path,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }

    entries = load_registry()
    entries.append(entry)
    save_registry(entries)

    if conn is not None:
        conn.execute(
            """INSERT INTO model_runs (model_name, layer, hyperparams, metrics, artifact_path)
               VALUES (?,?,?,?,?)""",
            (
                model_name,
                layer,
                json.dumps(hyperparams or {}),
                json.dumps(metrics or {}),
                artifact_path,
            ),
        )

    return entry


def get_best_model(target: str, metric: str = "mae") -> dict | None:
    entries = [e for e in load_registry() if e.get("target") == target]
    if not entries:
        return None
    valid = [e for e in entries if metric in (e.get("metrics") or {})]
    if not valid:
        return entries[-1]
    return min(valid, key=lambda e: e["metrics"][metric])


def list_runs(target: str | None = None, layer: str | None = None) -> list[dict]:
    entries = load_registry()
    if target:
        entries = [e for e in entries if e.get("target") == target]
    if layer:
        entries = [e for e in entries if e.get("layer") == layer]
    return entries
