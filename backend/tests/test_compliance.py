import pytest
from app.compliance.encryption import encrypt, decrypt, cipher

def test_encryption_decryption_cycle():
    """Verify that a string can be encrypted and successfully decrypted back to the original."""
    original_text = "Sensitive salary data: INR 60,000"
    
    # Encrypt
    encrypted_text = encrypt(original_text)
    assert encrypted_text is not None
    assert encrypted_text != original_text
    
    # Decrypt
    decrypted_text = decrypt(encrypted_text)
    assert decrypted_text == original_text

def test_encryption_handles_none():
    """Verify that encrypt and decrypt handle None values gracefully."""
    assert encrypt(None) is None
    assert decrypt(None) is None

def test_invalid_decryption_raises():
    """Verify that attempting to decrypt an invalid cipher text raises a ValueError."""
    with pytest.raises(ValueError):
        decrypt("not_a_valid_fernet_token")
