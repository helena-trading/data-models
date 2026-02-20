"""
Credential Manager - Handles database operations for encrypted credentials
"""

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy.orm import Session

from data_models.logging import error, info, warning
from data_models.database.tables.encrypted_credential import (
    CredentialAuditLog,
    EncryptedCredential,
)
from data_models.security.credential_encryption import (
    CredentialEncryption,
    EncryptedData,
    MasterKeyProvider,
)


class CredentialManager:
    """Manages encrypted credential storage and retrieval"""

    def __init__(self, session: Session, encryption_service: CredentialEncryption) -> None:
        """
        Initialize the credential manager

        Args:
            session: SQLAlchemy database session
            encryption_service: Service for encrypting/decrypting credentials
        """
        self.session = session
        self.encryption_service = encryption_service

    def store_credentials(
        self,
        account_id: int,
        credentials: Dict[str, str],
        created_by: Optional[str] = None,
    ) -> bool:
        """
        Store encrypted credentials for an account

        Args:
            account_id: ID of the account
            credentials: Dictionary of credentials (api_key, api_secret, passphrase)
            created_by: User or system that created the credentials

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate account exists
            from data_models.database.tables.account import Account

            account = self.session.query(Account).filter_by(id=account_id).first()
            if not account:
                error(f"Account {account_id} not found")
                return False

            # Store each credential
            for cred_type, cred_value in credentials.items():
                if not cred_value:  # Skip empty values
                    continue

                # Check if credential already exists
                existing = (
                    self.session.query(EncryptedCredential).filter_by(account_id=account_id, credential_type=cred_type).first()
                )

                # Encrypt the credential
                encrypted_data = self.encryption_service.encrypt_credential(cred_value)

                if existing:
                    # Update existing credential
                    existing.encrypted_value = encrypted_data.encrypted_value  # type: ignore[assignment]  # SQLAlchemy Column descriptor
                    existing.encryption_metadata = encrypted_data.metadata  # type: ignore[assignment]  # SQLAlchemy Column descriptor
                    existing.updated_at = datetime.utcnow()  # type: ignore[assignment]  # SQLAlchemy Column descriptor
                    action = "update"
                    credential_id = existing.id
                else:
                    # Create new credential
                    new_cred = EncryptedCredential(
                        account_id=account_id,
                        credential_type=cred_type,
                        encrypted_value=encrypted_data.encrypted_value,
                        encryption_metadata=encrypted_data.metadata,
                        created_by=created_by,
                    )
                    self.session.add(new_cred)
                    self.session.flush()  # Get the ID
                    action = "create"
                    credential_id = new_cred.id

            # Commit credentials first
            self.session.commit()
            info(f"Successfully stored credentials for account {account_id}")

            # Audit log after commit (so audit failures don't rollback credentials)
            self.audit_access(
                credential_id=credential_id,  # type: ignore[arg-type]  # SQLAlchemy Column descriptor - works at runtime
                account_id=account_id,
                action=action,
                success=True,
            )

            return True

        except Exception as e:
            self.session.rollback()
            error(f"Failed to store credentials: {str(e)}")
            # Audit the failure
            self.audit_access(
                account_id=account_id,
                action="create",
                success=False,
                error_message=str(e),
            )
            return False

    def get_credentials(self, account_id: int, bot_id: Optional[int] = None) -> Optional[Dict[str, str]]:
        """
        Retrieve and decrypt credentials for an account

        Args:
            account_id: ID of the account
            bot_id: ID of the bot accessing credentials (for audit)

        Returns:
            Dictionary of decrypted credentials or None if not found
        """
        info(f"[CredentialManager] Getting credentials for account_id={account_id}, bot_id={bot_id}")
        try:
            # Get all encrypted credentials for the account
            encrypted_creds = self.session.query(EncryptedCredential).filter_by(account_id=account_id).all()

            if not encrypted_creds:
                warning(f"[CredentialManager] No encrypted credentials found for account {account_id}")
                return None

            info(f"[CredentialManager] Found {len(encrypted_creds)} encrypted credential(s) for account {account_id}")

            # Decrypt credentials
            credentials = {}
            for enc_cred in encrypted_creds:
                info(f"[CredentialManager] Decrypting credential type: {enc_cred.credential_type}")
                try:
                    # Create EncryptedData object
                    # (SQLAlchemy Column descriptors work at runtime)
                    encrypted_data = EncryptedData(
                        encrypted_value=enc_cred.encrypted_value,  # type: ignore[arg-type]
                        metadata=enc_cred.encryption_metadata,  # type: ignore[arg-type]
                    )

                    # Decrypt
                    decrypted_value = self.encryption_service.decrypt_credential(encrypted_data)
                    credentials[enc_cred.credential_type] = decrypted_value
                    info(f"[CredentialManager] ✓ Successfully decrypted {enc_cred.credential_type}")

                    # Update access tracking
                    enc_cred.last_accessed_at = datetime.utcnow()  # type: ignore[assignment]  # SQLAlchemy Column descriptor
                    enc_cred.access_count = (enc_cred.access_count or 0) + 1  # type: ignore[assignment]  # SQLAlchemy Column descriptor

                    # Audit successful access
                    self.audit_access(
                        credential_id=enc_cred.id,  # type: ignore[arg-type]  # SQLAlchemy Column descriptor - works at runtime
                        account_id=account_id,
                        action="read",
                        bot_id=bot_id,
                        success=True,
                    )

                except Exception as e:
                    error(f"[CredentialManager] ✗ Failed to decrypt credential {enc_cred.credential_type}: {str(e)}")
                    # Audit failed access
                    self.audit_access(
                        credential_id=enc_cred.id,  # type: ignore[arg-type]  # SQLAlchemy Column descriptor - works at runtime
                        account_id=account_id,
                        action="read",
                        bot_id=bot_id,
                        success=False,
                        error_message=str(e),
                    )
                    raise

            self.session.commit()
            # Return credentials only if dict is not empty
            if credentials:
                info(f"[CredentialManager] ✓ Successfully retrieved {len(credentials)} credential(s)")
                return credentials  # type: ignore[return-value]
            else:
                warning("[CredentialManager] No credentials were successfully decrypted")
                return None

        except Exception as e:
            self.session.rollback()
            error(f"[CredentialManager] ✗ Failed to get credentials for account {account_id}: {str(e)}")
            return None

    def update_credentials(
        self,
        account_id: int,
        credentials: Dict[str, str],
        updated_by: Optional[str] = None,
    ) -> bool:
        """
        Update encrypted credentials for an account

        Args:
            account_id: ID of the account
            credentials: Dictionary of credentials to update
            updated_by: User or system updating the credentials

        Returns:
            True if successful, False otherwise
        """
        # Use store_credentials which handles both create and update
        return self.store_credentials(account_id, credentials, updated_by)

    def delete_credentials(self, account_id: int) -> bool:
        """
        Delete all encrypted credentials for an account

        Args:
            account_id: ID of the account

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all credentials for audit
            creds = self.session.query(EncryptedCredential).filter_by(account_id=account_id).all()

            credential_ids = [c.id for c in creds]

            # Delete all credentials
            self.session.query(EncryptedCredential).filter_by(account_id=account_id).delete()

            # Audit deletions
            for cred_id in credential_ids:
                self.audit_access(
                    credential_id=cred_id,  # type: ignore[arg-type]  # SQLAlchemy Column descriptor - works at runtime
                    account_id=account_id,
                    action="delete",
                    success=True,
                )

            self.session.commit()
            info(f"Successfully deleted credentials for account {account_id}")
            return True

        except Exception as e:
            self.session.rollback()
            error(f"Failed to delete credentials: {str(e)}")
            self.audit_access(
                account_id=account_id,
                action="delete",
                success=False,
                error_message=str(e),
            )
            return False

    def rotate_credentials(self, account_id: int) -> bool:
        """
        Rotate encryption for all credentials of an account

        Args:
            account_id: ID of the account

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all encrypted credentials
            encrypted_creds = self.session.query(EncryptedCredential).filter_by(account_id=account_id).all()

            for enc_cred in encrypted_creds:
                # Create EncryptedData object
                encrypted_data = EncryptedData(
                    encrypted_value=enc_cred.encrypted_value,  # type: ignore[arg-type]  # SQLAlchemy Column descriptor - works at runtime
                    metadata=enc_cred.encryption_metadata,  # type: ignore[arg-type]  # SQLAlchemy Column descriptor - works at runtime
                )

                # Rotate the encryption
                new_encrypted_data = self.encryption_service.rotate_key(encrypted_data)

                # Update the record
                enc_cred.encrypted_value = new_encrypted_data.encrypted_value  # type: ignore[assignment]  # SQLAlchemy Column descriptor
                enc_cred.encryption_metadata = new_encrypted_data.metadata  # type: ignore[assignment]  # SQLAlchemy Column descriptor
                enc_cred.updated_at = datetime.utcnow()  # type: ignore[assignment]  # SQLAlchemy Column descriptor

                # Audit rotation
                self.audit_access(
                    credential_id=enc_cred.id,  # type: ignore[arg-type]  # SQLAlchemy Column descriptor - works at runtime
                    account_id=account_id,
                    action="rotate",
                    success=True,
                    metadata={
                        "old_key_id": encrypted_data.metadata.get("key_id"),
                        "new_key_id": new_encrypted_data.metadata.get("key_id"),
                    },
                )

            self.session.commit()
            info(f"Successfully rotated credentials for account {account_id}")
            return True

        except Exception as e:
            self.session.rollback()
            error(f"Failed to rotate credentials: {str(e)}")
            self.audit_access(
                account_id=account_id,
                action="rotate",
                success=False,
                error_message=str(e),
            )
            return False

    def audit_access(
        self,
        credential_id: Optional[int] = None,
        account_id: Optional[int] = None,
        action: str = "read",
        bot_id: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Create an audit log entry for credential access

        Args:
            credential_id: ID of the credential accessed
            account_id: ID of the account
            action: Action performed (create, read, update, delete, rotate)
            bot_id: ID of the bot accessing credentials
            success: Whether the action was successful
            error_message: Error message if action failed
            metadata: Additional metadata about the action
            ip_address: IP address of the request
            user_agent: User agent of the request
        """
        try:
            audit_entry = CredentialAuditLog(
                credential_id=credential_id,
                account_id=account_id,
                action=action,
                bot_id=bot_id,
                success=success,
                error_message=error_message,
                audit_metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            self.session.add(audit_entry)
            self.session.commit()
        except Exception as e:
            # Don't fail the main operation if audit fails
            error(f"Failed to create audit log: {str(e)}")
            self.session.rollback()

    def get_audit_log(
        self,
        account_id: Optional[int] = None,
        bot_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get audit log entries

        Args:
            account_id: Filter by account ID
            bot_id: Filter by bot ID
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries
        """
        query = self.session.query(CredentialAuditLog)

        if account_id:
            query = query.filter_by(account_id=account_id)
        if bot_id:
            query = query.filter_by(bot_id=bot_id)

        entries = query.order_by(CredentialAuditLog.timestamp.desc()).limit(limit).all()

        return [
            {
                "id": entry.id,
                "credential_id": entry.credential_id,
                "account_id": entry.account_id,
                "action": entry.action,
                "bot_id": entry.bot_id,
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                "ip_address": str(entry.ip_address) if entry.ip_address else None,
                "user_agent": entry.user_agent,
                "success": entry.success,
                "error_message": entry.error_message,
                "metadata": entry.audit_metadata,
            }
            for entry in entries
        ]


@contextmanager
def get_credential_manager(session: Session) -> Generator[CredentialManager, None, None]:
    """
    Context manager for credential operations

    Args:
        session: SQLAlchemy session

    Yields:
        CredentialManager instance
    """
    # Create master key provider and encryption service
    key_provider = MasterKeyProvider()
    encryption_service = CredentialEncryption(key_provider)

    # Create credential manager
    manager = CredentialManager(session, encryption_service)

    try:
        yield manager
    finally:
        # Clear any cached keys
        key_provider.clear_cache()
