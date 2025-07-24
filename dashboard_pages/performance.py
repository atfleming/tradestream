"""
Performance Analytics Page for TradeStream Dashboard
Display detailed performance metrics, charts, and analytics
Based on existing TradeStream database structure
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

def render_performance_page(db_manager):
    """Render the detailed performance analytics page"""
    
    st.markdown("## 📈 Performance Analytics")
    st.markdown("Detailed performance metrics and analytics for both paper and live trading.")
    
    # Create tabs for different performance views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Charts", "📋 Trade History", "🎯 Statistics"])
    
    with tab1:
        render_performance_overview(db_manager)
    
    with tab2:
        render_performance_charts(db_manager)
    
    with tab3:
        render_trade_history(db_manager)
    
    with tab4:
        render_detailed_statistics(db_manager)

def render_performance_overview(db_manager):
    """Render performance overview with key metrics"""
    st.markdown("### 📊 Performance Overview")
    
    # Get performance data from database
    performance_data = get_performance_data(db_manager)
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_pnl = performance_data.get('total_pnl', 0.0)
        pnl_delta = performance_data.get('daily_pnl', 0.0)
        st.metric(
            "💰 Total P&L", 
            f"${total_pnl:.2f}", 
            delta=f"${pnl_delta:.2f}",
            help="Total profit/loss across all trades"
        )
    
    with col2:
        total_trades = performance_data.get('total_trades', 0)
        daily_trades = performance_data.get('daily_trades', 0)
        st.metric(
            "📈 Total Trades", 
            str(total_trades), 
            delta=f"+{daily_trades} today",
            help="Total number of executed trades"
        )
    
    with col3:
        win_rate = performance_data.get('win_rate', 0.0)
        st.metric(
            "🎯 Win Rate", 
            f"{win_rate:.1f}%",
            help="Percentage of winning trades"
        )
    
    with col4:
        profit_factor = performance_data.get('profit_factor', 0.0)
        st.metric(
            "⚡ Profit Factor", 
            f"{profit_factor:.2f}",
            help="Gross profit / Gross loss ratio"
        )
    
    # Additional metrics row
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        active_positions = performance_data.get('active_positions', 0)
        st.metric("📍 Active Positions", str(active_positions))
    
    with col2:
        avg_win = performance_data.get('avg_win', 0.0)
        st.metric("📈 Avg Win", f"${avg_win:.2f}")
    
    with col3:
        avg_loss = performance_data.get('avg_loss', 0.0)
        st.metric("📉 Avg Loss", f"${avg_loss:.2f}")
    
    with col4:
        max_drawdown = performance_data.get('max_drawdown', 0.0)
        st.metric("⬇️ Max Drawdown", f"{max_drawdown:.1f}%")
    
    # Trading mode breakdown
    st.markdown("### 📊 Trading Mode Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 Paper Trading")
        paper_stats = get_paper_trading_stats(db_manager)
        
        paper_col1, paper_col2 = st.columns(2)
        with paper_col1:
            st.metric("Trades", str(paper_stats.get('trades', 0)))
            st.metric("Win Rate", f"{paper_stats.get('win_rate', 0):.1f}%")
        with paper_col2:
            st.metric("P&L", f"${paper_stats.get('pnl', 0):.2f}")
            st.metric("Profit Factor", f"{paper_stats.get('profit_factor', 0):.2f}")
    
    with col2:
        st.markdown("#### 🔴 Live Trading")
        live_stats = get_live_trading_stats(db_manager)
        
        live_col1, live_col2 = st.columns(2)
        with live_col1:
            st.metric("Trades", str(live_stats.get('trades', 0)))
            st.metric("Win Rate", f"{live_stats.get('win_rate', 0):.1f}%")
        with live_col2:
            st.metric("P&L", f"${live_stats.get('pnl', 0):.2f}")
            st.metric("Profit Factor", f"{live_stats.get('profit_factor', 0):.2f}")

def render_performance_charts(db_manager):
    """Render performance charts and visualizations"""
    st.markdown("### 📈 Performance Charts")
    
    # Time period selector
    col1, col2 = st.columns([1, 3])
    
    with col1:
        time_period = st.selectbox(
            "Time Period",
            options=["1D", "1W", "1M", "3M", "6M", "1Y", "ALL"],
            index=2,
            help="Select time period for charts"
        )
    
    # Get chart data
    chart_data = get_chart_data(db_manager, time_period)
    
    # P&L Chart
    st.markdown("#### 💰 Cumulative P&L")
    
    if not chart_data.empty:
        fig_pnl = go.Figure()
        
        fig_pnl.add_trace(go.Scatter(
            x=chart_data['date'],
            y=chart_data['cumulative_pnl'],
            mode='lines',
            name='Total P&L',
            line=dict(color='#1f77b4', width=2)
        ))
        
        # Add paper trading line if available
        if 'paper_pnl' in chart_data.columns:
            fig_pnl.add_trace(go.Scatter(
                x=chart_data['date'],
                y=chart_data['paper_pnl'],
                mode='lines',
                name='Paper Trading',
                line=dict(color='#ff7f0e', width=2, dash='dash')
            ))
        
        # Add live trading line if available
        if 'live_pnl' in chart_data.columns:
            fig_pnl.add_trace(go.Scatter(
                x=chart_data['date'],
                y=chart_data['live_pnl'],
                mode='lines',
                name='Live Trading',
                line=dict(color='#d62728', width=2)
            ))
        
        fig_pnl.update_layout(
            title="Cumulative P&L Over Time",
            xaxis_title="Date",
            yaxis_title="P&L ($)",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_pnl, use_container_width=True)
    else:
        st.info("No performance data available for the selected time period.")
    
    # Daily P&L Distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Daily P&L Distribution")
        
        if not chart_data.empty and 'daily_pnl' in chart_data.columns:
            fig_hist = px.histogram(
                chart_data, 
                x='daily_pnl',
                nbins=20,
                title="Daily P&L Distribution"
            )
            fig_hist.update_layout(height=300)
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("No daily P&L data available.")
    
    with col2:
        st.markdown("#### 🎯 Win/Loss Ratio")
        
        win_loss_data = get_win_loss_data(db_manager)
        if win_loss_data:
            fig_pie = px.pie(
                values=list(win_loss_data.values()),
                names=list(win_loss_data.keys()),
                title="Win/Loss Distribution"
            )
            fig_pie.update_layout(height=300)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No win/loss data available.")

def render_trade_history(db_manager):
    """Render detailed trade history table"""
    st.markdown("### 📋 Trade History")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        trade_type_filter = st.selectbox(
            "Trade Type",
            options=["All", "Paper", "Live"],
            help="Filter by trading mode"
        )
    
    with col2:
        symbol_filter = st.selectbox(
            "Symbol",
            options=["All", "MES", "ES", "NQ", "YM"],
            help="Filter by trading symbol"
        )
    
    with col3:
        status_filter = st.selectbox(
            "Status",
            options=["All", "Open", "Closed", "Cancelled"],
            help="Filter by trade status"
        )
    
    # Get trade history data
    trade_data = get_trade_history(db_manager, trade_type_filter, symbol_filter, status_filter)
    
    if not trade_data.empty:
        # Display trade history table
        st.dataframe(
            trade_data,
            use_container_width=True,
            column_config={
                "pnl": st.column_config.NumberColumn(
                    "P&L",
                    format="$%.2f"
                ),
                "entry_price": st.column_config.NumberColumn(
                    "Entry Price",
                    format="%.2f"
                ),
                "fill_price": st.column_config.NumberColumn(
                    "Fill Price",
                    format="%.2f"
                ),
                "created_at": st.column_config.DatetimeColumn(
                    "Created",
                    format="MM/DD/YY HH:mm"
                )
            }
        )
        
        # Export button
        if st.button("📊 Export Trade History"):
            csv = trade_data.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"trade_history_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    else:
        st.info("No trades found matching the selected filters.")

def render_detailed_statistics(db_manager):
    """Render detailed trading statistics"""
    st.markdown("### 🎯 Detailed Statistics")
    
    # Get detailed stats
    detailed_stats = get_detailed_statistics(db_manager)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Trading Performance")
        
        stats_data = {
            "Total Trades": detailed_stats.get('total_trades', 0),
            "Winning Trades": detailed_stats.get('winning_trades', 0),
            "Losing Trades": detailed_stats.get('losing_trades', 0),
            "Win Rate": f"{detailed_stats.get('win_rate', 0):.1f}%",
            "Average Win": f"${detailed_stats.get('avg_win', 0):.2f}",
            "Average Loss": f"${detailed_stats.get('avg_loss', 0):.2f}",
            "Largest Win": f"${detailed_stats.get('largest_win', 0):.2f}",
            "Largest Loss": f"${detailed_stats.get('largest_loss', 0):.2f}",
            "Profit Factor": f"{detailed_stats.get('profit_factor', 0):.2f}",
            "Expectancy": f"${detailed_stats.get('expectancy', 0):.2f}"
        }
        
        for key, value in stats_data.items():
            st.metric(key, value)
    
    with col2:
        st.markdown("#### 📈 Risk Metrics")
        
        risk_data = {
            "Max Drawdown": f"{detailed_stats.get('max_drawdown', 0):.1f}%",
            "Current Drawdown": f"{detailed_stats.get('current_drawdown', 0):.1f}%",
            "Sharpe Ratio": f"{detailed_stats.get('sharpe_ratio', 0):.2f}",
            "Sortino Ratio": f"{detailed_stats.get('sortino_ratio', 0):.2f}",
            "Calmar Ratio": f"{detailed_stats.get('calmar_ratio', 0):.2f}",
            "VaR (95%)": f"${detailed_stats.get('var_95', 0):.2f}",
            "Max Consecutive Wins": detailed_stats.get('max_consecutive_wins', 0),
            "Max Consecutive Losses": detailed_stats.get('max_consecutive_losses', 0),
            "Average Trade Duration": f"{detailed_stats.get('avg_trade_duration', 0):.1f} min",
            "Recovery Factor": f"{detailed_stats.get('recovery_factor', 0):.2f}"
        }
        
        for key, value in risk_data.items():
            st.metric(key, value)

def get_performance_data(db_manager):
    """Get performance data from database"""
    if not db_manager:
        return generate_mock_performance_data()
    
    try:
        # Get system stats from existing database structure
        stats = db_manager.get_system_stats()
        
        # Calculate additional metrics (would be implemented with real database queries)
        performance_data = {
            'total_pnl': 1250.75,  # Mock data - replace with real calculation
            'daily_pnl': 125.50,
            'total_trades': stats.get('total_trades', 0),
            'daily_trades': 3,  # Mock data
            'win_rate': 67.5,
            'profit_factor': 1.45,
            'active_positions': stats.get('open_positions', 0),
            'avg_win': 85.25,
            'avg_loss': -45.75,
            'max_drawdown': 8.5
        }
        
        return performance_data
        
    except Exception as e:
        st.error(f"Error fetching performance data: {str(e)}")
        return generate_mock_performance_data()

def get_paper_trading_stats(db_manager):
    """Get paper trading specific statistics"""
    # Mock data - replace with real database queries
    return {
        'trades': 15,
        'win_rate': 70.0,
        'pnl': 850.25,
        'profit_factor': 1.55
    }

def get_live_trading_stats(db_manager):
    """Get live trading specific statistics"""
    # Mock data - replace with real database queries
    return {
        'trades': 8,
        'win_rate': 62.5,
        'pnl': 400.50,
        'profit_factor': 1.25
    }

def get_chart_data(db_manager, time_period):
    """Get chart data for specified time period"""
    # Generate mock data for demonstration
    end_date = datetime.now()
    
    if time_period == "1D":
        start_date = end_date - timedelta(days=1)
        freq = 'H'
    elif time_period == "1W":
        start_date = end_date - timedelta(weeks=1)
        freq = 'D'
    elif time_period == "1M":
        start_date = end_date - timedelta(days=30)
        freq = 'D'
    else:
        start_date = end_date - timedelta(days=90)
        freq = 'D'
    
    dates = pd.date_range(start=start_date, end=end_date, freq=freq)
    
    # Generate mock cumulative P&L data
    cumulative_pnl = np.cumsum(np.random.normal(5, 25, len(dates)))
    daily_pnl = np.random.normal(5, 25, len(dates))
    
    return pd.DataFrame({
        'date': dates,
        'cumulative_pnl': cumulative_pnl,
        'daily_pnl': daily_pnl
    })

def get_win_loss_data(db_manager):
    """Get win/loss distribution data"""
    # Mock data - replace with real database queries
    return {
        'Wins': 18,
        'Losses': 9,
        'Breakeven': 2
    }

def get_trade_history(db_manager, trade_type_filter, symbol_filter, status_filter):
    """Get filtered trade history"""
    # Mock data - replace with real database queries
    mock_trades = [
        {
            'id': 1,
            'symbol': 'MES',
            'trade_type': 'LONG',
            'quantity': 2,
            'entry_price': 4750.25,
            'fill_price': 4750.50,
            'pnl': 62.50,
            'status': 'Closed',
            'created_at': datetime.now() - timedelta(hours=2)
        },
        {
            'id': 2,
            'symbol': 'MES',
            'trade_type': 'SHORT',
            'quantity': 1,
            'entry_price': 4748.75,
            'fill_price': 4745.25,
            'pnl': 43.75,
            'status': 'Closed',
            'created_at': datetime.now() - timedelta(hours=4)
        }
    ]
    
    return pd.DataFrame(mock_trades)

def get_detailed_statistics(db_manager):
    """Get detailed trading statistics"""
    # Mock data - replace with real database calculations
    return {
        'total_trades': 29,
        'winning_trades': 18,
        'losing_trades': 9,
        'win_rate': 62.1,
        'avg_win': 85.25,
        'avg_loss': -45.75,
        'largest_win': 245.50,
        'largest_loss': -125.25,
        'profit_factor': 1.45,
        'expectancy': 28.75,
        'max_drawdown': 8.5,
        'current_drawdown': 2.1,
        'sharpe_ratio': 1.25,
        'sortino_ratio': 1.65,
        'calmar_ratio': 0.85,
        'var_95': -125.50,
        'max_consecutive_wins': 5,
        'max_consecutive_losses': 3,
        'avg_trade_duration': 45.5,
        'recovery_factor': 2.15
    }

def generate_mock_performance_data():
    """Generate mock performance data when database is not available"""
    return {
        'total_pnl': 0.0,
        'daily_pnl': 0.0,
        'total_trades': 0,
        'daily_trades': 0,
        'win_rate': 0.0,
        'profit_factor': 0.0,
        'active_positions': 0,
        'avg_win': 0.0,
        'avg_loss': 0.0,
        'max_drawdown': 0.0
    }
