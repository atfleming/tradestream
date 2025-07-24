"""
E*TRADE Broker Adapter
Interfaces with DiscordAlertsTrader E*TRADE implementation for TradeStream
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
from ..config import ETradeConfig

class ETradeAdapter(BaseBrokerAdapter):
    """Adapter for E*TRADE broker using DiscordAlertsTrader implementation"""
    
    def __init__(self, config: ETradeConfig):
        super().__init__(config)
        self.name = "etrade"
        self.logger = logging.getLogger(__name__)
        
        # Set up configuration for DiscordAlertsTrader E*TRADE
        self._setup_etrade_config()
    
    def _setup_etrade_config(self):
        """Setup configuration for DiscordAlertsTrader E*TRADE implementation"""
        # Create a mock cfg structure that the E*TRADE implementation expects
        self.etrade_cfg = {
            "etrade": {
                "CONSUMER_KEY": os.getenv("ETRADE_CONSUMER_KEY", self.config.consumer_key),
                "CONSUMER_SECRET": os.getenv("ETRADE_CONSUMER_SECRET", self.config.consumer_secret),
                "PROD_BASE_URL": self.config.prod_base_url,
                "SANDBOX_BASE_URL": self.config.sandbox_base_url,
                "WITH_BROWSER": self.config.with_browser
            },
            "root": {
                "dir": os.path.expanduser("~/.tradestream")  # Directory for token storage
            }
        }
        
        # Ensure token directory exists
        os.makedirs(self.etrade_cfg["root"]["dir"], exist_ok=True)
    
    async def initialize(self) -> bool:
        """Initialize E*TRADE broker connection"""
        try:
            self.logger.info("Initializing E*TRADE broker connection...")
            
            # Import E*TRADE implementation
            from brokerages.eTrade_api import eTrade
            
            # Monkey patch the cfg to use our configuration
            import brokerages.eTrade_api as etrade_module
            etrade_module.cfg = self.etrade_cfg
            
            # Create E*TRADE instance
            self.broker_instance = eTrade()
            
            # Get session (login)
            success = await asyncio.get_event_loop().run_in_executor(
                None, self.broker_instance.get_session
            )
            
            if success:
                self.connected = True
                self.logger.info("E*TRADE broker initialized successfully")
                return True
            else:
                self.logger.error("Failed to login to E*TRADE")
                return False
                
        except Exception as e:
            self.logger.error(f"Error initializing E*TRADE broker: {str(e)}")
            return False
    
    async def execute_options_order(self, alert: ParsedOptionsAlert) -> BrokerExecutionResult:
        """Execute options order based on parsed alert"""
        if not self.connected or not self.broker_instance:
            return BrokerExecutionResult(
                success=False,
                error_message="E*TRADE broker not connected"
            )
        
        try:
            # Convert alert to E*TRADE format
            symbol = self._format_option_symbol(alert)
            quantity = alert.quantity or 1
            price = alert.price
            
            self.logger.info(f"Executing E*TRADE options order: {alert.action.value} {symbol} x{quantity} @ ${price}")
            
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
                self.logger.info(f"E*TRADE order executed successfully: {order_id}")
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
            self.logger.error(f"Error executing E*TRADE options order: {str(e)}")
            return BrokerExecutionResult(
                success=False,
                error_message=f"Execution error: {str(e)}"
            )
    
    def _format_option_symbol(self, alert: ParsedOptionsAlert) -> str:
        """Format option symbol for E*TRADE"""
        # E*TRADE expects format like: SPY_010324C480
        # Where: SYMBOL_MMDDYY[C/P]STRIKE
        
        exp_date = alert.expiration_date
        exp_str = exp_date.strftime("%m%d%y")
        
        option_type = "C" if alert.option_type == OptionsType.CALL else "P"
        strike_str = str(int(alert.strike_price)) if alert.strike_price == int(alert.strike_price) else str(alert.strike_price)
        
        return f"{alert.symbol}_{exp_str}{option_type}{strike_str}"
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions from E*TRADE"""
        if not self.connected or not self.broker_instance:
            return []
        
        try:
            positions = await asyncio.get_event_loop().run_in_executor(
                None, self.broker_instance.get_positions_orders
            )
            
            # Format positions for TradeStream
            formatted_positions = []
            if positions and 'PortfolioResponse' in positions:
                portfolio = positions['PortfolioResponse']
                if 'AccountPortfolio' in portfolio:
                    for account in portfolio['AccountPortfolio']:
                        if 'Position' in account:
                            for pos in account['Position']:
                                product = pos.get('Product', {})
                                formatted_positions.append({
                                    'symbol': product.get('symbol', ''),
                                    'quantity': pos.get('quantity', 0),
                                    'market_value': pos.get('marketValue', 0),
                                    'unrealized_pnl': pos.get('totalGain', 0),
                                    'cost_basis': pos.get('pricePaid', 0),
                                    'broker': 'etrade'
                                })
            
            return formatted_positions
            
        except Exception as e:
            self.logger.error(f"Error getting E*TRADE positions: {str(e)}")
            return []
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information from E*TRADE"""
        if not self.connected or not self.broker_instance:
            return {}
        
        try:
            account_info = await asyncio.get_event_loop().run_in_executor(
                None, self.broker_instance.get_account_info
            )
            
            if account_info and 'AccountListResponse' in account_info:
                accounts = account_info['AccountListResponse']['Accounts']['Account']
                if accounts:
                    account = accounts[0] if isinstance(accounts, list) else accounts
                    
                    return {
                        'broker': 'etrade',
                        'account_id': account.get('accountId', ''),
                        'buying_power': account.get('buyingPower', 0),
                        'total_value': account.get('netAccountValue', 0),
                        'cash': account.get('cashBalance', 0),
                        'day_trades_remaining': 3,  # E*TRADE default
                        'paper_trading': self.config.sandbox
                    }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Error getting E*TRADE account info: {str(e)}")
            return {}
    
    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get recent orders from E*TRADE"""
        if not self.connected or not self.broker_instance:
            return []
        
        try:
            orders = await asyncio.get_event_loop().run_in_executor(
                None, self.broker_instance.get_orders
            )
            
            # Format orders for TradeStream
            formatted_orders = []
            if orders and 'OrdersResponse' in orders:
                order_list = orders['OrdersResponse'].get('Order', [])
                if not isinstance(order_list, list):
                    order_list = [order_list]
                
                for order in order_list:
                    order_detail = order.get('OrderDetail', [])
                    if order_detail:
                        detail = order_detail[0] if isinstance(order_detail, list) else order_detail
                        instrument = detail.get('Instrument', [])
                        if instrument:
                            instr = instrument[0] if isinstance(instrument, list) else instrument
                            product = instr.get('Product', {})
                            
                            formatted_orders.append({
                                'order_id': order.get('orderId', ''),
                                'symbol': product.get('symbol', ''),
                                'action': detail.get('orderAction', ''),
                                'quantity': instr.get('quantity', 0),
                                'price': detail.get('priceType', 0),
                                'status': order.get('orderStatus', ''),
                                'timestamp': order.get('placedTime', ''),
                                'broker': 'etrade'
                            })
            
            return formatted_orders
            
        except Exception as e:
            self.logger.error(f"Error getting E*TRADE orders: {str(e)}")
            return []
    
    async def shutdown(self):
        """Shutdown E*TRADE broker connection"""
        self.logger.info("Shutting down E*TRADE broker connection...")
        await super().shutdown()
        
        # E*TRADE doesn't have explicit logout, just clear instance
        self.broker_instance = None
