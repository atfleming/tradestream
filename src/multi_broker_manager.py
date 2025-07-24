"""
Multi-Broker Manager for TradeStream
Manages multiple broker connections and routes trades to appropriate brokers
Adapted from DiscordAlertsTrader repository broker implementations
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .config import ConfigManager, WebullConfig, TDAConfig, ETradeConfig, IBKRConfig, TradeStationConfig, SchwabConfig
from .options_parser import ParsedOptionsAlert, OptionsAction

class BrokerType(Enum):
    """Supported broker types"""
    WEBULL = "webull"
    TDA = "tda"
    ETRADE = "etrade"
    IBKR = "ibkr"
    TRADESTATION = "tradestation"
    SCHWAB = "schwab"

@dataclass
class BrokerOrderResult:
    """Result of a broker order execution"""
    success: bool
    broker: str
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class MultiBrokerManager:
    """Manager for multiple broker connections and trade routing"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize multi-broker manager
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Broker instances
        self.brokers: Dict[BrokerType, Any] = {}
        self.broker_status: Dict[BrokerType, bool] = {}
        
        # Default broker preferences for different asset types
        self.default_options_broker = BrokerType.WEBULL
        self.default_futures_broker = None  # TopStepX handled separately
        
        # Initialize broker configurations
        self.broker_configs = {
            BrokerType.WEBULL: config_manager.webull,
            BrokerType.TDA: config_manager.tda,
            BrokerType.ETRADE: config_manager.etrade,
            BrokerType.IBKR: config_manager.ibkr,
            BrokerType.TRADESTATION: config_manager.tradestation,
            BrokerType.SCHWAB: config_manager.schwab
        }
    
    async def initialize_brokers(self) -> Dict[BrokerType, bool]:
        """Initialize all enabled brokers"""
        self.logger.info("Initializing multi-broker system...")
        
        initialization_results = {}
        
        for broker_type, config in self.broker_configs.items():
            if config and config.enabled:
                try:
                    broker_instance = await self._create_broker_instance(broker_type, config)
                    if broker_instance:
                        success = await broker_instance.initialize()
                        if success:
                            self.brokers[broker_type] = broker_instance
                            self.broker_status[broker_type] = True
                            self.logger.info(f"{broker_type.value} broker initialized successfully")
                        else:
                            self.broker_status[broker_type] = False
                            self.logger.error(f"Failed to initialize {broker_type.value} broker")
                        
                        initialization_results[broker_type] = success
                    else:
                        initialization_results[broker_type] = False
                        self.logger.error(f"Could not create {broker_type.value} broker instance")
                        
                except Exception as e:
                    self.logger.error(f"Error initializing {broker_type.value} broker: {str(e)}")
                    initialization_results[broker_type] = False
                    self.broker_status[broker_type] = False
            else:
                self.logger.info(f"{broker_type.value} broker is disabled")
                initialization_results[broker_type] = False
        
        # Log summary
        enabled_brokers = [bt.value for bt, status in self.broker_status.items() if status]
        self.logger.info(f"Multi-broker initialization complete. Active brokers: {enabled_brokers}")
        
        return initialization_results
    
    async def _create_broker_instance(self, broker_type: BrokerType, config: Any) -> Optional[Any]:
        """Create broker instance based on type"""
        try:
            if broker_type == BrokerType.WEBULL:
                from .adapters.webull_adapter import WebullAdapter
                return WebullAdapter(config)
            
            elif broker_type == BrokerType.TDA:
                from .adapters.tda_adapter import TDAAdapter
                return TDAAdapter(config)
            
            elif broker_type == BrokerType.ETRADE:
                from .adapters.etrade_adapter import ETradeAdapter
                return ETradeAdapter(config)
            
            elif broker_type == BrokerType.IBKR:
                from .adapters.ibkr_adapter import IBKRAdapter
                return IBKRAdapter(config)
            
            elif broker_type == BrokerType.TRADESTATION:
                from .adapters.tradestation_adapter import TradeStationAdapter
                return TradeStationAdapter(config)
            
            elif broker_type == BrokerType.SCHWAB:
                from .adapters.schwab_adapter import SchwabAdapter
                return SchwabAdapter(config)
            
            else:
                self.logger.error(f"Unknown broker type: {broker_type}")
                return None
                
        except ImportError as e:
            self.logger.error(f"Could not import {broker_type.value} adapter: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating {broker_type.value} instance: {str(e)}")
            return None
    
    async def execute_options_order(self, alert: ParsedOptionsAlert, preferred_broker: Optional[BrokerType] = None) -> BrokerOrderResult:
        """
        Execute options order using the best available broker
        
        Args:
            alert: Parsed options alert
            preferred_broker: Preferred broker to use (optional)
            
        Returns:
            BrokerOrderResult with execution details
        """
        # Determine which broker to use
        broker_to_use = self._select_broker_for_options(preferred_broker)
        
        if not broker_to_use:
            return BrokerOrderResult(
                success=False,
                broker="none",
                error_message="No available brokers for options trading"
            )
        
        broker_instance = self.brokers.get(broker_to_use)
        if not broker_instance:
            return BrokerOrderResult(
                success=False,
                broker=broker_to_use.value,
                error_message=f"{broker_to_use.value} broker not initialized"
            )
        
        try:
            self.logger.info(f"Executing options order via {broker_to_use.value}: {alert.action.value} {alert.option_symbol}")
            
            # Execute the order
            result = await broker_instance.execute_options_order(alert)
            
            return BrokerOrderResult(
                success=result.success,
                broker=broker_to_use.value,
                order_id=result.order_id,
                error_message=result.error_message,
                details=result.details
            )
            
        except Exception as e:
            self.logger.error(f"Error executing options order via {broker_to_use.value}: {str(e)}")
            return BrokerOrderResult(
                success=False,
                broker=broker_to_use.value,
                error_message=f"Execution error: {str(e)}"
            )
    
    def _select_broker_for_options(self, preferred_broker: Optional[BrokerType] = None) -> Optional[BrokerType]:
        """Select the best broker for options trading"""
        
        # Use preferred broker if specified and available
        if preferred_broker and preferred_broker in self.brokers and self.broker_status.get(preferred_broker, False):
            return preferred_broker
        
        # Use default options broker if available
        if self.default_options_broker in self.brokers and self.broker_status.get(self.default_options_broker, False):
            return self.default_options_broker
        
        # Find any available options-capable broker
        options_capable_brokers = [BrokerType.WEBULL, BrokerType.TDA, BrokerType.ETRADE, BrokerType.IBKR, BrokerType.TRADESTATION, BrokerType.SCHWAB]
        
        for broker_type in options_capable_brokers:
            if broker_type in self.brokers and self.broker_status.get(broker_type, False):
                return broker_type
        
        return None
    
    async def get_all_positions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get positions from all connected brokers"""
        all_positions = {}
        
        for broker_type, broker_instance in self.brokers.items():
            if self.broker_status.get(broker_type, False):
                try:
                    positions = await broker_instance.get_positions()
                    all_positions[broker_type.value] = positions
                except Exception as e:
                    self.logger.error(f"Error getting positions from {broker_type.value}: {str(e)}")
                    all_positions[broker_type.value] = []
        
        return all_positions
    
    async def get_all_account_info(self) -> Dict[str, Dict[str, Any]]:
        """Get account information from all connected brokers"""
        all_accounts = {}
        
        for broker_type, broker_instance in self.brokers.items():
            if self.broker_status.get(broker_type, False):
                try:
                    account_info = await broker_instance.get_account_info()
                    all_accounts[broker_type.value] = account_info
                except Exception as e:
                    self.logger.error(f"Error getting account info from {broker_type.value}: {str(e)}")
                    all_accounts[broker_type.value] = {}
        
        return all_accounts
    
    async def get_all_orders(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get recent orders from all connected brokers"""
        all_orders = {}
        
        for broker_type, broker_instance in self.brokers.items():
            if self.broker_status.get(broker_type, False):
                try:
                    orders = await broker_instance.get_orders()
                    all_orders[broker_type.value] = orders
                except Exception as e:
                    self.logger.error(f"Error getting orders from {broker_type.value}: {str(e)}")
                    all_orders[broker_type.value] = []
        
        return all_orders
    
    def get_broker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all brokers"""
        status = {}
        
        for broker_type in BrokerType:
            broker_instance = self.brokers.get(broker_type)
            config = self.broker_configs.get(broker_type)
            
            if broker_instance:
                broker_status = broker_instance.get_status()
            else:
                broker_status = {
                    'broker': broker_type.value,
                    'connected': False,
                    'enabled': config.enabled if config else False,
                    'supports_options': True,
                    'supports_futures': False
                }
            
            status[broker_type.value] = broker_status
        
        return status
    
    def set_default_options_broker(self, broker_type: BrokerType):
        """Set the default broker for options trading"""
        if broker_type in self.brokers:
            self.default_options_broker = broker_type
            self.logger.info(f"Default options broker set to {broker_type.value}")
        else:
            self.logger.error(f"Cannot set default broker to {broker_type.value} - not initialized")
    
    async def shutdown_all_brokers(self):
        """Shutdown all broker connections"""
        self.logger.info("Shutting down all broker connections...")
        
        for broker_type, broker_instance in self.brokers.items():
            try:
                await broker_instance.shutdown()
                self.logger.info(f"{broker_type.value} broker shut down successfully")
            except Exception as e:
                self.logger.error(f"Error shutting down {broker_type.value} broker: {str(e)}")
        
        self.brokers.clear()
        self.broker_status.clear()
        self.logger.info("All brokers shut down")

# Example usage
async def example_usage():
    """Example of how to use the multi-broker manager"""
    from .config import ConfigManager
    from .options_parser import ParsedOptionsAlert, OptionsAction, OptionsType
    from datetime import datetime, timedelta
    
    # Load configuration
    config_manager = ConfigManager()
    config_manager.load_config()
    
    # Initialize multi-broker manager
    broker_manager = MultiBrokerManager(config_manager)
    
    # Initialize all brokers
    init_results = await broker_manager.initialize_brokers()
    print(f"Broker initialization results: {init_results}")
    
    # Get broker status
    status = broker_manager.get_broker_status()
    print(f"Broker status: {status}")
    
    # Create sample options alert
    alert = ParsedOptionsAlert(
        raw_content="BOUGHT SPY 01/31 480 CALLS @ 2.50",
        timestamp=datetime.now(),
        author="Twinsight Bot #7577",
        channel="TWI_Options",
        action=OptionsAction.BTO,
        symbol="SPY",
        option_type=OptionsType.CALL,
        strike_price=480.0,
        expiration_date=datetime.now() + timedelta(days=7),
        quantity=1,
        price=2.50
    )
    
    # Execute options order
    result = await broker_manager.execute_options_order(alert)
    
    if result.success:
        print(f"Order executed successfully via {result.broker}: {result.order_id}")
    else:
        print(f"Order failed: {result.error_message}")
    
    # Get all positions
    positions = await broker_manager.get_all_positions()
    print(f"All positions: {positions}")
    
    # Cleanup
    await broker_manager.shutdown_all_brokers()

if __name__ == "__main__":
    asyncio.run(example_usage())
