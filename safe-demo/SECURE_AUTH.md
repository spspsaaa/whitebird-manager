# Secure authentication boundary (WB-002)

Status: **offline infrastructure only**. No live 2FA enrollment, TOTP generation, WhiteBird authentication, conversion or withdrawal is implemented.

## Modules

- `secure_auth.py` defines `AuthenticationAdapter`, which must be implemented against a documented, provider-approved login mechanism.
- `WithdrawalIntent` validates and canonically binds account, currency, amount, network, destination and fee.
- `ApprovalStore` issues opaque, short-lived, single-use approval tickets in SQLite. Tickets are stored only as SHA-256 hashes.

## Important limitations

**An approval ticket does not initiate, authorize with the provider, or confirm a real withdrawal.** A production financial integration must obtain separate, explicit owner approval and provider-side authorization for each operation, and must implement a durable execution ledger, external idempotency and post-failure reconciliation before submitting any financial transaction. If a transfer outcome is unknown, stop and reconcile instead of retrying blindly.

The existing Telegram demo stores account inventory in pinned chat messages and uses a temporary SQLite database. Do not connect this module to live accounts until persistence and backup handling are redesigned and reviewed.

Never store 2FA seeds, passwords, session cookies, wallet secrets or Telegram tokens in GitHub, Telegram messages or application logs. Use a managed secret store with scoped permissions, rotation and audit logs. Do not bypass or automate provider security challenges that require human action.

## Offline tests

```bash
cd safe-demo
python -m unittest -v test_secure_auth
```

No network access or credentials are needed.
