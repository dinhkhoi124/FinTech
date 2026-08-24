"""Shared pre-inference/pre-scoring integrity primitives for EV2."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Iterable

SOURCE_PREFIX = "src/payresolve_ai/"
TREE_ALGORITHM = "SORTED_PATH_NUL_U64BE_LENGTH_RAW_BYTES_SHA256_V1"


class IntegrityError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def aggregate_bindings_sha256(bindings: dict[str, str]) -> str:
    return stable_json_sha256([{"path": path, "sha256": bindings[path]} for path in sorted(bindings)])


def canonical_tree_sha256(entries: Iterable[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for relative, payload in sorted(entries):
        encoded = relative.replace("\\", "/").encode("utf-8")
        digest.update(encoded);digest.update(b"\0");digest.update(len(payload).to_bytes(8, "big"));digest.update(payload)
    return digest.hexdigest()


def candidate_source_tree_receipt(root: Path, commit: str) -> dict[str, Any]:
    listing = subprocess.check_output(["git", "ls-tree", "-r", "--full-tree", commit, "src/payresolve_ai"], cwd=root, text=True)
    entries = []
    for line in listing.splitlines():
        metadata, relative = line.split("\t", 1)
        mode, kind, blob = metadata.split()
        if kind != "blob":
            continue
        payload = subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=root)
        entries.append({"path": relative.replace("\\", "/"), "git_mode": mode, "git_blob": blob, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    if not entries:
        raise IntegrityError("CANDIDATE_EXECUTION_SOURCE_TREE_EMPTY")
    payloads = [(entry["path"], subprocess.check_output(["git", "show", f"{commit}:{entry['path']}"], cwd=root)) for entry in entries]
    return {
        "schema_version": "W3-003-EV2-CANDIDATE-SOURCE-TREE-V1",
        "algorithm": TREE_ALGORITHM,
        "candidate_commit": commit,
        "git_tree": subprocess.check_output(["git", "rev-parse", f"{commit}:src/payresolve_ai"], cwd=root, text=True).strip(),
        "entry_count": len(entries),
        "canonical_sha256": canonical_tree_sha256(payloads),
        "entries": entries,
    }


def verify_working_source_tree(root: Path, receipt: dict[str, Any]) -> str:
    if receipt.get("schema_version") != "W3-003-EV2-CANDIDATE-SOURCE-TREE-V1" or receipt.get("algorithm") != TREE_ALGORITHM:
        raise IntegrityError("CANDIDATE_SOURCE_TREE_RECEIPT_SCHEMA")
    expected = [entry["path"] for entry in receipt.get("entries", [])]
    source_root = root / "src/payresolve_ai"
    actual = sorted(path.relative_to(root).as_posix() for path in source_root.rglob("*") if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"})
    if actual != expected:
        raise IntegrityError("CANDIDATE_EXECUTION_SOURCE_TREE_DRIFT")
    payloads = []
    for entry in receipt["entries"]:
        path = root / entry["path"]
        payload = path.read_bytes()
        if len(payload) != entry["bytes"] or hashlib.sha256(payload).hexdigest() != entry["sha256"]:
            raise IntegrityError("CANDIDATE_EXECUTION_SOURCE_TREE_DRIFT")
        payloads.append((entry["path"], payload))
    actual_hash = canonical_tree_sha256(payloads)
    if actual_hash != receipt.get("canonical_sha256"):
        raise IntegrityError("CANDIDATE_EXECUTION_SOURCE_TREE_DRIFT")
    return actual_hash


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True);handle.write("\n");handle.flush();os.fsync(handle.fileno())
    os.replace(temporary, path)
