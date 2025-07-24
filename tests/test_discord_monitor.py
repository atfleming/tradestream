"""
Unit tests for Discord Monitor module
Tests Discord message handling, parsing integration, and callback functionality
"""

import unittest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Add src to path for imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from discord_monitor import DiscordMonitor
from message_parser import JMoneyMessageParser, ParsedAlert
from database import DatabaseManager
from config import DiscordConfig, ConfigManager


class MockDiscordMessage:
    """Mock Discord message for testing"""
    def __init__(self, content, author_name="JMoney", channel_id=123456789, message_id="msg_123"):
        self.content = content
        self.author = Mock()
        self.author.name = author_name
        self.author.display_name = author_name
        self.channel = Mock()
        self.channel.id = channel_id
        self.id = message_id
        self.created_at = datetime.now()


class MockDiscordClient:
    """Mock Discord client for testing"""
    def __init__(self):
        self.user = Mock()
        self.user.name = "TestBot"
        self.is_ready_flag = False
        
    def is_ready(self):
        return self.is_ready_flag
        
    async def start(self, token):
        self.is_ready_flag = True
        
    async def close(self):
        self.is_ready_flag = False


class TestDiscordMonitor(unittest.TestCase):
    """Test cases for DiscordMonitor class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Initialize database
        self.db = DatabaseManager(self.db_path)
        self.db.initialize_database()
        
        # Create test configuration manager
        self.config_manager = ConfigManager()
        self.config_manager.discord = DiscordConfig(
            token="test_token",
            channel_id=123456789,
            target_author="JMoney"
        )
        
        # Create callback mock
        self.callback_mock = AsyncMock()
        
        # Initialize Discord monitor
        self.monitor = DiscordMonitor(
            config=self.config_manager,
            db=self.db,
            on_valid_alert=self.callback_mock
        )
        
        # Mock the Discord client
        self.monitor.client = MockDiscordClient()
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_discord_monitor_initialization(self):
        """Test Discord monitor initialization"""
        self.assertIsNotNone(self.monitor.config)
        self.assertIsNotNone(self.monitor.db)
        self.assertIsNotNone(self.monitor.parser)
        self.assertEqual(self.monitor.config.discord.channel_id, 123456789)
        self.assertEqual(self.monitor.config.discord.target_author, "JMoney")
    
    def test_is_target_author_valid(self):
        """Test target author validation"""
        # Test valid author
        valid_message = MockDiscordMessage("Test message", author_name="JMoney")
        self.assertTrue(self.monitor._is_target_author(valid_message))
        
        # Test invalid author
        invalid_message = MockDiscordMessage("Test message", author_name="SomeoneElse")
        self.assertFalse(self.monitor._is_target_author(invalid_message))
        
        # Test case insensitive matching
        case_message = MockDiscordMessage("Test message", author_name="jmoney")
        self.assertTrue(self.monitor._is_target_author(case_message))
    
    def test_is_target_channel_valid(self):
        """Test target channel validation"""
        # Test valid channel
        valid_message = MockDiscordMessage("Test message", channel_id=123456789)
        self.assertTrue(self.monitor._is_target_channel(valid_message))
        
        # Test invalid channel
        invalid_message = MockDiscordMessage("Test message", channel_id=987654321)
        self.assertFalse(self.monitor._is_target_channel(invalid_message))
    
    def test_should_process_message_valid(self):
        """Test message processing criteria - valid message"""
        # Create valid message
        message = MockDiscordMessage(
            content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            author_name="JMoney",
            channel_id=123456789
        )
        
        self.assertTrue(self.monitor._should_process_message(message))
    
    def test_should_process_message_wrong_author(self):
        """Test message processing criteria - wrong author"""
        message = MockDiscordMessage(
            content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            author_name="WrongAuthor",
            channel_id=123456789
        )
        
        self.assertFalse(self.monitor._should_process_message(message))
    
    def test_should_process_message_wrong_channel(self):
        """Test message processing criteria - wrong channel"""
        message = MockDiscordMessage(
            content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            author_name="JMoney",
            channel_id=999999999
        )
        
        self.assertFalse(self.monitor._should_process_message(message))
    
    def test_should_process_message_bot_message(self):
        """Test message processing criteria - bot's own message"""
        message = MockDiscordMessage(
            content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            author_name="TestBot",
            channel_id=123456789
        )
        
        # Mock the bot user
        message.author = self.monitor.client.user
        
        self.assertFalse(self.monitor._should_process_message(message))
    
    async def test_handle_message_valid_alert(self):
        """Test handling valid alert message"""
        message = MockDiscordMessage(
            content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            author_name="JMoney",
            channel_id=123456789,
            message_id="valid_msg_123"
        )
        
        # Process the message
        await self.monitor._handle_message(message)
        
        # Verify alert was stored in database
        recent_alerts = self.db.get_recent_alerts(limit=1)
        self.assertEqual(len(recent_alerts), 1)
        self.assertEqual(recent_alerts[0]['raw_content'], message.content)
        self.assertEqual(recent_alerts[0]['author'], "JMoney")
        self.assertTrue(recent_alerts[0]['is_valid'])
        
        # Verify callback was called
        self.callback_mock.assert_called_once()
        
        # Verify callback was called with correct data
        call_args = self.callback_mock.call_args[0]
        parsed_alert = call_args[0]
        message_data = call_args[1]
        
        self.assertIsInstance(parsed_alert, ParsedAlert)
        self.assertTrue(parsed_alert.is_valid)
        self.assertEqual(parsed_alert.price, 4500.0)
        self.assertEqual(parsed_alert.size, "B")
        self.assertEqual(message_data['author'], "JMoney")
    
    async def test_handle_message_invalid_alert(self):
        """Test handling invalid alert message"""
        message = MockDiscordMessage(
            content="Just a regular message",
            author_name="JMoney",
            channel_id=123456789,
            message_id="invalid_msg_123"
        )
        
        # Process the message
        await self.monitor._handle_message(message)
        
        # Verify alert was stored in database but marked invalid
        recent_alerts = self.db.get_recent_alerts(limit=1)
        self.assertEqual(len(recent_alerts), 1)
        self.assertEqual(recent_alerts[0]['raw_content'], message.content)
        self.assertFalse(recent_alerts[0]['is_valid'])
        
        # Verify callback was NOT called for invalid alert
        self.callback_mock.assert_not_called()
    
    async def test_handle_message_duplicate_prevention(self):
        """Test duplicate message handling"""
        message = MockDiscordMessage(
            content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            author_name="JMoney",
            channel_id=123456789,
            message_id="duplicate_msg"
        )
        
        # Process the message twice
        await self.monitor._handle_message(message)
        await self.monitor._handle_message(message)
        
        # Should only have one alert in database due to unique constraint
        recent_alerts = self.db.get_recent_alerts(limit=10)
        duplicate_alerts = [a for a in recent_alerts if a['discord_message_id'] == "duplicate_msg"]
        self.assertEqual(len(duplicate_alerts), 1)
        
        # Callback should only be called once
        self.assertEqual(self.callback_mock.call_count, 1)
    
    async def test_handle_message_wrong_channel_ignored(self):
        """Test that messages from wrong channel are ignored"""
        message = MockDiscordMessage(
            content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            author_name="JMoney",
            channel_id=999999999,  # Wrong channel
            message_id="wrong_channel_msg"
        )
        
        # Process the message
        await self.monitor._handle_message(message)
        
        # Should not be stored in database
        recent_alerts = self.db.get_recent_alerts(limit=10)
        self.assertEqual(len(recent_alerts), 0)
        
        # Callback should not be called
        self.callback_mock.assert_not_called()
    
    async def test_handle_message_wrong_author_ignored(self):
        """Test that messages from wrong author are ignored"""
        message = MockDiscordMessage(
            content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            author_name="WrongAuthor",  # Wrong author
            channel_id=123456789,
            message_id="wrong_author_msg"
        )
        
        # Process the message
        await self.monitor._handle_message(message)
        
        # Should not be stored in database
        recent_alerts = self.db.get_recent_alerts(limit=10)
        self.assertEqual(len(recent_alerts), 0)
        
        # Callback should not be called
        self.callback_mock.assert_not_called()
    
    async def test_callback_error_handling(self):
        """Test error handling in callback execution"""
        # Create a callback that raises an exception
        error_callback = AsyncMock(side_effect=Exception("Callback error"))
        
        # Create monitor with error callback
        error_monitor = DiscordMonitor(
            config=self.config,
            db=self.db,
            parser=self.parser,
            on_valid_alert=error_callback
        )
        
        message = MockDiscordMessage(
            content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            author_name="JMoney",
            channel_id=123456789,
            message_id="error_test_msg"
        )
        
        # Process the message - should not raise exception
        await error_monitor._handle_message(message)
        
        # Alert should still be stored despite callback error
        recent_alerts = self.db.get_recent_alerts(limit=1)
        self.assertEqual(len(recent_alerts), 1)
        self.assertTrue(recent_alerts[0]['is_valid'])
        
        # Callback should have been attempted
        error_callback.assert_called_once()
    
    def test_message_data_extraction(self):
        """Test extraction of message data"""
        message = MockDiscordMessage(
            content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            author_name="JMoney",
            channel_id=123456789,
            message_id="data_test_msg"
        )
        
        message_data = self.monitor._extract_message_data(message)
        
        self.assertEqual(message_data['author'], "JMoney")
        self.assertEqual(message_data['channel_id'], 123456789)
        self.assertEqual(message_data['message_id'], "data_test_msg")
        self.assertEqual(message_data['content'], message.content)
        self.assertIn('timestamp', message_data)
    
    async def test_multiple_valid_alerts_processing(self):
        """Test processing multiple valid alerts"""
        messages = [
            MockDiscordMessage(
                content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
                message_id="msg_1"
            ),
            MockDiscordMessage(
                content="🚨 ES long 4510: A\nStop: 4500\n@everyone",
                message_id="msg_2"
            ),
            MockDiscordMessage(
                content="🚨 ES long 4520: C\nStop: 4510\n@everyone",
                message_id="msg_3"
            )
        ]
        
        # Process all messages
        for message in messages:
            await self.monitor._handle_message(message)
        
        # Verify all alerts were stored
        recent_alerts = self.db.get_recent_alerts(limit=10)
        self.assertEqual(len(recent_alerts), 3)
        
        # Verify all were valid
        valid_alerts = [a for a in recent_alerts if a['is_valid']]
        self.assertEqual(len(valid_alerts), 3)
        
        # Verify callback was called for each
        self.assertEqual(self.callback_mock.call_count, 3)
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Test with invalid config (missing token)
        invalid_config = DiscordConfig(
            token="",
            channel_id=123456789,
            target_author="JMoney"
        )
        
        with self.assertRaises(ValueError):
            DiscordMonitor(
                config=invalid_config,
                db=self.db,
                parser=self.parser,
                on_valid_alert=self.callback_mock
            )
    
    def test_monitor_without_callback(self):
        """Test monitor initialization without callback"""
        # Should work without callback
        monitor = DiscordMonitor(
            config=self.config,
            db=self.db,
            parser=self.parser
        )
        
        self.assertIsNotNone(monitor)
        self.assertIsNone(monitor.on_valid_alert)
    
    async def test_monitor_without_callback_processing(self):
        """Test message processing without callback"""
        monitor = DiscordMonitor(
            config=self.config,
            db=self.db,
            parser=self.parser
        )
        
        message = MockDiscordMessage(
            content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            author_name="JMoney",
            channel_id=123456789,
            message_id="no_callback_msg"
        )
        
        # Should process without error even without callback
        await monitor._handle_message(message)
        
        # Alert should still be stored
        recent_alerts = self.db.get_recent_alerts(limit=1)
        self.assertEqual(len(recent_alerts), 1)
        self.assertTrue(recent_alerts[0]['is_valid'])


