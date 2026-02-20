# data-models Bootstrap Manifest

Date: 2026-02-20

## Source Decision

- Canonical bootstrap source:
  - `/Users/gontijobernardo/helena-trading/core/src/database`
  - `/Users/gontijobernardo/helena-trading/core/src/models`
- Reason: contains latest decoupling and runtime contract updates in this workspace.

## Cross-Repo Snapshot Used

- Shared relative paths between `core/src` and `bot-manager-api/src`: **223**
- Byte-identical shared files: **219**
- Differing shared files: **4**

## Known Differing Files (Pre-bootstrap)

1. `src/database/operations/writer.py`
2. `src/models/__init__.py`
3. `src/database/migrations/README.md`
4. `src/bot_core/config/strategies.py`

## Hash Record (core vs api vs data-models)

- `writer.py`
  - core: `1d17d53c7f4d2b4a42093e585a19cade319683138cc4a18834c74afcef60f3f5`
  - api: `27a81eebab846461df9dbc1dcda9a836c88beb41d1ddbb60c21000b249b5246b`
  - data-models: `d2d1f383f462d0ca1b72d41e9dfd73feabc64c03615ea8c4048736e642a05450`
- `models/__init__.py`
  - core: `8342962f99ff48ca9c1c8d643ae75fc217dbc6506ee70d0d62688e9250c279af`
  - api: `4025e3b33c93772146290afa49ab8c9feb6f17bc16bcc4ea7cf7e95c03511da1`
  - data-models: `92c5528201bb1b38f10c301ffa102dc4d735a1b827ded1a49c4a84b7857cd4df`
- `migrations/README.md`
  - core: `275743f1e7f88e18733ab234ab5e0659e798c9d76fdfd8fd4ea7de20f5228bdb`
  - api: `fa5832a444ba54628e056b71cb67da71561148214e338697cef69e712a770f5f`
  - data-models: `275743f1e7f88e18733ab234ab5e0659e798c9d76fdfd8fd4ea7de20f5228bdb`

## Bootstrap Transformations Applied

1. Copied `core/src/database/*` to `data_models/database/*`.
2. Copied `core/src/models/*` to `data_models/models/*`.
3. Rewrote internal imports:
   - `src.database.*` -> `data_models.database.*`
   - `src.models.*` -> `data_models.models.*`
4. Replaced eager `database.tables` exports with lazy loading to avoid hard import failures at package init.

## Decoupling Status

- References to runtime/utilities packages still present: **0**
- All `src.bot_core.*` / `src.utilities.*` imports were replaced with package-local modules:
  - `data_models.logging.*`
  - `data_models.security.*`
  - `data_models.config.*`
  - `data_models.models.parameters.*`
  - `data_models.models.reporting.*`
- Consumer repos now import shared models/database directly from `data_models.*`.
- Runtime control-plane compat path was removed; canonical contract path is now only:
  - `data_models.models.runtime_control_plane`
