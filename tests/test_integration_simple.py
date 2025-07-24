"""
Simplified Integration Tests for JMoney Discord Trading Bot

Tests core component interactions and data flows using the actual API structure.
Focus on key integration patterns without complex mocking.
"""

import unittest
import tempfile
import shutil
import sqlite3
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import components for integration testing
from config import ConfigManager
from message_parser import JMoneyMessageParser, ParsedAlert
from database import DatabaseManager


class TestMessageParsingIntegration(unittest.TestCase):
    """Test message parsing integration with database storage"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test files
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Initialize components
        self.database = DatabaseManager(str(self.test_dir / "test_integration.db"))
        self.database.initialize_database()
        self.message_parser = JMoneyMessageParser()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_parse_and_store_alert_workflow(self):
        """Test complete workflow from message parsing to database storage"""
        # Test message that should trigger alert parsing
        test_message = "🚨 ES long 4500: C\nStop: 4495\n@everyone"
        
        # Step 1: Parse message
        alert = self.message_parser.parse_message(test_message)
        
        # Verify alert was parsed correctly
        self.assertIsNotNone(alert)
        self.assertTrue(alert.is_valid)
        self.assertEqual(alert.price, 4500)
        self.assertEqual(alert.size, "C")
        self.assertEqual(alert.stop, 4495)
        
        # Step 2: Store alert in database
        alert_id = self.database.insert_alert(
            discord_message_id="test_msg_123",
            author="JMoney",
            channel_id=123456789,
            raw_content=test_message,
            parsed_price=alert.price,
            parsed_size=alert.size,
            parsed_stop=alert.stop,
            target_1=alert.target_1,
            target_2=alert.target_2,
            is_valid=True
        )
        
        # Verify alert was stored
        self.assertIsNotNone(alert_id)
        
        # Step 3: Retrieve and verify stored alert
        stored_alerts = self.database.get_recent_alerts(limit=1)
        self.assertEqual(len(stored_alerts), 1)
        
        stored_alert = stored_alerts[0]
        self.assertEqual(stored_alert['parsed_price'], 4500)
        self.assertEqual(stored_alert['parsed_size'], "C")
        self.assertEqual(stored_alert['parsed_stop'], 4495)
        self.assertEqual(stored_alert['target_1'], alert.target_1)
        self.assertEqual(stored_alert['target_2'], alert.target_2)
    
    def test_multiple_alerts_processing(self):
        """Test processing multiple alerts in sequence"""
        test_messages = [
            "🚨 ES long 4500: C\nStop: 4495\n@everyone",
            "🚨 NQ short 15000: B\nStop: 15020\n@everyone",
            "🚨 ES long 4510: A\nStop: 4505\n@everyone"
        ]
        
        alert_ids = []
        
        for i, message in enumerate(test_messages):
            # Parse message
            alert = self.message_parser.parse_message(message)
            self.assertIsNotNone(alert)
            
            # Store in database
            alert_id = self.database.insert_alert(
                discord_message_id=f"test_msg_{i}",
                author="JMoney",
                channel_id=123456789,
                raw_content=message,
                parsed_price=alert.price,
                parsed_size=alert.size,
                parsed_stop=alert.stop,
                target_1=alert.target_1,
                target_2=alert.target_2,
                is_valid=True
            )
            alert_ids.append(alert_id)
        
        # Verify all alerts were stored
        self.assertEqual(len(alert_ids), 3)
        
        # Retrieve all alerts
        stored_alerts = self.database.get_recent_alerts(limit=10)
        self.assertEqual(len(stored_alerts), 3)
        
        # Verify alert details
        symbols = [alert['raw_content'].split()[1] for alert in stored_alerts]
        self.assertIn("ES", symbols)
        self.assertIn("NQ", symbols)
    
    def test_invalid_message_handling(self):
        """Test handling of invalid messages"""
        invalid_messages = [
            "Just a regular chat message",
            "ES is looking good today",
            "🚨 Invalid format message",
            "ES long but no price",
            ""
        ]
        
        for message in invalid_messages:
            alert = self.message_parser.parse_message(message)
            self.assertFalse(alert.is_valid, f"Should not parse invalid message: {message}")
        
        # Verify no invalid alerts were stored
        stored_alerts = self.database.get_recent_alerts(limit=10)
        self.assertEqual(len(stored_alerts), 0)


class TestConfigurationIntegration(unittest.TestCase):
    """Test configuration integration across components"""
    
    def setUp(self):
        """Set up configuration test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Create test configuration
        self.config_data = {
            "trading": {
                "account_id": "test_account",
                "paper_trading_enabled": True,
                "size_mapping": {"A": 3, "B": 2, "C": 1},
                "max_daily_trades": 10,
                "max_position_size": 5
            },
            "database": {
                "file_path": str(self.test_dir / "test_config.db")
            },
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "test@example.com",
                "password": "test_password",
                "from_address": "test@example.com",
                "to_addresses": ["recipient@example.com"]
            },
            "discord": {
                "token": "test_token",
                "channel_id": 123456789,
                "target_author": "JMoney"
            }
        }
        
        self.config_file = self.test_dir / "config.yaml"
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config_data, f)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_configuration_loading_and_validation(self):
        """Test configuration loading and validation"""
        # Create config manager
        config_manager = ConfigManager(str(self.config_file))
        
        # Load configuration
        load_result = config_manager.load_config()
        self.assertTrue(load_result)
        
        # Verify configuration was loaded correctly
        self.assertIsNotNone(config_manager.trading)
        self.assertIsNotNone(config_manager.database)
        self.assertIsNotNone(config_manager.email)
        self.assertIsNotNone(config_manager.discord)
        
        # Verify specific values
        self.assertEqual(config_manager.trading.account_id, "test_account")
        self.assertTrue(config_manager.trading.paper_trading_enabled)
        self.assertEqual(config_manager.trading.size_mapping["C"], 1)
        
        # Test size mapping functionality
        self.assertEqual(config_manager.get_size_for_alert("A"), 3)
        self.assertEqual(config_manager.get_size_for_alert("B"), 2)
        self.assertEqual(config_manager.get_size_for_alert("C"), 1)
        self.assertEqual(config_manager.get_size_for_alert("D"), 1)  # Default fallback
    
    def test_configuration_validation_errors(self):
        """Test configuration validation with invalid data"""
        # Create invalid configuration
        invalid_config_data = self.config_data.copy()
        invalid_config_data['discord']['token'] = ""  # Invalid empty token
        
        invalid_config_file = self.test_dir / "invalid_config.yaml"
        with open(invalid_config_file, 'w') as f:
            yaml.dump(invalid_config_data, f)
        
        # Create config manager with invalid config
        config_manager = ConfigManager(str(invalid_config_file))
        config_manager.load_config()
        
        # Validation should fail
        validation_result = config_manager.validate_config()
        self.assertFalse(validation_result)


