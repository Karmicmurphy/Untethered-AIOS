"""Foundation Release 0.4 libraries and fixed-worker harness.

These libraries are inert until a caller explicitly invokes them. In particular,
Worker Cards are declarations and do not create an operating-system sandbox;
only the two fixed harness workers have executable host integrations.
"""

from .worker_cards import (
    SUPPORTED_SCHEMA_VERSION,
    WorkerCardValidationResult,
    load_worker_card,
    validate_worker_card,
)
from .artifact_compass import ArtifactCompass, ArtifactRecord, StaleEntry, SyncResult
from .path_policy import PathDecision, WindowsPathPolicy
from .transactions import ReceiptChainVerification, TransactionManager, sha256_file
from .promotion import ActivationRegistry, CandidateStore, PromotionError
from .worker_harness import HarnessError, WorkerHarness

__all__ = [
    "SUPPORTED_SCHEMA_VERSION",
    "WorkerCardValidationResult",
    "load_worker_card",
    "validate_worker_card",
    "ArtifactCompass",
    "ArtifactRecord",
    "StaleEntry",
    "SyncResult",
    "PathDecision",
    "WindowsPathPolicy",
    "ReceiptChainVerification",
    "TransactionManager",
    "sha256_file",
    "ActivationRegistry",
    "CandidateStore",
    "PromotionError",
    "HarnessError",
    "WorkerHarness",
]
