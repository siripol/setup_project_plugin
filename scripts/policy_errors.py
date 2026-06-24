"""Error classes + exit codes for the policy catalog. Mirrors scripts/errors.py."""
from __future__ import annotations

EXIT_UNKNOWN_POLICY = 10
EXIT_UNKNOWN_PROFILE = 11
EXIT_EXCLUSIVE_GROUP_CONFLICT = 12
EXIT_REQUIRES_NOT_SATISFIED = 13
EXIT_USER_EDITED_BLOCKS_OP = 14
EXIT_CWD_AMBIGUOUS_OR_INVALID = 15
EXIT_POLICY_NOT_APPLIED = 16
EXIT_MIXED_OVERRIDE_FLAGS = 17
EXIT_CATALOG_DOWNGRADE = 18
EXIT_MALFORMED_PATCH = 19
EXIT_CONFLICTS_WITH_VIOLATION = 20


class PolicyError(Exception):
    exit_code: int = 99


class UnknownPolicy(PolicyError):
    exit_code = EXIT_UNKNOWN_POLICY


class UnknownProfile(PolicyError):
    exit_code = EXIT_UNKNOWN_PROFILE


class ExclusiveGroupConflict(PolicyError):
    exit_code = EXIT_EXCLUSIVE_GROUP_CONFLICT


class RequiresNotSatisfied(PolicyError):
    exit_code = EXIT_REQUIRES_NOT_SATISFIED


class UserEditedBlocksOp(PolicyError):
    exit_code = EXIT_USER_EDITED_BLOCKS_OP


class CwdAmbiguousOrInvalid(PolicyError):
    exit_code = EXIT_CWD_AMBIGUOUS_OR_INVALID


class PolicyNotApplied(PolicyError):
    exit_code = EXIT_POLICY_NOT_APPLIED


class MixedOverrideFlags(PolicyError):
    exit_code = EXIT_MIXED_OVERRIDE_FLAGS


class CatalogDowngrade(PolicyError):
    exit_code = EXIT_CATALOG_DOWNGRADE


class MalformedPatch(PolicyError):
    exit_code = EXIT_MALFORMED_PATCH


class ConflictsWithViolation(PolicyError):
    exit_code = EXIT_CONFLICTS_WITH_VIOLATION


class MalformedPolicy(PolicyError):
    """Catalog-side error: policy.yaml is malformed (used by loader + lint)."""
    exit_code = 99
