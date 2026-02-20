# Database Migrations Guide

**Helena Bot Core - Production Database Migration System**

This directory contains the Alembic-based migration framework for managing database schema changes across all environments (development, staging, production).

---

## 🎯 Overview

Helena Bot uses **Alembic** for database migrations, integrated with **GitHub Actions** for automated deployment.

**Key Features:**
- ✅ Version-controlled migrations
- ✅ Executed via GitHub Actions + AWS SSM
- ✅ Secure: migration commands run on the target EC2 host (no RDS public exposure)
- ✅ Safe: explicit operator-triggered migration workflow
- ✅ Rollback support
- ✅ Migration history tracking

**Architecture:**
```
GitHub Actions Workflow
  ↓ (manual workflow_dispatch)
Package migration bundle
  ↓
Upload to S3
  ↓
Run migration via SSM on target EC2
  ↓
Capture output + cleanup bundle
```

---

## 📁 Directory Structure

```
src/database/migrations/
├── README.md                           # This file
├── alembic/                            # Alembic framework
│   ├── env.py                          # Migration runtime environment
│   ├── script.py.mako                  # Migration template
│   └── versions/                       # Migration version files
│       ├── 024_add_account_linking.py  # Example migration
│       └── 025_your_new_migration.py   # Your new migrations go here
└── scripts/                            # Legacy SQL migrations (reference only)
    ├── 001_initial_schema.sql
    ├── 024_update_balance_position_tables_for_account_linking.sql
    └── ...

alembic.ini                             # Alembic configuration (project root)
```

---

## 🚀 How to Create a New Migration

### Method 1: Auto-Generate from Models (Recommended)

Alembic can detect changes in your SQLAlchemy models and generate migrations automatically.

```bash
# 1. Make changes to your SQLAlchemy models
# Example: Add new column to src/database/models/block_trade.py

# 2. Generate migration automatically
alembic revision --autogenerate -m "Add settlement_time to block_trades"

# This creates: src/database/migrations/alembic/versions/025_add_settlement_time.py

# 3. Review the generated migration
cat src/database/migrations/alembic/versions/025_*.py

# 4. Edit if needed (autogenerate isn't perfect)
# 5. Test locally (see "Testing Migrations Locally" below)
# 6. Commit and push - GitHub Actions will deploy automatically
```

**Pros:**
- ✅ Fast and automatic
- ✅ Catches all model changes
- ✅ Generates both upgrade() and downgrade()

**Cons:**
- ⚠️ Not perfect - always review generated code
- ⚠️ May miss complex changes (indexes, constraints)
- ⚠️ Requires local database with current schema

---

### Method 2: Write Migration Manually

For complex migrations or when you don't have autogenerate working:

```bash
# 1. Create blank migration
alembic revision -m "Add settlement_time to block_trades"

# This creates: src/database/migrations/alembic/versions/025_add_settlement_time.py

# 2. Edit the file and add your changes
```

**Example migration:**
```python
"""Add settlement_time to block_trades

Revision ID: 025
Revises: 024
Create Date: 2025-10-22 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025"
down_revision: Union[str, None] = "024"  # Previous migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add settlement_time column to block_trades table."""

    op.add_column(
        'block_trades',
        sa.Column('settlement_time', sa.DateTime(timezone=True), nullable=True)
    )

    # Add index for performance
    op.create_index(
        'idx_block_trades_settlement_time',
        'block_trades',
        ['settlement_time'],
        postgresql_ops={'settlement_time': 'DESC'}
    )


def downgrade() -> None:
    """Remove settlement_time column."""

    op.drop_index('idx_block_trades_settlement_time', table_name='block_trades')
    op.drop_column('block_trades', 'settlement_time')
```

---

### Method 3: Use Existing SQL File (For Idempotent Migrations)

If you have an existing SQL migration that uses `DO $$` blocks for idempotency:

```python
"""Execute SQL migration for complex schema changes

Revision ID: 025
Revises: 024
Create Date: 2025-10-22 15:00:00.000000

"""
import os
from typing import Sequence, Union

from alembic import op

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Execute idempotent SQL migration."""

    sql_file_path = os.path.join(
        os.path.dirname(__file__),
        "../../scripts/025_your_migration.sql"
    )

    with open(sql_file_path, "r") as f:
        migration_sql = f.read()

    op.execute(migration_sql)


def downgrade() -> None:
    """Reverse the migration."""
    # Add rollback logic here
    pass
```

