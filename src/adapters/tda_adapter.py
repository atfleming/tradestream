"""
TD Ameritrade Broker Adapter
Interfaces with DiscordAlertsTrader TDA implementation for TradeStream
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
from ..config import TDAConfig

class TDAAdapter(BaseBrokerAdapter):
    """Adapter for TD Ameritrade broker using DiscordAlertsTrader implementation"""
    
    def __init__(self, config: TDAConfig):
        super().__init__(config)
        self.name = "tda"
        self.logger = logging.getLogger(__name__)
        
        # Set up configuration for DiscordAlertsTrader TDA
        self._setup_tda_config()
    
    def _setup_tda_config(self):
        """Setup configuration for DiscordAlertsTrader TDA implementation"""
        # Create a mock cfg structure that the TDA implementation expects
        self.tda_cfg = {
            "TDA": {
                "client_id": os.getenv("TDA_CLIENT_ID", self.config.client_id),
                "redirect_url": os.getenv("TDA_REDIRECT_URL", self.config.redirect_url),
                "credentials_path": os.getenv("TDA_CREDENTIALS_PATH", self.config.credentials_path),
                "account_id": os.getenv("TDA_ACCOUNT_ID", self.config.account_id),
                "paper_trading": self.config.paper_trading
            }
        }
    
    async def initialize(self) -> bool:
        """Initialize TDA broker connection"""
        try:
            self.logger.info("Initializing TD Ameritrade broker connection...")
            
            # Import TDA implementation
            from brokerages.TDA_api import TDA
            
            # Monkey patch the cfg to use our configuration
            import brokerages.TDA_api as tda_module
            tda_module.cfg = self.tda_cfg
            
            # Create TDA instance
            self.broker_instance = TDA(accountId=self.config.account_id)
            
            # Get session (login)
            success = await asyncio.get_event_loop().run_in_executor(
                None, self.broker_instance.get_session
            )
            
            if success:
                self.connected = True
                self.logger.info("TD Ameritrade broker initialized successfully")
                return True
            else:
                self.logger.error("Failed to login to TD Ameritrade")
                return False
                
        except Exception as e:
            self.logger.error(f"Error initializing TD Ameritrade broker: {str(e)}")
            return False
    
    async def execute_options_order(self, alert: ParsedOptionsAlert) -> BrokerExecutionResult:
        """Execute options order based on parsed alert"""
        if not self.connected or not self.broker_instance:
            return BrokerExecutionResult(
                success=False,
                error_message="TD Ameritrade broker not connected"
            )
        
        try:
            # Convert alert to TDA format
            symbol = alert.symbol
            quantity = alert.quantity or 1
            price = alert.price
            
            self.logger.info(f"Executing TDA options order: {alert.action.value} {symbol} x{quantity} @ ${price}")
            
            # Create option leg for TDA order
            option_leg = self._create_option_leg(alert)
            
            # Execute order based on action
            if alert.action == OptionsAction.BTO:
                order = await asyncio.get_event_loop().run_in_executor(
                    None, self.broker_instance.make_BTO_lim_order, 
                    symbol, quantity, price, option_leg, "BTO"
                )
            elif alert.action == OptionsAction.STC:
                order = await asyncio.get_event_loop().run_in_executor(
                    None, self.broker_instance.make_STC_lim, 
                    symbol, quantity, price, option_leg, "STC"
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
                self.logger.info(f"TDA order executed successfully: {order_id}")
                return BrokerExecutionResult(
                    success=True,
                    order_id=str(order_id),
                    details={
                        'order_response': order_response,
                        'symbol': symbol,
                        'action': alert.action.value,
                        'quantity': quantity,
                        'price': price,
                        'option_leg': option_leg
                    }
                )
            else:
                return BrokerExecutionResult(
                    success=False,
                    error_message="Order execution failed - no order ID returned"
                )
                
        except Exception as e:
            self.logger.error(f"Error executing TDA options order: {str(e)}")
            return BrokerExecutionResult(
                success=False,
                error_message=f"Execution error: {str(e)}"
            )
    
    def _create_option_leg(self, alert: ParsedOptionsAlert) -> Dict[str, Any]:
        """Create option leg for TDA order"""
        # TDA expects specific format for option symbols and legs
        exp_date = alert.expiration_date
        exp_str = exp_date.strftime("%m%d%y")
        
        option_type = "CALL" if alert.option_type == OptionsType.CALL else "PUT"
        strike_price = alert.strike_price
        
        # TDA option symbol format: SYMBOL_MMDDYY[C/P]STRIKE
        option_symbol = f"{alert.symbol}_{exp_str}{option_type[0]}{strike_price}"
        
        return {
            'symbol': option_symbol,
            'underlying_symbol': alert.symbol,
            'option_type': option_type,
            'strike_price': strike_price,
            'expiration_date': exp_date.strftime("%Y-%m-%d"),
            'quantity': alert.quantity or 1
        }
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions from TDA"""
        if not self.connected or not self.broker_instance:
            return []
        
        try:
            positions = await asyncio.get_event_loop().run_in_executor(
                None, self.broker_instance.get_positions_orders
            )
            
            # Format positions for TradeStream
            formatted_positions = []
            if positions and 'securitiesAccount' in positions:
                account = positions['securitiesAccount']
                if 'positions' in account:
                    for pos in account['positions']:
                        instrument = pos.get('instrument', {})
                        formatted_positions.append({
                            'symbol': instrument.get('symbol', ''),
                            'quantity': pos.get('longQuantity', 0) - pos.get('shortQuantity', 0),
                            'market_value': pos.get('marketValue', 0),
                            'unrealized_pnl': pos.get('currentDayProfitLoss', 0),
                            'cost_basis': pos.get('averagePrice', 0),
                            'broker': 'tda'
                        })
            
            return formatted_positions
            
        except Exception as e:
            self.logger.error(f"Error getting TDA positions: {str(e)}")
            return []
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information from TDA"""
        if not self.connected or not self.broker_instance:
            return {}
        
        try:
            account_info = await asyncio.get_event_loop().run_in_executor(
                None, self.broker_instance.get_account_info
            )
            
            if account_info and 'securitiesAccount' in account_info:
                account = account_info['securitiesAccount']
                current_balances = account.get('currentBalances', {})
                
                return {
                    'broker': 'tda',
                    'account_id': account.get('accountId', ''),
                    'buying_power': current_balances.get('buyingPower', 0),
                    'total_value': current_balances.get('liquidationValue', 0),
                    'cash': current_balances.get('cashBalance', 0),
                    'day_trades_remaining': account.get('roundTrips', 0),
                    'paper_trading': self.config.paper_trading
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Error getting TDA account info: {str(e)}")
            return {}
    
    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get recent orders from TDA"""
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
                    order_legs = order.get('orderLegCollection', [])
                    symbol = ''
                    if order_legs:
                        instrument = order_legs[0].get('instrument', {})
                        symbol = instrument.get('symbol', '')
                    
                    formatted_orders.append({
                        'order_id': order.get('orderId', ''),
                        'symbol': symbol,
                        'action': order.get('orderStrategyType', ''),
                        'quantity': order.get('quantity', 0),
                        'price': order.get('price', 0),
                        'status': order.get('status', ''),
                        'timestamp': order.get('enteredTime', ''),
                        'broker': 'tda'
                    })
            
            return formatted_orders
            
        except Exception as e:
            self.logger.error(f"Error getting TDA orders: {str(e)}")
            return []
    
    async def shutdown(self):
        """Shutdown TDA broker connection"""
        self.logger.info("Shutting down TD Ameritrade broker connection...")
        await super().shutdown()
        
        # TDA doesn't have explicit logout, just clear instance
        self.broker_instance = None
