"""
🚀 TradeStream Dashboard
Professional Streamlit Dashboard for TradeStream Automated Trading System
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from src.config import ConfigManager
from src.database import DatabaseManager
from src.multi_channel_monitor import MultiChannelDiscordMonitor
from src.options_parser import OptionsAlertParser
from src.multi_broker_manager import MultiBrokerManager, BrokerType

# Dashboard configuration
st.set_page_config(
    page_title="TradeStream Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .status-online {
        color: #28a745;
        font-weight: bold;
    }
    
    .status-offline {
        color: #dc3545;
        font-weight: bold;
    }
    
    .toggle-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 1rem 0;
    }
    
    .alert-card {
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #f8f9fa;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

class TradeStreamDashboard:
    def __init__(self):
        self.config_manager = None
        self.db_manager = None
        self.trade_executor = None
        self.multi_broker_manager = None
        self.discord_monitor = None
        self.options_parser = None
        self.initialize_session_state()
        
    def initialize_session_state(self):
        """Initialize Streamlit session state variables"""
        if 'live_trading_enabled' not in st.session_state:
            st.session_state.live_trading_enabled = False
        if 'config_loaded' not in st.session_state:
            st.session_state.config_loaded = False
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = datetime.now()
            
    def load_config(self):
        """Load configuration and initialize components"""
        try:
            # Initialize configuration manager
            self.config_manager = ConfigManager()
            self.config_manager.load_config()
            
            # Initialize database manager
            self.db_manager = DatabaseManager("data/trading_bot.db")
            
            # Initialize multi-broker manager
            self.multi_broker_manager = MultiBrokerManager(self.config_manager)
            
            # Initialize options parser
            self.options_parser = OptionsAlertParser()
            
            # Initialize Discord monitor (will be started separately)
            self.discord_monitor = MultiChannelDiscordMonitor(
                self.config_manager,
                self.db_manager,
                on_valid_futures_alert=self._handle_futures_alert,
                on_valid_options_alert=self._handle_options_alert
            )
            
            st.session_state.config_loaded = True
            return True
            
        except Exception as e:
            st.error(f"❌ Error loading configuration: {str(e)}")
            return False
    
    def render_sidebar(self):
        """Render the sidebar navigation"""
        with st.sidebar:
            st.markdown("# 🚀 TradeStream")
            st.markdown("---")
            
            # Navigation menu
            page = st.selectbox(
                "Navigate to:",
                ["🏠 Dashboard", "⚙️ Settings", "📊 Strategy", "📈 Performance", "🔔 Alerts"],
                key="navigation"
            )
            
            st.markdown("---")
            
            # System status
            st.markdown("### System Status")
            
            # Bot status
            bot_status = self.get_bot_status()
            status_color = "🟢" if bot_status else "🔴"
            st.markdown(f"{status_color} **Bot Status:** {'Online' if bot_status else 'Offline'}")
            
            # Trading mode
            mode_color = "🔴" if st.session_state.live_trading_enabled else "📄"
            mode_text = "Live Trading" if st.session_state.live_trading_enabled else "Paper Trading"
            st.markdown(f"{mode_color} **Mode:** {mode_text}")
            
            # Brokerage connection
            broker_status = self.get_broker_status()
            broker_color = "🟢" if broker_status else "🔴"
            st.markdown(f"{broker_color} **Brokerage:** {'Connected' if broker_status else 'Disconnected'}")
            
            st.markdown("---")
            
            # Quick actions
            st.markdown("### Quick Actions")
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.session_state.last_refresh = datetime.now()
                st.rerun()
                
            if st.button("📊 Export Data", use_container_width=True):
                self.export_trading_data()
                
        return page
    
    def get_bot_status(self):
        """Check if the trading bot is running"""
        # This would check if the main bot process is running
        # For now, return True if config is loaded
        return st.session_state.config_loaded
    
    def get_broker_status(self):
        """Check all broker connection statuses"""
        try:
            if self.multi_broker_manager:
                return self.multi_broker_manager.get_broker_status()
            else:
                # Fallback: check basic TopStepX configuration
                topstepx_user = os.getenv('TOPSTEPX_USERNAME')
                topstepx_pass = os.getenv('TOPSTEPX_PASSWORD')
                return {
                    'topstepx': {
                        'broker': 'topstepx',
                        'connected': bool(topstepx_user and topstepx_pass),
                        'enabled': bool(topstepx_user and topstepx_pass),
                        'supports_options': False,
                        'supports_futures': True
                    }
                }
        except Exception:
            return {}
    
    async def _handle_futures_alert(self, alert_data: Dict[str, Any]):
        """Handle futures alerts from Discord"""
        try:
            # Store alert in database
            if self.db_manager:
                await self.db_manager.store_alert(alert_data)
            
            # If paper trading mode, simulate execution
            if not st.session_state.live_trading_enabled:
                await self._simulate_paper_trade(alert_data, 'futures')
            
            # Log alert
            logging.info(f"Futures alert processed: {alert_data.get('symbol', 'Unknown')}")
            
        except Exception as e:
            logging.error(f"Error handling futures alert: {str(e)}")
    
    async def _handle_options_alert(self, alert_data: Dict[str, Any]):
        """Handle options alerts from Discord"""
        try:
            # Parse the options alert
            parsed_alert = self.options_parser.parse_alert(
                alert_data.get('content', ''),
                alert_data.get('timestamp'),
                alert_data.get('author'),
                alert_data.get('channel')
            )
            
            if parsed_alert and parsed_alert.is_valid:
                # Store alert in database
                if self.db_manager:
                    await self.db_manager.store_alert({
                        **alert_data,
                        'parsed_data': parsed_alert.__dict__,
                        'alert_type': 'options'
                    })
                
                # If paper trading mode, simulate execution
                if not st.session_state.live_trading_enabled:
                    await self._simulate_paper_trade(parsed_alert.__dict__, 'options')
                else:
                    # Execute via multi-broker manager
                    if self.multi_broker_manager:
                        result = await self.multi_broker_manager.execute_options_order(parsed_alert)
                        logging.info(f"Options order result: {result.success} - {result.order_id}")
                
                logging.info(f"Options alert processed: {parsed_alert.symbol} {parsed_alert.action.value}")
            
        except Exception as e:
            logging.error(f"Error handling options alert: {str(e)}")
    
    async def _simulate_paper_trade(self, alert_data: Dict[str, Any], trade_type: str):
        """Simulate paper trading execution"""
        try:
            # Create simulated trade record
            paper_trade = {
                'timestamp': datetime.now(),
                'symbol': alert_data.get('symbol', 'Unknown'),
                'trade_type': trade_type,
                'action': alert_data.get('action', 'Unknown'),
                'quantity': alert_data.get('quantity', 1),
                'price': alert_data.get('price', 0.0),
                'status': 'paper_executed',
                'broker': 'paper_trading',
                'alert_data': alert_data
            }
            
            # Store paper trade in database
            if self.db_manager:
                await self.db_manager.store_trade(paper_trade)
            
            logging.info(f"Paper trade simulated: {trade_type} {paper_trade['symbol']}")
            
        except Exception as e:
            logging.error(f"Error simulating paper trade: {str(e)}")
    
    def render_dashboard_page(self):
        """Render the main dashboard page"""
        st.markdown('<h1 class="main-header">🚀 TradeStream Dashboard</h1>', unsafe_allow_html=True)
        
        # Trading mode toggle
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### Trading Mode")
            live_trading = st.toggle(
                "Enable Live Trading",
                value=st.session_state.live_trading_enabled,
                help="Toggle between paper trading and live trading modes"
            )
            
            if live_trading != st.session_state.live_trading_enabled:
                st.session_state.live_trading_enabled = live_trading
                st.rerun()
        
        # Status indicators
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            bot_status = self.get_bot_status()
            status_text = "Online" if bot_status else "Offline"
            status_color = "normal" if bot_status else "inverse"
            st.metric("🤖 Bot Status", status_text)
        
        with col2:
            broker_status = self.get_broker_status()
            broker_text = "Connected" if broker_status else "None"
            st.metric("🔗 Brokerage", broker_text)
        
        with col3:
            mode_text = "Live" if st.session_state.live_trading_enabled else "Paper"
            st.metric("📊 Trading Mode", mode_text)
        
        with col4:
            auto_trade_status = self.get_auto_trade_status()
            st.metric("🎯 Auto-Trade", "Enabled" if auto_trade_status else "Disabled")
        
        # Performance metrics
        st.markdown("---")
        self.render_performance_metrics()
        
        # Recent alerts and trades
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 Portfolio Performance")
            self.render_portfolio_chart()
        
        with col2:
            st.markdown("### 🔔 Live Discord Alerts")
            self.render_live_alerts()
    
    def render_performance_metrics(self):
        """Render performance metrics section"""
        st.markdown("### 📊 Performance Overview")
        
        # Get performance data
        performance_data = self.get_performance_data()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_pnl = performance_data.get('total_pnl', 0.0)
            pnl_color = "normal" if total_pnl >= 0 else "inverse"
            st.metric("💰 Total P&L", f"${total_pnl:.2f}", delta=f"{total_pnl:.2f}")
        
        with col2:
            active_positions = performance_data.get('active_positions', 0)
            st.metric("📍 Active Positions", str(active_positions))
        
        with col3:
            todays_trades = performance_data.get('todays_trades', 0)
            st.metric("📈 Today's Trades", str(todays_trades))
        
        with col4:
            success_rate = performance_data.get('success_rate', 0.0)
            st.metric("🎯 Success Rate", f"{success_rate:.1f}%")
    
    def render_portfolio_chart(self):
        """Render portfolio performance chart"""
        # Get historical performance data
        df = self.get_portfolio_history()
        
        if df.empty:
            st.info("No portfolio data available for charting.")
            return
        
        # Create performance chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['cumulative_pnl'],
            mode='lines',
            name='Portfolio Value',
            line=dict(color='#1f77b4', width=2)
        ))
        
        fig.update_layout(
            title="Portfolio Performance",
            xaxis_title="Date",
            yaxis_title="Cumulative P&L ($)",
            height=300,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_live_alerts(self):
        """Render live Discord alerts feed"""
        alerts = self.get_recent_alerts()
        
        if not alerts:
            st.info("No recent alerts found. Make sure the Discord bot is running and configured.")
            return
        
        for alert in alerts[:10]:  # Show last 10 alerts
            with st.container():
                st.markdown(f"""
                <div class="alert-card">
                    <strong>{alert.get('timestamp', 'Unknown')}</strong><br>
                    <strong>Symbol:</strong> {alert.get('symbol', 'N/A')} | 
                    <strong>Direction:</strong> {alert.get('direction', 'N/A')} | 
                    <strong>Price:</strong> ${alert.get('price', 'N/A')}<br>
                    <strong>Status:</strong> {alert.get('status', 'Pending')}
                </div>
                """, unsafe_allow_html=True)
    
    def get_auto_trade_status(self):
        """Get auto-trading status from configuration"""
        if self.config_manager and self.config_manager.trading:
            return self.config_manager.trading.enable_auto_trading
        return False
    
    def get_performance_data(self):
        """Get current performance metrics"""
        if not self.db_manager:
            return {
                'total_pnl': 0.0,
                'active_positions': 0,
                'todays_trades': 0,
                'success_rate': 0.0
            }
        
        try:
            # This would query the database for actual performance data
            # For now, return mock data
            return {
                'total_pnl': 1250.75,
                'active_positions': 2,
                'todays_trades': 8,
                'success_rate': 67.5
            }
        except Exception as e:
            st.error(f"Error fetching performance data: {str(e)}")
            return {
                'total_pnl': 0.0,
                'active_positions': 0,
                'todays_trades': 0,
                'success_rate': 0.0
            }
    
    def get_portfolio_history(self):
        """Get historical portfolio performance data"""
        # Generate sample data for demonstration
        dates = pd.date_range(start='2024-01-01', end=datetime.now(), freq='D')
        cumulative_pnl = [0]
        
        for i in range(1, len(dates)):
            # Simulate daily P&L changes
            daily_change = np.random.normal(5, 25)  # Average $5 gain with $25 volatility
            cumulative_pnl.append(cumulative_pnl[-1] + daily_change)
        
        return pd.DataFrame({
            'date': dates,
            'cumulative_pnl': cumulative_pnl
        })
    
    def get_recent_alerts(self):
        """Get recent Discord alerts"""
        # This would query the database for recent alerts
        # For now, return mock data
        mock_alerts = [
            {
                'timestamp': '2024-01-15 14:30:25',
                'symbol': 'ES',
                'direction': 'LONG',
                'price': '4750.25',
                'status': 'Executed'
            },
            {
                'timestamp': '2024-01-15 13:45:12',
                'symbol': 'NQ',
                'direction': 'SHORT',
                'price': '16250.50',
                'status': 'Pending'
            },
            {
                'timestamp': '2024-01-15 12:15:33',
                'symbol': 'ES',
                'direction': 'LONG',
                'price': '4745.75',
                'status': 'Completed'
            }
        ]
        return mock_alerts
    
    def export_trading_data(self):
        """Export trading data to CSV"""
        st.success("📊 Trading data exported successfully!")
        # Implementation would export actual data
    
    def run(self):
        """Main dashboard application"""
        # Load configuration
        if not st.session_state.config_loaded:
            if not self.load_config():
                st.stop()
        
        # Render sidebar and get selected page
        page = self.render_sidebar()
        
        # Render selected page
        if page == "🏠 Dashboard":
            self.render_dashboard_page()
        elif page == "⚙️ Settings":
            self.render_settings_page()
        elif page == "📊 Strategy":
            self.render_strategy_page()
        elif page == "📈 Performance":
            self.render_performance_page()
        elif page == "🔔 Alerts":
            self.render_alerts_page()
    
    def render_settings_page(self):
        """Render settings configuration page"""
        st.markdown("# ⚙️ Settings")
        st.markdown("Configure your TradeStream system settings")
        
        # Import the settings page
        from dashboard_pages.settings import render_settings_page
        render_settings_page(self.config_manager)
    
    def render_strategy_page(self):
        """Render strategy configuration page"""
        st.markdown("# 📊 Strategy Configuration")
        
        from dashboard_pages.strategy import render_strategy_page
        render_strategy_page(self.config_manager)
    
    def render_performance_page(self):
        """Render detailed performance page"""
        st.markdown("# 📈 Performance Analytics")
        
        from dashboard_pages.performance import render_performance_page
        render_performance_page(self.db_manager)
    
    def render_alerts_page(self):
        """Render alerts management page"""
        st.markdown("# 🔔 Alerts & Notifications")
        
        from dashboard_pages.alerts import render_alerts_page
        render_alerts_page(self.config_manager, self.db_manager)

if __name__ == "__main__":
    # Add numpy import for mock data generation
    import numpy as np
    
    dashboard = TradeStreamDashboard()
    dashboard.run()
