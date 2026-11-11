"""Domain errors mapped to user-friendly messages."""
from __future__ import annotations


class WhitebirdError(RuntimeError):
    """Base class."""


class OperationBlocked(WhitebirdError):
    """The platform requires an extra verification step (anti-fraud)."""

    def __init__(self, message: str, kind: str = "verification") -> None:
        super().__init__(message)
        self.kind = kind


class ConfirmationRequired(WhitebirdError):
    """The owner must confirm the operation explicitly."""


class AccountNotFound(WhitebirdError):
    """Unknown account id."""


class InvalidSettings(WhitebirdError):
    """The account settings are incomplete or invalid."""


# Whitebird error codes we handle explicitly.
BLOCKING_ERRORS = {
    "SMS_VERIFICATION_REQUIRED": "sms",
    "LIVENESS_VERIFICATION_REQUIRED": "liveness",
    "AML_FRAUD_VALIDATION_ERROR": "aml",
    "AML_BLOCKED": "aml",
    "PENDING_REVIEW": "review",
    "ARREST": "aml",
}

RETRYABLE_ERRORS = {
    "INVALID_CALCULATION",
    "ACTIVE_WITHDRAWAL_REQUEST_FOUND",
    "ACTIVE_BALANCE_OPERATION_FOUND",
}