**Use this when:**
- ✅ Migration uses complex PostgreSQL features (DO $$ blocks, triggers, functions)
- ✅ You already have tested SQL file
- ✅ Migration needs conditional logic that avoids transaction aborts

**Example:** Migration 024 uses this approach (see `versions/024_add_account_linking.py`)

---

## 🧪 Testing Migrations Locally

**ALWAYS test migrations before pushing to production!**

### Step 1: Setup Local Database

```bash
# Start local databases via docker-compose
docker-compose up -d postgres-credentials postgres-analytics

# Or connect to your local PostgreSQL
export DATABASE_URL="postgresql://helena:helena123@localhost:5432/helena_bot"
```

### Step 2: Check Current Migration State

```bash
# Show current migration version
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic current
alembic heads
```

### Step 3: Run Migration Locally

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade 025

# Apply next migration only
alembic upgrade +1
```

### Step 4: Verify Schema

```bash
# Connect to database
psql $DATABASE_URL

# Check table schema
\d table_name

# Verify indexes
SELECT indexname FROM pg_indexes WHERE tablename = 'table_name';

# Check migration version
SELECT version_num FROM alembic_version;
```

### Step 5: Test Rollback (Optional)

```bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade 024

# Rollback all
alembic downgrade base
```

---

## 🚀 Deploying Migrations to Production

### The Workflow Way (Recommended)

Use the dedicated migration workflow in this repo:

```bash
# 1. Create and test migration locally (see above)

# 2. Commit migration file
git add src/database/migrations/alembic/versions/025_*.py
git commit -m "feat: Add settlement_time to block_trades table"

# 3. Push branch/main
git push origin <branch>

# 4. Trigger migration workflow manually
gh workflow run run-migrations.yml \
  --repo bernardoteixeirabtc/helena-bot-core \
  -f environment=production \
  -f database=analytics \
  -f migration_action=upgrade-head

# 5. Monitor workflow
gh run list --repo bernardoteixeirabtc/helena-bot-core --limit 5

# 6. Watch specific run
gh run view <run-id> --repo bernardoteixeirabtc/helena-bot-core
```

**What Happens:**
```
GitHub Actions Workflow: "Run Database Migrations"

Jobs:
  1. Validate inputs                     ✓
  2. Package migration bundle            ✓
  3. Upload bundle to S3                 ✓
  4. Execute migration via SSM on EC2    ← Your migration runs here!
  5. Wait for completion + capture logs  ✓
  6. Cleanup S3 artifact                 ✓
```

**GitHub Actions Workflow:** `.github/workflows/run-migrations.yml`

---

## 🔍 Verifying Migration Success

### Via GitHub Actions UI

**URL:** https://github.com/bernardoteixeirabtc/helena-bot-core/actions

**Check:**
1. "Run Database Migrations" workflow shows a green checkmark
2. `run-migrations` job passed
3. command output includes expected Alembic revision transition

**View logs:**
```bash
gh run view <run-id> --repo bernardoteixeirabtc/helena-bot-core --log
```

**Expected output:**
```
🔄 Running database migrations...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 024 -> 025, Add settlement_time
✅ Migrations completed successfully

🔍 Verifying migration 025...
✅ Migration verification passed!
```

---

### Via Database Query

**Connect to production database:**
```bash
# Via bot-manager-api container (has DATABASE_URL configured)
aws ssm send-command \
  --region ap-northeast-1 \
  --instance-ids i-032a31e8c1f7537d9 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["docker exec bot-manager-api psql $DATABASE_URL -c \"SELECT version_num FROM alembic_version\""]'
```

**Check migration history:**
```sql
-- Current version
SELECT version_num FROM alembic_version;

-- Should show your migration number (e.g., '025')
```

**Verify schema changes:**
```sql
-- Check if column exists
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'block_trades'
  AND column_name = 'settlement_time';

-- Check if index exists
SELECT indexname
FROM pg_indexes
WHERE tablename = 'block_trades'
  AND indexname = 'idx_block_trades_settlement_time';
