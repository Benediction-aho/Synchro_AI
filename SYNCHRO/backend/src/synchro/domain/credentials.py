from sqlalchemy.orm import Session

from synchro.core.crypto import CryptoService, TamperedCiphertextError
from synchro.db.models.user import ApiCredential


def set_deriv_token(db: Session, credential: ApiCredential, plaintext: str, crypto: CryptoService) -> None:
    credential.deriv_token_encrypted = crypto.encrypt(plaintext)
    db.flush()


def get_deriv_token(credential: ApiCredential, crypto: CryptoService) -> str:
    stored = credential.deriv_token_encrypted
    if not stored:
        raise ValueError("credential has no stored Deriv token")
    try:
        return crypto.decrypt(stored)
    except TamperedCiphertextError as exc:
        raise TamperedCiphertextError(
            f"stored credential for credential_id={credential.id} failed integrity check"
        ) from exc
