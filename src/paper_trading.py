"""
Paper Trading Simulator for JMoney Discord Alert Trading System
Simulates realistic trading without actual money at risk
"""

import logging
import asyncio
import random
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

try:
    from .config import ConfigManager, PaperTradingConfig
    from .database import DatabaseManager
    from .message_parser import ParsedAlert
    from .trade_executor import TradePosition, TradeStatus, PositionStatus, OrderInfo
except ImportError:
    from config import ConfigManager, PaperTradingConfig
    from database import DatabaseManager
    from message_parser import ParsedAlert
    from trade_executor import TradePosition, TradeStatus, PositionStatus, OrderInfo


@dataclass
class PaperAccount:
    """Paper trading account state"""
    starting_balance: float
    current_balance: float
    available_margin: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    max_drawdown: float = 0.0
    peak_balance: float = 0.0
    commission_paid: float = 0.0
    
    def __post_init__(self):
        if self.peak_balance == 0.0:
            self.peak_balance = self.starting_balance


class PaperTradingSimulator:
    """Simulates trading without real money"""
    
    def __init__(self, config: ConfigManager, db: DatabaseManager):
        """
        Initialize paper trading simulator
        
        Args:
            config: Configuration manager
            db: Database manager
        """
        self.config = config
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # Paper trading configuration
        self.paper_config = config.trading.paper_trading if config.trading else PaperTradingConfig()
        
        # Paper account
        self.account = PaperAccount(
            starting_balance=self.paper_config.starting_balance,
            current_balance=self.paper_config.starting_balance,
            available_margin=self.paper_config.starting_balance * 0.8  # 80% available for trading
        )
        
        # Active paper positions
        self.paper_positions: Dict[int, TradePosition] = {}
        
        # Market data simulation
        self.current_price = 6300.0  # Starting ES price
        self.price_volatility = 2.0  # Price movement volatility
        
        # Order tracking
        self.next_order_id = 1000
        self.pending_orders: Dict[str, Dict[str, Any]] = {}
        
        # Statistics tracking
        self.daily_stats = {
            'trades': 0,
            'pnl': 0.0,
            'wins': 0,
            'losses': 0
        }
        
    async def initialize(self) -> bool:
        """Initialize paper trading simulator"""
        try:
            self.logger.info("🎯 Initializing Paper Trading Simulator...")
            
            # Load any existing paper positions from database
            await self._load_paper_positions()
            
            # Start price simulation
            await self._start_price_simulation()
            
            self.logger.info(f"✅ Paper Trading Simulator initialized")
            self.logger.info(f"📊 Paper Account Balance: ${self.account.current_balance:,.2f}")
            self.logger.info(f"📊 Available Margin: ${self.account.available_margin:,.2f}")
            self.logger.info(f"📊 Active Paper Positions: {len(self.paper_positions)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing paper trading simulator: {e}")
            return False
    
    async def place_market_order(self, side: str, quantity: int, 
                               contract_id: Optional[str] = None) -> Optional[OrderInfo]:
        """
        Simulate placing a market order
        
        Args:
            side: "BUY" or "SELL"
            quantity: Number of contracts
            contract_id: Contract ID (ignored for paper trading)
            
        Returns:
            OrderInfo with simulated order details
        """
        try:
            order_id = str(self.next_order_id)
            self.next_order_id += 1
            
            # Simulate realistic fill price with slippage
            fill_price = self._simulate_fill_price(side, "MARKET")
            
            # Calculate commission
            commission = quantity * self.paper_config.commission_per_contract
            
            # Create order info
            order_info = OrderInfo(
                order_id=order_id,
                side=side,
                quantity=quantity,
                order_type="MARKET",
                status="FILLED",
                fill_price=fill_price,
                fill_quantity=quantity,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Update account balance
            if side == "BUY":
                cost = fill_price * quantity * self.config.trading.tick_value + commission
                self.account.available_margin -= cost
            else:  # SELL
                proceeds = fill_price * quantity * self.config.trading.tick_value - commission
                self.account.available_margin += proceeds
            
            self.account.commission_paid += commission
            
            self.logger.info(f"📝 Paper Order Filled: {side} {quantity} @ {fill_price:.2f} (Order: {order_id})")
            self.logger.info(f"💰 Commission: ${commission:.2f}, Available Margin: ${self.account.available_margin:,.2f}")
            
            # Log to database with paper trading flag
            self.db.log_system_event(
                level="INFO",
                component="paper_trading",
                message=f"Paper order filled: {side} {quantity} @ {fill_price}",
                details=f"Order ID: {order_id}, Commission: ${commission:.2f}"
            )
            
            return order_info
            
        except Exception as e:
            self.logger.error(f"Error placing paper market order: {e}")
            return None
    
    async def place_stop_order(self, side: str, quantity: int, stop_price: float,
                             contract_id: Optional[str] = None) -> Optional[OrderInfo]:
        """
        Simulate placing a stop order
        
        Args:
            side: "BUY" or "SELL"
            quantity: Number of contracts
            stop_price: Stop trigger price
            contract_id: Contract ID (ignored for paper trading)
            
        Returns:
            OrderInfo with simulated order details
        """
        try:
            order_id = str(self.next_order_id)
            self.next_order_id += 1
            
            # Create pending stop order
            self.pending_orders[order_id] = {
                'side': side,
                'quantity': quantity,
                'stop_price': stop_price,
                'order_type': 'STOP',
                'timestamp': datetime.now(timezone.utc)
            }
            
            order_info = OrderInfo(
                order_id=order_id,
                side=side,
                quantity=quantity,
                price=stop_price,
                order_type="STOP",
                status="SUBMITTED",
                timestamp=datetime.now(timezone.utc)
            )
            
            self.logger.info(f"📝 Paper Stop Order Placed: {side} {quantity} @ {stop_price:.2f} (Order: {order_id})")
            
            return order_info
            
        except Exception as e:
            self.logger.error(f"Error placing paper stop order: {e}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending paper order"""
        try:
            if order_id in self.pending_orders:
                del self.pending_orders[order_id]
                self.logger.info(f"📝 Paper Order Cancelled: {order_id}")
                return True
            else:
                self.logger.warning(f"Paper order {order_id} not found for cancellation")
                return False
                
        except Exception as e:
            self.logger.error(f"Error cancelling paper order: {e}")
            return False
    
    def _simulate_fill_price(self, side: str, order_type: str) -> float:
        """Simulate realistic fill price with slippage"""
        base_price = self.current_price
        
        if not self.paper_config.realistic_slippage:
            return base_price
        
        # Add realistic slippage
        slippage_amount = self.paper_config.slippage_ticks * self.config.trading.tick_size
        
        if order_type == "MARKET":
            if side == "BUY":
                # Market buy orders typically fill slightly higher
                return base_price + (slippage_amount * random.uniform(0.5, 1.5))
            else:  # SELL
                # Market sell orders typically fill slightly lower
                return base_price - (slippage_amount * random.uniform(0.5, 1.5))
        
        return base_price
    
    async def _start_price_simulation(self):
        """Start simulating market price movements"""
        asyncio.create_task(self._price_simulation_loop())
    
    async def _price_simulation_loop(self):
        """Simulate realistic price movements"""
        while True:
            try:
                # Simulate price movement (random walk with slight upward bias)
                price_change = random.gauss(0.05, self.price_volatility)  # Slight upward bias
                self.current_price += price_change
                
                # Keep price in reasonable range
                self.current_price = max(6000.0, min(7000.0, self.current_price))
                
                # Check pending stop orders
                await self._check_pending_orders()
                
                # Sleep for simulation interval (1 second = 1 minute of market time)
                await asyncio.sleep(1.0)
                
            except Exception as e:
                self.logger.error(f"Error in price simulation: {e}")
                await asyncio.sleep(5.0)
    
    async def _check_pending_orders(self):
        """Check if any pending stop orders should be triggered"""
        triggered_orders = []
        
        for order_id, order_data in self.pending_orders.items():
            if order_data['order_type'] == 'STOP':
                stop_price = order_data['stop_price']
                side = order_data['side']
                
                # Check if stop should trigger
                should_trigger = False
                if side == "SELL" and self.current_price <= stop_price:
                    should_trigger = True
                elif side == "BUY" and self.current_price >= stop_price:
                    should_trigger = True
                
                if should_trigger:
                    triggered_orders.append(order_id)
        
        # Execute triggered orders
        for order_id in triggered_orders:
            await self._execute_triggered_order(order_id)
    
    async def _execute_triggered_order(self, order_id: str):
        """Execute a triggered stop order"""
        try:
            order_data = self.pending_orders[order_id]
            
            # Simulate fill
            fill_price = self._simulate_fill_price(order_data['side'], "STOP")
            quantity = order_data['quantity']
            commission = quantity * self.paper_config.commission_per_contract
            
            # Update account
            if order_data['side'] == "SELL":
                proceeds = fill_price * quantity * self.config.trading.tick_value - commission
                self.account.available_margin += proceeds
            
            self.account.commission_paid += commission
            
            self.logger.info(f"🛑 Paper Stop Order Triggered: {order_data['side']} {quantity} @ {fill_price:.2f}")
            
            # Remove from pending orders
            del self.pending_orders[order_id]
            
        except Exception as e:
            self.logger.error(f"Error executing triggered order: {e}")
    
    def get_current_price(self) -> float:
        """Get current simulated market price"""
        return self.current_price
    
    def get_account_balance(self) -> float:
        """Get current paper account balance"""
        return self.account.current_balance
    
    def get_available_margin(self) -> float:
        """Get available paper margin"""
        return self.account.available_margin
    
    def get_current_positions(self) -> Dict[str, Any]:
        """Get current paper positions"""
        return {
            'MES': {
                'quantity': sum(pos.current_quantity for pos in self.paper_positions.values()),
                'unrealized_pnl': sum(pos.unrealized_pnl for pos in self.paper_positions.values())
            }
        }
    
    def is_market_open(self) -> bool:
        """Paper market is always open"""
        return True
    
    def update_trade_pnl(self, trade_pnl: float):
        """Update paper account with trade P&L"""
        self.account.realized_pnl += trade_pnl
        self.account.current_balance += trade_pnl
        
        # Update statistics
        self.account.total_trades += 1
        if trade_pnl > 0:
            self.account.winning_trades += 1
            self.account.consecutive_wins += 1
            self.account.consecutive_losses = 0
            self.account.largest_win = max(self.account.largest_win, trade_pnl)
        else:
            self.account.losing_trades += 1
            self.account.consecutive_losses += 1
            self.account.consecutive_wins = 0
            self.account.largest_loss = min(self.account.largest_loss, trade_pnl)
        
        # Update peak balance and drawdown
        if self.account.current_balance > self.account.peak_balance:
            self.account.peak_balance = self.account.current_balance
        
        current_drawdown = self.account.peak_balance - self.account.current_balance
        self.account.max_drawdown = max(self.account.max_drawdown, current_drawdown)
        
        self.logger.info(f"💰 Paper Account Updated: Balance: ${self.account.current_balance:,.2f}, P&L: ${trade_pnl:+.2f}")
    
    def get_paper_statistics(self) -> Dict[str, Any]:
        """Get comprehensive paper trading statistics"""
        win_rate = (self.account.winning_trades / self.account.total_trades * 100) if self.account.total_trades > 0 else 0
        
        return {
            'account_balance': self.account.current_balance,
            'starting_balance': self.account.starting_balance,
            'total_pnl': self.account.realized_pnl,
            'total_trades': self.account.total_trades,
            'winning_trades': self.account.winning_trades,
            'losing_trades': self.account.losing_trades,
            'win_rate': win_rate,
            'largest_win': self.account.largest_win,
            'largest_loss': self.account.largest_loss,
            'max_drawdown': self.account.max_drawdown,
            'commission_paid': self.account.commission_paid,
            'consecutive_wins': self.account.consecutive_wins,
            'consecutive_losses': self.account.consecutive_losses,
            'active_positions': len(self.paper_positions)
        }
    
    async def _load_paper_positions(self):
        """Load paper positions from database"""
        try:
            # This would load paper positions from database
            # For now, start with empty positions
            self.paper_positions = {}
            self.logger.info("Paper positions loaded from database")
            
        except Exception as e:
            self.logger.error(f"Error loading paper positions: {e}")
    
    async def disconnect(self):
        """Disconnect paper trading simulator"""
        try:
            self.logger.info("✅ Paper Trading Simulator disconnected")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting paper trading: {e}")


# Global instance (will be initialized by main application)
paper_trader: Optional[PaperTradingSimulator] = None
