"""
Alert Tracking System for TradeStream
Comprehensive tracking of Discord alerts, parsing results, and execution status
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json

from .database_manager import DatabaseManager
from .options_parser import ParsedOptionsAlert, OptionsAction, OptionsType

class AlertStatus(Enum):
    """Alert processing status"""
    RECEIVED = "received"
    PARSED = "parsed"
    PARSE_FAILED = "parse_failed"
    PAPER_EXECUTED = "paper_executed"
    LIVE_EXECUTED = "live_executed"
    EXECUTION_FAILED = "execution_failed"
    IGNORED = "ignored"

class AlertType(Enum):
    """Type of trading alert"""
    FUTURES = "futures"
    OPTIONS = "options"
    UNKNOWN = "unknown"

@dataclass
class TrackedAlert:
    """Comprehensive alert tracking record"""
    id: Optional[str] = None
    timestamp: datetime = None
    raw_content: str = ""
    author: str = ""
    channel: str = ""
    alert_type: AlertType = AlertType.UNKNOWN
    status: AlertStatus = AlertStatus.RECEIVED
    
    # Parsing results
    is_valid: bool = False
    parse_confidence: float = 0.0
    parsed_data: Optional[Dict[str, Any]] = None
    parse_error: Optional[str] = None
    
    # Execution results
    execution_broker: Optional[str] = None
    execution_order_id: Optional[str] = None
    execution_price: Optional[float] = None
    execution_quantity: Optional[int] = None
    execution_error: Optional[str] = None
    execution_timestamp: Optional[datetime] = None
    
    # Performance tracking
    current_pnl: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    realized_pnl: Optional[float] = None
    
    # Metadata
    processing_time_ms: Optional[float] = None
    notes: Optional[str] = None

class AlertTracker:
    """Comprehensive alert tracking and analytics system"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize alert tracker
        
        Args:
            db_manager: Database manager for persistent storage
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # In-memory cache for recent alerts
        self.recent_alerts: List[TrackedAlert] = []
        self.max_cache_size = 1000
        
        # Statistics tracking
        self.stats = {
            'total_alerts': 0,
            'valid_alerts': 0,
            'executed_alerts': 0,
            'failed_alerts': 0,
            'futures_alerts': 0,
            'options_alerts': 0,
            'paper_trades': 0,
            'live_trades': 0
        }
        
        # Initialize database tables
        asyncio.create_task(self._initialize_database())
    
    async def _initialize_database(self):
        """Initialize database tables for alert tracking"""
        try:
            # Create alerts table if it doesn't exist
            await self.db_manager.execute_query("""
                CREATE TABLE IF NOT EXISTS tracked_alerts (
                    id TEXT PRIMARY KEY,
                    timestamp DATETIME,
                    raw_content TEXT,
                    author TEXT,
                    channel TEXT,
                    alert_type TEXT,
                    status TEXT,
                    is_valid BOOLEAN,
                    parse_confidence REAL,
                    parsed_data TEXT,
                    parse_error TEXT,
                    execution_broker TEXT,
                    execution_order_id TEXT,
                    execution_price REAL,
                    execution_quantity INTEGER,
                    execution_error TEXT,
                    execution_timestamp DATETIME,
                    current_pnl REAL,
                    unrealized_pnl REAL,
                    realized_pnl REAL,
                    processing_time_ms REAL,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better query performance
            await self.db_manager.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON tracked_alerts(timestamp)
            """)
            
            await self.db_manager.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_alerts_status ON tracked_alerts(status)
            """)
            
            await self.db_manager.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_alerts_type ON tracked_alerts(alert_type)
            """)
            
            self.logger.info("Alert tracking database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing alert tracking database: {str(e)}")
    
    async def track_alert(self, 
                         raw_content: str,
                         author: str,
                         channel: str,
                         timestamp: Optional[datetime] = None) -> TrackedAlert:
        """
        Track a new Discord alert
        
        Args:
            raw_content: Raw Discord message content
            author: Message author
            channel: Discord channel name
            timestamp: Message timestamp (defaults to now)
            
        Returns:
            TrackedAlert object
        """
        start_time = datetime.now()
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create tracked alert
        alert = TrackedAlert(
            id=f"{channel}_{author}_{timestamp.timestamp()}",
            timestamp=timestamp,
            raw_content=raw_content,
            author=author,
            channel=channel,
            status=AlertStatus.RECEIVED
        )
        
        # Determine alert type based on channel
        if "futures" in channel.lower() or "es" in raw_content.upper() or "nq" in raw_content.upper():
            alert.alert_type = AlertType.FUTURES
        elif "options" in channel.lower() or "call" in raw_content.upper() or "put" in raw_content.upper():
            alert.alert_type = AlertType.OPTIONS
        else:
            alert.alert_type = AlertType.UNKNOWN
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        alert.processing_time_ms = processing_time
        
        # Add to cache
        self._add_to_cache(alert)
        
        # Store in database
        await self._store_alert(alert)
        
        # Update statistics
        self._update_stats('total_alerts', 1)
        if alert.alert_type == AlertType.FUTURES:
            self._update_stats('futures_alerts', 1)
        elif alert.alert_type == AlertType.OPTIONS:
            self._update_stats('options_alerts', 1)
        
        self.logger.info(f"Alert tracked: {alert.id} ({alert.alert_type.value})")
        
        return alert
    
    async def update_alert_parsing(self,
                                  alert_id: str,
                                  is_valid: bool,
                                  parse_confidence: float = 0.0,
                                  parsed_data: Optional[Dict[str, Any]] = None,
                                  parse_error: Optional[str] = None) -> bool:
        """
        Update alert with parsing results
        
        Args:
            alert_id: Alert ID to update
            is_valid: Whether parsing was successful
            parse_confidence: Confidence score (0.0 to 1.0)
            parsed_data: Parsed alert data
            parse_error: Error message if parsing failed
            
        Returns:
            True if update successful
        """
        try:
            # Find alert in cache
            alert = self._find_alert_in_cache(alert_id)
            
            if alert:
                # Update alert
                alert.is_valid = is_valid
                alert.parse_confidence = parse_confidence
                alert.parsed_data = parsed_data
                alert.parse_error = parse_error
                alert.status = AlertStatus.PARSED if is_valid else AlertStatus.PARSE_FAILED
                
                # Store updated alert
                await self._store_alert(alert)
                
                # Update statistics
                if is_valid:
                    self._update_stats('valid_alerts', 1)
                else:
                    self._update_stats('failed_alerts', 1)
                
                self.logger.info(f"Alert parsing updated: {alert_id} (valid: {is_valid})")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating alert parsing: {str(e)}")
            return False
    
    async def update_alert_execution(self,
                                   alert_id: str,
                                   broker: str,
                                   order_id: Optional[str] = None,
                                   price: Optional[float] = None,
                                   quantity: Optional[int] = None,
                                   error: Optional[str] = None,
                                   is_paper_trade: bool = False) -> bool:
        """
        Update alert with execution results
        
        Args:
            alert_id: Alert ID to update
            broker: Broker used for execution
            order_id: Order ID from broker
            price: Execution price
            quantity: Execution quantity
            error: Error message if execution failed
            is_paper_trade: Whether this was a paper trade
            
        Returns:
            True if update successful
        """
        try:
            # Find alert in cache
            alert = self._find_alert_in_cache(alert_id)
            
            if alert:
                # Update alert
                alert.execution_broker = broker
                alert.execution_order_id = order_id
                alert.execution_price = price
                alert.execution_quantity = quantity
                alert.execution_error = error
                alert.execution_timestamp = datetime.now()
                
                if error:
                    alert.status = AlertStatus.EXECUTION_FAILED
                    self._update_stats('failed_alerts', 1)
                elif is_paper_trade:
                    alert.status = AlertStatus.PAPER_EXECUTED
                    self._update_stats('paper_trades', 1)
                else:
                    alert.status = AlertStatus.LIVE_EXECUTED
                    self._update_stats('live_trades', 1)
                
                self._update_stats('executed_alerts', 1)
                
                # Store updated alert
                await self._store_alert(alert)
                
                self.logger.info(f"Alert execution updated: {alert_id} (broker: {broker})")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error updating alert execution: {str(e)}")
            return False
    
    async def get_recent_alerts(self, limit: int = 50, alert_type: Optional[AlertType] = None) -> List[TrackedAlert]:
        """
        Get recent alerts from cache and database
        
        Args:
            limit: Maximum number of alerts to return
            alert_type: Filter by alert type (optional)
            
        Returns:
            List of TrackedAlert objects
        """
        try:
            # Filter cache by type if specified
            cache_alerts = self.recent_alerts
            if alert_type:
                cache_alerts = [a for a in cache_alerts if a.alert_type == alert_type]
            
            # Sort by timestamp (most recent first)
            cache_alerts.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Return up to limit
            return cache_alerts[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting recent alerts: {str(e)}")
            return []
    
    async def get_alert_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get alert statistics for the specified period
        
        Args:
            days: Number of days to include in statistics
            
        Returns:
            Dictionary with statistics
        """
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            # Get alerts from database for the period
            query = """
                SELECT alert_type, status, COUNT(*) as count
                FROM tracked_alerts 
                WHERE timestamp >= ? 
                GROUP BY alert_type, status
            """
            
            results = await self.db_manager.fetch_all(query, (since_date,))
            
            # Process results
            stats = {
                'period_days': days,
                'total_alerts': 0,
                'futures_alerts': 0,
                'options_alerts': 0,
                'valid_alerts': 0,
                'executed_alerts': 0,
                'paper_trades': 0,
                'live_trades': 0,
                'failed_alerts': 0,
                'success_rate': 0.0,
                'by_status': {},
                'by_type': {}
            }
            
            for row in results:
                alert_type, status, count = row
                stats['total_alerts'] += count
                
                if alert_type == AlertType.FUTURES.value:
                    stats['futures_alerts'] += count
                elif alert_type == AlertType.OPTIONS.value:
                    stats['options_alerts'] += count
                
                if status in [AlertStatus.PARSED.value]:
                    stats['valid_alerts'] += count
                elif status in [AlertStatus.PAPER_EXECUTED.value, AlertStatus.LIVE_EXECUTED.value]:
                    stats['executed_alerts'] += count
                    if status == AlertStatus.PAPER_EXECUTED.value:
                        stats['paper_trades'] += count
                    else:
                        stats['live_trades'] += count
                elif status in [AlertStatus.PARSE_FAILED.value, AlertStatus.EXECUTION_FAILED.value]:
                    stats['failed_alerts'] += count
                
                # Track by status and type
                stats['by_status'][status] = stats['by_status'].get(status, 0) + count
                stats['by_type'][alert_type] = stats['by_type'].get(alert_type, 0) + count
            
            # Calculate success rate
            if stats['total_alerts'] > 0:
                stats['success_rate'] = (stats['executed_alerts'] / stats['total_alerts']) * 100
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting alert statistics: {str(e)}")
            return {}
    
    def _add_to_cache(self, alert: TrackedAlert):
        """Add alert to in-memory cache"""
        self.recent_alerts.append(alert)
        
        # Maintain cache size
        if len(self.recent_alerts) > self.max_cache_size:
            self.recent_alerts = self.recent_alerts[-self.max_cache_size:]
    
    def _find_alert_in_cache(self, alert_id: str) -> Optional[TrackedAlert]:
        """Find alert in cache by ID"""
        for alert in self.recent_alerts:
            if alert.id == alert_id:
                return alert
        return None
    
    async def _store_alert(self, alert: TrackedAlert):
        """Store alert in database"""
        try:
            # Convert parsed_data to JSON string
            parsed_data_json = json.dumps(alert.parsed_data) if alert.parsed_data else None
            
            # Upsert alert
            query = """
                INSERT OR REPLACE INTO tracked_alerts (
                    id, timestamp, raw_content, author, channel, alert_type, status,
                    is_valid, parse_confidence, parsed_data, parse_error,
                    execution_broker, execution_order_id, execution_price, execution_quantity,
                    execution_error, execution_timestamp, current_pnl, unrealized_pnl,
                    realized_pnl, processing_time_ms, notes, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            values = (
                alert.id, alert.timestamp, alert.raw_content, alert.author, alert.channel,
                alert.alert_type.value, alert.status.value, alert.is_valid, alert.parse_confidence,
                parsed_data_json, alert.parse_error, alert.execution_broker, alert.execution_order_id,
                alert.execution_price, alert.execution_quantity, alert.execution_error,
                alert.execution_timestamp, alert.current_pnl, alert.unrealized_pnl,
                alert.realized_pnl, alert.processing_time_ms, alert.notes, datetime.now()
            )
            
            await self.db_manager.execute_query(query, values)
            
        except Exception as e:
            self.logger.error(f"Error storing alert in database: {str(e)}")
    
    def _update_stats(self, key: str, increment: int):
        """Update statistics counter"""
        self.stats[key] = self.stats.get(key, 0) + increment
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current in-memory statistics"""
        return self.stats.copy()

# Example usage
async def example_usage():
    """Example of how to use the alert tracker"""
    from .database_manager import DatabaseManager
    
    # Initialize database and tracker
    db_manager = DatabaseManager("data/trading_bot.db")
    tracker = AlertTracker(db_manager)
    
    # Track a new alert
    alert = await tracker.track_alert(
        raw_content="BOUGHT SPY 01/31 480 CALLS @ 2.50",
        author="Twinsight Bot #7577",
        channel="TWI_Options"
    )
    
    # Update with parsing results
    await tracker.update_alert_parsing(
        alert.id,
        is_valid=True,
        parse_confidence=0.95,
        parsed_data={"symbol": "SPY", "action": "BTO", "price": 2.50}
    )
    
    # Update with execution results
    await tracker.update_alert_execution(
        alert.id,
        broker="webull",
        order_id="WB123456",
        price=2.50,
        quantity=1,
        is_paper_trade=True
    )
    
    # Get statistics
    stats = await tracker.get_alert_statistics(days=7)
    print(f"Alert statistics: {stats}")
    
    # Get recent alerts
    recent = await tracker.get_recent_alerts(limit=10)
    print(f"Recent alerts: {len(recent)}")

if __name__ == "__main__":
    asyncio.run(example_usage())
