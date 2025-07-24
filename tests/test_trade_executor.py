"""
Unit tests for Trade Executor module
Tests trade execution, position management, and risk controls
"""

import unittest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from dataclasses import dataclass

# Add src to path for imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock the circular import dependencies first
sys.modules['paper_trading'] = Mock()
sys.modules['tsx_integration'] = Mock()
sys.modules['email_notifier'] = Mock()

from trade_executor import TradeExecutor, TradePosition, TradeStatus, PositionStatus
from message_parser import ParsedAlert
from database import DatabaseManager
from config import ConfigManager, TradingConfig


class MockTSXIntegration:
    """Mock TopStepX integration for testing"""
    def __init__(self):
        self.account_balance = 10000.0
        self.market_open = True
        self.orders = {}
        self.order_counter = 1
        
    def get_account_balance(self):
        return self.account_balance
        
    def is_market_open(self):
        return self.market_open
        
    async def place_market_order(self, side, quantity):
        order_id = f"ORDER_{self.order_counter}"
        self.order_counter += 1
        self.orders[order_id] = {
            'type': 'MARKET',
            'side': side,
            'quantity': quantity,
            'status': 'SUBMITTED'
        }
        return MockOrderInfo(order_id)
        
    async def place_stop_order(self, side, quantity, price):
        order_id = f"STOP_{self.order_counter}"
        self.order_counter += 1
        self.orders[order_id] = {
            'type': 'STOP',
            'side': side,
            'quantity': quantity,
            'price': price,
            'status': 'SUBMITTED'
        }
        return MockOrderInfo(order_id)
        
    async def get_current_price(self, symbol):
        return 4500.0  # Mock current price
        
    async def cancel_order(self, order_id):
        """Mock method for canceling orders"""
        return True


class MockOrderInfo:
    """Mock order info for testing"""
    def __init__(self, order_id):
        self.order_id = order_id
        self.status = 'SUBMITTED'


class MockPaperTrader:
    """Mock paper trading simulator for testing"""
    def __init__(self):
        self.balance = 10000.0
        self.positions = {}
        
    async def place_market_order(self, side, quantity):
        return MockOrderInfo(f"PAPER_ORDER_{len(self.positions) + 1}")
        
    async def place_stop_order(self, side, quantity, price):
        return MockOrderInfo(f"PAPER_STOP_{len(self.positions) + 1}")
        
    async def get_current_price(self, symbol):
        return 4500.0
        
    def update_trade_pnl(self, pnl):
        """Mock method for updating P&L"""
        pass
        
    async def cancel_order(self, order_id):
        """Mock method for canceling orders"""
        return True


class MockEmailNotifier:
    """Mock email notifier for testing"""
    def __init__(self):
        self.sent_emails = []
        
    async def send_alert_email(self, **kwargs):
        self.sent_emails.append(('alert', kwargs))
        
    async def send_trade_email(self, trade_data):
        self.sent_emails.append(('trade', trade_data))


