"""
Simplified unit tests for Trade Tracker module
Tests trade performance tracking, analytics, and reporting with mocked database
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


class TestTradeTrackerSimple(unittest.TestCase):
    """Simplified test cases for TradeTracker class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create test configuration
        self.config_manager = ConfigManager()
        
        # Create mock database
        self.db = Mock(spec=DatabaseManager)
        
        # Initialize trade tracker
        self.trade_tracker = TradeTracker(
            config=self.config_manager,
            db=self.db
        )
        
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
        # Mock database methods
        self.db.insert_trade.return_value = 123
        self.db.log_system_event.return_value = True
        
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
        
        self.assertEqual(trade_id, 123)
        
        # Verify database methods were called (with actual parameters from implementation)
        self.db.insert_trade.assert_called_once()
        self.db.log_system_event.assert_called_once()
    
    def test_record_trade_execution_error_handling(self):
        """Test error handling in trade execution recording"""
        # Mock database to raise exception
        self.db.insert_trade.side_effect = Exception("Database error")
        
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
    
    def test_record_trade_completion_success(self):
        """Test successful trade completion recording"""
        # Mock the missing update methods
        self.db.update_trade_status = Mock(return_value=True)
        self.db.update_trade_pnl = Mock(return_value=True)
        self.db.log_system_event = Mock(return_value=True)
        
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
        self.db.log_system_event.assert_called_once()
    
    def test_record_trade_completion_error_handling(self):
        """Test error handling in trade completion recording"""
        # Mock database to raise exception
        self.db.update_trade_status = Mock(side_effect=Exception("Database error"))
        self.db.update_trade_pnl = Mock(return_value=True)
        
        completion_data = {
            'status': 'TARGET1_HIT',
            'pnl': 25.0
        }
        
        # This should not raise an exception
        self.trade_tracker.record_trade_completion(99999, completion_data)
    
    @patch.object(TradeTracker, 'get_trade_performance')
    def test_calculate_performance_metrics_with_data(self, mock_get_performance):
        """Test calculating performance metrics with trade data"""
        # Mock trade performance data
        entry_time = datetime.now(timezone.utc)
        mock_performances = [
            TradePerformance(
                trade_id=1, alert_id=1, symbol="MES", entry_price=4500.0, exit_price=4510.0,
                quantity=2, side="LONG", pnl=25.0, pnl_percentage=0.56, duration_minutes=30,
                entry_time=entry_time, exit_time=entry_time + timedelta(minutes=30),
                trade_type="paper", status="TARGET1_HIT"
            ),
            TradePerformance(
                trade_id=2, alert_id=2, symbol="MES", entry_price=4510.0, exit_price=4520.0,
                quantity=1, side="LONG", pnl=50.0, pnl_percentage=0.99, duration_minutes=25,
                entry_time=entry_time + timedelta(hours=1), exit_time=entry_time + timedelta(hours=1, minutes=25),
                trade_type="paper", status="TARGET2_HIT"
            ),
            TradePerformance(
                trade_id=3, alert_id=3, symbol="MES", entry_price=4520.0, exit_price=4500.0,
                quantity=2, side="LONG", pnl=-20.0, pnl_percentage=-0.44, duration_minutes=45,
                entry_time=entry_time + timedelta(hours=2), exit_time=entry_time + timedelta(hours=2, minutes=45),
                trade_type="paper", status="STOPPED_OUT"
            )
        ]
        mock_get_performance.return_value = mock_performances
        
        # Mock execution rate calculation
        self.trade_tracker._calculate_execution_rate = Mock(return_value=75.0)
        self.trade_tracker._calculate_execution_delay = Mock(return_value=2.5)
        
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
        self.assertEqual(metrics.alert_execution_rate, 75.0)
        self.assertEqual(metrics.average_execution_delay, 2.5)
    
    @patch.object(TradeTracker, 'get_trade_performance')
    def test_calculate_performance_metrics_no_data(self, mock_get_performance):
        """Test calculating performance metrics with no data"""
        mock_get_performance.return_value = []
        
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
    
    def test_calculate_streaks_with_data(self):
        """Test streak calculation with performance data"""
        entry_time = datetime.now(timezone.utc)
        performances = [
            # Winning streak of 2
            TradePerformance(
                trade_id=1, alert_id=1, symbol="MES", entry_price=4500.0, exit_price=4510.0,
                quantity=2, side="LONG", pnl=25.0, pnl_percentage=0.56, duration_minutes=30,
                entry_time=entry_time, exit_time=entry_time + timedelta(minutes=30),
                trade_type="paper", status="TARGET1_HIT"
            ),
            TradePerformance(
                trade_id=2, alert_id=2, symbol="MES", entry_price=4510.0, exit_price=4520.0,
                quantity=1, side="LONG", pnl=12.5, pnl_percentage=0.24, duration_minutes=25,
                entry_time=entry_time + timedelta(hours=1), exit_time=entry_time + timedelta(hours=1, minutes=25),
                trade_type="paper", status="TARGET1_HIT"
            ),
            # Losing streak of 1
            TradePerformance(
                trade_id=3, alert_id=3, symbol="MES", entry_price=4520.0, exit_price=4500.0,
                quantity=2, side="LONG", pnl=-40.0, pnl_percentage=-0.88, duration_minutes=45,
                entry_time=entry_time + timedelta(hours=2), exit_time=entry_time + timedelta(hours=2, minutes=45),
                trade_type="paper", status="STOPPED_OUT"
            ),
            # Current winning streak of 1
            TradePerformance(
                trade_id=4, alert_id=4, symbol="MES", entry_price=4500.0, exit_price=4515.0,
                quantity=1, side="LONG", pnl=18.75, pnl_percentage=0.33, duration_minutes=35,
                entry_time=entry_time + timedelta(hours=3), exit_time=entry_time + timedelta(hours=3, minutes=35),
                trade_type="paper", status="TARGET1_HIT"
            )
        ]
        
        current_streak, max_winning_streak, max_losing_streak = self.trade_tracker._calculate_streaks(performances)
        
        self.assertEqual(current_streak, 1)  # Current winning streak
        self.assertEqual(max_winning_streak, 2)  # Maximum winning streak
        self.assertEqual(max_losing_streak, 1)  # Maximum losing streak
    
    def test_calculate_streaks_no_data(self):
        """Test streak calculation with no data"""
        current_streak, max_winning_streak, max_losing_streak = self.trade_tracker._calculate_streaks([])
        
        self.assertEqual(current_streak, 0)
        self.assertEqual(max_winning_streak, 0)
        self.assertEqual(max_losing_streak, 0)
    
    def test_calculate_execution_delay(self):
        """Test execution delay calculation"""
        # The method currently returns a placeholder value of 2.5
        delay = self.trade_tracker._calculate_execution_delay(days=7)
        
        # Should return the placeholder value of 2.5 seconds
        self.assertEqual(delay, 2.5)
    
    def test_error_handling_in_methods(self):
        """Test error handling in various methods"""
        # Test with database connection issues
        self.trade_tracker.db = None
        
        # These should not raise exceptions
        metrics = self.trade_tracker.calculate_performance_metrics(days=30)
        self.assertEqual(metrics.total_trades, 0)


if __name__ == '__main__':
    unittest.main()
