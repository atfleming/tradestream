"""
Webull Broker Integration for TradeStream
Handles options trading execution via Webull API
Based on DiscordAlertsTrader implementation patterns
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

from .config import WebullConfig
from .options_parser import ParsedOptionsAlert, OptionsAction

try:
    from webull import webull
except ImportError:
    webull = None
    logging.warning("Webull library not installed. Install with: pip install webull")

@dataclass
class WebullOrderResult:
    """Result of a Webull order execution"""
    success: bool
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class WebullBroker:
    """Webull broker for options trading execution"""
    
    def __init__(self, config: WebullConfig):
        """
        Initialize Webull broker
        
        Args:
            config: Webull configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.wb = None
        self.is_connected = False
        self.is_paper_trading = config.paper_trading
        
        if not webull:
            raise ImportError("Webull library is required. Install with: pip install webull")
    
    async def initialize(self) -> bool:
        """Initialize Webull connection"""
        try:
            if not self.config.enabled:
                self.logger.info("Webull broker is disabled in configuration")
                return False
            
            self.logger.info("Initializing Webull broker connection...")
            
            # Initialize Webull client
            self.wb = webull()
            
            # Login with credentials
            login_result = self.wb.login(
                username=self.config.username,
                password=self.config.password,
                device_name=self.config.device_id,
                mfa=self.config.trading_pin
            )
            
            if login_result:
                self.is_connected = True
                
                # Get account info
                account_info = self.wb.get_account()
                self.logger.info(f"Webull connected successfully. Account: {account_info.get('accountId', 'Unknown')}")
                
                # Set paper trading mode if configured
                if self.is_paper_trading:
                    self.logger.info("Webull configured for paper trading")
                else:
                    self.logger.warning("Webull configured for LIVE trading")
                
                return True
            else:
                self.logger.error("Failed to login to Webull")
                return False
                
        except Exception as e:
            self.logger.error(f"Error initializing Webull broker: {str(e)}")
            self.is_connected = False
            return False
    
    async def execute_options_order(self, alert: ParsedOptionsAlert) -> WebullOrderResult:
        """
        Execute options order based on parsed alert
        
        Args:
            alert: Parsed options alert
            
        Returns:
            WebullOrderResult with execution details
        """
        try:
            if not self.is_connected:
                return WebullOrderResult(
                    success=False,
                    error_message="Webull broker not connected"
                )
            
            # Map alert action to Webull order type
            if alert.action == OptionsAction.BTO:
                order_type = "BUY"
                action = "OPEN"
            elif alert.action == OptionsAction.STC:
                order_type = "SELL"
                action = "CLOSE"
            else:
                return WebullOrderResult(
                    success=False,
                    error_message=f"Unsupported options action: {alert.action}"
                )
            
            # Get option instrument ID
            option_id = await self._get_option_instrument_id(alert)
            if not option_id:
                return WebullOrderResult(
                    success=False,
                    error_message="Could not find option instrument"
                )
            
            # Prepare order parameters
            order_params = {
                'stock': alert.symbol,
                'optionId': option_id,
                'lmtPrice': alert.price if alert.price else None,
                'stpPrice': None,  # No stop price for options
                'quantity': alert.quantity,
                'action': action,
                'orderType': 'LMT' if alert.price else 'MKT',
                'enforce': 'DAY',
                'quant': alert.quantity
            }
            
            self.logger.info(f"Executing Webull options order: {alert.action.value} {alert.option_symbol}")
            
            # Execute the order
            if self.is_paper_trading:
                # Webull paper trading only supports BTO orders
                if alert.action != OptionsAction.BTO:
                    return WebullOrderResult(
                        success=False,
                        error_message="Webull paper trading only supports BTO orders"
                    )
                
                # Execute paper order
                result = self.wb.place_option_order(**order_params)
            else:
                # Execute live order
                result = self.wb.place_option_order(**order_params)
            
            if result and result.get('success', False):
                order_id = result.get('orderId', 'Unknown')
                
                self.logger.info(f"Webull options order executed successfully: {order_id}")
                
                return WebullOrderResult(
                    success=True,
                    order_id=order_id,
                    details=result
                )
            else:
                error_msg = result.get('msg', 'Unknown error') if result else 'No response from Webull'
                
                self.logger.error(f"Webull options order failed: {error_msg}")
                
                return WebullOrderResult(
                    success=False,
                    error_message=error_msg,
                    details=result
                )
                
        except Exception as e:
            self.logger.error(f"Error executing Webull options order: {str(e)}")
            return WebullOrderResult(
                success=False,
                error_message=f"Execution error: {str(e)}"
            )
    
    async def _get_option_instrument_id(self, alert: ParsedOptionsAlert) -> Optional[str]:
        """Get Webull option instrument ID for the alert"""
        try:
            # Get options chain for the underlying symbol
            exp_date_str = alert.expiration_date.strftime('%Y-%m-%d')
            
            options_data = self.wb.get_options(
                stock=alert.symbol,
                expireDate=exp_date_str
            )
            
            if not options_data:
                self.logger.error(f"No options data found for {alert.symbol} {exp_date_str}")
                return None
            
            # Find the specific option contract
            option_type = 'call' if alert.option_type.value == 'CALL' else 'put'
            
            for option in options_data.get(option_type, []):
                if float(option.get('strikePrice', 0)) == alert.strike_price:
                    return option.get('tickerId')
            
            self.logger.error(f"Option contract not found: {alert.option_symbol}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting option instrument ID: {str(e)}")
            return None
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get Webull account information"""
        try:
            if not self.is_connected:
                return {}
            
            account_info = self.wb.get_account()
            return account_info or {}
            
        except Exception as e:
            self.logger.error(f"Error getting Webull account info: {str(e)}")
            return {}
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current Webull positions"""
        try:
            if not self.is_connected:
                return []
            
            positions = self.wb.get_positions()
            return positions or []
            
        except Exception as e:
            self.logger.error(f"Error getting Webull positions: {str(e)}")
            return []
    
    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get recent Webull orders"""
        try:
            if not self.is_connected:
                return []
            
            orders = self.wb.get_history_orders()
            return orders or []
            
        except Exception as e:
            self.logger.error(f"Error getting Webull orders: {str(e)}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get broker connection status"""
        return {
            'broker': 'Webull',
            'connected': self.is_connected,
            'paper_trading': self.is_paper_trading,
            'enabled': self.config.enabled,
            'supports_options': True,
            'supports_futures': False
        }
    
    async def shutdown(self):
        """Shutdown Webull broker connection"""
        try:
            if self.wb:
                # Webull doesn't have explicit logout, just clear the instance
                self.wb = None
            
            self.is_connected = False
            self.logger.info("Webull broker connection closed")
            
        except Exception as e:
            self.logger.error(f"Error shutting down Webull broker: {str(e)}")

