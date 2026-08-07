import logging
from typing import Optional
from cryptography.fernet import Fernet
from sqlalchemy.types import TypeDecorator, String
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Fernet cipher
try:
    # Fernet keys must be 32 url-safe base64-encoded bytes
    # Ensure key length is exactly 32 bytes after decoding. If invalid, pad/adjust or generate one.
    key = settings.ENCRYPTION_KEY.encode()
    # Test key validity
    cipher = Fernet(key)
except Exception as e:
    logger.warning(f"Invalid ENCRYPTION_KEY provided: {e}. Generating a temporary development key.")
    # For safe fallback in tests/dev if the provided key is invalid
    key = Fernet.generate_key()
    cipher = Fernet(key)

def encrypt(plain_text: Optional[str]) -> Optional[str]:
    """Encrypt plain text using Fernet cipher."""
    if plain_text is None:
        return None
    try:
        return cipher.encrypt(plain_text.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        raise ValueError("Failed to encrypt data") from e

def decrypt(cipher_text: Optional[str]) -> Optional[str]:
    """Decrypt cipher text using Fernet cipher."""
    if cipher_text is None:
        return None
    try:
        return cipher.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise ValueError("Failed to decrypt data. The encryption key may be invalid or file is corrupted.") from e

class EncryptedString(TypeDecorator):
    """
    SQLAlchemy custom type that transparently encrypts data written to the database
    and decrypts data read from the database.
    """
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        return encrypt(str(value))

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        return decrypt(value)
