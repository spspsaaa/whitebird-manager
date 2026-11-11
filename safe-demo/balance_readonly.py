"""Read-only account status boundary. No browser sessions or financial endpoints."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

@dataclass(frozen=True)
class BalanceSnapshot:
    account_id: int
    rub: Decimal
    usdt: Decimal
    observed_at: datetime
    source: str

class BalanceUnavailable(RuntimeError):
    pass

def validate_snapshot(account_id, payload):
    """Validate a snapshot supplied by a separately approved data provider."""
    if not isinstance(payload, dict) or payload.get("account_id") != account_id:
        raise ValueError("Account mismatch")
    if payload.get("source") != "approved_read_only_provider":
        raise ValueError("Unapproved balance source")
    try:
        rub = Decimal(str(payload["rub"]))
        usdt = Decimal(str(payload["usdt"]))
        observed_at = datetime.fromisoformat(payload["observed_at"])
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError("Invalid balance snapshot") from exc
    if not rub.is_finite() or not usdt.is_finite() or rub < 0 or usdt < 0:
        raise ValueError("Invalid balance amounts")
    if observed_at.tzinfo is None:
        raise ValueError("Timezone required")
    now = datetime.now(timezone.utc)
    if observed_at > now or (now - observed_at).total_seconds() > 300:
        raise ValueError("Stale or future snapshot")
    return BalanceSnapshot(account_id, rub, usdt, observed_at, payload["source"])

class ReadOnlyBalanceProvider:
    """Explicitly unavailable until an official integration is approved."""
    def fetch(self, account_id):
        raise BalanceUnavailable("No approved WhiteBird balance integration configured")
