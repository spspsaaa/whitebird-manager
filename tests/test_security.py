import pytest

from app.security import Vault, is_owner


def test_vault_roundtrip():
    vault = Vault()
    token = vault.encrypt("super-secret")
    assert token != "super-secret"
    assert vault.decrypt(token) == "super-secret"


def test_vault_rejects_wrong_key():
    from cryptography.fernet import Fernet

    vault = Vault()
    token = vault.encrypt("secret")
    other = Vault(Fernet.generate_key().decode())
    with pytest.raises(ValueError):
        other.decrypt(token)


def test_is_owner():
    assert is_owner(42) is True
    assert is_owner(43) is False
    assert is_owner(None) is False
