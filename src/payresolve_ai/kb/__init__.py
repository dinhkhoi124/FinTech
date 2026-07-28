"""Controlled synthetic knowledge-base contracts and validation."""

from payresolve_ai.kb.validation import (
    KBValidationError,
    canonical_dataset_sha256,
    is_document_eligible,
    load_documents,
    validate_kb,
)

__all__ = [
    "KBValidationError",
    "canonical_dataset_sha256",
    "is_document_eligible",
    "load_documents",
    "validate_kb",
]
