"""
Simplified unit tests for Discord Monitor module
Tests core Discord message handling functionality
"""

import unittest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Add src to path for imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from discord_monitor import DiscordMonitor
from message_parser import ParsedAlert
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


class TestDiscordMonitorSimple(unittest.TestCase):
    """Simplified test cases for DiscordMonitor class"""
    
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
        
        # Mock the Discord client to avoid actual connection
        self.monitor.client = Mock()
        self.monitor.client.user = Mock()
        self.monitor.client.user.name = "TestBot"
        
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
        self.assertIsNotNone(self.monitor.on_valid_alert)
    
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
        self.assertEqual(recent_alerts[0]['parsed_price'], 4500.0)
        self.assertEqual(recent_alerts[0]['parsed_size'], "B")
        
        # Verify callback was called
        self.callback_mock.assert_called_once()
        
        # Verify statistics were updated
        self.assertEqual(self.monitor.stats['messages_processed'], 1)
        self.assertEqual(self.monitor.stats['valid_alerts'], 1)
        self.assertEqual(self.monitor.stats['invalid_alerts'], 0)
    
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
        
        # Verify statistics were updated
        self.assertEqual(self.monitor.stats['messages_processed'], 1)
        self.assertEqual(self.monitor.stats['valid_alerts'], 0)
        self.assertEqual(self.monitor.stats['invalid_alerts'], 1)
    
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
        
        # Statistics should not be updated
        self.assertEqual(self.monitor.stats['messages_processed'], 0)
    
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
        
        # Statistics should not be updated
        self.assertEqual(self.monitor.stats['messages_processed'], 0)
    
    async def test_handle_message_bot_message_ignored(self):
        """Test that bot's own messages are ignored"""
        message = MockDiscordMessage(
            content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            author_name="JMoney",
            channel_id=123456789,
            message_id="bot_msg"
        )
        
        # Set message author to be the bot itself
        message.author = self.monitor.client.user
        
        # Process the message
        await self.monitor._handle_message(message)
        
        # Should not be stored in database
        recent_alerts = self.db.get_recent_alerts(limit=10)
        self.assertEqual(len(recent_alerts), 0)
        
        # Callback should not be called
        self.callback_mock.assert_not_called()
        
        # Statistics should not be updated
        self.assertEqual(self.monitor.stats['messages_processed'], 0)
    
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
        
        # Callback is called for each valid alert, even if database insert fails
        # This is because parsing succeeds both times
        self.assertEqual(self.callback_mock.call_count, 2)
        
        # Statistics should show 2 processed messages and 2 valid alerts
        # (since parsing succeeds both times, even if DB insert fails)
        self.assertEqual(self.monitor.stats['messages_processed'], 2)
        self.assertEqual(self.monitor.stats['valid_alerts'], 2)
    
    async def test_callback_error_handling(self):
        """Test error handling in callback execution"""
        # Create a callback that raises an exception
        error_callback = AsyncMock(side_effect=Exception("Callback error"))
        
        # Create monitor with error callback
        error_monitor = DiscordMonitor(
            config=self.config_manager,
            db=self.db,
            on_valid_alert=error_callback
        )
        error_monitor.client = self.monitor.client  # Use same mock client
        
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
        
        # Statistics should be updated
        self.assertEqual(error_monitor.stats['messages_processed'], 1)
        self.assertEqual(error_monitor.stats['valid_alerts'], 1)
    
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
        
        # Verify statistics
        self.assertEqual(self.monitor.stats['messages_processed'], 3)
        self.assertEqual(self.monitor.stats['valid_alerts'], 3)
        self.assertEqual(self.monitor.stats['invalid_alerts'], 0)
    
    def test_monitor_without_callback(self):
        """Test monitor initialization without callback"""
        # Should work without callback
        monitor = DiscordMonitor(
            config=self.config_manager,
            db=self.db
        )
        
        self.assertIsNotNone(monitor)
        self.assertIsNone(monitor.on_valid_alert)
    
    async def test_monitor_without_callback_processing(self):
        """Test message processing without callback"""
        monitor = DiscordMonitor(
            config=self.config_manager,
            db=self.db
        )
        monitor.client = self.monitor.client  # Use same mock client
        
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
        
        # Statistics should be updated
        self.assertEqual(monitor.stats['messages_processed'], 1)
        self.assertEqual(monitor.stats['valid_alerts'], 1)
    
    def test_get_status(self):
        """Test status reporting"""
        status = self.monitor.get_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('is_running', status)
        self.assertIn('is_connected', status)
        self.assertIn('reconnect_attempts', status)
        self.assertIn('stats', status)
        self.assertIn('target_channel', status)
        self.assertIn('target_author', status)
        
        self.assertEqual(status['target_channel'], 123456789)
        self.assertEqual(status['target_author'], "JMoney")
    
    def test_reset_stats(self):
        """Test statistics reset"""
        # Set some stats
        self.monitor.stats['messages_processed'] = 10
        self.monitor.stats['valid_alerts'] = 5
        self.monitor.stats['invalid_alerts'] = 3
        
        # Reset stats
        self.monitor.reset_stats()
        
        # Verify reset
        self.assertEqual(self.monitor.stats['messages_processed'], 0)
        self.assertEqual(self.monitor.stats['valid_alerts'], 0)
        self.assertEqual(self.monitor.stats['invalid_alerts'], 0)
        self.assertEqual(self.monitor.stats['connection_errors'], 0)
        self.assertIsNone(self.monitor.stats['last_alert_time'])
    
    async def test_case_insensitive_author_matching(self):
        """Test case insensitive author matching"""
        message = MockDiscordMessage(
            content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            author_name="jmoney",  # lowercase
            channel_id=123456789,
            message_id="case_test_msg"
        )
        
        # Process the message
        await self.monitor._handle_message(message)
        
        # Should be processed successfully
        recent_alerts = self.db.get_recent_alerts(limit=1)
        self.assertEqual(len(recent_alerts), 1)
        self.assertTrue(recent_alerts[0]['is_valid'])
        
        # Callback should be called
        self.callback_mock.assert_called_once()


# Helper function to run async tests
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
for name in dir(TestDiscordMonitorSimple):
    if name.startswith('test_') and asyncio.iscoroutinefunction(getattr(TestDiscordMonitorSimple, name)):
        setattr(TestDiscordMonitorSimple, name, async_test(getattr(TestDiscordMonitorSimple, name)))


if __name__ == '__main__':
    unittest.main()
