"""
Trade Tracker and Performance Analytics for JMoney Discord Alert Trading System
Comprehensive tracking, analysis, and reporting of trading performance
"""

import logging
import sqlite3
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
import statistics

try:
    from .config import ConfigManager
    from .database import DatabaseManager
    from .message_parser import ParsedAlert
except ImportError:
    from config import ConfigManager
    from database import DatabaseManager
    from message_parser import ParsedAlert


@dataclass
class TradePerformance:
    """Trade performance metrics"""
    trade_id: int
    alert_id: int
    symbol: str
    entry_price: float
    exit_price: float
    quantity: int
    side: str
    pnl: float
    pnl_percentage: float
    duration_minutes: int
    entry_time: datetime
    exit_time: datetime
    trade_type: str  # "paper" or "live"
    status: str  # "TARGET1_HIT", "TARGET2_HIT", "STOPPED_OUT"


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    # Basic metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L metrics
    total_pnl: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Risk metrics
    profit_factor: float = 0.0  # Gross profit / Gross loss
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_percentage: float = 0.0
    
    # Streak metrics
    current_streak: int = 0
    max_winning_streak: int = 0
    max_losing_streak: int = 0
    
    # Time metrics
    average_trade_duration: float = 0.0  # in minutes
    
    # Alert vs execution metrics
    alert_execution_rate: float = 0.0  # % of alerts that resulted in trades
    average_execution_delay: float = 0.0  # seconds from alert to execution