class TestDiscordMonitorIntegration(unittest.TestCase):
    """Integration tests for Discord Monitor with real components"""
    
    def setUp(self):
        """Set up integration test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Initialize real components
        self.db = DatabaseManager(self.db_path)
        self.db.initialize_database()
        self.parser = JMoneyMessageParser()
        
        self.config = DiscordConfig(
            token="test_token",
            channel_id=123456789,
            target_author="JMoney"
        )
        
        # Track alerts received
        self.received_alerts = []
        
        async def alert_handler(parsed_alert, message_data):
            self.received_alerts.append((parsed_alert, message_data))
        
        self.monitor = DiscordMonitor(
            config=self.config,
            db=self.db,
            parser=self.parser,
            on_valid_alert=alert_handler
        )
        
    def tearDown(self):
        """Clean up integration test environment"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    async def test_end_to_end_alert_processing(self):
        """Test complete alert processing flow"""
        # Create a realistic JMoney alert
        message = MockDiscordMessage(
            content="🚨 ES long 6326: A\nStop: 6316\n@everyone",
            author_name="JMoney",
            channel_id=123456789,
            message_id="e2e_test_msg"
        )
        
        # Process the message
        await self.monitor._handle_message(message)
        
        # Verify database storage
        recent_alerts = self.db.get_recent_alerts(limit=1)
        self.assertEqual(len(recent_alerts), 1)
        
        alert = recent_alerts[0]
        self.assertTrue(alert['is_valid'])
        self.assertEqual(alert['parsed_price'], 6326.0)
        self.assertEqual(alert['parsed_size'], 'A')
        self.assertEqual(alert['parsed_stop'], 6316.0)
        self.assertEqual(alert['target_1'], 6333.0)  # 6326 + 7
        self.assertEqual(alert['target_2'], 6338.0)  # 6326 + 12
        
        # Verify callback was called
        self.assertEqual(len(self.received_alerts), 1)
        
        parsed_alert, message_data = self.received_alerts[0]
        self.assertTrue(parsed_alert.is_valid)
        self.assertEqual(parsed_alert.price, 6326.0)
        self.assertEqual(parsed_alert.size, 'A')
        self.assertEqual(message_data['author'], 'JMoney')


if __name__ == '__main__':
    # Run async tests
    def async_test(coro):
        def wrapper(self):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro(self))
            finally:
                loop.close()
        return wrapper
    
    # Apply async_test decorator to async test methods
    for name in dir(TestDiscordMonitor):
        if name.startswith('test_') and asyncio.iscoroutinefunction(getattr(TestDiscordMonitor, name)):
            setattr(TestDiscordMonitor, name, async_test(getattr(TestDiscordMonitor, name)))
    
    for name in dir(TestDiscordMonitorIntegration):
        if name.startswith('test_') and asyncio.iscoroutinefunction(getattr(TestDiscordMonitorIntegration, name)):
            setattr(TestDiscordMonitorIntegration, name, async_test(getattr(TestDiscordMonitorIntegration, name)))
    
    unittest.main()
