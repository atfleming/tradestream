"""
Unit tests for Trade Tracker module
Tests trade performance tracking, analytics, and reporting
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta, date
from dataclasses import dataclass

# Add src to path for imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from trade_tracker import TradeTracker, TradePerformance, PerformanceMetrics
from message_parser import ParsedAlert
from database import DatabaseManager
from config import ConfigManager


class TestTradeTracker(unittest.TestCase):
    """Test cases for TradeTracker class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Initialize database
        self.db = DatabaseManager(self.db_path)
        self.db.initialize_database()
        
        # Create test configuration
        self.config_manager = ConfigManager()
        
        # Initialize trade tracker
        self.trade_tracker = TradeTracker(
            config=self.config_manager,
            db=self.db
        )
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_trade_tracker_initialization(self):
        """Test trade tracker initialization"""
        self.assertIsNotNone(self.trade_tracker.config)
        self.assertIsNotNone(self.trade_tracker.db)
        self.assertIsNotNone(self.trade_tracker.logger)
    
    def test_trade_performance_dataclass(self):
        """Test TradePerformance dataclass functionality"""
        entry_time = datetime.now(timezone.utc)
        exit_time = entry_time + timedelta(minutes=30)
        
        performance = TradePerformance(
            trade_id=1,
            alert_id=100,
            symbol="MES",
            entry_price=4500.0,
            exit_price=4510.0,
            quantity=2,
            side="LONG",
            pnl=25.0,
            pnl_percentage=0.56,
            duration_minutes=30,
            entry_time=entry_time,
            exit_time=exit_time,
            trade_type="paper",
            status="TARGET1_HIT"
        )
        
        self.assertEqual(performance.trade_id, 1)
        self.assertEqual(performance.alert_id, 100)
        self.assertEqual(performance.symbol, "MES")
        self.assertEqual(performance.entry_price, 4500.0)
        self.assertEqual(performance.exit_price, 4510.0)
        self.assertEqual(performance.quantity, 2)
        self.assertEqual(performance.side, "LONG")
        self.assertEqual(performance.pnl, 25.0)
        self.assertEqual(performance.pnl_percentage, 0.56)
        self.assertEqual(performance.duration_minutes, 30)
        self.assertEqual(performance.entry_time, entry_time)
        self.assertEqual(performance.exit_time, exit_time)
        self.assertEqual(performance.trade_type, "paper")
        self.assertEqual(performance.status, "TARGET1_HIT")
    
    def test_performance_metrics_dataclass(self):
        """Test PerformanceMetrics dataclass functionality"""
        metrics = PerformanceMetrics(
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=60.0,
            total_pnl=150.0,
            average_win=50.0,
            average_loss=-25.0,
            largest_win=100.0,
            largest_loss=-50.0,
            profit_factor=3.0,
            sharpe_ratio=1.5,
            max_drawdown=75.0,
            max_drawdown_percentage=7.5,
            current_streak=2,
            max_winning_streak=4,
            max_losing_streak=2,
            average_trade_duration=45.0,
            alert_execution_rate=85.0,
            average_execution_delay=2.5
        )
        
        self.assertEqual(metrics.total_trades, 10)
        self.assertEqual(metrics.winning_trades, 6)
        self.assertEqual(metrics.losing_trades, 4)
        self.assertEqual(metrics.win_rate, 60.0)
        self.assertEqual(metrics.total_pnl, 150.0)
        self.assertEqual(metrics.average_win, 50.0)
        self.assertEqual(metrics.average_loss, -25.0)
        self.assertEqual(metrics.largest_win, 100.0)
        self.assertEqual(metrics.largest_loss, -50.0)
        self.assertEqual(metrics.profit_factor, 3.0)
        self.assertEqual(metrics.sharpe_ratio, 1.5)
        self.assertEqual(metrics.max_drawdown, 75.0)
        self.assertEqual(metrics.max_drawdown_percentage, 7.5)
        self.assertEqual(metrics.current_streak, 2)
        self.assertEqual(metrics.max_winning_streak, 4)
        self.assertEqual(metrics.max_losing_streak, 2)
        self.assertEqual(metrics.average_trade_duration, 45.0)
        self.assertEqual(metrics.alert_execution_rate, 85.0)
        self.assertEqual(metrics.average_execution_delay, 2.5)
    
    def test_performance_metrics_defaults(self):
        """Test PerformanceMetrics default values"""
        metrics = PerformanceMetrics()
        
        self.assertEqual(metrics.total_trades, 0)
        self.assertEqual(metrics.winning_trades, 0)
        self.assertEqual(metrics.losing_trades, 0)
        self.assertEqual(metrics.win_rate, 0.0)
        self.assertEqual(metrics.total_pnl, 0.0)
        self.assertEqual(metrics.average_win, 0.0)
        self.assertEqual(metrics.average_loss, 0.0)
        self.assertEqual(metrics.largest_win, 0.0)
        self.assertEqual(metrics.largest_loss, 0.0)
        self.assertEqual(metrics.profit_factor, 0.0)
        self.assertEqual(metrics.sharpe_ratio, 0.0)
        self.assertEqual(metrics.max_drawdown, 0.0)
        self.assertEqual(metrics.max_drawdown_percentage, 0.0)
        self.assertEqual(metrics.current_streak, 0)
        self.assertEqual(metrics.max_winning_streak, 0)
        self.assertEqual(metrics.max_losing_streak, 0)
        self.assertEqual(metrics.average_trade_duration, 0.0)
        self.assertEqual(metrics.alert_execution_rate, 0.0)
        self.assertEqual(metrics.average_execution_delay, 0.0)
    
    def test_record_trade_execution_success(self):
        """Test successful trade execution recording"""
        # Create test alert
        alert = ParsedAlert(
            raw_message="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            is_valid=True,
            price=4500.0,
            size="B",
            stop=4490.0,
            target_1=4510.0,
            target_2=4520.0
        )
        alert.alert_id = 1
        
        trade_data = {
            'symbol': 'MES',
            'side': 'LONG',
            'entry_price': 4500.0,
            'quantity': 2,
            'stop_loss': 4490.0,
            'target_1': 4510.0
        }
        
        trade_id = self.trade_tracker.record_trade_execution(alert, trade_data)
        
        self.assertGreater(trade_id, 0)
        
        # Verify trade was inserted into database
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            trade_row = cursor.fetchone()
            
            self.assertIsNotNone(trade_row)
            self.assertEqual(trade_row[1], 1)  # alert_id
            self.assertEqual(trade_row[4], 4500.0)  # entry_price
            self.assertEqual(trade_row[5], 2)  # quantity
    
    def test_record_trade_execution_error_handling(self):
        """Test error handling in trade execution recording"""
        # Create invalid alert (no alert_id)
        alert = ParsedAlert(
            raw_message="Invalid alert",
            is_valid=False
        )
        
        trade_data = {
            'symbol': 'MES',
            'entry_price': 4500.0,
            'quantity': 2
        }
        
        trade_id = self.trade_tracker.record_trade_execution(alert, trade_data)
        
        self.assertEqual(trade_id, 0)  # Should return 0 on error
    
    @patch.object(DatabaseManager, 'update_trade_fill')
    def test_record_trade_completion_success(self, mock_update_fill):
        """Test successful trade completion recording"""
        mock_update_fill.return_value = True
        
        # Mock the missing update methods
        self.db.update_trade_status = Mock(return_value=True)
        self.db.update_trade_pnl = Mock(return_value=True)
        
        # Now complete the trade
        completion_data = {
            'status': 'TARGET1_HIT',
            'pnl': 25.0,
            'exit_price': 4510.0
        }
        
        # This should not raise an exception
        self.trade_tracker.record_trade_completion(1, completion_data)
        
        # Verify methods were called
        self.db.update_trade_status.assert_called_once_with(1, 'TARGET1_HIT')
        self.db.update_trade_pnl.assert_called_once_with(1, 25.0)
    
    def test_record_trade_completion_error_handling(self):
        """Test error handling in trade completion recording"""
        # Try to complete non-existent trade
        completion_data = {
            'status': 'TARGET1_HIT',
            'pnl': 25.0
        }
        
        # This should not raise an exception
        self.trade_tracker.record_trade_completion(99999, completion_data)
    
    def test_get_trade_performance_with_data(self):
        """Test getting trade performance data"""
        # Insert test trade data
        test_date = datetime.now(timezone.utc)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trades (
                    alert_id, trade_type, symbol, entry_price, quantity,
                    created_at, updated_at, status, pnl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                1, "BUY", "MES", 4500.0, 2,
                test_date, test_date, "TARGET1_HIT", 25.0
            ))
            conn.commit()
        
        performances = self.trade_tracker.get_trade_performance(days=30)
        
        self.assertEqual(len(performances), 1)
        performance = performances[0]
        self.assertEqual(performance.symbol, 'MES')
        self.assertEqual(performance.entry_price, 4500.0)
        self.assertEqual(performance.quantity, 2)
        self.assertEqual(performance.pnl, 25.0)
        self.assertEqual(performance.status, 'TARGET1_HIT')
    
    def test_get_trade_performance_no_data(self):
        """Test getting trade performance when no data exists"""
        performances = self.trade_tracker.get_trade_performance(days=30)
        
        self.assertEqual(len(performances), 0)
    
    def test_calculate_performance_metrics_with_data(self):
        """Test calculating performance metrics with trade data"""
        # Insert test trade data
        test_date = datetime.now(timezone.utc)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert winning trades
            cursor.execute('''
                INSERT INTO trades (
                    alert_id, trade_type, symbol, entry_price, quantity,
                    created_at, updated_at, status, pnl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (1, "BUY", "MES", 4500.0, 2, test_date, test_date, "TARGET1_HIT", 25.0))
            
            cursor.execute('''
                INSERT INTO trades (
                    alert_id, trade_type, symbol, entry_price, quantity,
                    created_at, updated_at, status, pnl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (2, "BUY", "MES", 4510.0, 1, test_date, test_date, "TARGET2_HIT", 50.0))
            
            # Insert losing trade
            cursor.execute('''
                INSERT INTO trades (
                    alert_id, trade_type, symbol, entry_price, quantity,
                    created_at, updated_at, status, pnl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (3, "BUY", "MES", 4520.0, 2, test_date, test_date, "STOPPED_OUT", -20.0))
            
            # Insert alerts for execution rate calculation
            for i in range(1, 5):
                cursor.execute('''
                    INSERT INTO alerts (
                        timestamp, discord_message_id, author, channel_id, raw_content,
                        parsed_price, parsed_size, parsed_stop, is_valid
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (test_date, f"msg_{i}", "JMoney", 123456, f"Alert {i}", 4500.0, "B", 4490.0, 1))
            
            conn.commit()
        
        metrics = self.trade_tracker.calculate_performance_metrics(days=30)
        
        self.assertEqual(metrics.total_trades, 3)
        self.assertEqual(metrics.winning_trades, 2)
        self.assertEqual(metrics.losing_trades, 1)
        self.assertAlmostEqual(metrics.win_rate, 66.67, places=1)
        self.assertEqual(metrics.total_pnl, 55.0)  # 25 + 50 - 20
        self.assertEqual(metrics.average_win, 37.5)  # (25 + 50) / 2
        self.assertEqual(metrics.average_loss, -20.0)
        self.assertEqual(metrics.largest_win, 50.0)
        self.assertEqual(metrics.largest_loss, -20.0)
        self.assertAlmostEqual(metrics.profit_factor, 3.75, places=2)  # 75 / 20
        self.assertEqual(metrics.alert_execution_rate, 75.0)  # 3 trades / 4 alerts
    
    def test_calculate_performance_metrics_no_data(self):
        """Test calculating performance metrics with no data"""
        metrics = self.trade_tracker.calculate_performance_metrics(days=30)
        
        # Should return default metrics
        self.assertEqual(metrics.total_trades, 0)
        self.assertEqual(metrics.winning_trades, 0)
        self.assertEqual(metrics.losing_trades, 0)
        self.assertEqual(metrics.win_rate, 0.0)
        self.assertEqual(metrics.total_pnl, 0.0)
        self.assertEqual(metrics.average_win, 0.0)
        self.assertEqual(metrics.average_loss, 0.0)
        self.assertEqual(metrics.profit_factor, 0.0)
        self.assertEqual(metrics.alert_execution_rate, 0.0)
    
    def test_calculate_drawdown_with_data(self):
        """Test drawdown calculation with performance data"""
        # Create test performance data
        entry_time = datetime.now(timezone.utc)
        performances = [
            TradePerformance(
                trade_id=1, alert_id=1, symbol="MES", entry_price=4500.0, exit_price=4510.0,
                quantity=2, side="LONG", pnl=25.0, pnl_percentage=0.56, duration_minutes=30,
                entry_time=entry_time, exit_time=entry_time + timedelta(minutes=30),
                trade_type="paper", status="TARGET1_HIT"
            ),
            TradePerformance(
                trade_id=2, alert_id=2, symbol="MES", entry_price=4510.0, exit_price=4490.0,
                quantity=2, side="LONG", pnl=-40.0, pnl_percentage=-0.88, duration_minutes=45,
                entry_time=entry_time + timedelta(hours=1), exit_time=entry_time + timedelta(hours=1, minutes=45),
                trade_type="paper", status="STOPPED_OUT"
            ),
            TradePerformance(
                trade_id=3, alert_id=3, symbol="MES", entry_price=4520.0, exit_price=4530.0,
                quantity=1, side="LONG", pnl=12.5, pnl_percentage=0.28, duration_minutes=20,
                entry_time=entry_time + timedelta(hours=2), exit_time=entry_time + timedelta(hours=2, minutes=20),
                trade_type="paper", status="TARGET1_HIT"
            )
        ]
        
        max_drawdown, max_drawdown_pct = self.trade_tracker._calculate_drawdown(performances)
        
        self.assertGreater(max_drawdown, 0)
        self.assertGreater(max_drawdown_pct, 0)
        # The maximum drawdown should be 40.0 (the loss from the second trade)
        self.assertEqual(max_drawdown, 40.0)
    
    def test_calculate_drawdown_no_data(self):
        """Test drawdown calculation with no data"""
        max_drawdown, max_drawdown_pct = self.trade_tracker._calculate_drawdown([])
        
        self.assertEqual(max_drawdown, 0.0)
        self.assertEqual(max_drawdown_pct, 0.0)
    
    def test_calculate_execution_rate_with_data(self):
        """Test execution rate calculation with data"""
        test_date = datetime.now(timezone.utc)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert 4 alerts
            for i in range(1, 5):
                cursor.execute('''
                    INSERT INTO alerts (
                        timestamp, discord_message_id, author, channel_id, raw_content,
                        parsed_price, parsed_size, parsed_stop, is_valid
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (test_date, f"msg_{i}", "JMoney", 123456, f"Alert {i}", 4500.0 + i, "B", 4490.0 + i, 1))
            
            # Insert 3 executed trades
            for i in range(1, 4):
                cursor.execute('''
                    INSERT INTO trades (
                        alert_id, trade_type, symbol, entry_price, quantity,
                        created_at, updated_at, status, pnl
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (i, "BUY", "MES", 4500.0 + i, 2, test_date, test_date, "TARGET1_HIT", 25.0))
            
            conn.commit()
        
        execution_rate = self.trade_tracker._calculate_execution_rate(days=7)
        
        self.assertEqual(execution_rate, 75.0)  # 3 trades / 4 alerts = 75%
    
    def test_calculate_execution_rate_no_data(self):
        """Test execution rate calculation with no data"""
        execution_rate = self.trade_tracker._calculate_execution_rate(days=7)
        
        self.assertEqual(execution_rate, 0.0)
    
    def test_get_daily_summary_with_data(self):
        """Test getting daily summary with data"""
        test_date = datetime.now(timezone.utc).date()
        test_datetime = datetime.combine(test_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert trades for the test date
            cursor.execute('''
                INSERT INTO trades (
                    alert_id, trade_type, symbol, entry_price, quantity,
                    created_at, updated_at, status, pnl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (1, "BUY", "MES", 4500.0, 2, test_datetime, test_datetime, "TARGET1_HIT", 25.0))
            
            cursor.execute('''
                INSERT INTO trades (
                    alert_id, trade_type, symbol, entry_price, quantity,
                    created_at, updated_at, status, pnl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (2, "BUY", "MES", 4510.0, 1, test_datetime, test_datetime, "STOPPED_OUT", -12.5))
            
            # Insert alerts for the test date
            for i in range(1, 4):
                cursor.execute('''
                    INSERT INTO alerts (
                        raw_message, is_valid, parsed_price, parsed_size, parsed_stop,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (f"Alert {i}", 1, 4500.0, "B", 4490.0, test_datetime))
            
            conn.commit()
        
        summary = self.trade_tracker.get_daily_summary(test_date)
        
        self.assertEqual(summary['date'], test_date.isoformat())
        self.assertEqual(summary['total_pnl'], 12.5)  # 25.0 - 12.5
        self.assertEqual(summary['trade_count'], 2)
        self.assertEqual(summary['winning_trades'], 1)
        self.assertEqual(summary['losing_trades'], 1)
        self.assertEqual(summary['win_rate'], 50.0)  # 1/2 * 100
        self.assertEqual(summary['alert_count'], 3)
        self.assertAlmostEqual(summary['execution_rate'], 66.67, places=1)  # 2/3 * 100
    
    def test_get_daily_summary_no_data(self):
        """Test getting daily summary with no data"""
        test_date = datetime.now(timezone.utc).date()
        
        summary = self.trade_tracker.get_daily_summary(test_date)
        
        self.assertEqual(summary['date'], test_date.isoformat())
        self.assertEqual(summary['total_pnl'], 0.0)
        self.assertEqual(summary['trade_count'], 0)
        self.assertEqual(summary['winning_trades'], 0)
        self.assertEqual(summary['losing_trades'], 0)
        self.assertEqual(summary['win_rate'], 0.0)
        self.assertEqual(summary['alert_count'], 0)
        self.assertEqual(summary['execution_rate'], 0.0)
    
    def test_get_alert_vs_execution_comparison_with_data(self):
        """Test alert vs execution comparison with data"""
        test_date = datetime.now(timezone.utc)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert alerts
            cursor.execute('''
                INSERT INTO alerts (
                    alert_id, raw_message, is_valid, parsed_price, parsed_size, parsed_stop,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (1, "Alert 1", 1, 4500.0, "B", 4490.0, test_date))
            
            cursor.execute('''
                INSERT INTO alerts (
                    alert_id, raw_message, is_valid, parsed_price, parsed_size, parsed_stop,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (2, "Alert 2", 1, 4510.0, "A", 4500.0, test_date))
            
            # Insert trade for first alert only
            cursor.execute('''
                INSERT INTO trades (
                    alert_id, trade_type, symbol, entry_price, quantity,
                    created_at, updated_at, status, pnl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (1, "BUY", "MES", 4502.0, 2, test_date, test_date, "TARGET1_HIT", 25.0))
            
            conn.commit()
        
        comparisons = self.trade_tracker.get_alert_vs_execution_comparison(days=7)
        
        self.assertEqual(len(comparisons), 2)
        
        # First alert should be executed
        executed_alert = next(c for c in comparisons if c['alert_id'] == 1)
        self.assertTrue(executed_alert['executed'])
        self.assertEqual(executed_alert['execution_price'], 4502.0)
        self.assertEqual(executed_alert['execution_quantity'], 2)
        self.assertEqual(executed_alert['pnl'], 25.0)
        self.assertEqual(executed_alert['status'], 'TARGET1_HIT')
        self.assertEqual(executed_alert['price_slippage'], 2.0)  # 4502 - 4500
        
        # Second alert should not be executed
        not_executed_alert = next(c for c in comparisons if c['alert_id'] == 2)
        self.assertFalse(not_executed_alert['executed'])
        self.assertIsNone(not_executed_alert['execution_price'])
        self.assertIsNone(not_executed_alert['execution_quantity'])
        self.assertIsNone(not_executed_alert['pnl'])
        self.assertEqual(not_executed_alert['status'], 'NOT_EXECUTED')
        self.assertEqual(not_executed_alert['price_slippage'], 0.0)
    
    def test_get_alert_vs_execution_comparison_no_data(self):
        """Test alert vs execution comparison with no data"""
        comparisons = self.trade_tracker.get_alert_vs_execution_comparison(days=7)
        
        self.assertEqual(len(comparisons), 0)
    
    def test_error_handling_in_methods(self):
        """Test error handling in various methods"""
        # Test with database connection issues
        self.trade_tracker.db = None
        
        # These should not raise exceptions
        metrics = self.trade_tracker.calculate_performance_metrics(days=30)
        self.assertEqual(metrics.total_trades, 0)
        
        summary = self.trade_tracker.get_daily_summary()
        self.assertEqual(summary['total_pnl'], 0.0)
        
        comparisons = self.trade_tracker.get_alert_vs_execution_comparison(days=7)
        self.assertEqual(len(comparisons), 0)


if __name__ == '__main__':
    unittest.main()
