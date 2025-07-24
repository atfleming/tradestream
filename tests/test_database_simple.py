"""
Simplified unit tests for Database module
Tests core database operations and data integrity
"""

import unittest
import tempfile
import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Add src to path for imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager class"""
    
    def setUp(self):
        """Set up test database"""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Initialize database
        self.db = DatabaseManager(self.db_path)
        self.db.initialize_database()
        
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_database_initialization(self):
        """Test database initialization and table creation"""
        # Check if database file exists
        self.assertTrue(os.path.exists(self.db_path))
        
        # Check if tables exist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check alerts table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'")
        self.assertIsNotNone(cursor.fetchone())
        
        # Check trades table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
        self.assertIsNotNone(cursor.fetchone())
        
        # Check positions table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='positions'")
        self.assertIsNotNone(cursor.fetchone())
        
        # Check performance table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='performance'")
        self.assertIsNotNone(cursor.fetchone())
        
        conn.close()
    
    def test_insert_alert_valid(self):
        """Test inserting valid alert"""
        alert_id = self.db.insert_alert(
            discord_message_id="msg_123",
            author="JMoney",
            channel_id=123456789,
            raw_content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            parsed_price=4500.0,
            parsed_size="B",
            parsed_stop=4490.0,
            target_1=4507.0,
            target_2=4512.0,
            is_valid=True
        )
        
        self.assertIsNotNone(alert_id)
        self.assertIsInstance(alert_id, int)
        self.assertGreater(alert_id, 0)
    
    def test_insert_alert_invalid(self):
        """Test inserting invalid alert"""
        alert_id = self.db.insert_alert(
            discord_message_id="msg_124",
            author="Someone",
            channel_id=123456789,
            raw_content="Invalid message",
            is_valid=False
        )
        
        self.assertIsNotNone(alert_id)
        self.assertIsInstance(alert_id, int)
    
    def test_get_alert_by_id(self):
        """Test retrieving alert by ID"""
        # Insert test alert
        alert_id = self.db.insert_alert(
            discord_message_id="msg_125",
            author="JMoney",
            channel_id=123456789,
            raw_content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            parsed_price=4500.0,
            parsed_size="B",
            parsed_stop=4490.0,
            target_1=4507.0,
            target_2=4512.0,
            is_valid=True
        )
        
        # Retrieve alert
        retrieved_alert = self.db.get_alert(alert_id)
        
        self.assertIsNotNone(retrieved_alert)
        self.assertEqual(retrieved_alert['raw_content'], "🚨 ES long 4500: B\nStop: 4490\n@everyone")
        self.assertEqual(retrieved_alert['author'], "JMoney")
        self.assertEqual(retrieved_alert['channel_id'], 123456789)
        self.assertEqual(retrieved_alert['parsed_price'], 4500.0)
        self.assertEqual(retrieved_alert['parsed_size'], "B")
    
    def test_get_nonexistent_alert(self):
        """Test retrieving non-existent alert"""
        result = self.db.get_alert(99999)
        self.assertIsNone(result)
    
    def test_insert_trade(self):
        """Test inserting trade"""
        # First insert an alert
        alert_id = self.db.insert_alert(
            discord_message_id="msg_126",
            author="JMoney",
            channel_id=123456789,
            raw_content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            parsed_price=4500.0,
            parsed_size="B",
            is_valid=True
        )
        
        # Insert trade
        trade_id = self.db.insert_trade(
            alert_id=alert_id,
            trade_type="LONG",
            symbol="MES",
            entry_price=4500.25,
            quantity=2,
            stop_loss=4490.0,
            target_1=4507.0,
            target_2=4512.0,
            order_id="order_123"
        )
        
        self.assertIsNotNone(trade_id)
        self.assertIsInstance(trade_id, int)
        self.assertGreater(trade_id, 0)
    
    def test_get_recent_alerts(self):
        """Test retrieving recent alerts"""
        # Insert multiple alerts
        alert_ids = []
        for i in range(5):
            alert_id = self.db.insert_alert(
                discord_message_id=f"msg_{i}",
                author="JMoney",
                channel_id=123456789,
                raw_content=f"🚨 ES long {4500 + i}: B\nStop: {4490 + i}\n@everyone",
                parsed_price=4500.0 + i,
                parsed_size="B",
                is_valid=True
            )
            alert_ids.append(alert_id)
        
        # Get recent alerts
        recent_alerts = self.db.get_recent_alerts(limit=3)
        
        self.assertEqual(len(recent_alerts), 3)
        # Should be in reverse chronological order (most recent first)
        self.assertGreater(recent_alerts[0]['id'], recent_alerts[1]['id'])
    
    def test_get_open_trades(self):
        """Test retrieving open trades"""
        # Insert alert and trade
        alert_id = self.db.insert_alert(
            discord_message_id="msg_127",
            author="JMoney",
            channel_id=123456789,
            raw_content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            is_valid=True
        )
        
        trade_id = self.db.insert_trade(
            alert_id=alert_id,
            trade_type="LONG",
            symbol="MES",
            entry_price=4500.0,
            quantity=2,
            order_id="order_124"
        )
        
        # Get open trades
        open_trades = self.db.get_open_trades()
        
        self.assertGreater(len(open_trades), 0)
        # Find our trade
        our_trade = next((t for t in open_trades if t['id'] == trade_id), None)
        self.assertIsNotNone(our_trade)
        self.assertEqual(our_trade['symbol'], "MES")
        self.assertEqual(our_trade['quantity'], 2)
    
    def test_system_stats(self):
        """Test retrieving system statistics"""
        # Insert some test data
        alert_id = self.db.insert_alert(
            discord_message_id="msg_128",
            author="JMoney",
            channel_id=123456789,
            raw_content="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            is_valid=True
        )
        
        self.db.insert_trade(
            alert_id=alert_id,
            trade_type="LONG",
            symbol="MES",
            entry_price=4500.0,
            quantity=2
        )
        
        # Get system stats
        stats = self.db.get_system_stats()
        
        self.assertIsNotNone(stats)
        self.assertIn('total_alerts', stats)
        self.assertIn('valid_alerts', stats)
        self.assertIn('total_trades', stats)
        self.assertGreater(stats['total_alerts'], 0)
        self.assertGreater(stats['valid_alerts'], 0)
        self.assertGreater(stats['total_trades'], 0)
    
    def test_log_system_event(self):
        """Test logging system events"""
        success = self.db.log_system_event(
            level="INFO",
            component="TEST",
            message="Test message",
            details="Test details"
        )
        
        self.assertTrue(success)
    
    def test_update_daily_performance(self):
        """Test updating daily performance"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        success = self.db.update_daily_performance(
            date=today,
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
            net_pnl=150.0,
            win_rate=0.6
        )
        
        self.assertTrue(success)
    
    def test_duplicate_discord_message_id(self):
        """Test handling duplicate Discord message IDs"""
        # Insert first alert
        alert_id1 = self.db.insert_alert(
            discord_message_id="duplicate_msg",
            author="JMoney",
            channel_id=123456789,
            raw_content="First message",
            is_valid=True
        )
        
        self.assertIsNotNone(alert_id1)
        
        # Try to insert duplicate - should fail or handle gracefully
        alert_id2 = self.db.insert_alert(
            discord_message_id="duplicate_msg",
            author="JMoney",
            channel_id=123456789,
            raw_content="Second message",
            is_valid=True
        )
        
        # Should return None due to unique constraint
        self.assertIsNone(alert_id2)
    
    def test_database_connection_context_manager(self):
        """Test database connection context manager"""
        # This tests the internal get_connection method
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alerts")
            count = cursor.fetchone()[0]
            self.assertIsInstance(count, int)


if __name__ == '__main__':
    unittest.main()
