import pytest

from synchro.core.crypto import CryptoService, TamperedCiphertextError, backend_name
from synchro.db.models.user import Account, ApiCredential, AccountType, User
from synchro.domain.credentials import get_deriv_token, set_deriv_token

KEY = "unit-test-encryption-key-material-0123456789abcdef"


def test_backend_is_available():
    assert backend_name() in {"aes-gcm", "stdlib-hmac-aead"}


def test_encrypt_decrypt_roundtrip():
    crypto = CryptoService(KEY)
    secret = "pat_abcdef1234567890"
    token = crypto.encrypt(secret)
    assert secret not in token
    assert token.startswith("v1.")
    assert crypto.decrypt(token) == secret


def test_ciphertexts_are_non_deterministic():
    crypto = CryptoService(KEY)
    assert crypto.encrypt("same-input") != crypto.encrypt("same-input")


def test_tampered_ciphertext_rejected():
    crypto = CryptoService(KEY)
    token = crypto.encrypt("sensitive")
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    raw = bytearray(token.encode())
    pos = -5
    current = chr(raw[pos])
    assert current in alphabet
    raw[pos] = ord(alphabet[(alphabet.index(current) + 7) % len(alphabet)])
    with pytest.raises(TamperedCiphertextError):
        crypto.decrypt(raw.decode())


def test_wrong_key_rejected():
    token = CryptoService(KEY).encrypt("data")
    with pytest.raises(TamperedCiphertextError):
        CryptoService("another-key-material-9876543210ffffffff").decrypt(token)


def test_short_key_rejected():
    with pytest.raises(ValueError):
        CryptoService("short")


def test_stdlib_fallback_roundtrip(monkeypatch):
    import synchro.core.crypto as crypto_module

    monkeypatch.setattr(crypto_module, "_BACKEND", "stdlib-hmac-aead")
    crypto = CryptoService(KEY)
    token = crypto.encrypt("fallback-secret")
    assert crypto.decrypt(token) == "fallback-secret"


def test_credential_store_and_load(db_session):
    user = User(email="crypto@example.com", password_hash="x")
    db_session.add(user)
    db_session.flush()
    account = Account(user_id=user.id)
    db_session.add(account)
    db_session.flush()
    credential = ApiCredential(user_id=user.id, account_id=account.id, account_type=AccountType.DEMO)
    db_session.add(credential)

    crypto = CryptoService(KEY)
    set_deriv_token(db_session, credential, "pat_live_token_123", crypto)
    db_session.commit()

    stored = db_session.get(ApiCredential, credential.id)
    assert "pat_live_token_123" not in (stored.deriv_token_encrypted or "")
    assert get_deriv_token(stored, crypto) == "pat_live_token_123"

    stored.deriv_token_encrypted = "v1.corruptedblob"
    with pytest.raises(TamperedCiphertextError):
        get_deriv_token(stored, crypto)
