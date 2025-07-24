# 📖 TradeStream User Guide

> **Complete Setup and Usage Guide for Paper Trading and Live Trading with TradeForgePy**

## Table of Contents
1. [Overview](#overview)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Getting Started](#getting-started)
5. [Trading Modes](#trading-modes)
6. [Monitoring and Dashboard](#monitoring-and-dashboard)
7. [Risk Management](#risk-management)
8. [Backup and Recovery](#backup-and-recovery)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Features](#advanced-features)

## Overview

The JMoney Discord Alert Trading System is a sophisticated automated trading bot that:
- Monitors Discord channels for JMoney's trading alerts
- Parses "ES LONG" signals with entry, stop, and target levels
- Executes MES (Micro E-mini S&P 500) trades automatically
- Supports both paper trading and live trading modes
- Provides advanced position management with partial exits
- Offers comprehensive monitoring and risk management

### Key Features
- **Real-time Discord Monitoring**: Listens to JMoney's alerts 24/7
- **Advanced Position Management**: Target 1 (50% exit + breakeven), Target 2 (remaining 50%)
- **Dual Trading Modes**: Paper trading for testing, live trading for real money
- **Risk Management**: Daily limits, position controls, advanced risk metrics
- **Live Dashboard**: Real-time monitoring with performance metrics
- **Email Notifications**: HTML alerts for all trading events
- **Hot-reload Configuration**: Update settings without restarting
- **Backup System**: Automated data backup and recovery

## Installation

### Prerequisites
- Python 3.8 or higher
- Discord account with access to JMoney's channel
- TopStepX account (for live trading)
- Email account for notifications

### Step 1: Clone Repository
```bash
git clone <repository-url>
cd jmoney_alerts
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Install TradeForgePy (for live trading)
```bash
# TradeForgePy is included in requirements.txt
# It provides modern, production-ready TopStepX integration
pip install tradeforgepy>=1.0.0
```

## Configuration

### Basic Configuration

1. **Copy Configuration Template**
   ```bash
   cp config.yaml.example config.yaml
   ```

2. **Edit Configuration File**
   ```yaml
   # Discord Settings
   discord:
     token: "YOUR_DISCORD_BOT_TOKEN"
     channel_id: 123456789012345678
     target_author: "JMoney"
   
   # Trading Settings
   trading:
     symbol: "MES"
     enable_auto_trading: false  # Start with false for safety
     paper_trading_enabled: true  # Enable for testing
     live_trading_enabled: false  # Disable until ready
     
     # Size mapping (C=base, B=2*C, A=3*C)
     size_mapping:
       C: 1  # Modify this value
       B: 2  # Auto-calculated
       A: 3  # Auto-calculated
   
   # Email Settings
   email:
     enabled: true
     smtp_server: "smtp.gmail.com"
     smtp_port: 587
     sender_email: "your-email@gmail.com"
     recipient_email: "your-email@gmail.com"
   ```

### Environment Variables

Create a `.env` file in your project root for secure credential management:

```bash
# .env file - TradeForgePy automatically loads these
# Discord
DISCORD_BOT_TOKEN=your_discord_bot_token

# TopStepX Live Trading (TradeForgePy)
TS_USERNAME=your_topstepx_username
TS_API_KEY=your_topstepx_api_key
TS_ENVIRONMENT=DEMO  # Use DEMO for testing, LIVE for production

# Email
EMAIL_PASSWORD=your_gmail_app_password
```

> **🔒 Security Note**: Never commit the `.env` file to version control. Add it to your `.gitignore`.

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create new application
3. Go to "Bot" section
4. Create bot and copy token
5. Enable required intents:
   - Message Content Intent
   - Server Members Intent
6. Invite bot to server with appropriate permissions

## Getting Started

### 1. Test Configuration
```bash
python test_system.py
```

### 2. Start with Paper Trading
```bash
# Edit config.yaml
trading:
  enable_auto_trading: true
  paper_trading_enabled: true
  live_trading_enabled: false

# Run the system
python main.py
```

### 3. Monitor Dashboard
The system will display a real-time dashboard showing:
- System status and component health
- Trading performance metrics
- Recent alerts and executions
- Daily P&L and statistics

### 4. Verify Email Notifications
Check your email for:
- System startup confirmation
- Alert parsing confirmations
- Trade execution notifications
- Daily performance summaries

## Trading Modes

### Paper Trading Mode
- **Purpose**: Risk-free testing and strategy validation
- **Features**: 
  - Realistic market simulation with slippage
  - Commission simulation
  - Full position management testing
  - Separate P&L tracking
- **Configuration**:
  ```yaml
  trading:
    paper_trading_enabled: true
    paper_trading:
      starting_balance: 25000.0
      commission_per_contract: 0.62
      slippage_ticks: 1
  ```

### Live Trading Mode
- **Purpose**: Real money trading with TopStepX
- **Prerequisites**: 
  - Funded TopStepX account
  - Valid API credentials
  - Thorough paper trading testing
- **Configuration**:
  ```yaml
  trading:
    live_trading_enabled: true
    account_id: "YOUR_TOPSTEP_ACCOUNT_ID"
  ```

### Concurrent Mode
Run both paper and live trading simultaneously:
```yaml
trading:
  paper_trading_enabled: true
  live_trading_enabled: true
  concurrent_mode: true
```

## Monitoring and Dashboard

### Real-time Dashboard
The console dashboard updates every 5 seconds and shows:

#### System Status
- Component health (Database, Discord, Trading systems)
- Connection status
- Uptime information

#### Trading Status
- Active positions
- Daily P&L
- Trade count
- Win rate

#### Performance Metrics (30-day)
- Total trades and win rate
- Profit factor and Sharpe ratio
- Maximum drawdown
- Current streak

#### Recent Activity
- Last 5 alerts received
- Execution status
- Today's summary

### Performance Analytics
Access detailed analytics:
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit ÷ Gross loss
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Recovery Factor**: Net profit ÷ Maximum drawdown

## Risk Management

### Position Sizing
The system uses a C-based sizing approach:
- **C Size**: Base position size (user configurable)
- **B Size**: Automatically set to 2 × C
- **A Size**: Automatically set to 3 × C

Example: If C=2, then B=4, A=6 contracts

### Risk Controls
- **Daily Loss Limits**: Configurable maximum daily loss
- **Position Size Limits**: Maximum contracts per trade
- **Maximum Daily Trades**: Limit number of trades per day
- **Stop Loss Management**: Automatic stop placement and adjustment

### Advanced Risk Metrics
- **Value at Risk (VaR)**: Potential loss at 95% and 99% confidence
- **Volatility**: Annualized return volatility
- **Kelly Criterion**: Optimal position sizing percentage
- **Risk of Ruin**: Probability of losing all capital

### Risk Alerts
Automatic alerts for:
- Excessive drawdown
- Daily loss limits exceeded
- High volatility periods
- Component failures

## Backup and Recovery

### Automatic Backups
- **Frequency**: Every 6 hours
- **Retention**: 30 daily, 12 weekly, 12 monthly backups
- **Contents**: Database, configuration, logs, metadata

### Manual Backup
```python
# In Python console or script
from src.backup_system import backup_system
await backup_system.create_backup("manual")
```

### Recovery Process
```python
# Restore from backup
from src.backup_system import backup_system
await backup_system.restore_backup("path/to/backup.tar.gz")
```

### Data Integrity
- Automatic integrity checks every 24 hours
- Database consistency verification
- Configuration file validation
- Backup verification with checksums

## Troubleshooting

### Common Issues

#### 1. Discord Connection Failed
**Symptoms**: "Discord monitor failed to start"
**Solutions**:
- Verify Discord bot token
- Check bot permissions in server
- Ensure bot has access to target channel

#### 2. Database Errors
**Symptoms**: "Database initialization failed"
**Solutions**:
- Check file permissions
- Verify disk space
- Run integrity check: `PRAGMA integrity_check`

#### 3. Email Notifications Not Working
**Symptoms**: No email alerts received
**Solutions**:
- Verify SMTP settings
- Check app-specific password
- Test email configuration

#### 4. High CPU/Memory Usage
**Symptoms**: System performance degradation
**Solutions**:
- Check system resources in dashboard
- Review log files for errors
- Consider reducing monitoring frequency

### Log Analysis
Logs are stored in:
- **Main Log**: `trading_bot.log`
- **Component Logs**: Individual component logging
- **Error Logs**: Critical errors and exceptions

### Health Monitoring
Monitor system health via:
- Dashboard health section
- Email health alerts
- Performance metrics trends

## Advanced Features

### Configuration Hot-reload
Modify non-critical settings without restart:
- Trading limits
- Email preferences
- Risk thresholds
- Size mappings

Critical settings requiring restart:
- Discord credentials
- Trading account settings
- Database configuration

### Custom Alerts
Extend the system with custom alert types:
```python
# Add custom alert parsing
def parse_custom_alert(message):
    # Custom parsing logic
    return parsed_alert
```

### API Integration
The system provides internal APIs for:
- Trade execution status
- Performance metrics
- System health
- Configuration management

### Performance Optimization
- Database indexing for fast queries
- Async processing for concurrent operations
- Memory-efficient data structures
- Configurable monitoring intervals

### Security Best Practices
- Use environment variables for credentials
- Enable email notifications for security events
- Regular backup verification
- Monitor system access logs

## Support and Maintenance

### Regular Maintenance
- **Daily**: Review dashboard and email alerts
- **Weekly**: Check backup status and system health
- **Monthly**: Analyze performance metrics and optimize settings

### Updates and Upgrades
- Monitor for system updates
- Test updates in paper trading mode first
- Backup system before major updates

### Performance Monitoring
- Track system resource usage
- Monitor trade execution latency
- Review error rates and patterns

### Contact and Support
For technical support:
- Check documentation and troubleshooting guide
- Review log files for error details
- Test with paper trading mode first

---

**⚠️ Important Disclaimers:**
- This system is for educational and research purposes
- Trading involves substantial risk of loss
- Always test thoroughly with paper trading before live trading
- Past performance does not guarantee future results
- Use appropriate position sizing and risk management