class TestTradeExecutor(unittest.TestCase):
    """Test cases for TradeExecutor class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Initialize database
        self.db = DatabaseManager(self.db_path)
        self.db.initialize_database()
        
        # Mock the insert_trade method to match what TradeExecutor expects
        original_insert_trade = self.db.insert_trade
        def mock_insert_trade(alert_id, entry_price, quantity, stop_price=None, target_price=None, status=None, **kwargs):
            # Convert to the actual database signature
            return original_insert_trade(
                alert_id=alert_id,
                trade_type="LONG",
                symbol="MES",
                entry_price=entry_price,
                quantity=quantity,
                stop_loss=stop_price,
                target_1=target_price,
                target_2=None,
                order_id=None
            )
        self.db.insert_trade = mock_insert_trade
        
        # Mock additional database methods
        self.db.update_trade_status = Mock()
        self.db.update_trade_pnl = Mock()
        
        # Create test configuration
        self.config_manager = ConfigManager()
        self.config_manager.trading = TradingConfig(
            paper_trading_enabled=True,
            symbol="MES",
            contract_name="Micro E-mini S&P 500",
            tick_value=1.25,
            account_id="TEST_ACCOUNT",
            max_daily_trades=10,
            max_position_size=20,
            size_mapping={"A": 6, "B": 4, "C": 2}
        )
        
        # Create mock dependencies
        self.mock_tsx = MockTSXIntegration()
        self.mock_paper_trader = MockPaperTrader()
        self.mock_email_notifier = MockEmailNotifier()
        
        # Initialize trade executor
        self.executor = TradeExecutor(
            config=self.config_manager,
            db=self.db,
            tsx_api=self.mock_tsx,
            paper_trader=self.mock_paper_trader,
            email_notifier=self.mock_email_notifier
        )
        
        # Enable auto trading for tests
        self.executor.enable_auto_trading = True
        
        # Disable price monitoring to avoid async issues in tests
        self.executor.is_monitoring = False
        
        # Mock price monitoring methods to prevent them from running
        async def mock_start_price_monitoring():
            pass
        self.executor._start_price_monitoring = mock_start_price_monitoring
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_trade_executor_initialization(self):
        """Test trade executor initialization"""
        self.assertIsNotNone(self.executor.config)
        self.assertIsNotNone(self.executor.db)
        self.assertEqual(self.executor.paper_trading_enabled, True)
        self.assertEqual(self.executor.max_daily_trades, 10)
        self.assertEqual(self.executor.max_position_size, 20)
        self.assertEqual(self.executor.size_mapping, {"A": 6, "B": 4, "C": 2})
        self.assertEqual(len(self.executor.active_positions), 0)
        self.assertEqual(self.executor.daily_trade_count, 0)
        self.assertEqual(self.executor.daily_pnl, 0.0)
    
    async def test_execute_alert_valid_paper_trading(self):
        """Test executing valid alert in paper trading mode"""
        # Create valid alert
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
        
        # Execute alert
        result = await self.executor.execute_alert(alert)
        
        # Verify execution success
        self.assertTrue(result)
        self.assertEqual(len(self.executor.active_positions), 1)
        # Note: daily_trade_count is incremented when trades are filled, not submitted
        
        # Verify position details
        position = list(self.executor.active_positions.values())[0]
        self.assertEqual(position.alert_id, 1)
        self.assertEqual(position.entry_price, 4500.0)
        self.assertEqual(position.stop_price, 4490.0)
        self.assertEqual(position.target1_price, 4510.0)
        self.assertEqual(position.target2_price, 4520.0)
        self.assertEqual(position.size_code, "B")
        self.assertEqual(position.full_quantity, 4)  # B = 4 contracts
        self.assertEqual(position.position_status, PositionStatus.FULL)
        
        # Verify email notification sent
        self.assertEqual(len(self.mock_email_notifier.sent_emails), 1)
        email_type, email_data = self.mock_email_notifier.sent_emails[0]
        self.assertEqual(email_type, 'alert')
    
    async def test_execute_alert_invalid_alert(self):
        """Test executing invalid alert"""
        alert = ParsedAlert(
            raw_message="Invalid message",
            is_valid=False
        )
        
        result = await self.executor.execute_alert(alert)
        
        self.assertFalse(result)
        self.assertEqual(len(self.executor.active_positions), 0)
        self.assertEqual(self.executor.daily_trade_count, 0)
    
    async def test_execute_alert_auto_trading_disabled(self):
        """Test executing alert with auto trading disabled"""
        # Disable auto trading
        self.executor.enable_auto_trading = False
        
        alert = ParsedAlert(
            raw_message="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            is_valid=True,
            price=4500.0,
            size="B",
            stop=4490.0
        )
        
        result = await self.executor.execute_alert(alert)
        
        self.assertFalse(result)
        self.assertEqual(len(self.executor.active_positions), 0)
    
    async def test_pre_trade_risk_checks_daily_limit(self):
        """Test pre-trade risk checks - daily trade limit"""
        # Set daily trade count to maximum
        self.executor.daily_trade_count = 10
        
        alert = ParsedAlert(is_valid=True, size="A")
        
        result = await self.executor._pre_trade_risk_checks(alert)
        self.assertFalse(result)
    
    async def test_pre_trade_risk_checks_position_size_limit(self):
        """Test pre-trade risk checks - position size limit"""
        # Add existing positions that would exceed limit
        for i in range(3):
            position = TradePosition(
                alert_id=i,
                current_quantity=6  # A size = 6 contracts
            )
            self.executor.active_positions[i] = position
        
        # Try to add another A position (6 contracts) - would exceed limit of 20
        alert = ParsedAlert(is_valid=True, size="A")  # A = 6 contracts
        
        result = await self.executor._pre_trade_risk_checks(alert)
        self.assertFalse(result)  # 18 + 6 = 24 > 20 limit
    
    async def test_pre_trade_risk_checks_insufficient_balance(self):
        """Test pre-trade risk checks - insufficient account balance"""
        # Set low account balance
        self.mock_tsx.account_balance = 500.0
        
        alert = ParsedAlert(is_valid=True, size="B")
        
        result = await self.executor._pre_trade_risk_checks(alert)
        self.assertFalse(result)
    
    async def test_pre_trade_risk_checks_market_closed(self):
        """Test pre-trade risk checks - market closed"""
        # Set market as closed
        self.mock_tsx.market_open = False
        
        alert = ParsedAlert(is_valid=True, size="B")
        
        result = await self.executor._pre_trade_risk_checks(alert)
        self.assertFalse(result)
    
    async def test_pre_trade_risk_checks_success(self):
        """Test pre-trade risk checks - all checks pass"""
        alert = ParsedAlert(is_valid=True, size="B")
        
        result = await self.executor._pre_trade_risk_checks(alert)
        self.assertTrue(result)
    
    async def test_create_trade_position(self):
        """Test creating trade position from alert"""
        alert = ParsedAlert(
            is_valid=True,
            price=4500.0,
            size="C",
            stop=4490.0,
            target_1=4510.0,
            target_2=4520.0
        )
        alert.alert_id = 123
        
        position = await self.executor._create_trade_position(alert)
        
        self.assertIsNotNone(position)
        self.assertEqual(position.alert_id, 123)
        self.assertEqual(position.entry_price, 4500.0)
        self.assertEqual(position.stop_price, 4490.0)
        self.assertEqual(position.target1_price, 4510.0)
        self.assertEqual(position.target2_price, 4520.0)
        self.assertEqual(position.size_code, "C")
        self.assertEqual(position.full_quantity, 2)  # C = 2 contracts
        self.assertEqual(position.current_quantity, 2)
        self.assertEqual(position.position_status, PositionStatus.FULL)
        self.assertEqual(position.trade_status, TradeStatus.PENDING)
        self.assertIsNotNone(position.trade_id)
    
    async def test_execute_entry_order_paper_trading(self):
        """Test executing entry order in paper trading mode"""
        position = TradePosition(
            alert_id=1,
            entry_price=4500.0,
            full_quantity=4,
            current_quantity=4
        )
        
        result = await self.executor._execute_entry_order(position)
        
        self.assertTrue(result)
        self.assertEqual(position.trade_status, TradeStatus.ENTRY_SUBMITTED)
        self.assertIsNotNone(position.entry_order_id)
    
    async def test_execute_entry_order_live_trading(self):
        """Test executing entry order in live trading mode"""
        # Switch to live trading mode
        self.executor.paper_trading_enabled = False
        self.executor.live_trading_enabled = True
        
        position = TradePosition(
            alert_id=1,
            entry_price=4500.0,
            full_quantity=4,
            current_quantity=4
        )
        
        result = await self.executor._execute_entry_order(position)
        
        self.assertTrue(result)
        self.assertEqual(position.trade_status, TradeStatus.ENTRY_SUBMITTED)
        self.assertIsNotNone(position.entry_order_id)
        # Order ID should contain LIVE_ prefix from the route_order method
        self.assertIn("LIVE_", position.entry_order_id)
    
    async def test_handle_target1_hit(self):
        """Test handling Target 1 hit"""
        position = TradePosition(
            alert_id=1,
            entry_price=4500.0,
            target1_price=4510.0,
            full_quantity=4,
            current_quantity=4,
            position_status=PositionStatus.FULL,
            trade_status=TradeStatus.ENTRY_FILLED,
            entry_fill_price=4500.0  # Set the fill price
        )
        
        current_price = 4510.0
        await self.executor._handle_target1_hit(position, current_price)
        
        # Verify position updated
        self.assertEqual(position.position_status, PositionStatus.HALF)
        self.assertEqual(position.current_quantity, 2)  # Half of original
        self.assertEqual(position.trade_status, TradeStatus.TARGET1_HIT)
        self.assertEqual(position.target1_fill_price, current_price)
        self.assertIsNotNone(position.target1_fill_time)
        
        # Verify stop moved to breakeven
        self.assertEqual(position.stop_price, position.entry_price)
        
        # Verify P&L calculation
        expected_pnl = (current_price - position.entry_price) * 2 * 1.25  # 2 contracts * tick_value
        self.assertEqual(position.realized_pnl, expected_pnl)
    
    async def test_handle_target2_hit(self):
        """Test handling Target 2 hit"""
        position = TradePosition(
            alert_id=1,
            entry_price=4500.0,
            target2_price=4520.0,
            full_quantity=4,
            current_quantity=2,  # Already at half position
            position_status=PositionStatus.HALF,
            trade_status=TradeStatus.TARGET1_HIT,
            realized_pnl=25.0,  # From T1 hit
            entry_fill_price=4500.0  # Set the fill price
        )
        
        current_price = 4520.0
        await self.executor._handle_target2_hit(position, current_price)
        
        # Verify position closed
        self.assertEqual(position.position_status, PositionStatus.CLOSED)
        self.assertEqual(position.current_quantity, 0)
        self.assertEqual(position.trade_status, TradeStatus.TARGET2_HIT)
        self.assertEqual(position.target2_fill_price, current_price)
        self.assertIsNotNone(position.target2_fill_time)
        
        # Verify total P&L calculation
        t2_pnl = (current_price - position.entry_price) * 2 * 1.25  # Remaining 2 contracts
        expected_total_pnl = 25.0 + t2_pnl
        self.assertEqual(position.realized_pnl, expected_total_pnl)
        
        # Verify position removed from active positions
        self.assertNotIn(position.alert_id, self.executor.active_positions)
    
    async def test_handle_stop_hit(self):
        """Test handling stop loss hit"""
        position = TradePosition(
            alert_id=1,
            entry_price=4500.0,
            stop_price=4490.0,
            full_quantity=4,
            current_quantity=4,
            position_status=PositionStatus.FULL,
            trade_status=TradeStatus.ENTRY_FILLED,
            entry_fill_price=4500.0  # Set the fill price
        )
        
        # Add to active positions
        self.executor.active_positions[1] = position
        
        current_price = 4490.0
        await self.executor._handle_stop_hit(position, current_price)
        
        # Verify position closed
        self.assertEqual(position.position_status, PositionStatus.CLOSED)
        self.assertEqual(position.current_quantity, 0)
        self.assertEqual(position.trade_status, TradeStatus.STOPPED_OUT)
        self.assertEqual(position.stop_fill_price, current_price)
        self.assertIsNotNone(position.stop_fill_time)
        
        # Verify P&L calculation (loss)
        expected_pnl = (current_price - position.entry_price) * 4 * 1.25  # Negative P&L
        self.assertEqual(position.realized_pnl, expected_pnl)
        
        # Verify position removed from active positions
        self.assertNotIn(position.alert_id, self.executor.active_positions)
    
    async def test_check_position_targets_target1_hit(self):
        """Test checking position targets - Target 1 hit"""
        position = TradePosition(
            alert_id=1,
            entry_price=4500.0,
            target1_price=4510.0,
            target2_price=4520.0,
            stop_price=4490.0,
            position_status=PositionStatus.FULL,
            trade_status=TradeStatus.ENTRY_FILLED
        )
        
        # Mock the target hit handler
        with patch.object(self.executor, '_handle_target1_hit', new_callable=AsyncMock) as mock_t1:
            await self.executor._check_position_targets(position, 4510.0)
            mock_t1.assert_called_once_with(position, 4510.0)
    
    async def test_check_position_targets_target2_hit(self):
        """Test checking position targets - Target 2 hit"""
        position = TradePosition(
            alert_id=1,
            entry_price=4500.0,
            target1_price=4510.0,
            target2_price=4520.0,
            stop_price=4490.0,
            position_status=PositionStatus.HALF,  # Already hit T1
            trade_status=TradeStatus.TARGET1_HIT
        )
        
        # Mock the target hit handler
        with patch.object(self.executor, '_handle_target2_hit', new_callable=AsyncMock) as mock_t2:
            await self.executor._check_position_targets(position, 4520.0)
            mock_t2.assert_called_once_with(position, 4520.0)
    
    async def test_check_position_targets_stop_hit(self):
        """Test checking position targets - Stop hit"""
        position = TradePosition(
            alert_id=1,
            entry_price=4500.0,
            target1_price=4510.0,
            target2_price=4520.0,
            stop_price=4490.0,
            position_status=PositionStatus.FULL,
            trade_status=TradeStatus.ENTRY_FILLED
        )
        
        # Mock the stop hit handler
        with patch.object(self.executor, '_handle_stop_hit', new_callable=AsyncMock) as mock_stop:
            await self.executor._check_position_targets(position, 4490.0)
            mock_stop.assert_called_once_with(position, 4490.0)
    
    def test_get_active_positions(self):
        """Test getting active positions"""
        # Add some positions
        pos1 = TradePosition(alert_id=1)
        pos2 = TradePosition(alert_id=2)
        self.executor.active_positions[1] = pos1
        self.executor.active_positions[2] = pos2
        
        active = self.executor.get_active_positions()
        
        self.assertEqual(len(active), 2)
        self.assertIn(1, active)
        self.assertIn(2, active)
        # Verify it's a copy, not the original
        self.assertIsNot(active, self.executor.active_positions)
    
    def test_get_daily_pnl(self):
        """Test getting daily P&L"""
        self.executor.daily_pnl = 150.75
        self.assertEqual(self.executor.get_daily_pnl(), 150.75)
    
    def test_get_daily_trade_count(self):
        """Test getting daily trade count"""
        self.executor.daily_trade_count = 5
        self.assertEqual(self.executor.get_daily_trade_count(), 5)
    
    async def test_shutdown(self):
        """Test trade executor shutdown"""
        # Start price monitoring
        self.executor.is_monitoring = True
        self.executor.price_monitor_task = Mock()
        self.executor.price_monitor_task.cancel = Mock()
        self.executor.price_monitor_task.__await__ = Mock(return_value=iter([]))
        
        await self.executor.shutdown()
        
        self.assertFalse(self.executor.is_monitoring)
        self.executor.price_monitor_task.cancel.assert_called_once()
    
    def test_trade_position_dataclass(self):
        """Test TradePosition dataclass functionality"""
        position = TradePosition(
            alert_id=123,
            entry_price=4500.0,
            stop_price=4490.0,
            size_code="B"
        )
        
        self.assertEqual(position.alert_id, 123)
        self.assertEqual(position.entry_price, 4500.0)
        self.assertEqual(position.stop_price, 4490.0)
        self.assertEqual(position.size_code, "B")
        self.assertEqual(position.position_status, PositionStatus.FULL)
        self.assertEqual(position.trade_status, TradeStatus.PENDING)
        self.assertIsNotNone(position.created_at)
        self.assertIsNotNone(position.updated_at)
    
    def test_trade_status_enum(self):
        """Test TradeStatus enum values"""
        self.assertEqual(TradeStatus.PENDING.value, "PENDING")
        self.assertEqual(TradeStatus.ENTRY_SUBMITTED.value, "ENTRY_SUBMITTED")
        self.assertEqual(TradeStatus.ENTRY_FILLED.value, "ENTRY_FILLED")
        self.assertEqual(TradeStatus.TARGET1_HIT.value, "TARGET1_HIT")
        self.assertEqual(TradeStatus.TARGET2_HIT.value, "TARGET2_HIT")
        self.assertEqual(TradeStatus.STOPPED_OUT.value, "STOPPED_OUT")
    
    def test_position_status_enum(self):
        """Test PositionStatus enum values"""
        self.assertEqual(PositionStatus.FULL.value, "FULL")
        self.assertEqual(PositionStatus.HALF.value, "HALF")
        self.assertEqual(PositionStatus.CLOSED.value, "CLOSED")
    
    async def test_multiple_positions_management(self):
        """Test managing multiple active positions"""
        # Execute multiple alerts
        alerts = [
            ParsedAlert(raw_message="Alert 1", is_valid=True, price=4500.0, size="A", stop=4490.0, target_1=4510.0, target_2=4520.0),
            ParsedAlert(raw_message="Alert 2", is_valid=True, price=4505.0, size="B", stop=4495.0, target_1=4515.0, target_2=4525.0),
            ParsedAlert(raw_message="Alert 3", is_valid=True, price=4510.0, size="C", stop=4500.0, target_1=4520.0, target_2=4530.0)
        ]
        
        for i, alert in enumerate(alerts):
            alert.alert_id = i + 1
            result = await self.executor.execute_alert(alert)
            self.assertTrue(result)
        
        # Verify all positions are active
        self.assertEqual(len(self.executor.active_positions), 3)
        # Note: daily_trade_count is incremented when trades are filled, not submitted
        
        # Verify different position sizes
        positions = list(self.executor.active_positions.values())
        self.assertEqual(positions[0].full_quantity, 6)  # A = 6
        self.assertEqual(positions[1].full_quantity, 4)  # B = 4
        self.assertEqual(positions[2].full_quantity, 2)  # C = 2


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
for name in dir(TestTradeExecutor):
    if name.startswith('test_') and asyncio.iscoroutinefunction(getattr(TestTradeExecutor, name)):
        setattr(TestTradeExecutor, name, async_test(getattr(TestTradeExecutor, name)))


if __name__ == '__main__':
    unittest.main()
