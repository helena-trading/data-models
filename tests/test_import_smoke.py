def test_import_smoke_tables_and_models() -> None:
    from data_models.database.tables.bot import Bot  # noqa: F401
    from data_models.models.enums.exchange import ExchangeName  # noqa: F401
    from data_models.models.runtime_control_plane import RuntimeHealthReportContract  # noqa: F401


def test_runtime_contract_compat_path_removed() -> None:
    import importlib

    try:
        importlib.import_module("data_models.models.api.runtime_control_plane")
    except ModuleNotFoundError:
        pass
    else:
        raise AssertionError("compat path should be removed; use data_models.models.runtime_control_plane")


def test_import_smoke_support_modules() -> None:
    from data_models.config.aws_secrets import AWSSecretsManager  # noqa: F401
    from data_models.logging import get_current_run_id, info  # noqa: F401
    from data_models.models.parameters import PARAMETER_GROUPS, SpreadParameters  # noqa: F401
    from data_models.models.reporting.report_models import BlockTradeInfo  # noqa: F401
    from data_models.security.credential_encryption import CredentialEncryption, MasterKeyProvider  # noqa: F401
