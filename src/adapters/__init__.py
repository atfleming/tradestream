"""
Broker Adapters Package
Contains adapters for all supported brokers, interfacing with DiscordAlertsTrader implementations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from ..options_parser import ParsedOptionsAlert

@dataclass
class BrokerExecutionResult:
    """Result of broker order execution"""
    success: bool
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class BaseBrokerAdapter(ABC):
    """Base class for all broker adapters"""
    
    def __init__(self, config: Any):
        """Initialize broker adapter with configuration"""
        self.config = config
        self.broker_instance = None
        self.connected = False
        self.name = "unknown"
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize broker connection"""
        pass
    
    @abstractmethod
    async def execute_options_order(self, alert: ParsedOptionsAlert) -> BrokerExecutionResult:
        """Execute options order based on parsed alert"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        pass
    
    @abstractmethod
    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get recent orders"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get broker status"""
        return {
            'broker': self.name,
            'connected': self.connected,
            'enabled': self.config.enabled if hasattr(self.config, 'enabled') else False,
            'supports_options': True,
            'supports_futures': False
        }
    
    async def shutdown(self):
        """Shutdown broker connection"""
        self.connected = False
        if hasattr(self.broker_instance, 'close'):
            try:
                await self.broker_instance.close()
            except:
                pass
