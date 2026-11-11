# Local Octo Browser preparation (read-only)

This is a **configuration validation stub**, not a working Octo API connection.
It does not open browser profiles, connect to WhiteBird, extract balances, or send any network requests.

## Safe local trial

1. Install Python 3.12 on your own computer.
2. Create a private JSON file outside the repository, for example `profile.json`:
   ```json
   {"account_id": 1, "browser": "octo", "profile_id": "your-local-profile-id"}
   ```
   The account ID must match the account record in WhiteBird Manager. The profile ID is the Octo profile identifier, **not** a password, cookie, API token, or 2FA secret.
3. Set the environment variable `OCTO_PROFILE_CONFIG` to the absolute path of the JSON file.
4. Run `python safe-demo/local_octo_agent.py`.
5. The result will explicitly show `browser_connected: false` and `balances_available: false`. This is expected.

Do not commit the private JSON file. Do not share account credentials, browser cookies or authentication tokens.

## Before real read-only integration

- Verify Octo Browser's current official local API documentation and plan eligibility.
- Establish an authenticated, least-privilege local bridge that cannot execute financial actions.
- Implement an explicit allowlist for read-only account pages and balance fields.
- Keep all session material local and use opt-in data transmission.
- Add integration tests with mocked browser responses before any live access.
- Require separate approval before any deployment or live account connection.
