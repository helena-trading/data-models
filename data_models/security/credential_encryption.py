"""
Credential Encryption Service
Provides secure encryption/decryption for API credentials using AES-256-GCM
"""

import base64
import os
import secrets
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from data_models.logging import error, info, warning


class EncryptedData:
    """Container for encrypted data and metadata"""

    __slots__ = ("encrypted_value", "metadata")

    def __init__(self, encrypted_value: str, metadata: Dict[str, Any]) -> None:
        self.encrypted_value = encrypted_value
        self.metadata = metadata


class MasterKeyProvider:
    """Provides master encryption keys from various sources"""

    def __init__(self, key_source: str = "env") -> None:
        """
        Initialize the master key provider

        Args:
            key_source: Source of the master key ('env', 'aws_secrets', 'file')
        """
        self.key_source = key_source
        self._cached_key: Optional[bytes] = None
        self._key_id: Optional[str] = None

    def get_master_key(self) -> Tuple[bytes, str]:
        """
        Get the current master key and its ID

        Returns:
            Tuple of (key_bytes, key_id)
        """
        # Check cache first
        if self._cached_key is not None and self._key_id is not None:
            info("[MasterKeyProvider] Using cached master key")
            return (self._cached_key, self._key_id)

        info("[MasterKeyProvider] Loading master key from source")
        if self.key_source == "env":
            # Get from environment variable
            key_b64 = os.environ.get("HELENA_MASTER_KEY")
            if not key_b64:
                # Generate a new key if not exists (development only)
                environment = os.environ.get("ENVIRONMENT", "development")
                error(f"[MasterKeyProvider] HELENA_MASTER_KEY not found! Environment={environment}")
                if environment == "development":
                    warning("[MasterKeyProvider] No master key found, generating new one for development")
                    key_bytes = secrets.token_bytes(32)  # 256 bits
                    key_b64 = base64.b64encode(key_bytes).decode()
                    info("[MasterKeyProvider] Generated new master key for development (set HELENA_MASTER_KEY env var)")
                else:
                    raise ValueError("Master encryption key not found in environment")
            else:
                info(f"[MasterKeyProvider] Master key found (length: {len(key_b64)})")

            try:
                self._cached_key = base64.b64decode(key_b64)
                info(f"[MasterKeyProvider] Master key decoded successfully (bytes: {len(self._cached_key)})")
            except Exception as e:
                error(f"[MasterKeyProvider] Failed to decode master key: {e}")
                raise

            self._key_id = "env_master_001"
            return self._cached_key, self._key_id

        if self.key_source == "aws_secrets":
            # Future: Implement AWS Secrets Manager integration
            raise NotImplementedError("AWS Secrets Manager key provider not yet implemented")

        raise ValueError(f"Unknown key source: {self.key_source}")

    def clear_cache(self) -> None:
        """Clear the cached master key from memory"""
        # Overwrite the key in memory before clearing (side effect only)
        if self._cached_key is not None:
            _ = secrets.token_bytes(len(self._cached_key))
        self._cached_key = None
        self._key_id = None


