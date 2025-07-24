"""
Database Schema and Operations for JMoney Discord Alert Trading System
Handles SQLite database creation, management, and CRUD operations
"""

import sqlite3
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from contextlib import contextmanager


class DatabaseManager:
    """Main database manager for the trading system"""
    
    def __init__(self, db_path: str = "data/trading_data.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
    def initialize_database(self) -> bool:
        """Initialize database with all required tables"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create alerts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME NOT NULL,
                        discord_message_id TEXT UNIQUE,
                        author TEXT NOT NULL,
                        channel_id INTEGER NOT NULL,
                        raw_content TEXT NOT NULL,
                        parsed_price REAL,
                        parsed_size TEXT,
                        parsed_stop REAL,
                        target_1 REAL,
                        target_2 REAL,
                        is_valid BOOLEAN DEFAULT 0,
                        processing_status TEXT DEFAULT 'pending',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create trades table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        alert_id INTEGER,
                        trade_type TEXT NOT NULL,  -- 'LONG', 'SHORT'
                        symbol TEXT NOT NULL,
                        entry_price REAL,
                        quantity INTEGER NOT NULL,
                        stop_loss REAL,
                        target_1 REAL,
                        target_2 REAL,
                        order_id TEXT,
                        fill_price REAL,
                        fill_quantity INTEGER,
                        fill_timestamp DATETIME,
                        status TEXT DEFAULT 'pending',  -- 'pending', 'filled', 'cancelled', 'rejected'
                        pnl REAL DEFAULT 0.0,
                        commission REAL DEFAULT 0.0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (alert_id) REFERENCES alerts (id)
                    )
                ''')
                
                # Create positions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS positions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        avg_entry_price REAL NOT NULL,
                        current_price REAL,
                        unrealized_pnl REAL DEFAULT 0.0,
                        realized_pnl REAL DEFAULT 0.0,
                        stop_loss REAL,
                        target_1 REAL,
                        target_2 REAL,
                        status TEXT DEFAULT 'open',  -- 'open', 'closed', 'partial'
                        opened_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        closed_at DATETIME,
                        related_trades TEXT  -- JSON array of trade IDs
                    )
                ''')
                
                # Create performance table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE NOT NULL UNIQUE,
                        total_trades INTEGER DEFAULT 0,
                        winning_trades INTEGER DEFAULT 0,
                        losing_trades INTEGER DEFAULT 0,
                        gross_profit REAL DEFAULT 0.0,
                        gross_loss REAL DEFAULT 0.0,
                        net_pnl REAL DEFAULT 0.0,
                        commission_paid REAL DEFAULT 0.0,
                        win_rate REAL DEFAULT 0.0,
                        avg_win REAL DEFAULT 0.0,
                        avg_loss REAL DEFAULT 0.0,
                        max_drawdown REAL DEFAULT 0.0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create system_log table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        level TEXT NOT NULL,
                        component TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details TEXT,  -- JSON for additional data
                        alert_id INTEGER,
                        trade_id INTEGER,
                        FOREIGN KEY (alert_id) REFERENCES alerts (id),
                        FOREIGN KEY (trade_id) REFERENCES trades (id)
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_author ON alerts(author)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_performance_date ON performance(date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_log_timestamp ON system_log(timestamp)')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            return False
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    # Alert operations
    def insert_alert(self, discord_message_id: str, author: str, channel_id: int, 
                    raw_content: str, parsed_price: Optional[float] = None,
                    parsed_size: Optional[str] = None, parsed_stop: Optional[float] = None,
                    target_1: Optional[float] = None, target_2: Optional[float] = None,
                    is_valid: bool = False) -> Optional[int]:
        """Insert a new alert record"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO alerts (
                        timestamp, discord_message_id, author, channel_id, raw_content,
                        parsed_price, parsed_size, parsed_stop, target_1, target_2, is_valid
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now(timezone.utc), discord_message_id, author, channel_id,
                    raw_content, parsed_price, parsed_size, parsed_stop, target_1, target_2, is_valid
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Error inserting alert: {e}")
            return None
    
    def get_alert(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """Get alert by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM alerts WHERE id = ?', (alert_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Error getting alert {alert_id}: {e}")
            return None
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM alerts 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting recent alerts: {e}")
            return []
    
    # Trade operations
    def insert_trade(self, alert_id: Optional[int], trade_type: str, symbol: str,
                    entry_price: Optional[float], quantity: int, stop_loss: Optional[float] = None,
                    target_1: Optional[float] = None, target_2: Optional[float] = None,
                    order_id: Optional[str] = None) -> Optional[int]:
        """Insert a new trade record"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trades (
                        alert_id, trade_type, symbol, entry_price, quantity,
                        stop_loss, target_1, target_2, order_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    alert_id, trade_type, symbol, entry_price, quantity,
                    stop_loss, target_1, target_2, order_id
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Error inserting trade: {e}")
            return None
    
    def update_trade_fill(self, trade_id: int, fill_price: float, fill_quantity: int,
                         fill_timestamp: datetime, status: str = 'filled') -> bool:
        """Update trade with fill information"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE trades 
                    SET fill_price = ?, fill_quantity = ?, fill_timestamp = ?, 
                        status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (fill_price, fill_quantity, fill_timestamp, status, trade_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error updating trade fill {trade_id}: {e}")
            return False
    
    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open trades"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM trades 
                    WHERE status IN ('pending', 'filled') 
                    ORDER BY created_at DESC
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting open trades: {e}")
            return []
    
    # Performance operations
    def update_daily_performance(self, date: str, **kwargs) -> bool:
        """Update daily performance metrics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                fields = []
                values = []
                for key, value in kwargs.items():
                    if key in ['total_trades', 'winning_trades', 'losing_trades', 'gross_profit',
                              'gross_loss', 'net_pnl', 'commission_paid', 'win_rate', 'avg_win',
                              'avg_loss', 'max_drawdown']:
                        fields.append(f"{key} = ?")
                        values.append(value)
                
                if not fields:
                    return False
                
                values.extend([date, date])
                
                cursor.execute(f'''
                    INSERT INTO performance (date, {', '.join(kwargs.keys())})
                    VALUES (?, {', '.join(['?' for _ in kwargs])})
                    ON CONFLICT(date) DO UPDATE SET
                    {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
                ''', [date] + list(kwargs.values()) + values[:-2])
                
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error updating daily performance: {e}")
            return False
    
    # System log operations
    def log_system_event(self, level: str, component: str, message: str,
                        details: Optional[str] = None, alert_id: Optional[int] = None,
                        trade_id: Optional[int] = None) -> bool:
        """Log system event to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO system_log (level, component, message, details, alert_id, trade_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (level, component, message, details, alert_id, trade_id))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error logging system event: {e}")
            return False
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get basic system statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total alerts
                cursor.execute('SELECT COUNT(*) FROM alerts')
                stats['total_alerts'] = cursor.fetchone()[0]
                
                # Valid alerts
                cursor.execute('SELECT COUNT(*) FROM alerts WHERE is_valid = 1')
                stats['valid_alerts'] = cursor.fetchone()[0]
                
                # Total trades
                cursor.execute('SELECT COUNT(*) FROM trades')
                stats['total_trades'] = cursor.fetchone()[0]
                
                # Open positions
                cursor.execute('SELECT COUNT(*) FROM positions WHERE status = "open"')
                stats['open_positions'] = cursor.fetchone()[0]
                
                return stats
        except Exception as e:
            self.logger.error(f"Error getting system stats: {e}")
            return {}


# Global database instance
db = DatabaseManager()