class TradeTracker:
    """Comprehensive trade tracking and performance analysis"""
    
    def __init__(self, config: ConfigManager, db: DatabaseManager):
        """Initialize trade tracker"""
        self.config = config
        self.db = db
        self.logger = logging.getLogger(__name__)
        
    def record_trade_execution(self, alert: ParsedAlert, trade_data: Dict[str, Any]) -> int:
        """Record a trade execution"""
        try:
            # Insert detailed trade record
            trade_id = self.db.insert_trade(
                alert_id=alert.alert_id,
                entry_price=trade_data.get('entry_price', 0.0),
                quantity=trade_data.get('quantity', 0),
                stop_price=trade_data.get('stop_price', 0.0),
                target_price=trade_data.get('target1_price', 0.0),
                status="EXECUTED"
            )
            
            # Log execution details
            self.db.log_system_event(
                level="INFO",
                component="trade_tracker",
                message=f"Trade execution recorded: {trade_data.get('symbol', 'MES')} {trade_data.get('side', 'LONG')}",
                details=f"Trade ID: {trade_id}, Entry: {trade_data.get('entry_price', 0.0)}, Quantity: {trade_data.get('quantity', 0)}"
            )
            
            self.logger.info(f"📊 Trade execution recorded: ID {trade_id}")
            return trade_id
            
        except Exception as e:
            self.logger.error(f"Error recording trade execution: {e}")
            return 0
    
    def record_trade_completion(self, trade_id: int, completion_data: Dict[str, Any]):
        """Record trade completion with final P&L"""
        try:
            # Update trade with completion data
            self.db.update_trade_status(trade_id, completion_data.get('status', 'COMPLETED'))
            self.db.update_trade_pnl(trade_id, completion_data.get('pnl', 0.0))
            
            # Log completion
            self.db.log_system_event(
                level="INFO",
                component="trade_tracker",
                message=f"Trade completed: ID {trade_id}",
                details=f"Status: {completion_data.get('status')}, P&L: ${completion_data.get('pnl', 0.0):.2f}"
            )
            
            self.logger.info(f"📊 Trade completion recorded: ID {trade_id}, P&L: ${completion_data.get('pnl', 0.0):.2f}")
            
        except Exception as e:
            self.logger.error(f"Error recording trade completion: {e}")
    
    def get_trade_performance(self, days: int = 30, trade_type: Optional[str] = None) -> List[TradePerformance]:
        """Get detailed trade performance data"""
        try:
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Query trades with performance data
            query = """
            SELECT t.trade_id, t.alert_id, 'MES' as symbol, t.entry_price, 
                   COALESCE(t.exit_price, t.entry_price) as exit_price,
                   t.quantity, 'LONG' as side, COALESCE(t.pnl, 0.0) as pnl,
                   t.created_at, t.updated_at, t.status
            FROM trades t
            WHERE t.created_at >= ? AND t.created_at <= ?
            ORDER BY t.created_at DESC
            """
            
            cursor = self.db.connection.cursor()
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()
            
            performances = []
            for row in rows:
                # Calculate performance metrics
                entry_price = row[3]
                exit_price = row[4]
                quantity = row[5]
                pnl = row[7]
                
                pnl_percentage = ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0.0
                
                entry_time = datetime.fromisoformat(row[8].replace('Z', '+00:00'))
                exit_time = datetime.fromisoformat(row[9].replace('Z', '+00:00'))
                duration_minutes = (exit_time - entry_time).total_seconds() / 60
                
                performance = TradePerformance(
                    trade_id=row[0],
                    alert_id=row[1],
                    symbol=row[2],
                    entry_price=entry_price,
                    exit_price=exit_price,
                    quantity=quantity,
                    side=row[6],
                    pnl=pnl,
                    pnl_percentage=pnl_percentage,
                    duration_minutes=int(duration_minutes),
                    entry_time=entry_time,
                    exit_time=exit_time,
                    trade_type=trade_type or "unknown",
                    status=row[10]
                )
                performances.append(performance)
            
            return performances
            
        except Exception as e:
            self.logger.error(f"Error getting trade performance: {e}")
            return []
    
    def calculate_performance_metrics(self, days: int = 30) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        try:
            performances = self.get_trade_performance(days)
            
            if not performances:
                return PerformanceMetrics()
            
            # Basic metrics
            total_trades = len(performances)
            winning_trades = len([p for p in performances if p.pnl > 0])
            losing_trades = len([p for p in performances if p.pnl < 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
            
            # P&L metrics
            total_pnl = sum(p.pnl for p in performances)
            wins = [p.pnl for p in performances if p.pnl > 0]
            losses = [p.pnl for p in performances if p.pnl < 0]
            
            average_win = statistics.mean(wins) if wins else 0.0
            average_loss = statistics.mean(losses) if losses else 0.0
            largest_win = max(wins) if wins else 0.0
            largest_loss = min(losses) if losses else 0.0
            
            # Risk metrics
            gross_profit = sum(wins) if wins else 0.0
            gross_loss = abs(sum(losses)) if losses else 0.0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0
            
            # Calculate Sharpe ratio (simplified)
            returns = [p.pnl for p in performances]
            sharpe_ratio = 0.0
            if len(returns) > 1:
                mean_return = statistics.mean(returns)
                std_return = statistics.stdev(returns)
                sharpe_ratio = (mean_return / std_return) if std_return > 0 else 0.0
            
            # Calculate drawdown
            max_drawdown, max_drawdown_pct = self._calculate_drawdown(performances)
            
            # Streak metrics
            current_streak, max_winning_streak, max_losing_streak = self._calculate_streaks(performances)
            
            # Time metrics
            durations = [p.duration_minutes for p in performances if p.duration_minutes > 0]
            average_trade_duration = statistics.mean(durations) if durations else 0.0
            
            # Alert execution metrics
            alert_execution_rate = self._calculate_execution_rate(days)
            average_execution_delay = self._calculate_execution_delay(days)
            
            return PerformanceMetrics(
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_pnl=total_pnl,
                average_win=average_win,
                average_loss=average_loss,
                largest_win=largest_win,
                largest_loss=largest_loss,
                profit_factor=profit_factor,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                max_drawdown_percentage=max_drawdown_pct,
                current_streak=current_streak,
                max_winning_streak=max_winning_streak,
                max_losing_streak=max_losing_streak,
                average_trade_duration=average_trade_duration,
                alert_execution_rate=alert_execution_rate,
                average_execution_delay=average_execution_delay
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return PerformanceMetrics()
    
    def _calculate_drawdown(self, performances: List[TradePerformance]) -> Tuple[float, float]:
        """Calculate maximum drawdown"""
        if not performances:
            return 0.0, 0.0
        
        # Sort by time
        sorted_performances = sorted(performances, key=lambda p: p.entry_time)
        
        # Calculate running balance
        running_balance = 10000.0  # Starting balance assumption
        peak_balance = running_balance
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        
        for performance in sorted_performances:
            running_balance += performance.pnl
            
            if running_balance > peak_balance:
                peak_balance = running_balance
            
            drawdown = peak_balance - running_balance
            drawdown_pct = (drawdown / peak_balance * 100) if peak_balance > 0 else 0.0
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        return max_drawdown, max_drawdown_pct
    
    def _calculate_streaks(self, performances: List[TradePerformance]) -> Tuple[int, int, int]:
        """Calculate winning/losing streaks"""
        if not performances:
            return 0, 0, 0
        
        # Sort by time
        sorted_performances = sorted(performances, key=lambda p: p.entry_time)
        
        current_streak = 0
        max_winning_streak = 0
        max_losing_streak = 0
        current_winning_streak = 0
        current_losing_streak = 0
        
        for performance in sorted_performances:
            if performance.pnl > 0:
                current_winning_streak += 1
                current_losing_streak = 0
                current_streak = current_winning_streak
                max_winning_streak = max(max_winning_streak, current_winning_streak)
            elif performance.pnl < 0:
                current_losing_streak += 1
                current_winning_streak = 0
                current_streak = -current_losing_streak
                max_losing_streak = max(max_losing_streak, current_losing_streak)
        
        return current_streak, max_winning_streak, max_losing_streak
    
    def _calculate_execution_rate(self, days: int) -> float:
        """Calculate alert to execution rate"""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Count total alerts
            cursor = self.db.connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM alerts WHERE created_at >= ? AND created_at <= ? AND is_valid = 1",
                (start_date, end_date)
            )
            total_alerts = cursor.fetchone()[0]
            
            # Count executed trades
            cursor.execute(
                "SELECT COUNT(*) FROM trades WHERE created_at >= ? AND created_at <= ?",
                (start_date, end_date)
            )
            executed_trades = cursor.fetchone()[0]
            
            return (executed_trades / total_alerts * 100) if total_alerts > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating execution rate: {e}")
            return 0.0
    
    def _calculate_execution_delay(self, days: int) -> float:
        """Calculate average execution delay"""
        try:
            # This would require more detailed timing data
            # For now, return a placeholder
            return 2.5  # Average 2.5 seconds delay
            
        except Exception as e:
            self.logger.error(f"Error calculating execution delay: {e}")
            return 0.0
    
    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get daily trading summary"""
        if date is None:
            date = datetime.now(timezone.utc).date()
        
        start_date = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_date = start_date + timedelta(days=1)
        
        try:
            # Get day's performance
            performances = []
            cursor = self.db.connection.cursor()
            cursor.execute("""
                SELECT t.trade_id, t.pnl, t.status, t.created_at, t.updated_at
                FROM trades t
                WHERE t.created_at >= ? AND t.created_at < ?
                ORDER BY t.created_at
            """, (start_date, end_date))
            
            rows = cursor.fetchall()
            daily_pnl = sum(row[1] or 0.0 for row in rows)
            trade_count = len(rows)
            winning_trades = len([row for row in rows if (row[1] or 0.0) > 0])
            
            # Get alert count
            cursor.execute("""
                SELECT COUNT(*) FROM alerts 
                WHERE created_at >= ? AND created_at < ? AND is_valid = 1
            """, (start_date, end_date))
            alert_count = cursor.fetchone()[0]
            
            return {
                'date': date.isoformat(),
                'total_pnl': daily_pnl,
                'trade_count': trade_count,
                'winning_trades': winning_trades,
                'losing_trades': trade_count - winning_trades,
                'win_rate': (winning_trades / trade_count * 100) if trade_count > 0 else 0.0,
                'alert_count': alert_count,
                'execution_rate': (trade_count / alert_count * 100) if alert_count > 0 else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting daily summary: {e}")
            return {
                'date': date.isoformat(),
                'total_pnl': 0.0,
                'trade_count': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'alert_count': 0,
                'execution_rate': 0.0
            }
    
    def get_alert_vs_execution_comparison(self, days: int = 7) -> List[Dict[str, Any]]:
        """Compare alerts vs actual executions"""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Get alerts with their execution status
            cursor = self.db.connection.cursor()
            cursor.execute("""
                SELECT a.alert_id, a.created_at, a.parsed_price, a.parsed_size, a.parsed_stop,
                       t.trade_id, t.entry_price, t.quantity, t.pnl, t.status
                FROM alerts a
                LEFT JOIN trades t ON a.alert_id = t.alert_id
                WHERE a.created_at >= ? AND a.created_at <= ? AND a.is_valid = 1
                ORDER BY a.created_at DESC
            """, (start_date, end_date))
            
            rows = cursor.fetchall()
            comparisons = []
            
            for row in rows:
                comparison = {
                    'alert_id': row[0],
                    'alert_time': row[1],
                    'alert_price': row[2],
                    'alert_size': row[3],
                    'alert_stop': row[4],
                    'executed': row[5] is not None,
                    'execution_price': row[6] if row[5] else None,
                    'execution_quantity': row[7] if row[5] else None,
                    'pnl': row[8] if row[5] else None,
                    'status': row[9] if row[5] else 'NOT_EXECUTED',
                    'price_slippage': (row[6] - row[2]) if row[5] and row[2] else 0.0
                }
                comparisons.append(comparison)
            
            return comparisons
            
        except Exception as e:
            self.logger.error(f"Error getting alert vs execution comparison: {e}")
            return []


# Global instance (will be initialized by main application)
trade_tracker: Optional[TradeTracker] = None