# Example usage
async def example_usage():
    """Example of how to use the Webull broker"""
    from .config import WebullConfig
    from .options_parser import ParsedOptionsAlert, OptionsAction, OptionsType
    from datetime import datetime, timedelta
    
    # Configure Webull
    config = WebullConfig(
        username="your_username",
        password="your_password", 
        device_id="your_device_id",
        trading_pin="123456",
        paper_trading=True,
        enabled=True
    )
    
    # Initialize broker
    broker = WebullBroker(config)
    
    if await broker.initialize():
        # Create sample options alert
        alert = ParsedOptionsAlert(
            raw_content="BOUGHT SPY 01/31 480 CALLS @ 2.50",
            timestamp=datetime.now(),
            author="TestUser",
            channel="TWI_Options",
            action=OptionsAction.BTO,
            symbol="SPY",
            option_type=OptionsType.CALL,
            strike_price=480.0,
            expiration_date=datetime.now() + timedelta(days=7),
            quantity=1,
            price=2.50
        )
        
        # Execute order
        result = await broker.execute_options_order(alert)
        
        if result.success:
            print(f"Order executed successfully: {result.order_id}")
        else:
            print(f"Order failed: {result.error_message}")
        
        # Cleanup
        await broker.shutdown()

if __name__ == "__main__":
    asyncio.run(example_usage())
