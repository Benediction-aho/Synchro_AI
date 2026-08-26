import base64
import hashlib
import hmac
import os
import secrets

_BACKEND = None
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    _probe_key = AESGCM(os.urandom(32))
    _probe_key.encrypt(os.urandom(12), b"probe", None)
    _BACKEND = "aes-gcm"
except Exception:
    AESGCM = None
    _BACKEND = "stdlib-hmac-aead"

_NONCE_BYTES = 12
_VERSION_PREFIX = "v1."


class TamperedCiphertextError(ValueError):
    pass


def backend_name() -> str:
    return _BACKEND


class CryptoService:
    """Authenticated symmetric encryption for secrets at rest.

    Primary: AES-256-GCM via the cryptography package.
    Fallback (only if that native stack is unavailable/blocked):
    stdlib HMAC-SHA256 CTR keystream with encrypt-then-MAC.
    """

    def __init__(self, key_material: str):
        if not key_material or len(key_material) < 32:
            raise ValueError("encryption key must be at least 32 characters")
        self._master = hashlib.sha256(key_material.encode("utf-8")).digest()

    def _subkey(self, label: str) -> bytes:
        return hmac.new(self._master, label.encode("utf-8"), hashlib.sha256).digest()

    def encrypt(self, plaintext: str | bytes) -> str:
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")
        nonce = secrets.token_bytes(_NONCE_BYTES)
        if _BACKEND == "aes-gcm":
            ct = AESGCM(self._master).encrypt(nonce, plaintext, b"synchro")
            blob = nonce + ct
        else:
            enc_key = self._subkey("enc-v1")
            mac_key = self._subkey("mac-v1")
            keystream = self._keystream(enc_key, nonce, len(plaintext))
            ct = bytes(a ^ b for a, b in zip(plaintext, keystream))
            tag = hmac.new(mac_key, nonce + ct, hashlib.sha256).digest()
            blob = nonce + tag + ct
        return _VERSION_PREFIX + base64.urlsafe_b64encode(blob).decode("ascii")

    def decrypt(self, token: str) -> str:
        if not token.startswith(_VERSION_PREFIX):
            raise TamperedCiphertextError("unknown ciphertext version")
        try:
            blob = base64.b64decode(
                token[len(_VERSION_PREFIX) :], altchars=b"-_", validate=True
            )
            if _BACKEND == "aes-gcm":
                nonce, ct = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
                pt = AESGCM(self._master).decrypt(nonce, ct, b"synchro")
            else:
                nonce, tag, ct = (
                    blob[:_NONCE_BYTES],
                    blob[_NONCE_BYTES : _NONCE_BYTES + 32],
                    blob[_NONCE_BYTES + 32 :],
                )
                expected = hmac.new(
                    self._subkey("mac-v1"), nonce + ct, hashlib.sha256
                ).digest()
                if not hmac.compare_digest(expected, tag):
                    raise TamperedCiphertextError("authentication failed")
                keystream = self._keystream(self._subkey("enc-v1"), nonce, len(ct))
                pt = bytes(a ^ b for a, b in zip(ct, keystream))
            return pt.decode("utf-8")
        except TamperedCiphertextError:
            raise
        except Exception as exc:
            raise TamperedCiphertextError("decryption failed") from exc

    def _keystream(self, key: bytes, nonce: bytes, length: int) -> bytes:
        blocks = []
        counter = 0
        while sum(len(b) for b in blocks) < length:
            blocks.append(hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest())
            counter += 1
        return b"".join(blocks)[:length]