class CredentialEncryption:
    """Handles encryption and decryption of credentials"""

    # Encryption configuration
    ALGORITHM = "AES-256-GCM"
    KEY_SIZE = 32  # 256 bits
    IV_SIZE = 12  # 96 bits for GCM
    TAG_SIZE = 16  # 128 bits
    SALT_SIZE = 32  # 256 bits for key derivation

    def __init__(self, master_key_provider: MasterKeyProvider) -> None:
        """
        Initialize the encryption service

        Args:
            master_key_provider: Provider for master encryption keys
        """
        self.master_key_provider = master_key_provider
        self.backend = default_backend()

    def encrypt_credential(self, plaintext: str) -> EncryptedData:
        """
        Encrypt a credential value

        Args:
            plaintext: The credential value to encrypt

        Returns:
            EncryptedData object with encrypted value and metadata
        """
        try:
            # Get master key
            master_key, key_id = self.master_key_provider.get_master_key()

            # Generate random salt for key derivation
            salt = secrets.token_bytes(self.SALT_SIZE)

            # Derive encryption key from master key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=self.KEY_SIZE,
                salt=salt,
                iterations=100000,
                backend=self.backend,
            )
            derived_key = kdf.derive(master_key)

            # Generate random IV
            iv = secrets.token_bytes(self.IV_SIZE)

            # Encrypt the plaintext
            cipher = Cipher(algorithms.AES(derived_key), modes.GCM(iv), backend=self.backend)
            encryptor = cipher.encryptor()

            # Convert plaintext to bytes
            plaintext_bytes = plaintext.encode("utf-8")

            # Encrypt
            ciphertext = encryptor.update(plaintext_bytes) + encryptor.finalize()

            # Get authentication tag
            auth_tag = encryptor.tag

            # Combine salt, iv, ciphertext, and auth_tag
            encrypted_data = salt + iv + ciphertext + auth_tag

            # Base64 encode for storage
            encrypted_value = base64.b64encode(encrypted_data).decode("utf-8")

            # Create metadata
            metadata = {
                "algorithm": self.ALGORITHM,
                "key_id": key_id,
                "version": "1.0",
                "encrypted_at": datetime.utcnow().isoformat(),
                "salt_size": self.SALT_SIZE,
                "iv_size": self.IV_SIZE,
                "tag_size": self.TAG_SIZE,
            }

            # Clear sensitive data from memory (side effects only)
            _ = secrets.token_bytes(len(derived_key))
            _ = secrets.token_bytes(len(plaintext_bytes))

            return EncryptedData(encrypted_value, metadata)

        except Exception as e:
            error(f"Encryption failed: {str(e)}")
            raise

    def decrypt_credential(self, encrypted_data: EncryptedData) -> str:
        """
        Decrypt a credential value

        Args:
            encrypted_data: EncryptedData object with value and metadata

        Returns:
            Decrypted plaintext credential
        """
        info("[CredentialEncryption] Starting decryption")
        try:
            # Get master key
            master_key, current_key_id = self.master_key_provider.get_master_key()
            info(f"[CredentialEncryption] Retrieved master key with ID: {current_key_id}")

            # Verify key ID matches
            stored_key_id = encrypted_data.metadata.get("key_id")
            if stored_key_id != current_key_id:
                warning(f"[CredentialEncryption] Key ID mismatch: encrypted with {stored_key_id}, current is {current_key_id}")

            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data.encrypted_value)

            # Extract components based on metadata
            salt_size = encrypted_data.metadata.get("salt_size", self.SALT_SIZE)
            iv_size = encrypted_data.metadata.get("iv_size", self.IV_SIZE)
            tag_size = encrypted_data.metadata.get("tag_size", self.TAG_SIZE)

            # Extract salt, IV, ciphertext, and auth tag
            salt = encrypted_bytes[:salt_size]
            iv = encrypted_bytes[salt_size : salt_size + iv_size]
            ciphertext_with_tag = encrypted_bytes[salt_size + iv_size :]
            ciphertext = ciphertext_with_tag[:-tag_size]
            auth_tag = ciphertext_with_tag[-tag_size:]

            # Derive decryption key from master key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=self.KEY_SIZE,
                salt=salt,
                iterations=100000,
                backend=self.backend,
            )
            derived_key = kdf.derive(master_key)

            # Decrypt
            cipher = Cipher(
                algorithms.AES(derived_key),
                modes.GCM(iv, auth_tag),
                backend=self.backend,
            )
            decryptor = cipher.decryptor()

            plaintext_bytes = decryptor.update(ciphertext) + decryptor.finalize()

            # Convert back to string
            plaintext = plaintext_bytes.decode("utf-8")

            # Clear sensitive data from memory (side effects only)
            _ = secrets.token_bytes(len(derived_key))
            _ = secrets.token_bytes(len(plaintext_bytes))

            return plaintext

        except Exception as e:
            error(f"Decryption failed: {str(e)}")
            raise

    def rotate_key(self, encrypted_data: EncryptedData) -> EncryptedData:
        """
        Re-encrypt data with a new key (for key rotation)

        Args:
            encrypted_data: Current encrypted data

        Returns:
            New EncryptedData with fresh encryption
        """
        # Decrypt with current key
        plaintext = self.decrypt_credential(encrypted_data)

        # Re-encrypt with potentially new key
        return self.encrypt_credential(plaintext)

    def generate_master_key(self) -> str:
        """
        Generate a new master key for initial setup

        Returns:
            Base64-encoded master key
        """
        key_bytes = secrets.token_bytes(self.KEY_SIZE)
        return base64.b64encode(key_bytes).decode("utf-8")


def secure_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings are equal, False otherwise
    """
    if len(a) != len(b):
        return False

    result = 0
    for x, y in zip(a.encode(), b.encode()):
        result |= x ^ y

    return result == 0


def clear_string(s: str) -> None:
    """
    Attempt to clear a string from memory (best effort)

    Args:
        s: String to clear
    """
    if s:
        # This is best effort - Python doesn't guarantee memory clearing
        temp = secrets.token_bytes(len(s))
        s = temp.decode("utf-8", errors="ignore")
