"""
Advanced Risk Management System for JMoney Discord Alert Trading System
Comprehensive risk metrics, monitoring, and control mechanisms
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import statistics
import math

try:
    from .config import ConfigManager
    from .database import DatabaseManager
    from .trade_tracker import TradeTracker, PerformanceMetrics
except ImportError:
    from config import ConfigManager
    from database import DatabaseManager
    from trade_tracker import TradeTracker, PerformanceMetrics


@dataclass
class RiskMetrics:
    """Advanced risk metrics"""
    # Volatility metrics
    volatility: float = 0.0  # Annualized volatility
    var_95: float = 0.0  # Value at Risk (95% confidence)
    var_99: float = 0.0  # Value at Risk (99% confidence)
    
    # Drawdown metrics
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0  # Days
    recovery_factor: float = 0.0  # Net profit / Max drawdown
    
    # Risk-adjusted returns
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0  # Uses downside deviation
    calmar_ratio: float = 0.0  # Annual return / Max drawdown
    
    # Trade distribution
    skewness: float = 0.0  # Distribution asymmetry
    kurtosis: float = 0.0  # Distribution tail heaviness
    
    # Risk ratios
    profit_factor: float = 0.0  # Gross profit / Gross loss
    risk_reward_ratio: float = 0.0  # Average win / Average loss
    expectancy: float = 0.0  # Expected value per trade
    
    # Consistency metrics
    win_rate: float = 0.0
    consecutive_losses_max: int = 0
    consecutive_wins_max: int = 0
    
    # Position sizing risk
    kelly_criterion: float = 0.0  # Optimal position size percentage
    risk_of_ruin: float = 0.0  # Probability of losing all capital


@dataclass
class RiskAlert:
    """Risk alert notification"""
    level: str  # "WARNING", "CRITICAL", "EMERGENCY"
    category: str  # "DRAWDOWN", "POSITION_SIZE", "DAILY_LOSS", etc.
    message: str
    value: float
    threshold: float
    timestamp: datetime
    action_required: bool = False


class RiskManager:
    """Advanced risk management and monitoring system"""
    
    def __init__(self, config: ConfigManager, db: DatabaseManager, trade_tracker: TradeTracker):
        """Initialize risk manager"""
        self.config = config
        self.db = db
        self.trade_tracker = trade_tracker
        self.logger = logging.getLogger(__name__)
        
        # Risk monitoring state
        self.current_drawdown = 0.0
        self.peak_balance = 10000.0  # Starting balance assumption
        self.daily_pnl = 0.0
        self.risk_alerts: List[RiskAlert] = []
        
        # Risk thresholds
        self.max_drawdown_threshold = 0.10  # 10%
        self.daily_loss_threshold = 0.02  # 2% of account
        self.var_threshold = 0.05  # 5% VaR limit
        
    def calculate_advanced_risk_metrics(self, days: int = 30) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        try:
            # Get performance data
            performances = self.trade_tracker.get_trade_performance(days)
            
            if not performances:
                return RiskMetrics()
            
            # Extract returns
            returns = [p.pnl for p in performances]
            positive_returns = [r for r in returns if r > 0]
            negative_returns = [r for r in returns if r < 0]
            
            # Basic statistics
            mean_return = statistics.mean(returns) if returns else 0.0
            std_return = statistics.stdev(returns) if len(returns) > 1 else 0.0
            
            # Volatility (annualized)
            volatility = std_return * math.sqrt(252) if std_return > 0 else 0.0
            
            # Value at Risk
            var_95, var_99 = self._calculate_var(returns)
            
            # Drawdown metrics
            current_dd, max_dd, max_dd_duration, recovery_factor = self._calculate_drawdown_metrics(performances)
            
            # Risk-adjusted returns
            sharpe_ratio = self._calculate_sharpe_ratio(returns, mean_return, std_return)
            sortino_ratio = self._calculate_sortino_ratio(returns, mean_return)
            calmar_ratio = self._calculate_calmar_ratio(returns, max_dd)
            
            # Distribution metrics
            skewness = self._calculate_skewness(returns)
            kurtosis = self._calculate_kurtosis(returns)
            
            # Risk ratios
            profit_factor = self._calculate_profit_factor(positive_returns, negative_returns)
            risk_reward_ratio = self._calculate_risk_reward_ratio(positive_returns, negative_returns)
            expectancy = self._calculate_expectancy(returns)
            
            # Consistency metrics
            win_rate = (len(positive_returns) / len(returns) * 100) if returns else 0.0
            consecutive_losses, consecutive_wins = self._calculate_consecutive_streaks(performances)
            
            # Position sizing
            kelly_criterion = self._calculate_kelly_criterion(returns)
            risk_of_ruin = self._calculate_risk_of_ruin(returns)
            
            return RiskMetrics(
                volatility=volatility,
                var_95=var_95,
                var_99=var_99,
                current_drawdown=current_dd,
                max_drawdown=max_dd,
                max_drawdown_duration=max_dd_duration,
                recovery_factor=recovery_factor,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                skewness=skewness,
                kurtosis=kurtosis,
                profit_factor=profit_factor,
                risk_reward_ratio=risk_reward_ratio,
                expectancy=expectancy,
                win_rate=win_rate,
                consecutive_losses_max=consecutive_losses,
                consecutive_wins_max=consecutive_wins,
                kelly_criterion=kelly_criterion,
                risk_of_ruin=risk_of_ruin
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            return RiskMetrics()
    
    def _calculate_var(self, returns: List[float]) -> Tuple[float, float]:
        """Calculate Value at Risk at 95% and 99% confidence levels"""
        if len(returns) < 20:  # Need sufficient data
            return 0.0, 0.0
        
        sorted_returns = sorted(returns)
        n = len(sorted_returns)
        
        # 95% VaR (5th percentile)
        var_95_index = int(0.05 * n)
        var_95 = abs(sorted_returns[var_95_index]) if var_95_index < n else 0.0
        
        # 99% VaR (1st percentile)
        var_99_index = int(0.01 * n)
        var_99 = abs(sorted_returns[var_99_index]) if var_99_index < n else 0.0
        
        return var_95, var_99
    
    def _calculate_drawdown_metrics(self, performances) -> Tuple[float, float, int, float]:
        """Calculate comprehensive drawdown metrics"""
        if not performances:
            return 0.0, 0.0, 0, 0.0
        
        # Sort by time
        sorted_performances = sorted(performances, key=lambda p: p.entry_time)
        
        # Calculate running balance and drawdowns
        running_balance = self.peak_balance
        peak_balance = running_balance
        max_drawdown = 0.0
        current_drawdown = 0.0
        max_dd_duration = 0
        current_dd_duration = 0
        total_return = 0.0
        
        for performance in sorted_performances:
            running_balance += performance.pnl
            total_return += performance.pnl
            
            if running_balance > peak_balance:
                peak_balance = running_balance
                current_dd_duration = 0
            else:
                current_dd_duration += 1
            
            drawdown = (peak_balance - running_balance) / peak_balance * 100
            current_drawdown = drawdown
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_dd_duration = max(max_dd_duration, current_dd_duration)
        
        # Recovery factor
        recovery_factor = (total_return / max_drawdown) if max_drawdown > 0 else 0.0
        
        return current_drawdown, max_drawdown, max_dd_duration, recovery_factor
    
    def _calculate_sharpe_ratio(self, returns: List[float], mean_return: float, std_return: float) -> float:
        """Calculate Sharpe ratio (assuming risk-free rate = 0)"""
        if std_return == 0 or len(returns) < 2:
            return 0.0
        
        # Annualize the ratio
        return (mean_return / std_return) * math.sqrt(252)
    
    def _calculate_sortino_ratio(self, returns: List[float], mean_return: float) -> float:
        """Calculate Sortino ratio (uses downside deviation)"""
        negative_returns = [r for r in returns if r < 0]
        
        if not negative_returns:
            return float('inf') if mean_return > 0 else 0.0
        
        downside_deviation = statistics.stdev(negative_returns)
        if downside_deviation == 0:
            return 0.0
        
        return (mean_return / downside_deviation) * math.sqrt(252)
    
    def _calculate_calmar_ratio(self, returns: List[float], max_drawdown: float) -> float:
        """Calculate Calmar ratio (annual return / max drawdown)"""
        if max_drawdown == 0:
            return 0.0
        
        annual_return = sum(returns) * (252 / len(returns)) if returns else 0.0
        return annual_return / (max_drawdown / 100)
    
    def _calculate_skewness(self, returns: List[float]) -> float:
        """Calculate skewness of returns distribution"""
        if len(returns) < 3:
            return 0.0
        
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        if std_return == 0:
            return 0.0
        
        n = len(returns)
        skewness = sum(((r - mean_return) / std_return) ** 3 for r in returns) / n
        
        return skewness
    
    def _calculate_kurtosis(self, returns: List[float]) -> float:
        """Calculate kurtosis of returns distribution"""
        if len(returns) < 4:
            return 0.0
        
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        if std_return == 0:
            return 0.0
        
        n = len(returns)
        kurtosis = sum(((r - mean_return) / std_return) ** 4 for r in returns) / n - 3
        
        return kurtosis
    
    def _calculate_profit_factor(self, positive_returns: List[float], negative_returns: List[float]) -> float:
        """Calculate profit factor"""
        gross_profit = sum(positive_returns) if positive_returns else 0.0
        gross_loss = abs(sum(negative_returns)) if negative_returns else 0.0
        
        return (gross_profit / gross_loss) if gross_loss > 0 else 0.0
    
    def _calculate_risk_reward_ratio(self, positive_returns: List[float], negative_returns: List[float]) -> float:
        """Calculate risk/reward ratio"""
        avg_win = statistics.mean(positive_returns) if positive_returns else 0.0
        avg_loss = abs(statistics.mean(negative_returns)) if negative_returns else 0.0
        
        return (avg_win / avg_loss) if avg_loss > 0 else 0.0
    
    def _calculate_expectancy(self, returns: List[float]) -> float:
        """Calculate expectancy (expected value per trade)"""
        return statistics.mean(returns) if returns else 0.0
    
    def _calculate_consecutive_streaks(self, performances) -> Tuple[int, int]:
        """Calculate maximum consecutive winning and losing streaks"""
        if not performances:
            return 0, 0
        
        sorted_performances = sorted(performances, key=lambda p: p.entry_time)
        
        max_losing_streak = 0
        max_winning_streak = 0
        current_losing_streak = 0
        current_winning_streak = 0
        
        for performance in sorted_performances:
            if performance.pnl > 0:
                current_winning_streak += 1
                current_losing_streak = 0
                max_winning_streak = max(max_winning_streak, current_winning_streak)
            elif performance.pnl < 0:
                current_losing_streak += 1
                current_winning_streak = 0
                max_losing_streak = max(max_losing_streak, current_losing_streak)
        
        return max_losing_streak, max_winning_streak
    
    def _calculate_kelly_criterion(self, returns: List[float]) -> float:
        """Calculate Kelly criterion for optimal position sizing"""
        if not returns:
            return 0.0
        
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r < 0]
        
        if not wins or not losses:
            return 0.0
        
        win_rate = len(wins) / len(returns)
        avg_win = statistics.mean(wins)
        avg_loss = abs(statistics.mean(losses))
        
        if avg_loss == 0:
            return 0.0
        
        # Kelly % = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_rate, q = 1-win_rate
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - win_rate
        
        kelly = (b * p - q) / b
        
        # Cap at reasonable levels
        return max(0.0, min(kelly, 0.25))  # Max 25% position size
    
    def _calculate_risk_of_ruin(self, returns: List[float]) -> float:
        """Calculate risk of ruin probability"""
        if not returns:
            return 0.0
        
        # Simplified risk of ruin calculation
        # This is a basic implementation - more sophisticated models exist
        
        win_rate = len([r for r in returns if r > 0]) / len(returns)
        
        if win_rate >= 0.5:
            return 0.0  # No risk if win rate >= 50%
        
        # Basic risk of ruin formula for unfavorable games
        risk_of_ruin = ((1 - win_rate) / win_rate) ** (self.peak_balance / 1000)  # Assuming $1000 risk units
        
        return min(risk_of_ruin, 1.0)
    
    async def monitor_real_time_risk(self) -> List[RiskAlert]:
        """Monitor real-time risk and generate alerts"""
        alerts = []
        
        try:
            # Check current drawdown
            current_metrics = self.calculate_advanced_risk_metrics(days=1)
            
            if current_metrics.current_drawdown > self.max_drawdown_threshold * 100:
                alert = RiskAlert(
                    level="CRITICAL",
                    category="DRAWDOWN",
                    message=f"Current drawdown {current_metrics.current_drawdown:.1f}% exceeds threshold {self.max_drawdown_threshold*100:.1f}%",
                    value=current_metrics.current_drawdown,
                    threshold=self.max_drawdown_threshold * 100,
                    timestamp=datetime.now(timezone.utc),
                    action_required=True
                )
                alerts.append(alert)
            
            # Check daily P&L
            daily_summary = self.trade_tracker.get_daily_summary()
            daily_pnl_pct = (daily_summary.get('total_pnl', 0.0) / self.peak_balance) * 100
            
            if daily_pnl_pct < -self.daily_loss_threshold * 100:
                alert = RiskAlert(
                    level="WARNING",
                    category="DAILY_LOSS",
                    message=f"Daily loss {daily_pnl_pct:.1f}% exceeds threshold {self.daily_loss_threshold*100:.1f}%",
                    value=daily_pnl_pct,
                    threshold=-self.daily_loss_threshold * 100,
                    timestamp=datetime.now(timezone.utc),
                    action_required=True
                )
                alerts.append(alert)
            
            # Check VaR
            if current_metrics.var_95 > self.var_threshold * self.peak_balance:
                alert = RiskAlert(
                    level="WARNING",
                    category="VAR",
                    message=f"95% VaR ${current_metrics.var_95:.2f} exceeds threshold ${self.var_threshold * self.peak_balance:.2f}",
                    value=current_metrics.var_95,
                    threshold=self.var_threshold * self.peak_balance,
                    timestamp=datetime.now(timezone.utc)
                )
                alerts.append(alert)
            
            # Store alerts
            self.risk_alerts.extend(alerts)
            
            # Log alerts
            for alert in alerts:
                if alert.level == "CRITICAL":
                    self.logger.critical(f"🚨 RISK ALERT: {alert.message}")
                elif alert.level == "WARNING":
                    self.logger.warning(f"⚠️ RISK ALERT: {alert.message}")
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error monitoring real-time risk: {e}")
            return []
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        try:
            metrics = self.calculate_advanced_risk_metrics(days=30)
            recent_alerts = [alert for alert in self.risk_alerts if 
                           (datetime.now(timezone.utc) - alert.timestamp).days < 1]
            
            return {
                'risk_metrics': metrics,
                'recent_alerts': len(recent_alerts),
                'critical_alerts': len([a for a in recent_alerts if a.level == "CRITICAL"]),
                'risk_score': self._calculate_risk_score(metrics),
                'recommendations': self._generate_risk_recommendations(metrics)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting risk summary: {e}")
            return {}
    
    def _calculate_risk_score(self, metrics: RiskMetrics) -> float:
        """Calculate overall risk score (0-100, lower is better)"""
        score = 0.0
        
        # Drawdown component (0-30 points)
        if metrics.max_drawdown > 20:
            score += 30
        elif metrics.max_drawdown > 10:
            score += 15
        elif metrics.max_drawdown > 5:
            score += 5
        
        # Volatility component (0-25 points)
        if metrics.volatility > 50:
            score += 25
        elif metrics.volatility > 30:
            score += 15
        elif metrics.volatility > 20:
            score += 5
        
        # Win rate component (0-20 points)
        if metrics.win_rate < 30:
            score += 20
        elif metrics.win_rate < 45:
            score += 10
        elif metrics.win_rate < 55:
            score += 5
        
        # Sharpe ratio component (0-25 points)
        if metrics.sharpe_ratio < 0:
            score += 25
        elif metrics.sharpe_ratio < 0.5:
            score += 15
        elif metrics.sharpe_ratio < 1.0:
            score += 5
        
        return min(score, 100.0)
    
    def _generate_risk_recommendations(self, metrics: RiskMetrics) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        if metrics.max_drawdown > 15:
            recommendations.append("Consider reducing position sizes due to high drawdown")
        
        if metrics.sharpe_ratio < 0.5:
            recommendations.append("Risk-adjusted returns are low - review strategy")
        
        if metrics.consecutive_losses_max > 5:
            recommendations.append("High consecutive losses - consider adding filters")
        
        if metrics.kelly_criterion < 0.1:
            recommendations.append("Kelly criterion suggests very small position sizes")
        
        if metrics.risk_of_ruin > 0.05:
            recommendations.append("Risk of ruin is elevated - reduce risk exposure")
        
        if metrics.volatility > 40:
            recommendations.append("High volatility detected - consider position sizing adjustments")
        
        return recommendations


# Global instance (will be initialized by main application)
risk_manager: Optional[RiskManager] = None
