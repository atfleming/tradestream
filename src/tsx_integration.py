"""
TopStepX API Integration for JMoney Discord Alert Trading System
Handles authentication, session management, and trading operations with TopStepX
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

try:
    from .config import ConfigManager
    from .database import DatabaseManager
    from .trade_models import OrderInfo
except ImportError:
    from config import ConfigManager
    from database import DatabaseManager
    from trade_models import OrderInfo

# TopStepX API imports (will be available after installing tsx_api)
try:
    from tsxapipy.auth import authenticate
    from tsxapipy.api.client import APIClient
    from tsxapipy.trading import OrderPlacer
    from tsxapipy.real_time import UserHubStream
    from tsxapipy.api import schemas as api_schemas
    from tsxapipy.api.exceptions import APIError, APIResponseParsingError
except ImportError:
    # Mock classes for development/testing
    class APIClient:
        def __init__(self, *args, **kwargs): pass
    class OrderPlacer:
        def __init__(self, *args, **kwargs): pass
    class UserHubStream:
        def __init__(self, *args, **kwargs): pass
    class APIError(Exception): pass
    class APIResponseParsingError(Exception): pass
    def authenticate(): return "mock_token", datetime.now()


@dataclass
class TSXCredentials:
    """TopStepX API credentials"""
    api_key: str
    api_secret: str
    account_id: str
    environment: str = "DEMO"  # "DEMO" or "LIVE"


@dataclass
class ContractInfo:
    """Contract information for trading"""
    contract_id: str
    symbol: str
    tick_size: float
    tick_value: float
    margin_requirement: float


# OrderInfo is now imported from trade_models.py to avoid circular dependencies


class TopStepXIntegration:
    """Main class for TopStepX API integration"""
    
    def __init__(self, config: ConfigManager, db: DatabaseManager):
        """
        Initialize TopStepX integration
        
        Args:
            config: Configuration manager instance
            db: Database manager instance
        """
        self.config = config
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # API components
        self.api_client: Optional[APIClient] = None
        self.order_placer: Optional[OrderPlacer] = None
        self.user_stream: Optional[UserHubStream] = None
        
        # Connection status
        self.is_connected = False
        self.is_authenticated = False
        self.last_auth_time: Optional[datetime] = None
        
        # Contract information
        self.mes_contract: Optional[ContractInfo] = None
        
        # Account information
        self.account_balance: float = 0.0
        self.available_margin: float = 0.0
        self.current_positions: Dict[str, Any] = {}
        
    async def initialize(self) -> bool:
        """Initialize TopStepX API connection and authentication"""
        try:
            self.logger.info("Initializing TopStepX API connection...")
            
            # Load credentials from environment variables
            credentials = self._load_credentials()
            if not credentials:
                self.logger.error("Failed to load TopStepX credentials")
                return False
            
            # Authenticate with TopStepX API
            if not await self._authenticate(credentials):
                self.logger.error("Failed to authenticate with TopStepX")
                return False
            
            # Initialize API client and order placer
            if not await self._initialize_api_client():
                self.logger.error("Failed to initialize API client")
                return False
            
            # Load contract information
            if not await self._load_contract_info():
                self.logger.error("Failed to load contract information")
                return False
            
            # Initialize user stream for real-time updates
            if not await self._initialize_user_stream():
                self.logger.error("Failed to initialize user stream")
                return False
            
            # Get initial account information
            if not await self._update_account_info():
                self.logger.error("Failed to get account information")
                return False
            
            self.is_connected = True
            self.logger.info("✅ TopStepX API initialized successfully")
            
            # Log successful connection
            self.db.log_system_event(
                level="INFO",
                component="tsx_integration",
                message="TopStepX API connection established",
                details=f"Account: {credentials.account_id}, Environment: {credentials.environment}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing TopStepX API: {e}")
            return False
    
    def _load_credentials(self) -> Optional[TSXCredentials]:
        """Load TopStepX credentials from environment variables"""
        try:
            api_key = os.getenv('TOPSTEP_API_KEY')
            api_secret = os.getenv('TOPSTEP_API_SECRET')
            environment = os.getenv('TOPSTEP_ENVIRONMENT', 'DEMO')
            
            if not api_key or not api_secret:
                self.logger.error("TOPSTEP_API_KEY and TOPSTEP_API_SECRET environment variables required")
                return None
            
            account_id = self.config.trading.account_id if self.config.trading else None
            if not account_id:
                self.logger.error("TopStep account ID not configured")
                return None
            
            return TSXCredentials(
                api_key=api_key,
                api_secret=api_secret,
                account_id=account_id,
                environment=environment
            )
            
        except Exception as e:
            self.logger.error(f"Error loading credentials: {e}")
            return None
    
    async def _authenticate(self, credentials: TSXCredentials) -> bool:
        """Authenticate with TopStepX API"""
        try:
            # Set environment variables for tsx_api
            os.environ['TOPSTEP_API_KEY'] = credentials.api_key
            os.environ['TOPSTEP_API_SECRET'] = credentials.api_secret
            os.environ['TOPSTEP_ENVIRONMENT'] = credentials.environment
            
            # Authenticate using tsx_api
            token_str, acquired_at_dt = authenticate()
            
            if token_str:
                self.is_authenticated = True
                self.last_auth_time = acquired_at_dt
                self.logger.info(f"✅ Authenticated successfully at {acquired_at_dt}")
                return True
            else:
                self.logger.error("Authentication failed - no token received")
                return False
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    async def _initialize_api_client(self) -> bool:
        """Initialize API client and order placer"""
        try:
            if not self.is_authenticated:
                return False
            
            # Create API client
            token_str, acquired_at_dt = authenticate()  # Get fresh token
            self.api_client = APIClient(initial_token=token_str, token_acquired_at=acquired_at_dt)
            
            # Create order placer
            account_id = int(self.config.trading.account_id) if self.config.trading else 0
            self.order_placer = OrderPlacer(api_client=self.api_client, account_id=account_id)
            
            self.logger.info("✅ API client and order placer initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing API client: {e}")
            return False
    
    async def _load_contract_info(self) -> bool:
        """Load MES contract information"""
        try:
            if not self.api_client:
                return False
            
            # Search for MES contract
            contracts = self.api_client.search_contracts_by_text("MES")
            
            if not contracts:
                self.logger.error("No MES contracts found")
                return False
            
            # Find the current month contract
            mes_contract = None
            for contract in contracts:
                if contract.symbol_root == "MES" and contract.is_active:
                    mes_contract = contract
                    break
            
            if not mes_contract:
                self.logger.error("No active MES contract found")
                return False
            
            # Store contract information using config values
            trading_config = self.config.trading
            self.mes_contract = ContractInfo(
                contract_id=mes_contract.contract_id,
                symbol=mes_contract.symbol,
                tick_size=trading_config.tick_size if trading_config else 0.25,
                tick_value=trading_config.tick_value if trading_config else 1.25,
                margin_requirement=trading_config.margin_requirement if trading_config else 500.0
            )
            
            self.logger.info(f"✅ MES contract loaded: {self.mes_contract.symbol}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading contract info: {e}")
            return False
    
    async def _initialize_user_stream(self) -> bool:
        """Initialize user stream for real-time account updates"""
        try:
            if not self.api_client:
                return False
            
            account_id = int(self.config.trading.account_id) if self.config.trading else 0
            
            # Create user stream with callbacks
            self.user_stream = UserHubStream(
                api_client=self.api_client,
                account_id_to_watch=account_id,
                on_order_update=self._handle_order_update,
                on_position_update=self._handle_position_update,
                on_account_update=self._handle_account_update,
                on_user_trade_update=self._handle_trade_update,
                on_state_change_callback=self._handle_stream_state_change
            )
            
            # Start the stream
            if self.user_stream.start():
                self.logger.info("✅ User stream initialized and started")
                return True
            else:
                self.logger.error("Failed to start user stream")
                return False
                
        except Exception as e:
            self.logger.error(f"Error initializing user stream: {e}")
            return False
    
    async def _update_account_info(self) -> bool:
        """Update account balance and margin information"""
        try:
            if not self.api_client:
                return False
            
            # Get account information
            accounts = self.api_client.get_accounts()
            
            if not accounts:
                self.logger.error("No accounts found")
                return False
            
            # Find our account
            target_account_id = self.config.trading.account_id if self.config.trading else ""
            account = None
            
            for acc in accounts:
                if str(acc.account_id) == target_account_id:
                    account = acc
                    break
            
            if not account:
                self.logger.error(f"Account {target_account_id} not found")
                return False
            
            # Update account information
            self.account_balance = float(account.net_liquidation_value or 0)
            self.available_margin = float(account.available_funds or 0)
            
            self.logger.info(f"✅ Account info updated - Balance: ${self.account_balance:.2f}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating account info: {e}")
            return False
    
    # Real-time stream event handlers
    def _handle_order_update(self, order_data: Dict[str, Any]):
        """Handle order update from user stream"""
        try:
            self.logger.info(f"Order update: {order_data}")
            
            # Log to database
            self.db.log_system_event(
                level="INFO",
                component="tsx_integration",
                message="Order update received",
                details=str(order_data)
            )
            
        except Exception as e:
            self.logger.error(f"Error handling order update: {e}")
    
    def _handle_position_update(self, position_data: Dict[str, Any]):
        """Handle position update from user stream"""
        try:
            self.logger.info(f"Position update: {position_data}")
            
            # Update current positions
            symbol = position_data.get('symbol', '')
            if symbol:
                self.current_positions[symbol] = position_data
            
            # Log to database
            self.db.log_system_event(
                level="INFO",
                component="tsx_integration",
                message="Position update received",
                details=str(position_data)
            )
            
        except Exception as e:
            self.logger.error(f"Error handling position update: {e}")
    
    def _handle_account_update(self, account_data: Dict[str, Any]):
        """Handle account update from user stream"""
        try:
            self.logger.info(f"Account update: {account_data}")
            
            # Update account balance if available
            if 'net_liquidation_value' in account_data:
                self.account_balance = float(account_data['net_liquidation_value'])
            
            if 'available_funds' in account_data:
                self.available_margin = float(account_data['available_funds'])
            
        except Exception as e:
            self.logger.error(f"Error handling account update: {e}")
    
    def _handle_trade_update(self, trade_data: Dict[str, Any]):
        """Handle trade update from user stream"""
        try:
            self.logger.info(f"Trade update: {trade_data}")
            
            # Log to database
            self.db.log_system_event(
                level="INFO",
                component="tsx_integration",
                message="Trade update received",
                details=str(trade_data)
            )
            
        except Exception as e:
            self.logger.error(f"Error handling trade update: {e}")
    
    def _handle_stream_state_change(self, state_name: str):
        """Handle user stream state changes"""
        self.logger.info(f"User stream state: {state_name}")
    
    # Trading operations
    async def place_market_order(self, side: str, quantity: int, 
                               contract_id: Optional[str] = None) -> Optional[OrderInfo]:
        """
        Place a market order
        
        Args:
            side: "BUY" or "SELL"
            quantity: Number of contracts
            contract_id: Contract ID (uses MES if not specified)
            
        Returns:
            OrderInfo object with order details
        """
        try:
            if not self.order_placer or not self.mes_contract:
                self.logger.error("Order placer or contract not initialized")
                return None
            
            contract_id = contract_id or self.mes_contract.contract_id
            
            self.logger.info(f"Placing {side} market order: {quantity} contracts of {contract_id}")
            
            # Place order using tsx_api
            order_id = self.order_placer.place_market_order(
                side=side,
                size=quantity,
                contract_id=contract_id
            )
            
            if order_id:
                order_info = OrderInfo(
                    order_id=str(order_id),
                    side=side,
                    quantity=quantity,
                    order_type="MARKET",
                    status="SUBMITTED",
                    timestamp=datetime.now(timezone.utc)
                )
                
                self.logger.info(f"✅ Market order placed: {order_id}")
                
                # Log to database
                self.db.log_system_event(
                    level="INFO",
                    component="tsx_integration",
                    message=f"Market order placed: {side} {quantity} contracts",
                    details=f"Order ID: {order_id}"
                )
                
                return order_info
            else:
                self.logger.error("Failed to place market order")
                return None
                
        except Exception as e:
            self.logger.error(f"Error placing market order: {e}")
            return None
    
    async def place_stop_order(self, side: str, quantity: int, stop_price: float,
                             contract_id: Optional[str] = None) -> Optional[OrderInfo]:
        """
        Place a stop loss order
        
        Args:
            side: "BUY" or "SELL"
            quantity: Number of contracts
            stop_price: Stop trigger price
            contract_id: Contract ID (uses MES if not specified)
            
        Returns:
            OrderInfo object with order details
        """
        try:
            if not self.order_placer or not self.mes_contract:
                self.logger.error("Order placer or contract not initialized")
                return None
            
            contract_id = contract_id or self.mes_contract.contract_id
            
            self.logger.info(f"Placing {side} stop order: {quantity} contracts at {stop_price}")
            
            # Place stop order using tsx_api
            order_id = self.order_placer.place_stop_order(
                side=side,
                size=quantity,
                stop_price=stop_price,
                contract_id=contract_id
            )
            
            if order_id:
                order_info = OrderInfo(
                    order_id=str(order_id),
                    side=side,
                    quantity=quantity,
                    price=stop_price,
                    order_type="STOP",
                    status="SUBMITTED",
                    timestamp=datetime.now(timezone.utc)
                )
                
                self.logger.info(f"✅ Stop order placed: {order_id}")
                
                # Log to database
                self.db.log_system_event(
                    level="INFO",
                    component="tsx_integration",
                    message=f"Stop order placed: {side} {quantity} contracts at {stop_price}",
                    details=f"Order ID: {order_id}"
                )
                
                return order_info
            else:
                self.logger.error("Failed to place stop order")
                return None
                
        except Exception as e:
            self.logger.error(f"Error placing stop order: {e}")
            return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            if not self.order_placer:
                self.logger.error("Order placer not initialized")
                return False
            
            self.logger.info(f"Cancelling order: {order_id}")
            
            # Cancel order using tsx_api
            success = self.order_placer.cancel_order(int(order_id))
            
            if success:
                self.logger.info(f"✅ Order cancelled: {order_id}")
                
                # Log to database
                self.db.log_system_event(
                    level="INFO",
                    component="tsx_integration",
                    message=f"Order cancelled: {order_id}"
                )
                
                return True
            else:
                self.logger.error(f"Failed to cancel order: {order_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error cancelling order: {e}")
            return False
    
    def get_current_price(self) -> Optional[float]:
        """Get current market price for MES"""
        try:
            # This would typically come from market data stream
            # For now, return None - will be implemented with market data integration
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting current price: {e}")
            return None
    
    def get_account_balance(self) -> float:
        """Get current account balance"""
        return self.account_balance
    
    def get_available_margin(self) -> float:
        """Get available margin"""
        return self.available_margin
    
    def get_current_positions(self) -> Dict[str, Any]:
        """Get current positions"""
        return self.current_positions.copy()
    
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        # This would typically check market hours
        # For now, return True - will be implemented with proper market hours logic
        return True
    
    async def disconnect(self):
        """Disconnect from TopStepX API"""
        try:
            if self.user_stream:
                self.user_stream.stop()
            
            self.is_connected = False
            self.is_authenticated = False
            
            self.logger.info("✅ Disconnected from TopStepX API")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")


# Global instance (will be initialized by main application)
tsx_api: Optional[TopStepXIntegration] = None
