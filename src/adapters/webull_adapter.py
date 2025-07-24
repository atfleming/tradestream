"""
Webull Broker Adapter
Interfaces with DiscordAlertsTrader Webull implementation for TradeStream
"""

import logging
import asyncio
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add DiscordAlertsTrader to path for imports
discord_alerts_path = os.path.join(os.path.dirname(__file__), '../../DiscordAlertsTrader-main/DiscordAlertsTrader')
if discord_alerts_path not in sys.path:
    sys.path.append(discord_alerts_path)

from . import BaseBrokerAdapter, BrokerExecutionResult
from ..options_parser import ParsedOptionsAlert, OptionsAction, OptionsType
from ..config import WebullConfig

class WebullAdapter(BaseBrokerAdapter):
    """Adapter for Webull broker using DiscordAlertsTrader implementation"""
    
    def __init__(self, config: WebullConfig):
        super().__init__(config)
        self.name = "webull"
        self.logger = logging.getLogger(__name__)
        
        # Set up configuration for DiscordAlertsTrader Webull
        self._setup_webull_config()
    
    def _setup_webull_config(self):
        """Setup configuration for DiscordAlertsTrader Webull implementation"""
        # Create a mock cfg structure that the Webull implementation expects
        self.webull_cfg = {
            "webull": {
                "LOGIN_EMAIL": os.getenv("WEBULL_EMAIL", self.config.email),
                "LOGIN_PWD": os.getenv("WEBULL_PASSWORD", self.config.password),
                "TRADING_PIN": os.getenv("WEBULL_TRADING_PIN", self.config.trading_pin),
                "DEVICE_ID": os.getenv("WEBULL_DEVICE_ID", self.config.device_id),
                "SECURITY_DID": os.getenv("WEBULL_SECURITY_DID", self.config.security_did),
                "PAPER_TRADING": self.config.paper_trading
            }
        }
    
    async def initialize(self) -> bool:
        """Initialize Webull broker connection"""
        try:
            self.logger.info("Initializing Webull broker connection...")
            
            # Import Webull implementation
            from brokerages.weBull_api import weBull
            
            # Monkey patch the cfg to use our configuration
            import brokerages.weBull_api as webull_module
            webull_module.cfg = self.webull_cfg
            
            # Create Webull instance
            self.broker_instance = weBull()
            
            # Get session (login)
            success = await asyncio.get_event_loop().run_in_executor(
                None, self.broker_instance.get_session, True
            )
            
            if success:
                self.connected = True
                self.logger.info("Webull broker initialized successfully")
                return True
            else:
                self.logger.error("Failed to login to Webull")
                return False
                
        except Exception as e:
            self.logger.error(f"Error initializing Webull broker: {str(e)}")
            return False
    
    async def execute_options_order(self, alert: ParsedOptionsAlert) -> BrokerExecutionResult:
        """Execute options order based on parsed alert"""
        if not self.connected or not self.broker_instance:
            return BrokerExecutionResult(
                success=False,
                error_message="Webull broker not connected"
            )
        
        try:
            # Convert alert to Webull format
            symbol = self._format_option_symbol(alert)
            quantity = alert.quantity or 1
            price = alert.price
            
            self.logger.info(f"Executing Webull options order: {alert.action.value} {symbol} x{quantity} @ ${price}")
            
            # Execute order based on action
            if alert.action == OptionsAction.BTO:
                order = await asyncio.get_event_loop().run_in_executor(
                    None, self.broker_instance.make_BTO_lim_order, symbol, quantity, price, "BTO"
                )
            elif alert.action == OptionsAction.STC:
                order = await asyncio.get_event_loop().run_in_executor(
                    None, self.broker_instance.make_STC_lim, symbol, quantity, price, None, "STC"
                )
            else:
                return BrokerExecutionResult(
                    success=False,
                    error_message=f"Unsupported action: {alert.action.value}"
                )
            
            # Send order
            order_response, order_id = await asyncio.get_event_loop().run_in_executor(
                None, self.broker_instance.send_order, order
            )
            
            if order_response and order_id:
                self.logger.info(f"Webull order executed successfully: {order_id}")
                return BrokerExecutionResult(
                    success=True,
                    order_id=str(order_id),
                    details={
                        'order_response': order_response,
                        'symbol': symbol,
                        'action': alert.action.value,
                        'quantity': quantity,
                        'price': price
                    }
                )
            else:
                return BrokerExecutionResult(
                    success=False,
                    error_message="Order execution failed - no order ID returned"
                )
                
        except Exception as e:
            self.logger.error(f"Error executing Webull options order: {str(e)}")
            return BrokerExecutionResult(
                success=False,
                error_message=f"Execution error: {str(e)}"
            )
    
    def _format_option_symbol(self, alert: ParsedOptionsAlert) -> str:
        """Format option symbol for Webull"""
        # Webull expects format like: SPY_010324C480
        # Where: SYMBOL_MMDDYY[C/P]STRIKE
        
        exp_date = alert.expiration_date
        exp_str = exp_date.strftime("%m%d%y")
        
        option_type = "C" if alert.option_type == OptionsType.CALL else "P"
        strike_str = str(int(alert.strike_price)) if alert.strike_price == int(alert.strike_price) else str(alert.strike_price)
        
        return f"{alert.symbol}_{exp_str}{option_type}{strike_str}"
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions from Webull"""
        if not self.connected or not self.broker_instance:
            return []
        
        try:
            positions = await asyncio.get_event_loop().run_in_executor(
                None, self.broker_instance.get_positions_orders
            )
            
            # Format positions for TradeStream
            formatted_positions = []
            if positions and 'positions' in positions:
                for pos in positions['positions']:
                    formatted_positions.append({
                        'symbol': pos.get('ticker', {}).get('symbol', ''),
                        'quantity': pos.get('position', 0),
                        'market_value': pos.get('marketValue', 0),
                        'unrealized_pnl': pos.get('unrealizedProfitLoss', 0),
                        'cost_basis': pos.get('costPrice', 0),
                        'broker': 'webull'
                    })
            
            return formatted_positions
            
        except Exception as e:
            self.logger.error(f"Error getting Webull positions: {str(e)}")
            return []
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information from Webull"""
        if not self.connected or not self.broker_instance:
            return {}
        
        try:
            account_info = await asyncio.get_event_loop().run_in_executor(
                None, self.broker_instance.get_account_info
            )
            
            if account_info:
                return {
                    'broker': 'webull',
                    'account_id': account_info.get('accountId', ''),
                    'buying_power': account_info.get('buyingPower', 0),
                    'total_value': account_info.get('netLiquidation', 0),
                    'cash': account_info.get('settledFunds', 0),
                    'day_trades_remaining': account_info.get('dayTradesRemaining', 0),
                    'paper_trading': self.config.paper_trading
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Error getting Webull account info: {str(e)}")
            return {}
    
    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get recent orders from Webull"""
        if not self.connected or not self.broker_instance:
            return []
        
        try:
            orders = await asyncio.get_event_loop().run_in_executor(
                None, self.broker_instance.get_orders
            )
            
            # Format orders for TradeStream
            formatted_orders = []
            if orders:
                for order in orders:
                    formatted_orders.append({
                        'order_id': order.get('orderId', ''),
                        'symbol': order.get('ticker', {}).get('symbol', ''),
                        'action': order.get('action', ''),
                        'quantity': order.get('totalQuantity', 0),
                        'price': order.get('lmtPrice', 0),
                        'status': order.get('status', ''),
                        'timestamp': order.get('placedTime', ''),
                        'broker': 'webull'
                    })
            
            return formatted_orders
            
        except Exception as e:
            self.logger.error(f"Error getting Webull orders: {str(e)}")
            return []
    
    async def shutdown(self):
        """Shutdown Webull broker connection"""
        self.logger.info("Shutting down Webull broker connection...")
        await super().shutdown()
        
        # Webull doesn't have explicit logout, just clear instance
        self.broker_instance = None
