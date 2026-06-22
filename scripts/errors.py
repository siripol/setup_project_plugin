"""Exit codes + error classes for sn-init."""

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_TARGET_NON_EMPTY = 3
EXIT_CLAUDE_EXISTS_NO_STATE = 4
EXIT_VAULT_UNWRITABLE = 5
EXIT_INSTALL_FAILED = 6
EXIT_VALIDATION_FAILED = 7
EXIT_TEMPLATE_VERSION_MISMATCH = 8
EXIT_MISSING_DEP = 9
EXIT_INTERNAL = 99


class SnInitError(Exception):
    """Base exception for sn-init."""

    exit_code: int = EXIT_INTERNAL

    def __init__(self, message: str, exit_code: int | None = None):
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


class UsageError(SnInitError):
    exit_code = EXIT_USAGE


class TargetNonEmptyError(SnInitError):
    exit_code = EXIT_TARGET_NON_EMPTY


class ClaudeExistsNoStateError(SnInitError):
    exit_code = EXIT_CLAUDE_EXISTS_NO_STATE


class VaultUnwritableError(SnInitError):
    exit_code = EXIT_VAULT_UNWRITABLE


class InstallFailedError(SnInitError):
    exit_code = EXIT_INSTALL_FAILED


class ValidationFailedError(SnInitError):
    exit_code = EXIT_VALIDATION_FAILED


class TemplateVersionMismatchError(SnInitError):
    exit_code = EXIT_TEMPLATE_VERSION_MISMATCH


class MissingAnalyzerError(SnInitError):
    exit_code = EXIT_MISSING_DEP
