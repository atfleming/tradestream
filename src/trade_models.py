"""
Shared Trade Models for TradeStream
Contains data classes and enums used across multiple modules to avoid circular imports
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum


class TradeStatus(Enum):
    """Trade execution status"""
    PENDING = "PENDING"
    ENTRY_SUBMITTED = "ENTRY_SUBMITTED"
    ENTRY_FILLED = "ENTRY_FILLED"
    STOP_PLACED = "STOP_PLACED"
    TARGET1_HIT = "TARGET1_HIT"
    TARGET2_HIT = "TARGET2_HIT"
    STOPPED_OUT = "STOPPED_OUT"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


class PositionStatus(Enum):
    """Position status"""
    FULL = "FULL"          # Full position active
    HALF = "HALF"          # Half position after T1 hit
    CLOSED = "CLOSED"      # Position fully closed


@dataclass
class OrderInfo:
    """Order information"""
    order_id: Optional[str] = None
    side: str = ""  # "BUY" or "SELL"
    quantity: int = 0
    price: Optional[float] = None
    order_type: str = "MARKET"  # "MARKET" or "LIMIT"
    status: str = "PENDING"
    fill_price: Optional[float] = None
    fill_quantity: int = 0
    timestamp: Optional[datetime] = None


@dataclass
class TradePosition:
    """Represents an active trade position"""
    alert_id: int
    trade_id: Optional[int] = None
    
    # Alert details
    entry_price: float = 0.0
    stop_price: float = 0.0
    target1_price: float = 0.0
    target2_price: float = 0.0
    size_code: str = ""
    full_quantity: int = 0
    
    # Position tracking
    current_quantity: int = 0
    position_status: PositionStatus = PositionStatus.FULL
    trade_status: TradeStatus = TradeStatus.PENDING
    
    # Order tracking
    entry_order_id: Optional[str] = None
    stop_order_id: Optional[str] = None
    target1_order_id: Optional[str] = None
    target2_order_id: Optional[str] = None
    
    # Execution details
    entry_fill_price: Optional[float] = None
    entry_fill_time: Optional[datetime] = None
    target1_fill_price: Optional[float] = None
    target1_fill_time: Optional[datetime] = None
    target2_fill_price: Optional[float] = None
    target2_fill_time: Optional[datetime] = None
    stop_fill_price: Optional[float] = None
    stop_fill_time: Optional[datetime] = None
    
    # P&L tracking
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'alert_id': self.alert_id,
            'trade_id': self.trade_id,
            'entry_price': self.entry_price,
            'stop_price': self.stop_price,
            'target1_price': self.target1_price,
            'target2_price': self.target2_price,
            'size_code': self.size_code,
            'full_quantity': self.full_quantity,
            'current_quantity': self.current_quantity,
            'position_status': self.position_status.value,
            'trade_status': self.trade_status.value,
            'entry_order_id': self.entry_order_id,
            'stop_order_id': self.stop_order_id,
            'target1_order_id': self.target1_order_id,
            'target2_order_id': self.target2_order_id,
            'entry_fill_price': self.entry_fill_price,
            'entry_fill_time': self.entry_fill_time.isoformat() if self.entry_fill_time else None,
            'target1_fill_price': self.target1_fill_price,
            'target1_fill_time': self.target1_fill_time.isoformat() if self.target1_fill_time else None,
            'target2_fill_price': self.target2_fill_price,
            'target2_fill_time': self.target2_fill_time.isoformat() if self.target2_fill_time else None,
            'stop_fill_price': self.stop_fill_price,
            'stop_fill_time': self.stop_fill_time.isoformat() if self.stop_fill_time else None,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