class TestDatabaseIntegration(unittest.TestCase):
    """Test database integration with multiple components"""
    
    def setUp(self):
        """Set up database integration test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.database = DatabaseManager(str(self.test_dir / "test_db_integration.db"))
        self.database.initialize_database()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_database_operations_consistency(self):
        """Test database operations consistency across different data types"""
        # Insert alert
        alert_id = self.database.insert_alert(
            discord_message_id="test_alert_123",
            author="JMoney",
            channel_id=123456789,
            raw_content="🚨 ES long 4500: C\nStop: 4495\n@everyone",
            parsed_price=4500,
            parsed_size="C",
            parsed_stop=4495,
            target_1=4507,
            target_2=4512,
            is_valid=True
        )
        
        # Insert trade related to alert
        trade_id = self.database.insert_trade(
            alert_id=alert_id,
            trade_type="LONG",
            symbol="ES",
            entry_price=4500,
            quantity=1,
            stop_loss=4495,
            target_1=4507,
            target_2=4512,
            order_id="test_order_123"
        )
        
        # Log system event
        log_result = self.database.log_system_event(
            level="INFO",
            component="test_integration",
            message="Test trade executed",
            details="Integration test trade execution",
            alert_id=alert_id,
            trade_id=trade_id
        )
        
        # Verify all operations succeeded
        self.assertIsNotNone(alert_id)
        self.assertIsNotNone(trade_id)
        self.assertTrue(log_result)
        
        # Verify data relationships
        alert = self.database.get_alert(alert_id)
        self.assertIsNotNone(alert)
        self.assertEqual(alert['parsed_price'], 4500)
        
        # Verify system stats
        stats = self.database.get_system_stats()
        self.assertEqual(stats['total_alerts'], 1)
        self.assertEqual(stats['valid_alerts'], 1)
        self.assertEqual(stats['total_trades'], 1)
    
    def test_concurrent_database_operations(self):
        """Test database handling of concurrent operations"""
        # Simulate multiple alerts being processed simultaneously
        alerts_data = [
            ("msg_1", "🚨 ES long 4500: C\nStop: 4495\n@everyone", 4500, "C"),
            ("msg_2", "🚨 NQ short 15000: B\nStop: 15020\n@everyone", 15000, "B"),
            ("msg_3", "🚨 ES long 4510: A\nStop: 4505\n@everyone", 4510, "A")
        ]
        
        alert_ids = []
        for msg_id, content, price, size in alerts_data:
            alert_id = self.database.insert_alert(
                discord_message_id=msg_id,
                author="JMoney",
                channel_id=123456789,
                raw_content=content,
                parsed_price=price,
                parsed_size=size,
                parsed_stop=price - 5 if "long" in content else price + 20,
                is_valid=True
            )
            alert_ids.append(alert_id)
        
        # Verify all alerts were stored correctly
        self.assertEqual(len(alert_ids), 3)
        self.assertTrue(all(aid is not None for aid in alert_ids))
        
        # Verify database consistency
        recent_alerts = self.database.get_recent_alerts(limit=10)
        self.assertEqual(len(recent_alerts), 3)
        
        # Verify unique message IDs
        message_ids = [alert['discord_message_id'] for alert in recent_alerts]
        self.assertEqual(len(set(message_ids)), 3)  # All unique


class TestComponentInteractionPatterns(unittest.TestCase):
    """Test common component interaction patterns"""
    
    def setUp(self):
        """Set up component interaction test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Initialize core components
        self.database = DatabaseManager(str(self.test_dir / "test_interactions.db"))
        self.database.initialize_database()
        self.message_parser = JMoneyMessageParser()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_alert_processing_pipeline(self):
        """Test complete alert processing pipeline"""
        # Step 1: Raw message input
        raw_message = "🚨 ES long 4500: C\nStop: 4495\n@everyone"
        
        # Step 2: Message parsing
        alert = self.message_parser.parse_message(raw_message)
        self.assertIsNotNone(alert)
        
        # Step 3: Database storage
        alert_id = self.database.insert_alert(
            discord_message_id="pipeline_test_123",
            author="JMoney",
            channel_id=123456789,
            raw_content=raw_message,
            parsed_price=alert.price,
            parsed_size=alert.size,
            parsed_stop=alert.stop,
            target_1=alert.target_1,
            target_2=alert.target_2,
            is_valid=True
        )
        
        # Step 4: Verify pipeline integrity
        self.assertIsNotNone(alert_id)
        
        # Retrieve and verify data consistency
        stored_alert = self.database.get_alert(alert_id)
        self.assertEqual(stored_alert['parsed_price'], alert.price)
        self.assertEqual(stored_alert['parsed_size'], alert.size)
        self.assertEqual(stored_alert['target_1'], alert.target_1)
        self.assertEqual(stored_alert['target_2'], alert.target_2)
        
        # Step 5: System logging
        log_result = self.database.log_system_event(
            level="INFO",
            component="alert_pipeline",
            message="Alert processed successfully",
            alert_id=alert_id
        )
        self.assertTrue(log_result)
    
    def test_error_handling_integration(self):
        """Test error handling across component boundaries"""
        # Test invalid message parsing
        invalid_message = "Invalid message format"
        alert = self.message_parser.parse_message(invalid_message)
        self.assertFalse(alert.is_valid)
        
        # Test database error handling with invalid data
        try:
            # Attempt to insert alert with missing required fields
            alert_id = self.database.insert_alert(
                discord_message_id="",  # Invalid empty ID
                author="",  # Invalid empty author
                channel_id=0,  # Invalid channel ID
                raw_content="",  # Invalid empty content
            )
            # Should handle gracefully and return None or raise handled exception
        except Exception as e:
            # Error should be handled gracefully
            self.assertIsInstance(e, (ValueError, sqlite3.Error))
        
        # Verify system remains stable after errors
        stats = self.database.get_system_stats()
        self.assertIsInstance(stats, dict)


if __name__ == '__main__':
    # Run integration tests
    unittest.main(verbosity=2)