```

---

## 🛠️ Common Migration Patterns

### Add Column

```python
def upgrade() -> None:
    op.add_column(
        'table_name',
        sa.Column('new_column', sa.String(50), nullable=True)
    )

def downgrade() -> None:
    op.drop_column('table_name', 'new_column')
```

### Rename Column

```python
def upgrade() -> None:
    op.alter_column('table_name', 'old_name', new_column_name='new_name')

def downgrade() -> None:
    op.alter_column('table_name', 'new_name', new_column_name='old_name')
```

### Add Foreign Key

```python
def upgrade() -> None:
    # Add column first
    op.add_column('child_table', sa.Column('parent_id', sa.Integer(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_child_parent',
        'child_table',
        'parent_table',
        ['parent_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_child_parent', 'child_table', type_='foreignkey')
    op.drop_column('child_table', 'parent_id')
```

### Create Index

```python
def upgrade() -> None:
    op.create_index(
        'idx_table_column',
        'table_name',
        ['column_name'],
        postgresql_ops={'column_name': 'DESC'}  # Optional: DESC sorting
    )

def downgrade() -> None:
    op.drop_index('idx_table_column', table_name='table_name')
```

### Add Trigger

```python
def upgrade() -> None:
    # Create trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER update_table_timestamp
        BEFORE UPDATE ON table_name
        FOR EACH ROW EXECUTE FUNCTION update_timestamp();
    """)

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_table_timestamp ON table_name;")
    op.execute("DROP FUNCTION IF EXISTS update_timestamp();")
```

---

## 🔐 Security & Best Practices

### ✅ DO:

1. **Always test locally first**
   ```bash
   alembic upgrade head  # Test on local database
   alembic downgrade -1  # Test rollback
   ```

2. **Keep migrations idempotent** (safe to run multiple times)
   ```python
   # Use if_exists=True, if_not_exists=True
   op.create_index('idx_name', 'table', ['col'], if_not_exists=True)
   op.drop_index('idx_name', if_exists=True)
   ```

3. **Add both upgrade() and downgrade()**
   - Always provide rollback logic
   - Test downgrade locally

4. **Use descriptive migration messages**
   ```bash
   alembic revision -m "Add user_preferences table with JSON config"
   ```

5. **Add comments to complex migrations**
   ```python
   def upgrade() -> None:
       """Add user preferences.

       This migration adds a new table for storing user-specific
       preferences in JSONB format for flexibility.
       """
   ```

6. **Keep migrations small and focused**
   - One logical change per migration
   - Easier to debug and rollback

### ❌ DON'T:

1. **Don't modify existing migrations** that have been deployed
   - Create a new migration to fix issues
   - Alembic tracks by revision ID

2. **Don't use try/except in Alembic operations** (causes PostgreSQL transaction aborts)
   ```python
   # BAD:
   try:
       op.add_column('table', sa.Column('col', sa.Integer()))
   except:
       pass  # This aborts the transaction!

   # GOOD: Use SQL with DO $$ blocks instead
   op.execute("""
       DO $$
       BEGIN
           IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='table' AND column_name='col') THEN
               ALTER TABLE table ADD COLUMN col INTEGER;
           END IF;
       END $$;
   """)
   ```

3. **Don't commit sensitive data**
   - No passwords, API keys, or secrets in migrations
   - Use environment variables or AWS Secrets Manager

4. **Don't skip testing**
   - Always test locally before pushing
   - Test rollback (downgrade) works

---

## 🔧 Troubleshooting

### Local Alembic Commands Fail with "Could not parse SQLAlchemy URL"

**Symptom:**
```bash
$ alembic current
sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from given URL string
```

**Cause:**
The `DATABASE_URL` environment variable is not set or is empty.

**Solution:**
```bash
# Set DATABASE_URL before running alembic commands
export DATABASE_URL="postgresql://helena:helena123@localhost:5432/helena_credentials"

# For analytics database migrations (chat tables, trades, etc.)
export DATABASE_URL="postgresql://helena:helena123@localhost:5432/helena_analytics"

# Then run alembic
alembic current
alembic upgrade head
```

**Note:** The `alembic.ini` file intentionally leaves `sqlalchemy.url` empty (best practice for multi-environment). The database URL is read from the `DATABASE_URL` environment variable in `env.py`.

---

### Migration Fails in GitHub Actions

**Check workflow logs:**
```bash
gh run list --repo bernardoteixeirabtc/helena-bot-core --limit 5
gh run view <run-id> --log-failed
```

**Common issues:**

1. **Syntax Error in Migration**
   - Fix: Test locally with `alembic upgrade head`
   - Commit fix and push

2. **Missing Python Dependencies**
   - Fix: Update migration runtime dependencies used by `.github/scripts/run-migration.sh`
   - Re-run workflow after validating dependency install on target host

3. **Database Connection Error**
   - Check: AWS Secrets Manager has correct credentials
   - Verify: RDS security group allows runner's VPC

4. **Transaction Abort / "commands ignored until end of transaction block"**
   - Fix: Remove try/except blocks, use SQL DO $$ blocks instead
   - See Migration 024 for example

### Migration Runs But Doesn't Apply Changes

**Check Alembic version:**
```bash
docker exec bot-manager-api python3 -c "
import psycopg, os
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT version_num FROM alembic_version')
print(f'Current version: {cur.fetchone()[0]}')
"
```

**Manually run migration:**
```bash
# SSH to EC2 or use SSM
docker exec bot-manager-api bash -c "cd /app && alembic upgrade head"
```

### Rollback Migration in Production

**⚠️ Use with caution!** Rollbacks can lose data.

```bash
# Trigger rollback workflow action instead of executing inside a local runner container
gh workflow run run-migrations.yml \
  --repo bernardoteixeirabtc/helena-bot-core \
  -f environment=production \
  -f database=analytics \
  -f migration_action=downgrade-1
```

---

## 📝 Migration Checklist

Before pushing a migration to production:

- [ ] Migration tested locally (`alembic upgrade head`)
- [ ] Rollback tested locally (`alembic downgrade -1`)
- [ ] Both `upgrade()` and `downgrade()` implemented
- [ ] Migration is idempotent (safe to run multiple times)
- [ ] No try/except blocks in Alembic operations
- [ ] No sensitive data (passwords, keys) in migration
- [ ] Migration has descriptive commit message
- [ ] Code passes pre-commit hooks (mypy, black, isort, flake8)

---

## 📚 Additional Resources

**Alembic Documentation:**
- Official Docs: https://alembic.sqlalchemy.org/
- Tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- Auto-generate: https://alembic.sqlalchemy.org/en/latest/autogenerate.html

**GitHub Actions:**
- Self-hosted Runners: https://docs.github.com/en/actions/hosting-your-own-runners
- Workflow Syntax: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions

**PostgreSQL:**
- DO $$ Blocks: https://www.postgresql.org/docs/current/sql-do.html
- Triggers: https://www.postgresql.org/docs/current/sql-createtrigger.html

**Helena Bot Docs:**
- Runner Setup: `docs/GITHUB_RUNNER_SETUP.md`
- Migration 024 Guide: `docs/MIGRATION_024_EXECUTION_GUIDE.md`

---

## 🎓 Example: Complete Migration Workflow

Let's say you want to add `execution_venue` column to `order_executions` table:

### 1. Create Migration

```bash
# Auto-generate
alembic revision --autogenerate -m "Add execution_venue to order_executions"

# Or manual
alembic revision -m "Add execution_venue to order_executions"
```

### 2. Edit Migration File

**File:** `src/database/migrations/alembic/versions/026_add_execution_venue.py`

```python
"""Add execution_venue to order_executions

Revision ID: 026
Revises: 025
Create Date: 2025-10-22 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add execution_venue column to track where orders execute."""

    op.add_column(
        'order_executions',
        sa.Column('execution_venue', sa.String(50), nullable=True)
    )

    # Add index for filtering by venue
    op.create_index(
        'idx_order_executions_venue',
        'order_executions',
        ['execution_venue']
    )

    # Add comment
    op.execute("""
        COMMENT ON COLUMN order_executions.execution_venue IS
        'Exchange/venue where order was executed (e.g., binance, ripio_trade)';
    """)


def downgrade() -> None:
    """Remove execution_venue column."""

    op.drop_index('idx_order_executions_venue', table_name='order_executions')
    op.drop_column('order_executions', 'execution_venue')
```

### 3. Test Locally

```bash
# Apply migration
export DATABASE_URL="postgresql://helena:helena123@localhost:5432/helena_bot"
alembic upgrade head

# Verify
psql $DATABASE_URL -c "\d order_executions"

# Test rollback
alembic downgrade -1

# Re-apply
alembic upgrade head
```

### 4. Commit and Deploy

```bash
git add src/database/migrations/alembic/versions/026_add_execution_venue.py
git commit -m "feat: Add execution_venue to order_executions table

Track which exchange/venue each order executes on.

Migration 026:
- Add execution_venue VARCHAR(50) column
- Create index for venue filtering
- Add column comment for documentation

🚀 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin main
```

### 5. Monitor Deployment

```bash
# Watch workflow
gh run list --repo bernardoteixeirabtc/helena-bot-core --limit 1

# View details
gh run view --repo bernardoteixeirabtc/helena-bot-core

# If migration passes, deployment continues automatically
```

### 6. Verify in Production

```bash
# Check migration version
docker exec bot-manager-api python3 -c "
import psycopg, os
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT version_num FROM alembic_version')
print(f'Migration version: {cur.fetchone()[0]}')
"

# Check column exists
docker exec bot-manager-api python3 -c "
import psycopg, os
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT column_name FROM information_schema.columns WHERE table_name='\''order_executions'\'' AND column_name='\''execution_venue'\''')
print(f'Column exists: {bool(cur.fetchone())}')
"
```

---

## 🚨 Emergency Rollback Procedure

**If a migration causes critical issues in production:**

### 1. Quick Rollback

```bash
# Trigger rollback directly via workflow
gh workflow run run-migrations.yml \
  --repo bernardoteixeirabtc/helena-bot-core \
  -f environment=production \
  -f database=analytics \
  -f migration_action=downgrade-1
```

### 2. Verify Rollback

```bash
# Check version
docker exec bot-manager-api python3 -c "
import psycopg, os
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT version_num FROM alembic_version')
print(f'Version after rollback: {cur.fetchone()[0]}')
"
```

### 3. Deploy Old Code

```bash
# Revert the code changes
git revert HEAD
git push origin main

# GitHub Actions will deploy old code
```

---

## 🎉 Success Story: Migration 024

**Migration 024** is a perfect example of our production migration system:

**What it did:**
- Added account_id foreign keys to balance/position tables
- Renamed 4 columns in account_balances
- Added 3 new columns
- Created 12 performance indexes
- Added auto-update triggers

**How it was deployed:**
1. Created Alembic migration: `versions/024_add_account_linking.py`
2. Used original idempotent SQL file to avoid transaction aborts
3. Pushed to main branch
4. GitHub Actions automatically:
   - Packaged migration bundle
   - Executed migration via SSM on production host
   - Verified success
   - Cleaned up temporary artifacts
5. **Total time: 2.5 minutes, zero downtime**

**View the workflow:**
- https://github.com/bernardoteixeirabtc/helena-bot-core/actions/runs/18716684528

**Migration file:**
- `src/database/migrations/alembic/versions/024_add_account_linking.py`

---

## 📞 Getting Help

**Issues with migrations?**

1. Check GitHub Actions logs:
   ```bash
   gh run list --repo bernardoteixeirabtc/helena-bot-core --limit 5
   gh run view <run-id> --log-failed
   ```

2. Check migration command status:
   ```bash
   gh run view <run-id> --repo bernardoteixeirabtc/helena-bot-core --log
   ```

3. Check database connection from host app container:
   ```bash
   docker exec bot-manager-api python3 -c "import psycopg; print('Psycopg installed!')"
   ```

4. Consult documentation:
   - `docs/GITHUB_RUNNER_SETUP.md` - Runner setup guide
   - `docs/MIGRATION_024_EXECUTION_GUIDE.md` - Migration 024 reference
   - `docs/PRODUCTION_DEPLOYMENT_GUIDE.md` - Deployment procedures

---

**Created**: 2025-10-22
**Last Updated**: 2025-10-22
**Migration System Version**: Alembic 1.17.0
**Current Production Migration**: 024

**This is the PROPER way to do database migrations. No more manual SQL execution!** 🚀
