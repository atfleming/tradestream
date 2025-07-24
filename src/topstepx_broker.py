"""
TopStepX Live Broker Integration for TradeStream

This module provides live trading execution through TopStepX API using TradeForgePy library.
Integrates with existing TradeStream architecture while replacing paper trading with live execution.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass

try:
    from tradeforgepy import TradeForgePy
    from tradeforgepy.exceptions import TradeForgeError
    from tradeforgepy.core.enums import MarketDataType, StreamConnectionStatus
    TRADEFORGEPY_AVAILABLE = True
except ImportError:
    TRADEFORGEPY_AVAILABLE = False

from trade_models import TradeStatus, PositionStatus, TradePosition, OrderInfo


@dataclass
class TopStepXConfig:
    """Configuration for TopStepX broker integration"""
    username: str
    api_key: str
    environment: str = "DEMO"  # "DEMO" or "LIVE"
    account_id: Optional[str] = None
    enable_streaming: bool = True
    order_timeout_seconds: int = 30


class TopStepXBroker:
    """
    TopStepX Live Broker Integration
    
    Provides live trading execution through TopStepX API using TradeForgePy
    while maintaining compatibility with existing TradeStream architecture and strategy logic.
    """
    
    def __init__(self, config: TopStepXConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize TradeForgePy provider
        self.provider: Optional[TradeForgePy] = None
        self.account_id: Optional[str] = None
        
        # Active positions and orders tracking
        self.active_positions: Dict[str, TradePosition] = {}
        self.active_orders: Dict[str, OrderInfo] = {}
        
        # Connection status
        self.is_connected = False
        self.stream_status = StreamConnectionStatus.DISCONNECTED
        
        # Event handlers
        self.position_updates = []
        
        if not TRADEFORGEPY_AVAILABLE:
            raise ImportError("TradeForgePy library not available. Install with: pip install tradeforgepy")
    
    async def initialize(self) -> bool:
        """
        Initialize TopStepX broker connection and authentication
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Initializing TopStepX broker connection...")
            
            # Create TradeForgePy provider for TopStepX
            # Note: TradeForgePy automatically loads credentials from .env file
            self.provider = TradeForgePy.create_provider("TopStepX")
            
            # Set up event handlers
            self.provider.on_event(self._handle_market_event)
            self.provider.on_status_change(self._handle_status_change)
            self.provider.on_error(self._handle_stream_error)
            
            # Connect to the provider
            await self.provider.connect()
            self.logger.info("✅ TopStepX connection established")
            
            # Get account information
            accounts = await self.provider.get_accounts()
            if not accounts:
                self.logger.error("No active TopStepX accounts found")
                return False
            
            # Use specified account or first active account
            if self.config.account_id:
                account = next((acc for acc in accounts if acc.provider_account_id == self.config.account_id), None)
                if not account:
                    self.logger.error(f"Specified account ID {self.config.account_id} not found")
                    return False
            else:
                account = accounts[0]
            
            self.account_id = account.provider_account_id
            self.logger.info(f"Using TopStepX account: {account.account_name} (ID: {account.provider_account_id}, Balance: ${account.balance})")
            
            # Start streaming if enabled
            if self.config.enable_streaming:
                await self._start_streaming()
            
            self.is_connected = True
            self.logger.info("✅ TopStepX broker initialization complete")
            return True
            
        except TradeForgeError as e:
            self.logger.error(f"TopStepX API error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"TopStepX initialization error: {e}", exc_info=True)
            return False
    
    async def _start_streaming(self):
        """Start real-time data streaming"""
        try:
            # Start the streaming runner in the background
            self.stream_task = asyncio.create_task(self.provider.run_forever())
            
            # Wait for connection to be established
            await asyncio.sleep(2)
            
            self.logger.info(f"✅ TopStepX streaming started for account {self.account_id}")
                
        except Exception as e:
            self.logger.error(f"Error starting TopStepX streaming: {e}", exc_info=True)
    
    async def _handle_market_event(self, event):
        """Handle real-time market events from TopStepX"""
        try:
            self.logger.debug(f"TopStepX market event: {event.model_dump_json()}")
            # Process market data events for position management
            # This could include quotes, trades, position updates, etc.
        except Exception as e:
            self.logger.error(f"Error handling market event: {e}", exc_info=True)
    
    async def _handle_status_change(self, status: StreamConnectionStatus, reason: str):
        """Handle stream connection status changes"""
        self.stream_status = status
        self.logger.info(f"TopStepX stream status: {status.value} - {reason}")
    
    async def _handle_stream_error(self, error: Exception):
        """Handle streaming errors"""
        self.logger.error(f"TopStepX stream error: {error}", exc_info=True)
    
    async def execute_trade(self, alert_data: Dict[str, Any]) -> Optional[TradePosition]:
        """
        Execute live trade through TopStepX based on parsed alert
        
        Args:
            alert_data: Parsed alert data from JMoney message parser
            
        Returns:
            TradePosition: Created position if successful, None otherwise
        """
        if not self.is_connected or not self.provider:
            self.logger.error("TopStepX broker not connected")
            return None
        
        try:
            self.logger.info(f"Executing TopStepX trade: {alert_data}")
            
            # Extract trade parameters
            symbol = alert_data.get('symbol', 'ES')
            direction = alert_data.get('direction', 'long').upper()
            price = alert_data.get('price')
            size = alert_data.get('size', 1)
            stop_loss = alert_data.get('stop')
            
            # Convert size mapping (A/B/C) to contract quantity
            contract_quantity = self._convert_size_to_quantity(size)
            
            # Get contract information for the symbol
            contract = await self._get_contract_by_symbol(symbol)
            if not contract:
                self.logger.error(f"Could not find contract for symbol: {symbol}")
                return None
            
            # Determine order side
            side = "BUY" if direction == "LONG" else "SELL"
            
            # Place market order for entry using TradeForgePy
            order_result = await self.provider.place_order(
                account_id=self.account_id,
                contract_id=contract.provider_contract_id,
                order_type="MARKET",
                side=side,
                quantity=contract_quantity
            )
            
            if not order_result or not order_result.order_id:
                self.logger.error("Failed to place TopStepX market order")
                return None
            
            self.logger.info(f"✅ TopStepX market order placed: ID {order_result.order_id}, {side} {contract_quantity} {symbol}")
            
            # Create position tracking
            position = TradePosition(
                id=f"tsx_{order_result.order_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                symbol=symbol,
                direction=direction.lower(),
                entry_price=price,
                quantity=contract_quantity,
                stop_loss=stop_loss,
                target_1=price + (7 if direction == "LONG" else -7),  # +7 points for Target 1
                target_2=price + (12 if direction == "LONG" else -12),  # +12 points for Target 2
                status=PositionStatus.OPEN,
                entry_time=datetime.now(),
                broker_order_id=str(order_result.order_id)
            )
            
            # Store position for tracking
            self.active_positions[position.id] = position
            
            # Schedule Target 1/Target 2 management
            asyncio.create_task(self._manage_position_exits(position, contract))
            
            self.logger.info(f"✅ TopStepX position created: {position.id}")
            return position
            
        except TradeForgeError as e:
            self.logger.error(f"TopStepX API error executing trade: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error executing TopStepX trade: {e}", exc_info=True)
            return None
    
    async def _get_contract_by_symbol(self, symbol: str):
        """
        Get TopStepX contract for trading symbol
        
        Args:
            symbol: Trading symbol (e.g., 'ES', 'NQ')
            
        Returns:
            Contract object if found, None otherwise
        """
        try:
            # Use TradeForgePy's contract search functionality
            contracts = await self.provider.search_contracts(symbol)
            
            if not contracts:
                self.logger.error(f"No contracts found for symbol: {symbol}")
                return None
            
            # Find the most appropriate contract (usually the front month)
            # This is a simplified approach - you may want more sophisticated contract selection
            active_contract = None
            for contract in contracts:
                if contract.symbol.startswith(symbol) and getattr(contract, 'is_active', True):
                    active_contract = contract
                    break
            
            if not active_contract:
                # Fallback to first contract if no active contract found
                active_contract = contracts[0]
            
            self.logger.info(f"Selected contract for {symbol}: {active_contract.provider_contract_id} ({active_contract.symbol})")
            return active_contract
            
        except Exception as e:
            self.logger.error(f"Error getting contract for {symbol}: {e}", exc_info=True)
            return None
    
    def _convert_size_to_quantity(self, size: Any) -> int:
        """
        Convert TradeStream size notation to contract quantity
        
        Args:
            size: Size from alert (A/B/C or numeric)
            
        Returns:
            int: Number of contracts to trade
        """
        if isinstance(size, int):
            return size
        
        if isinstance(size, str):
            size_mapping = {
                'A': 1,  # Small position
                'B': 2,  # Medium position  
                'C': 3   # Large position
            }
            return size_mapping.get(size.upper(), 1)
        
        return 1  # Default to 1 contract
    
    async def _manage_position_exits(self, position: TradePosition, contract_id: str):
        """
        Manage Target 1 and Target 2 exits for a position
        
        Args:
            position: Position to manage
            contract_id: TopStepX contract ID
        """
        try:
            self.logger.info(f"Starting exit management for position {position.id}")
            
            # Monitor position for Target 1 and Target 2 exits
            # This is a simplified implementation - you may want more sophisticated monitoring
            
            while position.status == PositionStatus.OPEN:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Get current market price (you'd implement real-time price monitoring)
                # For now, we'll use a placeholder
                current_price = await self._get_current_price(contract_id)
                
                if current_price is None:
                    continue
                
                # Check for Target 1 (50% exit at +7 points)
                if not position.target_1_hit:
                    target_1_reached = (
                        (position.direction == "long" and current_price >= position.target_1) or
                        (position.direction == "short" and current_price <= position.target_1)
                    )
                    
                    if target_1_reached:
                        await self._execute_partial_exit(position, contract_id, 0.5, "Target 1")
                        position.target_1_hit = True
                        
                        # Move stop to breakeven
                        position.stop_loss = position.entry_price
                        self.logger.info(f"Position {position.id}: Target 1 hit, stop moved to breakeven")
                
                # Check for Target 2 (remaining 50% exit at +12 points)
                if position.target_1_hit and not position.target_2_hit:
                    target_2_reached = (
                        (position.direction == "long" and current_price >= position.target_2) or
                        (position.direction == "short" and current_price <= position.target_2)
                    )
                    
                    if target_2_reached:
                        await self._execute_partial_exit(position, contract_id, 1.0, "Target 2")
                        position.target_2_hit = True
                        position.status = PositionStatus.CLOSED
                        break
                
                # Check for stop loss
                stop_hit = (
                    (position.direction == "long" and current_price <= position.stop_loss) or
                    (position.direction == "short" and current_price >= position.stop_loss)
                )
                
                if stop_hit:
                    await self._execute_stop_loss(position, contract_id)
                    position.status = PositionStatus.STOPPED
                    break
            
            self.logger.info(f"Exit management completed for position {position.id}")
            
        except Exception as e:
            self.logger.error(f"Error managing position exits: {e}", exc_info=True)
    
    async def _get_current_price(self, contract_id: str) -> Optional[float]:
        """
        Get current market price for contract
        
        Args:
            contract_id: TopStepX contract ID
            
        Returns:
            float: Current price if available, None otherwise
        """
        try:
            # This is a placeholder - you'd implement real-time price fetching
            # Using TopStepX DataStream for real-time quotes
            return None
        except Exception as e:
            self.logger.error(f"Error getting current price: {e}", exc_info=True)
            return None
    
    async def _execute_partial_exit(self, position: TradePosition, contract_id: str, 
                                  exit_percentage: float, exit_reason: str):
        """
        Execute partial position exit
        
        Args:
            position: Position to exit
            contract_id: TopStepX contract ID
            exit_percentage: Percentage of position to exit (0.5 = 50%)
            exit_reason: Reason for exit (for logging)
        """
        try:
            exit_quantity = int(position.quantity * exit_percentage)
            if exit_quantity <= 0:
                return
            
            # Determine exit side (opposite of entry)
            exit_side = "SELL" if position.direction == "long" else "BUY"
            
            # Place market order for exit
            order_id = self.order_placer.place_market_order(
                side=exit_side,
                size=exit_quantity,
                contract_id=contract_id
            )
            
            if order_id:
                self.logger.info(f"Position {position.id}: {exit_reason} exit order placed - "
                               f"{exit_side} {exit_quantity} contracts (Order ID: {order_id})")
                position.quantity -= exit_quantity
            else:
                self.logger.error(f"Failed to place {exit_reason} exit order for position {position.id}")
                
        except Exception as e:
            self.logger.error(f"Error executing partial exit: {e}", exc_info=True)
    
    async def _execute_stop_loss(self, position: TradePosition, contract_id: str):
        """
        Execute stop loss for entire remaining position
        
        Args:
            position: Position to stop out
            contract_id: TopStepX contract ID
        """
        try:
            # Exit entire remaining position
            exit_side = "SELL" if position.direction == "long" else "BUY"
            
            order_id = self.order_placer.place_market_order(
                side=exit_side,
                size=position.quantity,
                contract_id=contract_id
            )
            
            if order_id:
                self.logger.info(f"Position {position.id}: Stop loss executed - "
                               f"{exit_side} {position.quantity} contracts (Order ID: {order_id})")
                position.quantity = 0
            else:
                self.logger.error(f"Failed to place stop loss order for position {position.id}")
                
        except Exception as e:
            self.logger.error(f"Error executing stop loss: {e}", exc_info=True)
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current account information
        
        Returns:
            dict: Account information if available, None otherwise
        """
        if not self.api_client:
            return None
        
        try:
            accounts = self.api_client.get_accounts(only_active=True)
            account = next((acc for acc in accounts if acc.id == self.account_id), None)
            
            if account:
                return {
                    'account_id': account.id,
                    'name': account.name,
                    'balance': account.balance,
                    'buying_power': getattr(account, 'buying_power', None),
                    'environment': self.config.environment
                }
            
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}", exc_info=True)
        
        return None
    
    async def get_positions(self) -> List[TradePosition]:
        """
        Get current active positions
        
        Returns:
            List[TradePosition]: List of active positions
        """
        return list(self.active_positions.values())
    
    async def close_position(self, position_id: str) -> bool:
        """
        Manually close a position
        
        Args:
            position_id: ID of position to close
            
        Returns:
            bool: True if successful, False otherwise
        """
        position = self.active_positions.get(position_id)
        if not position:
            self.logger.error(f"Position {position_id} not found")
            return False
        
        try:
            # Get contract ID and close position
            contract_id = await self._get_contract_id(position.symbol)
            if contract_id:
                await self._execute_partial_exit(position, contract_id, 1.0, "Manual Close")
                position.status = PositionStatus.CLOSED
                return True
                
        except Exception as e:
            self.logger.error(f"Error closing position {position_id}: {e}", exc_info=True)
        
        return False
    
    async def shutdown(self):
        """Shutdown broker connection and cleanup resources"""
        try:
            self.logger.info("Shutting down TopStepX broker...")
            
            # Stop streaming task
            if hasattr(self, 'stream_task') and self.stream_task:
                self.stream_task.cancel()
                try:
                    await self.stream_task
                except asyncio.CancelledError:
                    pass
            
            # Disconnect provider
            if self.provider:
                await self.provider.disconnect()
            
            # Close any remaining positions if needed
            # (This would be configurable based on user preference)
            
            self.is_connected = False
            self.logger.info("✅ TopStepX broker shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during TopStepX shutdown: {e}", exc_info=True)


# Factory function for easy integration
def create_topstepx_broker(config_dict: Dict[str, Any]) -> TopStepXBroker:
    """
    Factory function to create TopStepX broker instance
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        TopStepXBroker: Configured broker instance
    """
    tsx_config = TopStepXConfig(
        api_key=config_dict.get('api_key', ''),
        environment=config_dict.get('environment', 'DEMO'),
        account_id=config_dict.get('account_id'),
        enable_streaming=config_dict.get('enable_streaming', True),
        order_timeout_seconds=config_dict.get('order_timeout_seconds', 30)
    )
    
    return TopStepXBroker(tsx_config)
