"""
Unit tests for Database module
Tests database operations, data integrity, and alert/trade storage
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
from message_parser import ParsedAlert


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
        alert = ParsedAlert(
            is_valid=False,
            raw_message="Invalid message",
            error_message="Not an ES LONG alert"
        )
        
        alert_id = self.db.insert_alert(
            raw_message=alert.raw_message,
            parsed_data=alert.to_dict(),
            author="Someone",
            channel_id=123456789
        )
        
        self.assertIsNotNone(alert_id)
        self.assertIsInstance(alert_id, int)
    
    def test_get_alert_by_id(self):
        """Test retrieving alert by ID"""
        # Insert test alert
        alert = ParsedAlert(
            is_valid=True,
            raw_message="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            price=4500.0,
            size="B",
            stop=4490.0,
            target_1=4507.0,
            target_2=4512.0
        )
        
        alert_id = self.db.insert_alert(
            raw_message=alert.raw_message,
            parsed_data=alert.to_dict(),
            author="JMoney",
            channel_id=123456789
        )
        
        # Retrieve alert
        retrieved_alert = self.db.get_alert_by_id(alert_id)
        
        self.assertIsNotNone(retrieved_alert)
        self.assertEqual(retrieved_alert['raw_message'], alert.raw_message)
        self.assertEqual(retrieved_alert['author'], "JMoney")
        self.assertEqual(retrieved_alert['channel_id'], 123456789)
    
    def test_get_nonexistent_alert(self):
        """Test retrieving non-existent alert"""
        result = self.db.get_alert_by_id(99999)
        self.assertIsNone(result)
    
    def test_insert_trade_execution(self):
        """Test inserting trade execution"""
        # First insert an alert
        alert_id = self.db.insert_alert(
            raw_message="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            parsed_data={"price": 4500.0, "size": "B"},
            author="JMoney",
            channel_id=123456789
        )
        
        # Insert trade execution
        trade_id = self.db.insert_trade_execution(
            alert_id=alert_id,
            action="BUY",
            symbol="MES",
            quantity=2,
            price=4500.25,
            order_type="MARKET",
            is_paper_trade=True
        )
        
        self.assertIsNotNone(trade_id)
        self.assertIsInstance(trade_id, int)
        self.assertGreater(trade_id, 0)
    
    def test_update_trade_status(self):
        """Test updating trade status"""
        # Insert alert and trade
        alert_id = self.db.insert_alert(
            raw_message="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            parsed_data={"price": 4500.0, "size": "B"},
            author="JMoney",
            channel_id=123456789
        )
        
        trade_id = self.db.insert_trade_execution(
            alert_id=alert_id,
            action="BUY",
            symbol="MES",
            quantity=2,
            price=4500.25,
            order_type="MARKET",
            is_paper_trade=True
        )
        
        # Update trade status
        success = self.db.update_trade_status(
            trade_id=trade_id,
            status="FILLED",
            fill_price=4500.50,
            fill_quantity=2,
            pnl=0.50
        )
        
        self.assertTrue(success)
    
    def test_get_recent_alerts(self):
        """Test retrieving recent alerts"""
        # Insert multiple alerts
        for i in range(5):
            self.db.insert_alert(
                raw_message=f"🚨 ES long {4500 + i}: B\nStop: {4490 + i}\n@everyone",
                parsed_data={"price": 4500.0 + i, "size": "B"},
                author="JMoney",
                channel_id=123456789
            )
        
        # Get recent alerts
        recent_alerts = self.db.get_recent_alerts(limit=3)
        
        self.assertEqual(len(recent_alerts), 3)
        # Should be in reverse chronological order (most recent first)
        self.assertGreater(recent_alerts[0]['timestamp'], recent_alerts[1]['timestamp'])
    
    def test_get_trades_for_alert(self):
        """Test retrieving trades for specific alert"""
        # Insert alert
        alert_id = self.db.insert_alert(
            raw_message="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            parsed_data={"price": 4500.0, "size": "B"},
            author="JMoney",
            channel_id=123456789
        )
        
        # Insert multiple trades for this alert
        trade_ids = []
        for i in range(3):
            trade_id = self.db.insert_trade_execution(
                alert_id=alert_id,
                action="BUY" if i == 0 else "SELL",
                symbol="MES",
                quantity=1,
                price=4500.0 + i,
                order_type="MARKET",
                is_paper_trade=True
            )
            trade_ids.append(trade_id)
        
        # Get trades for alert
        trades = self.db.get_trades_for_alert(alert_id)
        
        self.assertEqual(len(trades), 3)
        # Verify all trades belong to the correct alert
        for trade in trades:
            self.assertEqual(trade['alert_id'], alert_id)
    
    def test_get_daily_summary(self):
        """Test retrieving daily summary"""
        # Insert some test data
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Insert alerts and trades
        alert_id = self.db.insert_alert(
            raw_message="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            parsed_data={"price": 4500.0, "size": "B"},
            author="JMoney",
            channel_id=123456789
        )
        
        self.db.insert_trade_execution(
            alert_id=alert_id,
            action="BUY",
            symbol="MES",
            quantity=2,
            price=4500.0,
            order_type="MARKET",
            is_paper_trade=True
        )
        
        # Get daily summary
        summary = self.db.get_daily_summary(today)
        
        self.assertIsNotNone(summary)
        self.assertIn('total_alerts', summary)
        self.assertIn('total_trades', summary)
        self.assertEqual(summary['total_alerts'], 1)
        self.assertEqual(summary['total_trades'], 1)
    
    def test_database_backup_and_restore(self):
        """Test database backup functionality"""
        # Insert some test data
        alert_id = self.db.insert_alert(
            raw_message="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            parsed_data={"price": 4500.0, "size": "B"},
            author="JMoney",
            channel_id=123456789
        )
        
        # Create backup
        backup_path = self.db_path + ".backup"
        success = self.db.backup_database(backup_path)
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(backup_path))
        
        # Verify backup contains data
        backup_db = TradingDatabase(backup_path)
        retrieved_alert = backup_db.get_alert_by_id(alert_id)
        self.assertIsNotNone(retrieved_alert)
        backup_db.close()
        
        # Clean up backup
        os.unlink(backup_path)
    
    def test_database_connection_handling(self):
        """Test database connection handling"""
        # Test that database can be reopened after closing
        self.db.close()
        
        # Reopen database
        self.db = TradingDatabase(self.db_path)
        
        # Should still be able to insert data
        alert_id = self.db.insert_alert(
            raw_message="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            parsed_data={"price": 4500.0, "size": "B"},
            author="JMoney",
            channel_id=123456789
        )
        
        self.assertIsNotNone(alert_id)
    
    def test_data_integrity_constraints(self):
        """Test database constraints and data integrity"""
        # Test that we can't insert trade without valid alert_id
        with self.assertRaises(Exception):
            self.db.insert_trade_execution(
                alert_id=99999,  # Non-existent alert ID
                action="BUY",
                symbol="MES",
                quantity=1,
                price=4500.0,
                order_type="MARKET",
                is_paper_trade=True
            )
    
    def test_concurrent_access(self):
        """Test concurrent database access"""
        # Create second database connection
        db2 = TradingDatabase(self.db_path)
        
        # Insert from first connection
        alert_id1 = self.db.insert_alert(
            raw_message="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            parsed_data={"price": 4500.0, "size": "B"},
            author="JMoney",
            channel_id=123456789
        )
        
        # Insert from second connection
        alert_id2 = db2.insert_alert(
            raw_message="🚨 ES long 4501: A\nStop: 4491\n@everyone",
            parsed_data={"price": 4501.0, "size": "A"},
            author="JMoney",
            channel_id=123456789
        )
        
        # Both should succeed and have different IDs
        self.assertIsNotNone(alert_id1)
        self.assertIsNotNone(alert_id2)
        self.assertNotEqual(alert_id1, alert_id2)
        
        # Both connections should see both records
        alert1_from_db2 = db2.get_alert_by_id(alert_id1)
        alert2_from_db1 = self.db.get_alert_by_id(alert_id2)
        
        self.assertIsNotNone(alert1_from_db2)
        self.assertIsNotNone(alert2_from_db1)
        
        db2.close()


if __name__ == '__main__':
    unittest.main()
