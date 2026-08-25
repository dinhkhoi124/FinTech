"""Read-only structural verifier for W3-003-EV2-E1-INC1-R1.

This program never imports the production runner, retrieval code, or evaluator.
It reports hashes, counts, ordering, and frozen identity bindings only.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


EXPECTED = {
    "a3_sha256": "19ad35b27bd3f60e0a76ae7e42ea4c06a197166e1e9ae3ea26dbecc05ae5ee54",
    "a4_sha256": "cc27895247a15a144d0f13e340ab5476fb4ec30129ca2cc7c64e2cdbcd0016e7",
    "a4_nonce": "W3-003-EV2-A4-AUTH1-20260825-0001",
    "candidate_commit": "8492659a50fe00f066f9f64d8759d544356b3a41",
    "candidate_source_sha256": "fbcd9248faf8058571ac2b8747125a013fbc73e52925cfc0d813edd55fbd0193",
    "runtime_aggregate_sha256": "7cbaa6fe5ad2f18e8f4a4c7932fa20b0d50f861ba5f1a2341fcfc3cd65f025da",
    "selected_retriever": "R0",
    "retrieval_decision_sha256": "c883478417e3a31d61457d07f4f6cb2f6c196ef54234a6deb3afb5cc1189c3ce",
    "inference_input_sha256": "4f68b235763d8fad289575291410f1a14c39353ff3e2649809ba2f3fe92e9f80",
    "case_order_sha256": "22db778f7dc83f8624d987ec9b1a9f1ff7cc9f8a46921c98f3bc759c531eb139",
    "e1_harness_sha256": "dccfc5a29dadf9731be86f130d14f994d11205e9e72d4dcc30689ce0e54e336b",
    "receipt_sha256": "169e47629d614c4bc0df0ccbeaab4a859814f1ca767d6eec563faad5d0a022d0",
    "raw_sha256": "d7c9a16fb4867f52ded6b793ccda227b3a9c0210eca44c17869d1cab4a60d263",
    "manifest_sha256": "5be5e1e4535f60413c56867ba4f4b4fb11e5b95190d28b609acf3a2cafe5d413",
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_atomic_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    paths = {
        "a3": root / "reports/week_03/results/w3_003_ev2_a3_frozen_manifest.json",
        "a4": root / "reports/week_03/results/w3_003_ev2_a4_authorization_receipt.json",
        "inputs": root / "reports/week_03/results/w3_003_ev2_a3_inference_inputs.jsonl",
        "case_order": root / "reports/week_03/results/w3_003_ev2_a3_case_order.json",
        "schema": root / "configs/evaluation/w3_003_ev2_raw_manifest_schema.json",
        "harness": root / "scripts/evaluation/week3_ev2_e1.py",
        "receipt": root / "reports/week_03/results/w3_003_ev2_e1_consumption_receipt.json",
        "raw": root / "reports/week_03/results/w3_003_ev2_e1_raw_output.jsonl",
        "manifest": root / "reports/week_03/results/w3_003_ev2_e1_raw_manifest.json",
    }
    payloads = {name: path.read_bytes() for name, path in paths.items()}
    hashes = {name: sha256_bytes(payload) for name, payload in payloads.items()}
    a3 = json.loads(payloads["a3"])
    a4 = json.loads(payloads["a4"])
    receipt = json.loads(payloads["receipt"])
    manifest = json.loads(payloads["manifest"])
    schema = json.loads(payloads["schema"])

    structural_inputs: list[dict[str, Any]] = []
    for encoded_line in payloads["inputs"].splitlines():
        source = json.loads(encoded_line)
        structural_inputs.append(
            {"ordinal": source.get("ordinal"), "case_id": source.get("case_id"), "query_sha256": source.get("query_sha256")}
        )
    frozen_case_order_source = load_json(paths["case_order"])
    frozen_case_order = [
        {"ordinal": row.get("ordinal"), "case_id": row.get("case_id"), "query_sha256": row.get("query_sha256")}
        for row in frozen_case_order_source
    ]

    physical_payloads = payloads["raw"].splitlines(keepends=True)
    ends_with_newline = payloads["raw"].endswith(b"\n")
    valid_objects: list[dict[str, Any]] = []
    malformed_ordinals: list[int] = []
    for ordinal, physical in enumerate(physical_payloads, 1):
        try:
            value = json.loads(physical)
        except (UnicodeDecodeError, json.JSONDecodeError):
            malformed_ordinals.append(ordinal)
            continue
        if not isinstance(value, dict):
            malformed_ordinals.append(ordinal)
            continue
        valid_objects.append(value)

    query_ids = [row.get("query_id") for row in valid_objects]
    unique_query_ids = set(query_ids)
    duplicate_query_ids = len(query_ids) - len(unique_query_ids)
    actual_row_hashes = [sha256_bytes(row) for row in physical_payloads]
    expected_row_hashes = manifest.get("raw_row_sha256", [])
    row_hash_matches = sum(a == b for a, b in zip(actual_row_hashes, expected_row_hashes))
    first_row_hash_mismatch = next(
        (index for index, (actual, wanted) in enumerate(zip(actual_row_hashes, expected_row_hashes), 1) if actual != wanted),
        None,
    )
    expected_case_ids = [row["case_id"] for row in structural_inputs]
    expected_query_hashes = [row["query_sha256"] for row in structural_inputs]
    case_order_matches = sum(a == b for a, b in zip(manifest.get("case_id_order", []), expected_case_ids))
    query_hash_order_matches = sum(a == b for a, b in zip(manifest.get("query_sha256_order", []), expected_query_hashes))
    raw_query_id_order_matches = sum(a == b for a, b in zip(query_ids, expected_case_ids))

    receipt_requirements = {
        "schema_version": "W3-003-EV2-CONSUMPTION-V3",
        "ev2_consumed": True,
        "started_ordinal": 1,
        "a3_manifest_sha256": EXPECTED["a3_sha256"],
        "a4_authorization_id": EXPECTED["a4_nonce"],
        "candidate_production_commit": EXPECTED["candidate_commit"],
        "candidate_source_tree_sha256": EXPECTED["candidate_source_sha256"],
        "runtime_input_aggregate_sha256": EXPECTED["runtime_aggregate_sha256"],
        "selected_retriever": EXPECTED["selected_retriever"],
        "retrieval_decision_sha256": EXPECTED["retrieval_decision_sha256"],
        "mid_run_resume_supported": False,
    }
    receipt_mismatches = [key for key, wanted in receipt_requirements.items() if receipt.get(key) != wanted]

    binding_requirements = {
        "schema_version": "W3-003-EV2-E1-RAW-MANIFEST-V2",
        "rows": 60,
        "raw_output_path": "reports/week_03/results/w3_003_ev2_e1_raw_output.jsonl",
        "raw_output_sha256": hashes["raw"],
        "case_order_sha256": EXPECTED["case_order_sha256"],
        "a3_manifest_sha256": EXPECTED["a3_sha256"],
        "a4_authorization_id": EXPECTED["a4_nonce"],
        "candidate_production_commit": EXPECTED["candidate_commit"],
        "candidate_source_tree_sha256": EXPECTED["candidate_source_sha256"],
        "runtime_input_aggregate_sha256": EXPECTED["runtime_aggregate_sha256"],
        "selected_retriever": EXPECTED["selected_retriever"],
        "retrieval_decision_sha256": EXPECTED["retrieval_decision_sha256"],
        "inference_input_sha256": EXPECTED["inference_input_sha256"],
        "consumption_receipt_path": "reports/week_03/results/w3_003_ev2_e1_consumption_receipt.json",
        "consumption_receipt_sha256": hashes["receipt"],
        "e1_harness_sha256": EXPECTED["e1_harness_sha256"],
        "scoring_loaded": False,
    }
    manifest_binding_mismatches = [key for key, wanted in binding_requirements.items() if manifest.get(key) != wanted]
    required_fields = schema.get("required_fields", [])
    manifest_schema = {
        "schema_version_match": manifest.get("schema_version") == schema.get("raw_manifest_schema_version"),
        "required_field_count": len(required_fields),
        "present_required_field_count": len(set(manifest) & set(required_fields)),
        "missing_fields": sorted(set(required_fields) - set(manifest)),
        "extra_fields": sorted(set(manifest) - set(required_fields)),
        "exact_field_set": set(manifest) == set(required_fields),
        "rows_match": manifest.get("rows") == schema.get("rows") == 60,
        "scoring_loaded_match": manifest.get("scoring_loaded") is schema.get("scoring_loaded") is False,
    }

    reconstructed = {
        "schema_version": "W3-003-EV2-E1-RAW-MANIFEST-V2",
        "rows": 60,
        "raw_output_path": "reports/week_03/results/w3_003_ev2_e1_raw_output.jsonl",
        "raw_output_sha256": hashes["raw"],
        "raw_row_sha256": actual_row_hashes,
        "case_id_order": expected_case_ids,
        "query_sha256_order": expected_query_hashes,
        "case_order_sha256": a3["case_order_sha256"],
        "a3_manifest_sha256": hashes["a3"],
        "a4_authorization_id": a4["authorization_nonce_or_id"],
        "candidate_production_commit": a3["candidate_production_commit"],
        "candidate_source_tree_sha256": a3["candidate_source_tree_sha256"],
        "runtime_input_aggregate_sha256": a3["runtime_input_aggregate_sha256"],
        "selected_retriever": a3["selected_retriever"],
        "retrieval_decision_sha256": a3["retrieval_decision_sha256"],
        "inference_input_sha256": a3["inference_input_sha256"],
        "consumption_receipt_path": "reports/week_03/results/w3_003_ev2_e1_consumption_receipt.json",
        "consumption_receipt_sha256": hashes["receipt"],
        "e1_harness_sha256": a3["e1_harness_sha256"],
        "scoring_loaded": False,
    }
    reconstructed_bytes = canonical_atomic_json(reconstructed)
    field_mismatches = sorted(
        key for key in set(reconstructed) | set(manifest) if reconstructed.get(key) != manifest.get(key)
    )
    identity_checks = {
        "a3": hashes["a3"] == EXPECTED["a3_sha256"],
        "a4": hashes["a4"] == EXPECTED["a4_sha256"],
        "inputs": hashes["inputs"] == EXPECTED["inference_input_sha256"],
        "case_order": hashes["case_order"] == EXPECTED["case_order_sha256"],
        "harness": hashes["harness"] == EXPECTED["e1_harness_sha256"],
        "receipt": hashes["receipt"] == EXPECTED["receipt_sha256"],
        "raw": hashes["raw"] == EXPECTED["raw_sha256"],
        "manifest": hashes["manifest"] == EXPECTED["manifest_sha256"],
    }
    result = {
        "identity_sha256": hashes,
        "identity_checks": identity_checks,
        "receipt": {"exact": not receipt_mismatches, "mismatch_fields": receipt_mismatches},
        "manifest_schema": manifest_schema,
        "manifest_binding": {"exact": not manifest_binding_mismatches, "mismatch_fields": manifest_binding_mismatches},
        "raw_structure": {
            "physical_rows": len(physical_payloads),
            "valid_json_object_rows": len(valid_objects),
            "unique_query_ids": len(unique_query_ids),
            "duplicate_query_ids": duplicate_query_ids,
            "malformed_rows": len(malformed_ordinals),
            "malformed_ordinals": malformed_ordinals,
            "trailing_partial_row": bool(physical_payloads and not physical_payloads[-1].endswith(b"\n")),
            "ends_with_newline": ends_with_newline,
        },
        "row_hashes": {
            "manifest_count": len(expected_row_hashes),
            "physical_count": len(actual_row_hashes),
            "match_count": row_hash_matches,
            "first_mismatch_ordinal": first_row_hash_mismatch,
        },
        "order": {
            "structural_input_count": len(structural_inputs),
            "case_order_file_exact": structural_inputs == frozen_case_order,
            "manifest_case_id_matches": case_order_matches,
            "manifest_query_sha256_matches": query_hash_order_matches,
            "raw_query_id_matches": raw_query_id_order_matches,
        },
        "reconstruction": {
            "deep_equal": reconstructed == manifest,
            "field_mismatch_count": len(field_mismatches),
            "field_mismatches": field_mismatches,
            "serialized_sha256": sha256_bytes(reconstructed_bytes),
            "serialized_bytes_equal_live": reconstructed_bytes == payloads["manifest"],
            "live_manifest_sha256": hashes["manifest"],
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
