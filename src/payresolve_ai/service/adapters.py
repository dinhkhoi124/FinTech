"""Process-level adapter for the frozen classifier, R0 retrieval, and V3 pipeline."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from payresolve_ai.baselines.semantic import _load_encoder
from payresolve_ai.generation.gate import build_idf
from payresolve_ai.generation.pipeline_v3 import run_case_v3
from payresolve_ai.generation.support_v2 import build_canonical_idf
from payresolve_ai.retrieval.corpus import load_jsonl
from payresolve_ai.retrieval.dense import rank, r0_scores, validate_embeddings

from .contracts import API_CONTRACT_VERSION, SERVICE_VERSION

RETRIEVAL_CONFIG_PATH = Path("configs/retrieval/kb_v1_r0_r1.json")
GENERATION_CONFIG_PATH = Path("configs/generation/grounded_pipeline_v3.json")


class RuntimeInitializationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdapterResult:
    core_output: dict[str, Any]
    intent_name: str
    intent_confidence: float
    classification_ms: float
    retrieval_ms: float
    generation_ms: float


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_generation_config(code_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config = json.loads((code_root / GENERATION_CONFIG_PATH).read_text(encoding="utf-8"))
    lexicon = json.loads((code_root / config["lexicon_config"]).read_text(encoding="utf-8"))
    required = {
        "route_only": "SAFE_CORRECTIVE",
        "approved_effective_only": True,
        "may_transition_to_standard": False,
        "may_override_failed_standard_authorization": False,
        "may_authorize_unbound_factual_resolution": False,
        "fallback": "ABSTAIN_ESCALATE",
    }
    discovery = config.get("corrective_discovery", {})
    if (
        config.get("default_mode") != "TARGET_AWARE"
        or "ALWAYS_ANSWER" in json.dumps(config)
        or not isinstance(discovery.get("enabled"), bool)
        or any(discovery.get(key) != value for key, value in required.items())
    ):
        raise RuntimeInitializationError("generation configuration is not fail-closed")
    return config, lexicon


class RealPayResolveAIAdapter:
    """Load read-only runtime assets once and serve unchanged candidate outputs."""

    pipeline_entrypoint = "payresolve_ai.generation.pipeline_v3.run_case_v3"
    retrieval_strategy = "R0"

    def __init__(self, *, code_root: Path | None = None, runtime_root: Path | None = None):
        self.code_root = Path(code_root or Path(__file__).resolve().parents[3]).resolve()
        configured_runtime_root = runtime_root or Path(os.environ.get("PAYRESOLVE_RUNTIME_ROOT", self.code_root))
        self.runtime_root = Path(configured_runtime_root).resolve()

        retrieval_config = json.loads((self.code_root / RETRIEVAL_CONFIG_PATH).read_text(encoding="utf-8"))
        classifier_config = self.code_root / retrieval_config["classifier"]["config"]
        classifier_parameters = self.runtime_root / retrieval_config["classifier"]["parameters"]
        if _sha256(classifier_config) != retrieval_config["classifier"]["config_sha256"]:
            raise RuntimeInitializationError("classifier config hash mismatch")
        if not classifier_parameters.is_file() or _sha256(classifier_parameters) != retrieval_config["classifier"]["parameters_sha256"]:
            raise RuntimeInitializationError("classifier parameters unavailable or hash-mismatched")
        encoder_contract = retrieval_config["encoder"]
        if (
            encoder_contract.get("revision") != "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
            or encoder_contract.get("dimension") != 384
            or encoder_contract.get("normalize_embeddings") is not True
        ):
            raise RuntimeInitializationError("encoder contract mismatch")

        cache = self.runtime_root / retrieval_config["cache"]["directory"]
        chunks = load_jsonl(cache / "corpus.jsonl")
        corpus_embeddings = np.load(cache / "corpus_embeddings.npy", allow_pickle=False)
        validate_embeddings(corpus_embeddings, len(chunks), encoder_contract["dimension"])
        manifest = json.loads((self.code_root / retrieval_config["outputs"]["corpus_manifest"]).read_text(encoding="utf-8"))
        alignment = hashlib.sha256(("\n".join(row["chunk_id"] for row in chunks) + "\n").encode()).hexdigest()
        if alignment != manifest["chunk_alignment_sha256"]:
            raise RuntimeInitializationError("corpus alignment hash mismatch")

        semantic = json.loads(classifier_config.read_text(encoding="utf-8"))
        semantic["cache"]["huggingface_home"] = encoder_contract["huggingface_home"]
        semantic["encoder"]["local_files_only"] = True
        encoder = _load_encoder(self.runtime_root, semantic)
        payload = json.loads(gzip.decompress(classifier_parameters.read_bytes()))
        if payload["encoder"]["revision"] != encoder_contract["revision"] or payload["encoder"]["normalize_embeddings"] is not True:
            raise RuntimeInitializationError("portable classifier encoder mismatch")

        generation_config, lexicon = _load_generation_config(self.code_root)
        self._encoder = encoder
        self._classes = payload["classes"]
        self._coef = np.asarray(payload["coefficients"], dtype=np.float64)
        self._intercept = np.asarray(payload["intercept"], dtype=np.float64)
        self._chunks = chunks
        self._corpus_embeddings = corpus_embeddings
        self._chunk_ids = [row["chunk_id"] for row in chunks]
        self._retrieval_config = retrieval_config
        self._generation_config = generation_config
        self._lexicon = lexicon
        stopwords = generation_config["tokenizer"]["stopwords"]
        self._raw_idf = build_idf(chunks, stopwords)
        self._canonical_idf = build_canonical_idf(chunks, lexicon, stopwords)
        self.versions = self._build_versions()

    @classmethod
    def from_components(
        cls,
        *,
        encoder: Any,
        classes: list[str],
        coefficients: np.ndarray,
        intercept: np.ndarray,
        chunks: list[dict[str, Any]],
        corpus_embeddings: np.ndarray,
        retrieval_config: dict[str, Any],
        generation_config: dict[str, Any],
        lexicon: dict[str, Any],
        versions: dict[str, str],
    ) -> "RealPayResolveAIAdapter":
        instance = cls.__new__(cls)
        instance._encoder = encoder
        instance._classes = classes
        instance._coef = coefficients
        instance._intercept = intercept
        instance._chunks = chunks
        instance._corpus_embeddings = corpus_embeddings
        instance._chunk_ids = [row["chunk_id"] for row in chunks]
        instance._retrieval_config = retrieval_config
        instance._generation_config = generation_config
        instance._lexicon = lexicon
        stopwords = generation_config["tokenizer"]["stopwords"]
        instance._raw_idf = build_idf(chunks, stopwords)
        instance._canonical_idf = build_canonical_idf(chunks, lexicon, stopwords)
        instance.versions = versions
        return instance

    def _build_versions(self) -> dict[str, str]:
        commit = subprocess.run(
            ["git", "-C", str(self.code_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        encoder = self._retrieval_config["encoder"]
        return {
            "service_version": SERVICE_VERSION,
            "api_contract_version": API_CONTRACT_VERSION,
            "model_version": f"{encoder['model_id']}@{encoder['revision']}",
            "kb_version": Path(self._retrieval_config["kb_config"]).stem,
            "retrieval_version": self.retrieval_strategy,
            "candidate_commit": commit,
        }

    def query(self, request_id: str, query_text: str) -> AdapterResult:
        started = perf_counter()
        embeddings = self._encoder.encode_function([query_text])
        validate_embeddings(embeddings, 1, self._retrieval_config["encoder"]["dimension"])
        logits = embeddings.astype(np.float64) @ self._coef.T + self._intercept
        logits -= logits.max(axis=1, keepdims=True)
        probabilities = np.exp(logits)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        index = int(probabilities.argmax(axis=1)[0])
        intent_name = self._classes[index]
        intent_confidence = float(probabilities[0, index])
        classification_ms = (perf_counter() - started) * 1000

        started = perf_counter()
        scores = r0_scores(embeddings[0], self._corpus_embeddings)
        rankings = rank(scores, self._chunk_ids, self._retrieval_config["retrieval"]["top_k"])
        retrieval_ms = (perf_counter() - started) * 1000

        started = perf_counter()
        core_output = run_case_v3(
            {"query_id": request_id, "query_text": query_text},
            rankings,
            self._chunks,
            self._raw_idf,
            self._canonical_idf,
            self._generation_config,
            self._lexicon,
        )
        generation_ms = (perf_counter() - started) * 1000
        return AdapterResult(
            core_output=core_output,
            intent_name=intent_name,
            intent_confidence=intent_confidence,
            classification_ms=classification_ms,
            retrieval_ms=retrieval_ms,
            generation_ms=generation_ms,
        )
