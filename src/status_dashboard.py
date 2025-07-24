"""
Real-time Status Dashboard for JMoney Discord Alert Trading System
Console-based monitoring and reporting dashboard
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import time

try:
    from .config import ConfigManager
    from .database import DatabaseManager
    from .trade_tracker import TradeTracker, PerformanceMetrics
    from .paper_trading import PaperTradingSimulator
    from .tsx_integration import TopStepXIntegration
    from .trade_executor import TradeExecutor
except ImportError:
    from config import ConfigManager
    from database import DatabaseManager
    from trade_tracker import TradeTracker, PerformanceMetrics
    from paper_trading import PaperTradingSimulator
    from tsx_integration import TopStepXIntegration
    from trade_executor import TradeExecutor


class StatusDashboard:
    """Real-time console-based status dashboard"""
    
    def __init__(self, config: ConfigManager, db: DatabaseManager, 
                 trade_tracker: TradeTracker, trade_executor: Optional[TradeExecutor] = None,
                 paper_trader: Optional[PaperTradingSimulator] = None,
                 tsx_api: Optional[TopStepXIntegration] = None):
        """Initialize status dashboard"""
        self.config = config
        self.db = db
        self.trade_tracker = trade_tracker
        self.trade_executor = trade_executor
        self.paper_trader = paper_trader
        self.tsx_api = tsx_api
        self.logger = logging.getLogger(__name__)
        
        # Dashboard state
        self.is_running = False
        self.refresh_interval = 5  # seconds
        self.last_update = datetime.now(timezone.utc)
        
    def clear_screen(self):
        """Clear the console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        try:
            # Get basic system info
            status = {
                'timestamp': datetime.now(timezone.utc),
                'uptime': (datetime.now(timezone.utc) - self.last_update).total_seconds(),
                'components': {
                    'database': self.db is not None,
                    'trade_executor': self.trade_executor is not None,
                    'paper_trader': self.paper_trader is not None,
                    'tsx_api': self.tsx_api is not None
                }
            }
            
            # Get trading status
            if self.trade_executor:
                active_positions = self.trade_executor.get_active_positions()
                status['trading'] = {
                    'active_positions': len(active_positions),
                    'daily_pnl': self.trade_executor.get_daily_pnl(),
                    'daily_trades': self.trade_executor.get_daily_trade_count()
                }
            
            # Get paper trading status
            if self.paper_trader:
                paper_stats = self.paper_trader.get_paper_statistics()
                status['paper_trading'] = paper_stats
            
            # Get live trading status
            if self.tsx_api:
                status['live_trading'] = {
                    'connected': self.tsx_api.is_connected,
                    'account_balance': self.tsx_api.get_account_balance(),
                    'available_margin': self.tsx_api.get_available_margin()
                }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}
    
    def format_currency(self, amount: float) -> str:
        """Format currency with color coding"""
        if amount > 0:
            return f"\033[92m+${amount:,.2f}\033[0m"  # Green for positive
        elif amount < 0:
            return f"\033[91m${amount:,.2f}\033[0m"   # Red for negative
        else:
            return f"${amount:,.2f}"
    
    def format_percentage(self, percentage: float) -> str:
        """Format percentage with color coding"""
        if percentage > 0:
            return f"\033[92m{percentage:+.1f}%\033[0m"  # Green for positive
        elif percentage < 0:
            return f"\033[91m{percentage:+.1f}%\033[0m"   # Red for negative
        else:
            return f"{percentage:.1f}%"
    
    def render_header(self):
        """Render dashboard header"""
        print("=" * 80)
        print("🚀 JMONEY DISCORD ALERT TRADING SYSTEM - LIVE DASHBOARD")
        print("=" * 80)
        print(f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()
    
    def render_system_status(self, status: Dict[str, Any]):
        """Render system status section"""
        print("🔧 SYSTEM STATUS")
        print("-" * 40)
        
        components = status.get('components', {})
        print(f"Database:      {'✅ Connected' if components.get('database') else '❌ Disconnected'}")
        print(f"Trade Executor: {'✅ Active' if components.get('trade_executor') else '❌ Inactive'}")
        print(f"Paper Trader:  {'✅ Active' if components.get('paper_trader') else '❌ Inactive'}")
        print(f"Live Trading:  {'✅ Active' if components.get('tsx_api') else '❌ Inactive'}")
        print()
    
    def render_trading_status(self, status: Dict[str, Any]):
        """Render trading status section"""
        print("📊 TRADING STATUS")
        print("-" * 40)
        
        trading = status.get('trading', {})
        if trading:
            print(f"Active Positions: {trading.get('active_positions', 0)}")
            print(f"Daily P&L:       {self.format_currency(trading.get('daily_pnl', 0.0))}")
            print(f"Daily Trades:    {trading.get('daily_trades', 0)}")
        else:
            print("No trading data available")
        print()
    
    def render_paper_trading(self, status: Dict[str, Any]):
        """Render paper trading section"""
        paper = status.get('paper_trading', {})
        if not paper:
            return
        
        print("🎯 PAPER TRADING")
        print("-" * 40)
        print(f"Account Balance:  {self.format_currency(paper.get('account_balance', 0.0))}")
        print(f"Total P&L:       {self.format_currency(paper.get('total_pnl', 0.0))}")
        print(f"Total Trades:    {paper.get('total_trades', 0)}")
        print(f"Win Rate:        {self.format_percentage(paper.get('win_rate', 0.0))}")
        print(f"Max Drawdown:    {self.format_currency(paper.get('max_drawdown', 0.0))}")
        print()
    
    def render_live_trading(self, status: Dict[str, Any]):
        """Render live trading section"""
        live = status.get('live_trading', {})
        if not live:
            return
        
        print("🚀 LIVE TRADING")
        print("-" * 40)
        print(f"Connection:      {'✅ Connected' if live.get('connected') else '❌ Disconnected'}")
        print(f"Account Balance: {self.format_currency(live.get('account_balance', 0.0))}")
        print(f"Available Margin: {self.format_currency(live.get('available_margin', 0.0))}")
        print()
    
    def render_performance_metrics(self):
        """Render performance metrics section"""
        try:
            metrics = self.trade_tracker.calculate_performance_metrics(days=30)
            
            print("📈 PERFORMANCE METRICS (30 Days)")
            print("-" * 40)
            print(f"Total Trades:    {metrics.total_trades}")
            print(f"Win Rate:        {self.format_percentage(metrics.win_rate)}")
            print(f"Total P&L:       {self.format_currency(metrics.total_pnl)}")
            print(f"Profit Factor:   {metrics.profit_factor:.2f}")
            print(f"Sharpe Ratio:    {metrics.sharpe_ratio:.2f}")
            print(f"Max Drawdown:    {self.format_currency(metrics.max_drawdown)}")
            print(f"Current Streak:  {metrics.current_streak:+d}")
            print()
            
        except Exception as e:
            print(f"❌ Error loading performance metrics: {e}")
            print()
    
    def render_recent_alerts(self):
        """Render recent alerts section"""
        try:
            # Get recent alerts from database
            cursor = self.db.connection.cursor()
            cursor.execute("""
                SELECT created_at, author, parsed_price, parsed_size, parsed_stop, is_valid
                FROM alerts 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            alerts = cursor.fetchall()
            
            print("📢 RECENT ALERTS")
            print("-" * 40)
            if alerts:
                for alert in alerts:
                    timestamp = alert[0][:19]  # Remove timezone info for display
                    status = "✅" if alert[5] else "❌"
                    print(f"{timestamp} | {status} | {alert[1]} | {alert[2]} | {alert[3]} | Stop: {alert[4]}")
            else:
                print("No recent alerts")
            print()
            
        except Exception as e:
            print(f"❌ Error loading recent alerts: {e}")
            print()
    
    def render_daily_summary(self):
        """Render today's summary"""
        try:
            daily_summary = self.trade_tracker.get_daily_summary()
            
            print("📅 TODAY'S SUMMARY")
            print("-" * 40)
            print(f"Alerts:          {daily_summary.get('alert_count', 0)}")
            print(f"Trades:          {daily_summary.get('trade_count', 0)}")
            print(f"Execution Rate:  {daily_summary.get('execution_rate', 0.0):.1f}%")
            print(f"Daily P&L:       {self.format_currency(daily_summary.get('total_pnl', 0.0))}")
            print(f"Win Rate:        {self.format_percentage(daily_summary.get('win_rate', 0.0))}")
            print()
            
        except Exception as e:
            print(f"❌ Error loading daily summary: {e}")
            print()
    
    def render_footer(self):
        """Render dashboard footer"""
        print("-" * 80)
        print("🔄 Auto-refresh every 5 seconds | Press Ctrl+C to exit")
        print("=" * 80)
    
    def render_dashboard(self):
        """Render complete dashboard"""
        try:
            # Clear screen and get status
            self.clear_screen()
            status = self.get_system_status()
            
            # Render all sections
            self.render_header()
            self.render_system_status(status)
            self.render_trading_status(status)
            self.render_paper_trading(status)
            self.render_live_trading(status)
            self.render_performance_metrics()
            self.render_recent_alerts()
            self.render_daily_summary()
            self.render_footer()
            
        except Exception as e:
            print(f"❌ Dashboard render error: {e}")
    
    async def start(self):
        """Start the dashboard"""
        self.is_running = True
        self.logger.info("📊 Status dashboard started")
        
        try:
            while self.is_running:
                self.render_dashboard()
                await asyncio.sleep(self.refresh_interval)
                
        except KeyboardInterrupt:
            self.logger.info("📊 Dashboard stopped by user")
        except Exception as e:
            self.logger.error(f"Dashboard error: {e}")
        finally:
            self.is_running = False
    
    def stop(self):
        """Stop the dashboard"""
        self.is_running = False
        self.logger.info("📊 Status dashboard stopped")
    
    def generate_daily_report(self) -> str:
        """Generate comprehensive daily report"""
        try:
            daily_summary = self.trade_tracker.get_daily_summary()
            metrics = self.trade_tracker.calculate_performance_metrics(days=1)
            alert_comparison = self.trade_tracker.get_alert_vs_execution_comparison(days=1)
            
            report = f"""
📊 JMONEY TRADING SYSTEM - DAILY REPORT
{'=' * 50}
Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}

📈 DAILY PERFORMANCE:
• Total Alerts: {daily_summary.get('alert_count', 0)}
• Trades Executed: {daily_summary.get('trade_count', 0)}
• Execution Rate: {daily_summary.get('execution_rate', 0.0):.1f}%
• Daily P&L: {daily_summary.get('total_pnl', 0.0):+.2f}
• Win Rate: {daily_summary.get('win_rate', 0.0):.1f}%

🎯 TRADE BREAKDOWN:
• Winning Trades: {daily_summary.get('winning_trades', 0)}
• Losing Trades: {daily_summary.get('losing_trades', 0)}
• Average Win: ${metrics.average_win:.2f}
• Average Loss: ${metrics.average_loss:.2f}

📊 ALERT ANALYSIS:
"""
            
            for comparison in alert_comparison[:5]:  # Show last 5 alerts
                status = "✅ EXECUTED" if comparison['executed'] else "❌ MISSED"
                pnl_text = f"P&L: ${comparison['pnl']:.2f}" if comparison['pnl'] else ""
                report += f"• {comparison['alert_time'][:19]} | {status} | Price: {comparison['alert_price']} | {pnl_text}\n"
            
            report += f"\n{'=' * 50}\n"
            return report
            
        except Exception as e:
            return f"❌ Error generating daily report: {e}"


async def run_dashboard_standalone():
    """Run dashboard as standalone application"""
    # This would be used if running dashboard separately
    from config import ConfigManager
    from database import DatabaseManager
    from trade_tracker import TradeTracker
    
    config = ConfigManager()
    config.load_config()
    
    db = DatabaseManager(config)
    db.initialize_database()
    
    tracker = TradeTracker(config, db)
    dashboard = StatusDashboard(config, db, tracker)
    
    await dashboard.start()


if __name__ == "__main__":
    asyncio.run(run_dashboard_standalone())
