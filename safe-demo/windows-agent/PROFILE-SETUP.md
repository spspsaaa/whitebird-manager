# Mapping Octo and Dolphin profiles

1. Copy `accounts.example.json` to `accounts.json` **on your Windows PC**.
2. Replace example profile IDs with the actual browser profile identifiers. Do not put credentials, passwords, cookies or API tokens in this file.
3. Add one record per account; browser must be `octo` or `dolphin`.
4. Double-click `CHECK-PROFILES.bat` to validate the mapping. Python 3 is required.

The file is local and not uploaded. **Do not commit `accounts.json` to GitHub**: profile mapping may be sensitive. This stage validates inventory only. It does not start browsers, retrieve balances or make transfers.
