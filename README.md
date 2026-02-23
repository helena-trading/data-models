# data-models

Shared database and model package for Helena Trading repositories.

## Scope

- `data_models.database.*`: database config, tables, operations, loaders, migrations
- `data_models.models.*`: shared domain/engine/exchange/broker/enums/protocols models
- Runtime control-plane contract: `data_models.models.runtime_control_plane`

## Canonical source for bootstrap

Initial bootstrap copied from `core` repository (`src/database`, `src/models`) on 2026-02-20.

## Release

- CI validates editable install + built artifacts.
- Publishing is automated via `.github/workflows/release.yml` on `v*` tags.
- Release artifacts (`.whl` and `.tar.gz`) are attached to GitHub Releases.
- Consumers should pin an exact package version (current: `1.0.1`).

## Consumption via GitHub Releases

Use direct wheel URL pinning in consumer repos:

`data-models @ https://github.com/helena-trading/data-models/releases/download/v1.0.1/data_models-1.0.1-py3-none-any.whl`
