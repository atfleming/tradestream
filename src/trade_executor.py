"""
Advanced Trade Executor for JMoney Discord Alert Trading System
Implements sophisticated position management with Target 1/Target 2 logic:
- Target 1: Exit 50% of position, move stop to breakeven
- Target 2: Exit remaining 50%
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

try:
    from .config import ConfigManager
    from .database import DatabaseManager
    from .message_parser import ParsedAlert
    from .tsx_integration import TopStepXIntegration
    from .email_notifier import EmailNotifier
    from .trade_models import TradeStatus, PositionStatus, TradePosition, OrderInfo
except ImportError:
    from config import ConfigManager
    from database import DatabaseManager
    from message_parser import ParsedAlert
    from tsx_integration import TopStepXIntegration
    from email_notifier import EmailNotifier
    from trade_models import TradeStatus, PositionStatus, TradePosition, OrderInfo


# Trade models are now imported from trade_models.py to avoid circular dependencies


class TradeExecutor:
    """Advanced trade executor with sophisticated position management"""
    
    def __init__(self, config: ConfigManager, db: DatabaseManager, 
                 tsx_api: Optional[TopStepXIntegration] = None, 
                 email_notifier: Optional[EmailNotifier] = None):
        """
        Initialize trade executor
        
        Args:
            config: Configuration manager
            db: Database manager
            tsx_api: TopStepX API integration (for live trading)
            email_notifier: Email notification system
        """
        self.config = config
        self.db = db
        self.tsx_api = tsx_api
        self.paper_trader = None  # Set later to avoid circular import
        self.email_notifier = email_notifier
        self.logger = logging.getLogger(__name__)
        
        # Trading mode configuration
        self.paper_trading_enabled = config.trading.paper_trading_enabled if config.trading else False
        self.live_trading_enabled = config.trading.live_trading_enabled if config.trading else False
        self.concurrent_trading = config.trading.concurrent_trading if config.trading else False
        
        # Active positions tracking
        self.active_positions: Dict[int, TradePosition] = {}
        
        # Size mapping from config
        self.size_mapping = {
            'A': 1,
            'B': 2,
            'C': 3
        }
        if self.config.trading and hasattr(self.config.trading, 'size_mapping'):
            self.size_mapping.update(self.config.trading.size_mapping)
        
        # Risk management settings
        self.max_daily_trades = getattr(self.config.trading, 'max_daily_trades', 10) if self.config.trading else 10
        self.max_position_size = getattr(self.config.trading, 'max_position_size', 5) if self.config.trading else 5
        self.enable_auto_trading = getattr(self.config.trading, 'enable_auto_trading', False) if self.config.trading else False
        
        # Daily tracking
        self.daily_trade_count = 0
        self.daily_pnl = 0.0
        
        # Price monitoring
        self.price_monitor_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
    
    def set_paper_trader(self, paper_trader):
        """Set paper trader after initialization to avoid circular import"""
        self.paper_trader = paper_trader
        self.logger.info("Paper trader set successfully")
    
    async def initialize(self) -> bool:
        """Initialize the trade executor"""
        try:
            self.logger.info("Initializing Trade Executor...")
            
            # Load active positions from database
            await self._load_active_positions()
            
            # Start price monitoring if we have active positions
            if self.active_positions:
                await self._start_price_monitoring()
            
            # Get daily trade count
            self.daily_trade_count = self.db.get_daily_trade_count()
            
            # Log MES contract specifications
            if self.config.trading:
                self.logger.info(f"📊 Trading Contract: {self.config.trading.symbol} ({self.config.trading.contract_name})")
                self.logger.info(f"📊 Exchange: {self.config.trading.exchange}")
                self.logger.info(f"📊 Tick Size: {self.config.trading.tick_size} points")
                self.logger.info(f"📊 Tick Value: ${self.config.trading.tick_value} per tick")
                self.logger.info(f"📊 Margin Requirement: ${self.config.trading.margin_requirement} per contract")
                
                # Log trading modes
                self.logger.info(f"🎯 Paper Trading: {'✅ ENABLED' if self.paper_trading_enabled else '❌ DISABLED'}")
                self.logger.info(f"🚀 Live Trading: {'✅ ENABLED' if self.live_trading_enabled else '❌ DISABLED'}")
                if self.concurrent_trading:
                    self.logger.info(f"⚡ Concurrent Mode: ✅ ENABLED (Both paper and live)")
                
                if self.paper_trading_enabled and self.paper_trader:
                    paper_stats = self.paper_trader.get_paper_statistics()
                    self.logger.info(f"💰 Paper Account Balance: ${paper_stats['account_balance']:,.2f}")
            
            self.logger.info(f"✅ Trade Executor initialized - Active positions: {len(self.active_positions)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing trade executor: {e}")
            return False
    
    async def execute_alert(self, alert: ParsedAlert) -> bool:
        """
        Execute a trading alert with advanced position management
        
        Args:
            alert: Parsed alert from JMoney
            
        Returns:
            True if execution started successfully
        """
        try:
            if not alert.is_valid:
                self.logger.warning("Cannot execute invalid alert")
                return False
            
            # Check if auto trading is enabled
            if not self.enable_auto_trading:
                self.logger.info("Auto trading disabled - alert logged but not executed")
                return False
            
            # Risk management checks
            if not await self._pre_trade_risk_checks(alert):
                return False
            
            # Create trade position
            position = await self._create_trade_position(alert)
            if not position:
                return False
            
            # Execute entry order
            if await self._execute_entry_order(position):
                self.active_positions[position.alert_id] = position
                
                # Start price monitoring if not already running
                if not self.is_monitoring:
                    await self._start_price_monitoring()
                
                self.logger.info(f"✅ Trade execution started for alert {position.alert_id}")
                
                # Send email notification
                if self.email_notifier:
                    await self._send_trade_notification(position, "ENTRY_SUBMITTED")
                
                return True
            else:
                self.logger.error(f"Failed to execute entry order for alert {position.alert_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing alert: {e}")
            return False
    
    async def _pre_trade_risk_checks(self, alert: ParsedAlert) -> bool:
        """Perform pre-trade risk management checks"""
        try:
            # Check daily trade limit
            if self.daily_trade_count >= self.max_daily_trades:
                self.logger.warning(f"Daily trade limit reached: {self.daily_trade_count}/{self.max_daily_trades}")
                return False
            
            # Check position size limit
            total_quantity = sum(pos.current_quantity for pos in self.active_positions.values())
            new_quantity = self.size_mapping.get(alert.size, 1)
            
            if total_quantity + new_quantity > self.max_position_size:
                self.logger.warning(f"Position size limit exceeded: {total_quantity + new_quantity}/{self.max_position_size}")
                return False
            
            # Check account balance
            account_balance = self.tsx_api.get_account_balance()
            if account_balance < 1000:  # Minimum balance check
                self.logger.warning(f"Insufficient account balance: ${account_balance}")
                return False
            
            # Check market hours
            if not self.tsx_api.is_market_open():
                self.logger.warning("Market is closed")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in pre-trade risk checks: {e}")
            return False
    
    async def _create_trade_position(self, alert: ParsedAlert) -> Optional[TradePosition]:
        """Create a new trade position from alert"""
        try:
            # Get quantity from size mapping
            quantity = self.size_mapping.get(alert.size, 1)
            
            # Create position
            position = TradePosition(
                alert_id=alert.alert_id or 0,
                entry_price=alert.price,
                stop_price=alert.stop,
                target1_price=alert.target_1,
                target2_price=alert.target_2,
                size_code=alert.size,
                full_quantity=quantity,
                current_quantity=quantity,
                position_status=PositionStatus.FULL,
                trade_status=TradeStatus.PENDING
            )
            
            # Insert trade record in database
            trade_id = self.db.insert_trade(
                alert_id=position.alert_id,
                entry_price=position.entry_price,
                quantity=position.full_quantity,
                stop_price=position.stop_price,
                target_price=position.target1_price,  # Will update for T2 later
                status="PENDING"
            )
            
            position.trade_id = trade_id
            
            self.logger.info(f"Created trade position: {position.size_code} {position.full_quantity} @ {position.entry_price}")
            return position
            
        except Exception as e:
            self.logger.error(f"Error creating trade position: {e}")
            return None
    
    async def _route_order(self, order_type: str, side: str, quantity: int, 
                          price: Optional[float] = None) -> List[OrderInfo]:
        """Route order to appropriate trading system(s)"""
        orders = []
        
        try:
            # Paper trading
            if self.paper_trading_enabled and self.paper_trader:
                if order_type == "MARKET":
                    paper_order = await self.paper_trader.place_market_order(side, quantity)
                elif order_type == "STOP":
                    paper_order = await self.paper_trader.place_stop_order(side, quantity, price)
                
                if paper_order:
                    # Mark as paper order
                    paper_order.order_id = f"PAPER_{paper_order.order_id}"
                    orders.append(paper_order)
                    self.logger.info(f"📝 Paper Order: {order_type} {side} {quantity} @ {price or 'market'}")
            
            # Live trading
            if self.live_trading_enabled and self.tsx_api:
                if order_type == "MARKET":
                    live_order = await self.tsx_api.place_market_order(side, quantity)
                elif order_type == "STOP":
                    live_order = await self.tsx_api.place_stop_order(side, quantity, price)
                
                if live_order:
                    # Mark as live order
                    live_order.order_id = f"LIVE_{live_order.order_id}"
                    orders.append(live_order)
                    self.logger.info(f"🚀 Live Order: {order_type} {side} {quantity} @ {price or 'market'}")
            
            return orders
            
        except Exception as e:
            self.logger.error(f"Error routing order: {e}")
            return []
    
    async def _execute_entry_order(self, position: TradePosition) -> bool:
        """Execute the initial entry order"""
        try:
            self.logger.info(f"Executing entry order: BUY {position.full_quantity} @ market")
            
            # Route order to appropriate trading system(s)
            orders = await self._route_order("MARKET", "BUY", position.full_quantity)
            
            if orders:
                # Store all order IDs (comma-separated for multiple orders)
                order_ids = [order.order_id for order in orders]
                position.entry_order_id = ",".join(order_ids)
                position.trade_status = TradeStatus.ENTRY_SUBMITTED
                position.updated_at = datetime.now(timezone.utc)
                
                # Update database
                if position.trade_id:
                    self.db.update_trade_status(position.trade_id, "ENTRY_SUBMITTED")
                
                self.logger.info(f"✅ Entry order(s) submitted: {position.entry_order_id}")
                return True
            else:
                self.logger.error("Failed to place entry order")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing entry order: {e}")
            return False
    
    async def _start_price_monitoring(self):
        """Start monitoring prices for active positions"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.price_monitor_task = asyncio.create_task(self._price_monitoring_loop())
        self.logger.info("✅ Price monitoring started")
    
    async def _price_monitoring_loop(self):
        """Main price monitoring loop"""
        while self.is_monitoring and self.active_positions:
            try:
                # Get current market price from appropriate source
                current_price = None
                
                # Prefer live price if available
                if self.live_trading_enabled and self.tsx_api:
                    current_price = self.tsx_api.get_current_price()
                
                # Fallback to paper trading price
                if current_price is None and self.paper_trading_enabled and self.paper_trader:
                    current_price = self.paper_trader.get_current_price()
                
                if current_price:
                    # Check all active positions
                    for position in list(self.active_positions.values()):
                        await self._check_position_targets(position, current_price)
                
                # Sleep for a short interval (e.g., 1 second)
                await asyncio.sleep(1.0)
                
            except Exception as e:
                self.logger.error(f"Error in price monitoring loop: {e}")
                await asyncio.sleep(5.0)  # Longer sleep on error
        
        self.is_monitoring = False
        self.logger.info("Price monitoring stopped")
    
    async def _check_position_targets(self, position: TradePosition, current_price: float):
        """Check if position targets or stops are hit"""
        try:
            # Skip if position is not filled yet
            if position.trade_status not in [TradeStatus.ENTRY_FILLED, TradeStatus.STOP_PLACED, TradeStatus.TARGET1_HIT]:
                return
            
            # Check Target 1 (only if full position)
            if (position.position_status == PositionStatus.FULL and 
                position.trade_status != TradeStatus.TARGET1_HIT and
                current_price >= position.target1_price):
                
                await self._handle_target1_hit(position, current_price)
            
            # Check Target 2 (only if half position)
            elif (position.position_status == PositionStatus.HALF and 
                  position.trade_status == TradeStatus.TARGET1_HIT and
                  current_price >= position.target2_price):
                
                await self._handle_target2_hit(position, current_price)
            
            # Check Stop Loss
            elif current_price <= position.stop_price:
                await self._handle_stop_hit(position, current_price)
                
        except Exception as e:
            self.logger.error(f"Error checking position targets: {e}")
    
    async def _handle_target1_hit(self, position: TradePosition, current_price: float):
        """Handle Target 1 hit - Exit 50% and move stop to breakeven"""
        try:
            self.logger.info(f"🎯 TARGET 1 HIT! Position {position.alert_id} @ {current_price}")
            
            # Calculate half quantity
            half_quantity = position.full_quantity // 2
            if half_quantity == 0:
                half_quantity = 1  # Ensure at least 1 contract
            
            # Place sell order for half position
            sell_orders = await self._route_order("MARKET", "SELL", half_quantity)
            
            if sell_orders:
                # Update position
                order_ids = [order.order_id for order in sell_orders]
                position.target1_order_id = ",".join(order_ids)
                position.target1_fill_price = current_price
                position.target1_fill_time = datetime.now(timezone.utc)
                position.current_quantity = position.full_quantity - half_quantity
                position.position_status = PositionStatus.HALF
                position.trade_status = TradeStatus.TARGET1_HIT
                position.updated_at = datetime.now(timezone.utc)
                
                # Calculate realized P&L for the half position using MES tick value
                tick_value = self.config.trading.tick_value if self.config.trading else 1.25
                target1_pnl = (current_price - position.entry_fill_price) * half_quantity * tick_value
                position.realized_pnl += target1_pnl
                self.daily_pnl += target1_pnl
                
                # Update paper trading P&L if applicable
                if self.paper_trading_enabled and self.paper_trader:
                    self.paper_trader.update_trade_pnl(target1_pnl)
                
                # Cancel existing stop orders
                if position.stop_order_id:
                    stop_order_ids = position.stop_order_id.split(",")
                    for stop_id in stop_order_ids:
                        if stop_id.startswith("PAPER_") and self.paper_trader:
                            await self.paper_trader.cancel_order(stop_id.replace("PAPER_", ""))
                        elif stop_id.startswith("LIVE_") and self.tsx_api:
                            await self.tsx_api.cancel_order(stop_id.replace("LIVE_", ""))
                
                # Place new stop at breakeven for remaining position
                breakeven_stops = await self._route_order(
                    "STOP", "SELL", position.current_quantity, position.entry_fill_price
                )
                
                if breakeven_stops:
                    stop_order_ids = [order.order_id for order in breakeven_stops]
                    position.stop_order_id = ",".join(stop_order_ids)
                    position.stop_price = position.entry_fill_price  # Update stop to breakeven
                
                # Update database
                if position.trade_id:
                    self.db.update_trade_status(position.trade_id, "TARGET1_HIT")
                    self.db.update_trade_pnl(position.trade_id, position.realized_pnl)
                
                self.logger.info(f"✅ Target 1 executed: Sold {half_quantity} @ {current_price}, P&L: ${target1_pnl:.2f}")
                self.logger.info(f"✅ Stop moved to breakeven: {position.entry_fill_price}")
                
                # Send email notification
                if self.email_notifier:
                    await self._send_trade_notification(position, "TARGET1_HIT")
                
            else:
                self.logger.error("Failed to execute Target 1 sell order")
                
        except Exception as e:
            self.logger.error(f"Error handling Target 1 hit: {e}")
    
    async def _handle_target2_hit(self, position: TradePosition, current_price: float):
        """Handle Target 2 hit - Exit remaining position"""
        try:
            self.logger.info(f"🎯 TARGET 2 HIT! Position {position.alert_id} @ {current_price}")
            
            # Place sell order for remaining position
            sell_order = await self.tsx_api.place_market_order(
                side="SELL",
                quantity=position.current_quantity
            )
            
            if sell_order:
                # Update position
                position.target2_order_id = sell_order.order_id
                position.target2_fill_price = current_price
                position.target2_fill_time = datetime.now(timezone.utc)
                position.trade_status = TradeStatus.TARGET2_HIT
                position.position_status = PositionStatus.CLOSED
                position.updated_at = datetime.now(timezone.utc)
                
                # Calculate realized P&L for remaining position using MES tick value
                tick_value = self.config.trading.tick_value if self.config.trading else 1.25
                target2_pnl = (current_price - position.entry_fill_price) * position.current_quantity * tick_value
                position.realized_pnl += target2_pnl
                self.daily_pnl += target2_pnl
                
                position.current_quantity = 0
                
                # Cancel stop order
                if position.stop_order_id:
                    await self.tsx_api.cancel_order(position.stop_order_id)
                
                # Update database
                if position.trade_id:
                    self.db.update_trade_status(position.trade_id, "TARGET2_HIT")
                    self.db.update_trade_pnl(position.trade_id, position.realized_pnl)
                
                # Remove from active positions
                if position.alert_id in self.active_positions:
                    del self.active_positions[position.alert_id]
                
                total_pnl = position.realized_pnl
                self.logger.info(f"✅ Target 2 executed: Sold {position.current_quantity} @ {current_price}")
                self.logger.info(f"🎉 TRADE COMPLETE! Total P&L: ${total_pnl:.2f}")
                
                # Send email notification
                if self.email_notifier:
                    await self._send_trade_notification(position, "TARGET2_HIT")
                
            else:
                self.logger.error("Failed to execute Target 2 sell order")
                
        except Exception as e:
            self.logger.error(f"Error handling Target 2 hit: {e}")
    
    async def _handle_stop_hit(self, position: TradePosition, current_price: float):
        """Handle stop loss hit"""
        try:
            self.logger.warning(f"🛑 STOP HIT! Position {position.alert_id} @ {current_price}")
            
            # Place sell order for current position
            sell_order = await self.tsx_api.place_market_order(
                side="SELL",
                quantity=position.current_quantity
            )
            
            if sell_order:
                # Update position
                position.stop_fill_price = current_price
                position.stop_fill_time = datetime.now(timezone.utc)
                position.trade_status = TradeStatus.STOPPED_OUT
                position.position_status = PositionStatus.CLOSED
                position.updated_at = datetime.now(timezone.utc)
                
                # Calculate realized P&L using MES tick value
                tick_value = self.config.trading.tick_value if self.config.trading else 1.25
                stop_pnl = (current_price - position.entry_fill_price) * position.current_quantity * tick_value
                position.realized_pnl += stop_pnl
                self.daily_pnl += stop_pnl
                
                position.current_quantity = 0
                
                # Update database
                if position.trade_id:
                    self.db.update_trade_status(position.trade_id, "STOPPED_OUT")
                    self.db.update_trade_pnl(position.trade_id, position.realized_pnl)
                
                # Remove from active positions
                if position.alert_id in self.active_positions:
                    del self.active_positions[position.alert_id]
                
                self.logger.info(f"✅ Stop executed: Sold {position.current_quantity} @ {current_price}, P&L: ${position.realized_pnl:.2f}")
                
                # Send email notification
                if self.email_notifier:
                    await self._send_trade_notification(position, "STOPPED_OUT")
                
            else:
                self.logger.error("Failed to execute stop loss order")
                
        except Exception as e:
            self.logger.error(f"Error handling stop hit: {e}")
    
    async def _load_active_positions(self):
        """Load active positions from database"""
        try:
            # This would load any positions that were active when the system was last running
            # For now, start with empty positions - this would be implemented based on database schema
            self.active_positions = {}
            self.logger.info("Active positions loaded from database")
            
        except Exception as e:
            self.logger.error(f"Error loading active positions: {e}")
    
    async def _send_trade_notification(self, position: TradePosition, event_type: str):
        """Send email notification for trade events"""
        try:
            if not self.email_notifier:
                return
            
            # Create trade data for email with explicit MES contract details
            symbol = self.config.trading.symbol if self.config.trading else 'MES'
            contract_name = self.config.trading.contract_name if self.config.trading else 'Micro E-mini S&P 500'
            
            trade_data = {
                'alert_id': position.alert_id,
                'symbol': symbol,
                'contract_name': contract_name,
                'side': 'LONG',
                'quantity': position.full_quantity,
                'entry_price': position.entry_fill_price or position.entry_price,
                'current_price': position.target1_fill_price or position.target2_fill_price or position.stop_fill_price,
                'pnl': position.realized_pnl,
                'event_type': event_type,
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Send appropriate notification
            if event_type == "ENTRY_SUBMITTED":
                tick_value = self.config.trading.tick_value if self.config.trading else 1.25
                await self.email_notifier.send_alert_email(
                    alert_id=position.alert_id,
                    symbol=symbol,
                    side='LONG',
                    entry_price=position.entry_price,
                    stop_price=position.stop_price,
                    target1_price=position.target1_price,
                    target2_price=position.target2_price,
                    quantity=position.full_quantity,
                    risk_amount=abs(position.entry_price - position.stop_price) * position.full_quantity * tick_value
                )
            else:
                await self.email_notifier.send_trade_email(trade_data)
                
        except Exception as e:
            self.logger.error(f"Error sending trade notification: {e}")
    
    def get_active_positions(self) -> Dict[int, TradePosition]:
        """Get all active positions"""
        return self.active_positions.copy()
    
    def get_daily_pnl(self) -> float:
        """Get daily P&L"""
        return self.daily_pnl
    
    def get_daily_trade_count(self) -> int:
        """Get daily trade count"""
        return self.daily_trade_count
    
    async def shutdown(self):
        """Shutdown the trade executor"""
        try:
            self.is_monitoring = False
            
            if self.price_monitor_task:
                self.price_monitor_task.cancel()
                try:
                    await self.price_monitor_task
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("✅ Trade Executor shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


# Global instance (will be initialized by main application)
trade_executor: Optional[TradeExecutor] = None
