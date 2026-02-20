"""
AWS Secrets Manager integration for Helena Bot.

This module provides utilities for retrieving configuration and secrets
from AWS Secrets Manager instead of local config files.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union, cast

import boto3
from botocore.exceptions import ClientError

from data_models.logging import debug, error, info, warning


class AWSSecretsManager:
    """AWS Secrets Manager client for retrieving bot configuration and secrets."""

    def __init__(self, region_name: Optional[str] = None) -> None:
        """
        Initialize AWS Secrets Manager client.

        Args:
            region_name: AWS region name. Defaults to AWS_DEFAULT_REGION env var.
        """
        self.region_name = region_name or os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-1")
        self._client = None
        self._cache: Dict[str, tuple[Union[str, Dict[str, Any]], datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)  # Cache secrets for 5 minutes

    @property
    def client(self) -> Any:
        """Lazy initialization of boto3 client."""
        if self._client is None:
            self._client = boto3.client("secretsmanager", region_name=self.region_name)
        return self._client

    def get_secret(self, secret_name: str, parse_json: bool = True) -> Optional[Union[str, Dict[str, Any]]]:
        """
        Retrieve a secret from AWS Secrets Manager.

        Args:
            secret_name: Name of the secret to retrieve
            parse_json: Whether to parse the secret as JSON

        Returns:
            Secret value (string or dict if parse_json=True)
        """
        # Check cache first
        if secret_name in self._cache:
            value, timestamp = self._cache[secret_name]
            if datetime.now() - timestamp < self._cache_ttl:
                debug(f"[AWSSecretsManager] Using cached value for secret: {secret_name}")
                return value

        try:
            response = self.client.get_secret_value(SecretId=secret_name)

            # Extract secret string
            if "SecretString" in response:
                secret_value = cast(str, response["SecretString"])
            else:
                # Binary secret (not supported for config)
                error(f"[AWSSecretsManager] Binary secrets not supported: {secret_name}")
                return None

            # Parse JSON if requested
            result_value: Union[str, Dict[str, Any]] = secret_value
            if parse_json:
                try:
                    parsed_value: Union[str, Dict[str, Any]] = json.loads(secret_value)
                    result_value = parsed_value
                except json.JSONDecodeError:
                    # Not JSON, return as string
                    pass

            # Cache the value
            self._cache[secret_name] = (result_value, datetime.now())
            info(f"[AWSSecretsManager] Successfully retrieved secret: {secret_name}")

            return result_value

        except ClientError as e:
            error_code = cast(str, e.response["Error"]["Code"])
            if error_code == "ResourceNotFoundException":
                warning(f"[AWSSecretsManager] Secret not found: {secret_name}")
            elif error_code == "AccessDeniedException":
                error(f"[AWSSecretsManager] Access denied to secret: {secret_name}")
            else:
                error(f"[AWSSecretsManager] Error retrieving secret {secret_name}: {str(e)}")
            return None

    def get_config(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the main bot configuration from AWS Secrets Manager.

        Returns:
            Configuration dictionary or None if not found
        """
        config_secret_name = os.environ.get("AWS_CONFIG_SECRET_NAME", "helena-bot/config")
        return cast(Optional[Dict[str, Any]], self.get_secret(config_secret_name, parse_json=True))

    def get_exchange_credentials(self, exchange_name: str) -> Optional[Dict[str, str]]:
        """
        Retrieve exchange-specific credentials.

        Args:
            exchange_name: Name of the exchange (e.g., 'binance', 'hyperliquid')

        Returns:
            Dictionary with exchange credentials or None
        """
        # Normalize exchange name to lowercase
        exchange_name = exchange_name.lower().replace(" ", "_")

        # Try the new structure first: helena-bot/credentials/{exchange}
        secret_name = f"helena-bot/credentials/{exchange_name}"
        credentials = cast(Optional[Dict[str, str]], self.get_secret(secret_name, parse_json=True))

        if credentials:
            info(f"[AWSSecretsManager] Found credentials for {exchange_name} in new structure")
            return credentials

        # Fallback to alternative AWS Secrets Manager structure
        prefix = f"helena-bot/exchanges/{exchange_name}"
        credentials = {}

        # Common credential keys
        credential_keys = [
            "api-key",
            "api-secret",
            "passphrase",
            "account-address",
            "wallet-address",
            "private-key",
        ]

        for key in credential_keys:
            secret_name = f"{prefix}/{key}"
            value = cast(Optional[str], self.get_secret(secret_name, parse_json=False))
            if value:
                # Convert hyphenated keys to underscored
                dict_key = key.replace("-", "_")
                credentials[dict_key] = value

        # If no individual secrets found, try bundle secret
        if not credentials:
            bundle_secret = f"helena-bot/{exchange_name}-credentials"
            credentials = cast(Dict[str, str], self.get_secret(bundle_secret, parse_json=True)) or {}

        return credentials if credentials else None

    def get_database_password(self) -> Optional[str]:
        """Retrieve database password from secrets manager."""
        secret_name = os.environ.get("DB_PASSWORD_SECRET_NAME", "helena-bot/database/password")
        return cast(Optional[str], self.get_secret(secret_name, parse_json=False))

    def clear_cache(self) -> None:
        """Clear the secrets cache."""
        self._cache.clear()
        info("[AWSSecretsManager] Cleared secrets cache")


# Global instance
_secrets_manager: Optional[AWSSecretsManager] = None


def get_secrets_manager() -> AWSSecretsManager:
    """Get or create the global AWS Secrets Manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = AWSSecretsManager()
    return _secrets_manager


def is_aws_secrets_enabled() -> bool:
    """Check if AWS Secrets Manager is enabled."""
    return os.environ.get("USE_AWS_SECRETS", "false").lower() == "true"
