# encryption.py
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv
load_dotenv()


# Must be set in .env
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise ValueError("❌ ENCRYPTION_KEY not set in environment. Generate one with Fernet.generate_key()")

fernet = Fernet(ENCRYPTION_KEY.encode())

def encrypt_field(value: str) -> str:
    if value is None:
        return None
    return fernet.encrypt(value.encode()).decode()

# encryption.py

def decrypt_field(value: str) -> str:   
    if value is None:
        return None
    return fernet.decrypt(value.encode()).decode()

# ------- ADD THIS NEW FUNCTION BELOW -------
def safe_decrypt_field(encrypted_value: str) -> str:
    """
    Safely decrypt a field. Returns the original value if decryption fails.
    This is useful for data that might be a mix of encrypted and unencrypted values.
    """
    if encrypted_value is None:
        return None
        
    # If it's not a string (e.g., a number, a boolean), just return it as-is.
    if not isinstance(encrypted_value, str):
        return encrypted_value
        
    try:
        # Try to decrypt it
        return decrypt_field(encrypted_value)
    except Exception:
        # If it fails (e.g., it was already decrypted), just return the original value.
        return encrypted_value
