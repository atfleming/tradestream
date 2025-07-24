"""
Configuration Management System for JMoney Discord Alert Trading System
Handles loading, validation, and management of all configuration settings
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DiscordConfig:
    """Discord bot configuration"""
    token: str
    channels: Dict[str, int]  # Channel name -> Channel ID mapping
    target_authors: List[str]  # List of authors to monitor
    reconnect_attempts: int = 5
    reconnect_delay: int = 30
    
    # Legacy support for single channel
    @property
    def channel_id(self) -> int:
        """Get primary channel ID for backward compatibility"""
        return list(self.channels.values())[0] if self.channels else 0
    
    @property
    def target_author(self) -> str:
        """Get primary author for backward compatibility"""
        return self.target_authors[0] if self.target_authors else "JMoney"


@dataclass
class PaperTradingConfig:
    """Paper trading specific configuration"""
    starting_balance: float = 50000.0
    realistic_slippage: bool = True
    slippage_ticks: int = 1
    commission_per_contract: float = 2.50
    track_separately: bool = True


@dataclass
class WebullConfig:
    """Webull broker configuration"""
    username: str = ""
    password: str = ""
    device_id: str = ""
    trading_pin: str = ""
    paper_trading: bool = True
    enabled: bool = False


@dataclass
class TDAConfig:
    """TD Ameritrade broker configuration"""
    client_id: str = ""
    redirect_uri: str = "https://localhost"
    token_path: str = "data/td_token.json"
    paper_trading: bool = True
    enabled: bool = False


@dataclass
class ETradeConfig:
    """E*TRADE broker configuration"""
    consumer_key: str = ""
    consumer_secret: str = ""
    prod_base_url: str = "https://api.etrade.com"
    sandbox_base_url: str = "https://etwssandbox.etrade.com"
    sandbox: bool = True
    with_browser: bool = True
    enabled: bool = False


@dataclass
class IBKRConfig:
    """Interactive Brokers configuration"""
    account: str = ""
    host: str = "127.0.0.1"
    port: int = 7497  # 7496 for live, 7497 for paper
    client_id: int = 123
    paper_trading: bool = True
    enabled: bool = False


@dataclass
class TradeStationConfig:
    """TradeStation broker configuration"""
    api_key: str = ""
    secret: str = ""
    redirect_uri: str = "https://localhost:3000"
    paper_trading: bool = True
    enabled: bool = False


@dataclass
class SchwabConfig:
    """Charles Schwab broker configuration"""
    app_key: str = ""
    app_secret: str = ""
    redirect_uri: str = "https://localhost"
    paper_trading: bool = True
    enabled: bool = False


@dataclass
class TradingConfig:
    """Trading configuration with MES contract specifications"""
    account_id: str = ""
    
    # Contract Specifications
    symbol: str = "MES"
    contract_name: str = "Micro E-mini S&P 500"
    exchange: str = "CME"
    tick_size: float = 0.25
    tick_value: float = 1.25
    margin_requirement: float = 500.0
    
    # Position Sizing
    size_mapping: Dict[str, int] = field(default_factory=lambda: {"A": 1, "B": 2, "C": 3})
    
    # Trading Limits
    max_daily_trades: int = 10
    max_position_size: int = 5
    
    # Trading Mode Configuration
    enable_auto_trading: bool = False
    paper_trading_enabled: bool = True
    live_trading_enabled: bool = False
    concurrent_trading: bool = False
    
    # Paper Trading Settings
    paper_trading: Optional[PaperTradingConfig] = None
    
    def __post_init__(self):
        if self.size_mapping is None:
            self.size_mapping = {"A": 1, "B": 2, "C": 3}


@dataclass
class RiskConfig:
    """Risk management configuration"""
    max_loss_per_trade: float = 100.0
    daily_loss_limit: float = 500.0
    max_consecutive_losses: int = 3
    position_size_limit: int = 5
    enable_circuit_breaker: bool = True


@dataclass
class DatabaseConfig:
    """Database configuration"""
    file_path: str = "data/trading_data.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    file_path: str = "logs/trading_bot.log"
    max_file_size_mb: int = 10
    backup_count: int = 5
    console_output: bool = True


@dataclass
class EmailConfig:
    """Email notification configuration"""
    enabled: bool = True
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    from_address: str = ""
    to_addresses: List[str] = None
    send_alert_confirmations: bool = True
    send_trade_executions: bool = True
    send_daily_summaries: bool = True
    daily_summary_time: str = "17:00"
    
    def __post_init__(self):
        if self.to_addresses is None:
            self.to_addresses = []


class ConfigManager:
    """Main configuration manager class"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = Path(config_file)
        self.discord: Optional[DiscordConfig] = None
        self.trading: Optional[TradingConfig] = None
        self.risk: Optional[RiskConfig] = None
        self.database: Optional[DatabaseConfig] = None
        self.logging: Optional[LoggingConfig] = None
        self.email: Optional[EmailConfig] = None
        # Multi-broker support
        self.webull: Optional[WebullConfig] = None
        self.tda: Optional[TDAConfig] = None
        self.etrade: Optional[ETradeConfig] = None
        self.ibkr: Optional[IBKRConfig] = None
        self.tradestation: Optional[TradeStationConfig] = None
        self.schwab: Optional[SchwabConfig] = None
        
    def load_config(self) -> bool:
        """Load configuration from YAML file and environment variables"""
        try:
            # Load from YAML file
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
            else:
                raise FileNotFoundError(f"Configuration file {self.config_file} not found")
            
            # Load Discord configuration with default multi-channel setup
            discord_data = config_data.get('discord', {})
            
            # Default Discord token (user provided)
            discord_token = os.getenv('DISCORD_TOKEN', discord_data.get('token', 'MzY5NTkyNzMwODM5Njc4OTc4.GKOPM9.sHQJ_AugT76APLe-flw5uqmX_O0JgxuJFgv1J8'))
            
            # Default channel configuration
            default_channels = {
                "TWI_Futures": 1127635026318721094,
                "TWI_Options": 1337621057552650240
            }
            channels = discord_data.get('channels', default_channels)
            
            # Default target authors
            default_authors = ["Twinsight Bot #7577", "twi_jmoney"]
            target_authors = discord_data.get('target_authors', default_authors)
            
            self.discord = DiscordConfig(
                token=discord_token,
                channels=channels,
                target_authors=target_authors,
                reconnect_attempts=discord_data.get('reconnect_attempts', 5),
                reconnect_delay=discord_data.get('reconnect_delay', 30)
            )
            
            # Load Trading configuration
            trading_data = config_data.get('trading', {})
            topstep_account = os.getenv('TOPSTEP_ACCOUNT_ID', trading_data.get('account_id', ''))
            if not topstep_account:
                raise ValueError("TopStep account ID must be provided in config file or TOPSTEP_ACCOUNT_ID environment variable")
            
            # Load paper trading configuration
            paper_trading_data = trading_data.get('paper_trading', {})
            paper_trading_config = PaperTradingConfig(
                starting_balance=paper_trading_data.get('starting_balance', 50000.0),
                realistic_slippage=paper_trading_data.get('realistic_slippage', True),
                slippage_ticks=paper_trading_data.get('slippage_ticks', 1),
                commission_per_contract=paper_trading_data.get('commission_per_contract', 2.50),
                track_separately=paper_trading_data.get('track_separately', True)
            )
            
            self.trading = TradingConfig(
                account_id=topstep_account,
                symbol=trading_data.get('symbol', 'MES'),
                contract_name=trading_data.get('contract_name', 'Micro E-mini S&P 500'),
                exchange=trading_data.get('exchange', 'CME'),
                tick_size=trading_data.get('tick_size', 0.25),
                tick_value=trading_data.get('tick_value', 1.25),
                margin_requirement=trading_data.get('margin_requirement', 500.0),
                size_mapping=trading_data.get('size_mapping', {"A": 1, "B": 2, "C": 3}),
                max_daily_trades=trading_data.get('max_daily_trades', 10),
                max_position_size=trading_data.get('max_position_size', 5),
                enable_auto_trading=trading_data.get('enable_auto_trading', False),
                paper_trading_enabled=trading_data.get('paper_trading_enabled', True),
                live_trading_enabled=trading_data.get('live_trading_enabled', False),
                concurrent_trading=trading_data.get('concurrent_trading', False),
                paper_trading=paper_trading_config
            )
            
            # Load Risk configuration
            risk_data = config_data.get('risk', {})
            self.risk = RiskConfig(
                max_loss_per_trade=risk_data.get('max_loss_per_trade', 100.0),
                daily_loss_limit=risk_data.get('daily_loss_limit', 500.0),
                max_consecutive_losses=risk_data.get('max_consecutive_losses', 3),
                position_size_limit=risk_data.get('position_size_limit', 5),
                enable_circuit_breaker=risk_data.get('enable_circuit_breaker', True)
            )
            
            # Load Database configuration
            db_data = config_data.get('database', {})
            self.database = DatabaseConfig(
                file_path=db_data.get('file_path', 'data/trading_data.db'),
                backup_enabled=db_data.get('backup_enabled', True),
                backup_interval_hours=db_data.get('backup_interval_hours', 24)
            )
            
            # Load Logging configuration
            log_data = config_data.get('logging', {})
            self.logging = LoggingConfig(
                level=log_data.get('level', 'INFO'),
                file_path=log_data.get('file_path', 'logs/trading_bot.log'),
                max_file_size_mb=log_data.get('max_file_size_mb', 10),
                backup_count=log_data.get('backup_count', 5),
                console_output=log_data.get('console_output', True)
            )
            
            # Load Email configuration
            email_data = config_data.get('email', {})
            # Override with environment variables if available
            email_username = os.getenv('GMAIL_USERNAME', email_data.get('username', ''))
            email_password = os.getenv('GMAIL_PASSWORD', email_data.get('password', ''))
            
            self.email = EmailConfig(
                enabled=email_data.get('enabled', True),
                smtp_server=email_data.get('smtp_server', 'smtp.gmail.com'),
                smtp_port=email_data.get('smtp_port', 587),
                username=email_username,
                password=email_password,
                from_address=email_data.get('from_address', email_username),
                to_addresses=email_data.get('to_addresses', []),
                send_alert_confirmations=email_data.get('send_alert_confirmations', True),
                send_trade_executions=email_data.get('send_trade_executions', True),
                send_daily_summaries=email_data.get('send_daily_summaries', True),
                daily_summary_time=email_data.get('daily_summary_time', '17:00')
            )
            
            return True
            
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
    
    def validate_config(self) -> bool:
        """Validate all configuration settings"""
        try:
            # Validate Discord config
            if not self.discord or not self.discord.token:
                raise ValueError("Discord token is required")
            if not self.discord.channel_id:
                raise ValueError("Discord channel ID is required")
            
            # Validate Trading config
            if not self.trading or not self.trading.account_id:
                raise ValueError("TopStep account ID is required")
            if not self.trading.size_mapping:
                raise ValueError("Size mapping is required")
            
            # Validate Risk config
            if not self.risk:
                raise ValueError("Risk configuration is required")
            if self.risk.max_loss_per_trade <= 0:
                raise ValueError("Max loss per trade must be positive")
            if self.risk.daily_loss_limit <= 0:
                raise ValueError("Daily loss limit must be positive")
            
            # Validate paths exist
            if self.database:
                Path(self.database.file_path).parent.mkdir(parents=True, exist_ok=True)
            if self.logging:
                Path(self.logging.file_path).parent.mkdir(parents=True, exist_ok=True)
            
            return True
            
        except Exception as e:
            print(f"Configuration validation error: {e}")
            return False
    
    def get_size_for_alert(self, size_letter: str) -> int:
        """Get contract size for alert size letter (A, B, C)"""
        if not self.trading or not self.trading.size_mapping:
            return 1  # Default fallback
        return self.trading.size_mapping.get(size_letter.upper(), 1)
    
    def is_trading_enabled(self) -> bool:
        """Check if auto trading is enabled"""
        return self.trading and self.trading.enable_auto_trading
    
    def reload_config(self) -> bool:
        """Reload configuration from file"""
        return self.load_config() and self.validate_config()


# Global configuration instance
config = ConfigManager()
