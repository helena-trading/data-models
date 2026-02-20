# Helena Bot Database Integration

This module provides TimescaleDB integration for storing and analyzing bot trading statistics.

## Features

- **Real-time data collection** with async batch writing
- **Time-series optimization** using TimescaleDB hypertables
- **Comprehensive analytics** queries for performance monitoring
- **Automatic data compression** and retention policies
- **Thread-safe connection pooling**

## Setup

### 1. Install TimescaleDB

#### Using Docker (Recommended)
```bash
docker run -d --name timescaledb -p 5432:5432 \
  -e POSTGRES_PASSWORD=helena123 \
  timescale/timescaledb:latest-pg14
```

#### Manual Installation
Follow the [TimescaleDB installation guide](https://docs.timescale.com/install/latest/)

### 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE helena_bot;
CREATE USER helena WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE helena_bot TO helena;
```

### 3. Run Migrations

```bash
# Using config file
python src/database/migrations/migrate.py migrate --config config/main/config.json

# Using environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=helena_bot
export DB_USER=helena
export DB_PASSWORD=your_secure_password
python src/database/migrations/migrate.py migrate --env

# Check migration status
python src/database/migrations/migrate.py status
```

### 4. Configure Bot

Update your `config.json`:
```json
{
  "database": {
    "enabled": true,
    "host": "localhost",
    "port": 5432,
    "database": "helena_bot",
    "user": "helena",
    "password": "your_secure_password",
    "min_connections": 2,
    "max_connections": 20
  }
}
```

## Usage

### Automatic Data Collection

When database is enabled in config, the bot automatically collects:
- Order executions
- Latency metrics
- Position snapshots
- Market data
- Block trades (arbitrage)
- Account balances

### Manual Analytics Queries

```python
from src.database.queries import get_analytics

analytics = get_analytics()

# Get trading summary
trading_summary = analytics.get_trading_summary(days=7)

# Get latency statistics
latency_stats = analytics.get_latency_statistics(hours=24)

# Get P&L summary
pnl_summary = analytics.get_pnl_summary(days=30)

# Get current positions
positions = analytics.get_current_positions()

# Get performance metrics
metrics = analytics.get_performance_metrics(hours=24)
```

## Database Schema

### Core Tables

1. **order_executions** - All order lifecycle events
2. **latency_metrics** - Performance timing data
3. **position_snapshots** - Position history
4. **market_data** - Orderbook snapshots
5. **block_trades** - Completed arbitrage trades
6. **account_balances** - Asset balance tracking

### Continuous Aggregates

- **order_exec_1min** - 1-minute order summaries
- **latency_5min** - 5-minute latency aggregates

## Performance Optimization

### Compression
```sql
-- Enable compression after 7 days
SELECT add_compression_policy('order_executions', INTERVAL '7 days');
SELECT add_compression_policy('market_data', INTERVAL '1 day');
```

### Retention
```sql
-- Drop old market data after 30 days
SELECT add_retention_policy('market_data', INTERVAL '30 days');

-- Keep orders for 1 year
SELECT add_retention_policy('order_executions', INTERVAL '1 year');
```

### Monitoring
```sql
-- Check database size
SELECT hypertable_size('order_executions');

-- Check compression status
SELECT * FROM timescaledb_information.compressed_hypertable_stats;

-- Active queries
SELECT * FROM pg_stat_activity WHERE state = 'active';
```

## Troubleshooting

### Connection Issues
- Check PostgreSQL is running: `pg_isready -h localhost -p 5432`
- Verify credentials: `psql -h localhost -U helena -d helena_bot`
- Check firewall/network settings

### Performance Issues
- Increase connection pool size in config
- Enable compression for historical data
- Add appropriate indexes for your queries
- Use continuous aggregates for dashboards

### Data Issues
- Check writer queue status in logs
- Verify data is being written: `SELECT COUNT(*) FROM order_executions WHERE time > NOW() - INTERVAL '1 hour';`
- Monitor disk space for high-volume data

## Architecture

```
Bot Components
     ↓
DatabaseIntegration
     ↓
DatabaseWriter (Async Batching)
     ↓
DatabaseManager (Connection Pool)
     ↓
TimescaleDB
```

The system uses:
- **Async batch writing** to minimize latency impact
- **Connection pooling** for efficient resource usage
- **Queue-based buffering** to handle traffic spikes
- **Automatic retries** for transient failures