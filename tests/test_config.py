"""
Unit Tests for Configuration System
Tests configuration loading, validation, and hot-reload functionality
"""

import unittest
import tempfile
import os
import yaml
import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config import ConfigManager, DiscordConfig, TradingConfig, EmailConfig


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_config_file = None
        
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_config_file and os.path.exists(self.temp_config_file):
            os.unlink(self.temp_config_file)
    
    def create_temp_config(self, config_data):
        """Create temporary config file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            self.temp_config_file = f.name
        return self.temp_config_file
    
    def test_load_valid_config(self):
        """Test loading valid configuration"""
        config_data = {
            'discord': {
                'token': 'test_token',
                'channel_id': 123456789,
                'target_author': 'JMoney'
            },
            'trading': {
                'account_id': 'test_account',
                'symbol': 'MES',
                'enable_auto_trading': False,
                'paper_trading_enabled': True,
                'live_trading_enabled': False,
                'size_mapping': {'A': 3, 'B': 2, 'C': 1}
            },
            'email': {
                'enabled': True,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': 'test@example.com',
                'from_address': 'test@example.com',
                'to_addresses': ['test@example.com']
            },
            'database': {
                'file_path': 'test.db'
            }
        }
        
        config_file = self.create_temp_config(config_data)
        config_manager = ConfigManager(config_file)
        
        self.assertTrue(config_manager.load_config())
        self.assertIsNotNone(config_manager.discord)
        self.assertIsNotNone(config_manager.trading)
        self.assertIsNotNone(config_manager.email)
        self.assertIsNotNone(config_manager.database)
    
    def test_load_missing_config_file(self):
        """Test loading missing configuration file"""
        config_manager = ConfigManager("nonexistent.yaml")
        self.assertFalse(config_manager.load_config())
    
    def test_validate_valid_config(self):
        """Test validation of valid configuration"""
        config_data = {
            'discord': {
                'token': 'test_token',
                'channel_id': 123456789,
                'target_author': 'JMoney'
            },
            'trading': {
                'account_id': 'test_account',
                'symbol': 'MES',
                'enable_auto_trading': False,
                'paper_trading_enabled': True,
                'live_trading_enabled': False,
                'size_mapping': {'A': 3, 'B': 2, 'C': 1}
            },
            'database': {
                'file_path': 'test.db'
            }
        }
        
        config_file = self.create_temp_config(config_data)
        config_manager = ConfigManager(config_file)
        config_manager.load_config()
        
        self.assertTrue(config_manager.validate_config())
    
    def test_validate_missing_discord_config(self):
        """Test validation with missing Discord configuration"""
        config_data = {
            'trading': {
                'symbol': 'MES',
                'enable_auto_trading': False
            },
            'database': {
                'file_path': 'test.db'
            }
        }
        
        config_file = self.create_temp_config(config_data)
        config_manager = ConfigManager(config_file)
        config_manager.load_config()
        
        self.assertFalse(config_manager.validate_config())
    
    def test_validate_missing_trading_config(self):
        """Test validation with missing trading configuration"""
        config_data = {
            'discord': {
                'token': 'test_token',
                'channel_id': 123456789,
                'target_author': 'JMoney'
            },
            'database': {
                'file_path': 'test.db'
            }
        }
        
        config_file = self.create_temp_config(config_data)
        config_manager = ConfigManager(config_file)
        config_manager.load_config()
        
        self.assertFalse(config_manager.validate_config())
    
    def test_validate_invalid_discord_channel_id(self):
        """Test validation with invalid Discord channel ID"""
        config_data = {
            'discord': {
                'token': 'test_token',
                'channel_id': 'invalid_id',
                'target_author': 'JMoney'
            },
            'trading': {
                'symbol': 'MES',
                'enable_auto_trading': False
            },
            'database': {
                'file_path': 'test.db'
            }
        }
        
        config_file = self.create_temp_config(config_data)
        config_manager = ConfigManager(config_file)
        config_manager.load_config()
        
        self.assertFalse(config_manager.validate_config())
    
    def test_environment_variable_override(self):
        """Test environment variable override"""
        config_data = {
            'discord': {
                'token': 'test_token',
                'channel_id': 123456789,
                'target_author': 'JMoney'
            },
            'trading': {
                'account_id': 'test_account',
                'symbol': 'MES',
                'enable_auto_trading': False
            },
            'database': {
                'file_path': 'test.db'
            }
        }
        
        # Set environment variable
        os.environ['DISCORD_TOKEN'] = 'env_token'
        
        try:
            config_file = self.create_temp_config(config_data)
            config_manager = ConfigManager(config_file)
            config_manager.load_config()
            
            # Environment variable should override config file
            self.assertEqual(config_manager.discord.token, 'env_token')
        finally:
            # Clean up environment variable
            if 'DISCORD_TOKEN' in os.environ:
                del os.environ['DISCORD_TOKEN']
    
    def test_size_mapping_validation(self):
        """Test size mapping validation"""
        config_data = {
            'discord': {
                'token': 'test_token',
                'channel_id': 123456789,
                'target_author': 'JMoney'
            },
            'trading': {
                'account_id': 'test_account',
                'symbol': 'MES',
                'enable_auto_trading': False,
                'size_mapping': {'A': 3, 'B': 2, 'C': 1}
            },
            'database': {
                'file_path': 'test.db'
            }
        }
        
        config_file = self.create_temp_config(config_data)
        config_manager = ConfigManager(config_file)
        config_manager.load_config()
        
        self.assertTrue(config_manager.validate_config())
        self.assertEqual(config_manager.trading.size_mapping['A'], 3)
        self.assertEqual(config_manager.trading.size_mapping['B'], 2)
        self.assertEqual(config_manager.trading.size_mapping['C'], 1)
    
    def test_invalid_size_mapping(self):
        """Test invalid size mapping"""
        config_data = {
            'discord': {
                'token': 'test_token',
                'channel_id': 123456789,
                'target_author': 'JMoney'
            },
            'trading': {
                'symbol': 'MES',
                'enable_auto_trading': False,
                'size_mapping': {'A': 3, 'B': 2}  # Missing C
            },
            'database': {
                'file_path': 'test.db'
            }
        }
        
        config_file = self.create_temp_config(config_data)
        config_manager = ConfigManager(config_file)
        config_manager.load_config()
        
        self.assertFalse(config_manager.validate_config())


class TestDiscordConfig(unittest.TestCase):
    """Test cases for DiscordConfig"""
    
    def test_discord_config_creation(self):
        """Test Discord configuration creation"""
        config = DiscordConfig(
            token="test_token",
            channel_id=123456789,
            target_author="JMoney"
        )
        
        self.assertEqual(config.token, "test_token")
        self.assertEqual(config.channel_id, 123456789)
        self.assertEqual(config.target_author, "JMoney")
    
    def test_discord_config_validation(self):
        """Test Discord configuration validation"""
        # Valid config
        config = DiscordConfig(
            token="test_token",
            channel_id=123456789,
            target_author="JMoney"
        )
        self.assertTrue(len(config.token) > 0)
        self.assertTrue(config.channel_id > 0)
        self.assertTrue(len(config.target_author) > 0)


class TestTradingConfig(unittest.TestCase):
    """Test cases for TradingConfig"""
    
    def test_trading_config_creation(self):
        """Test trading configuration creation"""
        config = TradingConfig(
            symbol="MES",
            enable_auto_trading=False,
            paper_trading_enabled=True,
            live_trading_enabled=False,
            size_mapping={'A': 3, 'B': 2, 'C': 1}
        )
        
        self.assertEqual(config.symbol, "MES")
        self.assertFalse(config.enable_auto_trading)
        self.assertTrue(config.paper_trading_enabled)
        self.assertFalse(config.live_trading_enabled)
        self.assertEqual(config.size_mapping['A'], 3)
    
    def test_trading_config_defaults(self):
        """Test trading configuration defaults"""
        config = TradingConfig()
        
        self.assertEqual(config.symbol, "MES")
        self.assertFalse(config.enable_auto_trading)
        self.assertTrue(config.paper_trading_enabled)
        self.assertFalse(config.live_trading_enabled)


class TestEmailConfig(unittest.TestCase):
    """Test cases for EmailConfig"""
    
    def test_email_config_creation(self):
        """Test email configuration creation"""
        config = EmailConfig(
            enabled=True,
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="test@example.com",
            from_address="test@example.com",
            to_addresses=["test@example.com"]
        )
        
        self.assertTrue(config.enabled)
        self.assertEqual(config.smtp_server, "smtp.gmail.com")
        self.assertEqual(config.smtp_port, 587)
        self.assertEqual(config.username, "test@example.com")
        self.assertEqual(config.from_address, "test@example.com")
        self.assertEqual(config.to_addresses, ["test@example.com"])
    
    def test_email_config_defaults(self):
        """Test email configuration defaults"""
        config = EmailConfig()
        
        self.assertTrue(config.enabled)  # Default is True in implementation
        self.assertEqual(config.smtp_server, "smtp.gmail.com")
        self.assertEqual(config.smtp_port, 587)
        self.assertEqual(config.username, "")
        self.assertEqual(config.from_address, "")
        self.assertEqual(config.to_addresses, [])


if __name__ == '__main__':
    unittest.main()
