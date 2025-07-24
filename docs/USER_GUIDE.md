# 📖 TradeStream User Guide

> **Complete Setup and Usage Guide for Multi-Broker Trading with Professional Dashboard**

## Table of Contents
1. [Overview](#overview)
2. [Installation](#installation)
3. [Multi-Broker Configuration](#multi-broker-configuration)
4. [Dashboard Interface](#dashboard-interface)
5. [Alert Tracking System](#alert-tracking-system)
6. [Trading Modes](#trading-modes)
7. [Paper Trading & Testing](#paper-trading--testing)
8. [Live Trading Setup](#live-trading-setup)
9. [Performance Analytics](#performance-analytics)
10. [Risk Management](#risk-management)
11. [Troubleshooting](#troubleshooting)
12. [Advanced Features](#advanced-features)

## Overview

TradeStream is a comprehensive multi-broker automated trading system that:
- **Multi-Channel Monitoring**: Monitors TWI_Futures and TWI_Options Discord channels simultaneously
- **Multi-Broker Support**: Integrates with Webull, TD Ameritrade, E*TRADE, IBKR, TradeStation, and Schwab
- **Futures Trading**: TopStepX integration for ES, NQ, YM, RTY futures via TradeForgePy
- **Options Trading**: Full options support with BTO/STC parsing and execution
- **Professional Dashboard**: Streamlit-based interface with real-time monitoring
- **Alert Tracking**: Comprehensive tracking from Discord reception to trade execution
- **Paper Trading**: Risk-free testing environment with realistic simulation
- **Live Trading**: Production-ready execution with advanced risk management

### Key Features

#### 🏦 **Multi-Broker Architecture**
- **Futures Broker**: TopStepX for ES, NQ, YM, RTY futures trading
- **Options Brokers**: Webull, TD Ameritrade, E*TRADE (fully implemented)
- **Future Brokers**: IBKR, TradeStation, Schwab (placeholder implementations)
- **Smart Routing**: Automatic broker selection based on asset type and availability
- **Unified Interface**: Consistent API across all broker implementations

#### 📡 **Multi-Channel Discord Integration**
- **TWI_Futures Channel**: JMoney futures alerts (ES LONG/SHORT signals)
- **TWI_Options Channel**: Options alerts with "BOUGHT" (BTO) and "SOLD" (STC) parsing
- **Multi-Author Support**: Twinsight Bot #7577 and twi_jmoney
- **Real-time Processing**: Sub-second alert processing and routing
- **Alert Validation**: Confidence scoring and parsing verification

#### 🖥️ **Professional Streamlit Dashboard**
- **Multi-Page Interface**: Settings, Strategy, Performance, Alerts, Live Trading
- **Real-Time Monitoring**: Live broker status, alert feeds, performance metrics
- **Multi-Broker Configuration**: Visual setup for all supported brokers
- **Alert Tracking Dashboard**: Dual feeds for trade alerts and all messages
- **Performance Analytics**: Futures vs options filtering, P&L charts, trade history
- **Live/Paper Toggle**: Seamless switching between trading modes

#### 📊 **Advanced Alert Tracking**
- **End-to-End Tracking**: From Discord reception to trade execution
- **Performance Analytics**: Success rates, parsing confidence, execution metrics
- **Database Persistence**: SQLite with optimized indexes for fast queries
- **Real-Time Statistics**: Live dashboard with comprehensive metrics
- **Audit Trail**: Complete history of all alert processing and execution

## Installation

### Prerequisites
- **Python 3.8+** with pip package manager
- **Discord Bot Token** with access to TWI_Futures and TWI_Options channels
- **TopStepX Account** (for futures live trading)
- **Broker Accounts** (optional, for options trading):
  - Webull, TD Ameritrade, E*TRADE, IBKR, TradeStation, or Schwab
- **Email Account** for notifications
- **Git** for repository cloning

### Step 1: Clone Repository
```bash
git clone https://github.com/atfleming/tradestream.git
cd tradestream
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Launch Dashboard
```bash
streamlit run dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`.

## Multi-Broker Configuration

### Supported Brokers

#### **TopStepX (Futures Trading)**
- **Assets**: ES, NQ, YM, RTY futures
- **Features**: Live trading, paper trading, real-time streaming
- **Setup**: Environment variables for credentials

#### **Webull (Options Trading)**
- **Assets**: Stocks, Options
- **Features**: BTO, STC, limit orders
- **Setup**: Email, password, trading PIN, device ID

#### **TD Ameritrade (Options Trading)**
- **Assets**: Stocks, Options, Futures
- **Features**: Full options support, OAuth authentication
- **Setup**: Client ID, redirect URL, credentials path

#### **E*TRADE (Options Trading)**
- **Assets**: Stocks, Options
- **Features**: OAuth authentication, sandbox testing
- **Setup**: Consumer key/secret from E*TRADE

### Environment Variables Setup

Create a `.env` file in the project root:

```bash
# TopStepX Futures Trading
TOPSTEPX_USERNAME=your_username
TOPSTEPX_PASSWORD=your_password
TOPSTEPX_API_KEY=your_api_key

# Webull Options Trading
WEBULL_EMAIL=your_email
WEBULL_PASSWORD=your_password
WEBULL_TRADING_PIN=123456
WEBULL_DEVICE_ID=your_device_id
WEBULL_SECURITY_DID=your_security_did

# TD Ameritrade Options Trading
TDA_CLIENT_ID=your_client_id
TDA_REDIRECT_URL=https://localhost
TDA_CREDENTIALS_PATH=./tda_credentials.json
TDA_ACCOUNT_ID=your_account_id

# E*TRADE Options Trading
ETRADE_CONSUMER_KEY=your_consumer_key
ETRADE_CONSUMER_SECRET=your_consumer_secret

# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token

# Email Notifications
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

## Dashboard Interface

### Main Dashboard
The main dashboard provides:
- **System Status**: Real-time broker connection status
- **Performance Metrics**: Live P&L, trade statistics, success rates
- **Alert Feeds**: Dual feeds for trade alerts and all messages
- **Live/Paper Toggle**: Switch between trading modes

### Settings Page
Configure all system components:
- **Discord Settings**: Token, channels, target authors
- **Trading Settings**: Risk parameters, position sizing
- **Multi-Broker Settings**: Configure all supported brokers
- **Email Settings**: Notification preferences
- **Advanced Settings**: System configuration

### Performance Page
Comprehensive analytics:
- **Metrics Overview**: Total P&L, win rate, Sharpe ratio
- **Performance Charts**: Equity curve, drawdown analysis
- **Trade History**: Detailed trade-by-trade breakdown
- **Futures vs Options**: Separate performance tracking

### Alerts Page
Alert management and monitoring:
- **Live Alerts**: Real-time alert processing
- **Alert History**: Historical alert database
- **Notifications**: Alert processing settings
- **Statistics**: Success rates, parsing confidence

## Alert Tracking System

### Alert Processing Flow
1. **Reception**: Discord message received
2. **Parsing**: Extract trading information
3. **Validation**: Confidence scoring and verification
4. **Routing**: Route to appropriate broker
5. **Execution**: Paper or live trade execution
6. **Tracking**: Store results and update analytics

### Alert Types

#### **Futures Alerts (TWI_Futures Channel)**
```
ES LONG 4750 STOP 4745 T1 4755 T2 4760
```
- **Symbol**: ES (E-mini S&P 500)
- **Direction**: LONG or SHORT
- **Entry**: 4750
- **Stop Loss**: 4745
- **Target 1**: 4755 (50% exit)
- **Target 2**: 4760 (remaining 50%)

#### **Options Alerts (TWI_Options Channel)**
```
BOUGHT SPY 01/31 480 CALLS @ 2.50
SOLD SPY 01/31 480 CALLS @ 3.25
```
- **Action**: BOUGHT (BTO) or SOLD (STC)
- **Symbol**: SPY
- **Expiration**: 01/31
- **Strike**: 480
- **Type**: CALLS or PUTS
- **Price**: 2.50

## Paper Trading & Testing

### Paper Trading Mode
- **Risk-Free Testing**: Test all functionality without real money
- **Realistic Simulation**: Includes slippage, commissions, market hours
- **Full Feature Set**: All features available in paper mode
- **Performance Tracking**: Complete analytics and reporting

### Testing Workflow
1. **Enable Paper Trading**: Use dashboard toggle
2. **Configure Brokers**: Set up broker connections
3. **Monitor Alerts**: Watch real Discord channels
4. **Review Performance**: Analyze results in dashboard
5. **Optimize Settings**: Adjust risk parameters
6. **Go Live**: Switch to live trading when ready

## Live Trading Setup

### Prerequisites
- **Funded Accounts**: Ensure sufficient capital in broker accounts
- **API Access**: Enable API trading in broker accounts
- **Risk Management**: Set appropriate position sizes and limits
- **Testing Complete**: Thoroughly test in paper mode first

### Go-Live Checklist
- [ ] Paper trading results satisfactory
- [ ] All broker connections tested
- [ ] Risk parameters configured
- [ ] Position sizing appropriate
- [ ] Stop losses and targets verified
- [ ] Email notifications working
- [ ] Dashboard monitoring active
- [ ] Backup systems in place

### Live Trading Activation
1. **Switch Mode**: Toggle from paper to live in dashboard
2. **Verify Connections**: Ensure all brokers connected
3. **Start Small**: Begin with minimum position sizes
4. **Monitor Closely**: Watch first few trades carefully
5. **Scale Gradually**: Increase size as confidence grows

## Performance Analytics

### Key Metrics
- **Total P&L**: Cumulative profit/loss across all trades
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profits / gross losses
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Average Trade**: Mean profit/loss per trade

### Filtering Options
- **Asset Type**: Futures vs Options
- **Broker**: Performance by broker
- **Time Period**: Daily, weekly, monthly analysis
- **Trade Type**: BTO, STC, LONG, SHORT

### Export Features
- **CSV Export**: Download trade data
- **PDF Reports**: Generate performance reports
- **Email Summaries**: Automated daily/weekly reports

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
