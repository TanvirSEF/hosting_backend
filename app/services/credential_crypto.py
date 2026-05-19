import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings


def get_fernet() -> Fernet:
    key = settings.PROVIDER_CREDENTIAL_ENCRYPTION_KEY.strip()
    if not key:
        digest = hashlib.sha256(settings.JWT_SECRET.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest).decode("utf-8")
    return Fernet(key.encode("utf-8"))


def encrypt_secret(secret: str) -> str:
    return get_fernet().encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(encrypted_secret: str) -> str:
    return get_fernet().decrypt(encrypted_secret.encode("utf-8")).decode("utf-8")
