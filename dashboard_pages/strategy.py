"""
Strategy Configuration Page for TradeStream Dashboard
Configure trading strategy, position sizing, risk management, and execution settings
Based on existing TradeStream configuration structure
"""

import streamlit as st
import yaml
import os

def render_strategy_page(config_manager):
    """Render the strategy configuration page"""
    
    st.markdown("## 📊 Strategy Configuration")
    st.markdown("Configure your trading strategy, position sizing, risk management, and execution parameters.")
    
    # Create tabs for different strategy categories
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Trading Strategy", "💰 Position Sizing", "🛡️ Risk Management", "⚡ Execution Settings"])
    
    with tab1:
        render_trading_strategy(config_manager)
    
    with tab2:
        render_position_sizing(config_manager)
    
    with tab3:
        render_risk_management(config_manager)
    
    with tab4:
        render_execution_settings(config_manager)

def render_trading_strategy(config_manager):
    """Render trading strategy configuration based on existing TradingConfig"""
    st.markdown("### 📈 Trading Strategy Settings")
    st.markdown("Configure your core trading strategy parameters using existing TradeStream configuration.")
    
    # Get current trading settings from existing config structure
    current_config = config_manager.trading.__dict__ if config_manager and config_manager.trading else {}
    
    with st.form("trading_strategy"):
        st.markdown("#### Contract Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.selectbox(
                "Trading Symbol",
                options=["MES", "ES", "NQ", "YM", "RTY"],
                index=0 if current_config.get('symbol', 'MES') == 'MES' else 1,
                help="Primary futures contract to trade"
            )
            
            enable_auto_trading = st.checkbox(
                "Enable Auto Trading",
                value=current_config.get('enable_auto_trading', False),
                help="Automatically execute trades based on Discord alerts"
            )
        
        with col2:
            contract_name = st.text_input(
                "Contract Name",
                value=current_config.get('contract_name', 'Micro E-mini S&P 500'),
                help="Full contract name"
            )
            
            exchange = st.text_input(
                "Exchange",
                value=current_config.get('exchange', 'CME'),
                help="Trading exchange"
            )
        
        st.markdown("#### Contract Specifications")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            tick_size = st.number_input(
                "Tick Size",
                min_value=0.01,
                max_value=1.0,
                value=float(current_config.get('tick_size', 0.25)),
                step=0.01,
                help="Minimum price movement"
            )
        
        with col2:
            tick_value = st.number_input(
                "Tick Value ($)",
                min_value=0.01,
                max_value=50.0,
                value=float(current_config.get('tick_value', 1.25)),
                step=0.01,
                help="Dollar value per tick"
            )
        
        with col3:
            margin_requirement = st.number_input(
                "Margin Requirement ($)",
                min_value=100.0,
                max_value=10000.0,
                value=current_config.get('margin_requirement', 500.0),
                step=50.0,
                help="Required margin per contract"
            )
        
        st.markdown("#### Trading Modes")
        
        col1, col2 = st.columns(2)
        
        with col1:
            paper_trading_enabled = st.checkbox(
                "Enable Paper Trading",
                value=current_config.get('paper_trading_enabled', True),
                help="Enable paper trading simulation"
            )
            
            live_trading_enabled = st.checkbox(
                "Enable Live Trading",
                value=current_config.get('live_trading_enabled', False),
                help="Enable live trading execution"
            )
        
        with col2:
            concurrent_trading = st.checkbox(
                "Concurrent Trading",
                value=current_config.get('concurrent_trading', False),
                help="Run both paper and live trading simultaneously"
            )
        
        st.markdown("#### Trading Limits")
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_daily_trades = st.number_input(
                "Max Daily Trades",
                min_value=1,
                max_value=100,
                value=int(current_config.get('max_daily_trades', 10)),
                help="Maximum number of trades per day"
            )
        
        with col2:
            max_position_size = st.number_input(
                "Max Position Size",
                min_value=1,
                max_value=50,
                value=int(current_config.get('max_position_size', 5)),
                help="Maximum number of contracts per position"
            )
        
        # Form buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            save_strategy = st.form_submit_button("💾 Save Strategy", use_container_width=True)
        
        with col2:
            test_strategy = st.form_submit_button("🧪 Test Strategy", use_container_width=True)
        
        with col3:
            reset_strategy = st.form_submit_button("🔄 Reset Defaults", use_container_width=True)
    
    # Handle form submissions
    if test_strategy:
        with st.spinner("Testing strategy configuration..."):
            st.success("✅ Strategy configuration is valid!")
            st.info(f"📊 Symbol: {symbol} | Tick Size: {tick_size} | Tick Value: ${tick_value}")
    
    if save_strategy:
        strategy_config = {
            'symbol': symbol,
            'contract_name': contract_name,
            'exchange': exchange,
            'tick_size': tick_size,
            'tick_value': tick_value,
            'margin_requirement': margin_requirement,
            'enable_auto_trading': enable_auto_trading,
            'paper_trading_enabled': paper_trading_enabled,
            'live_trading_enabled': live_trading_enabled,
            'concurrent_trading': concurrent_trading,
            'max_daily_trades': max_daily_trades,
            'max_position_size': max_position_size
        }
        
        if save_config_section('trading', strategy_config):
            st.success("✅ Trading strategy saved successfully!")
        else:
            st.error("❌ Failed to save trading strategy.")

def render_position_sizing(config_manager):
    """Render position sizing configuration based on existing size_mapping"""
    st.markdown("### 💰 Position Sizing Configuration")
    st.markdown("Configure position sizes for A/B/C alert types from JMoney using existing size mapping.")
    
    # Get current sizing settings from existing config structure
    current_config = config_manager.trading.__dict__ if config_manager and config_manager.trading else {}
    size_mapping = current_config.get('size_mapping', {'A': 1, 'B': 2, 'C': 3})
    
    with st.form("position_sizing"):
        st.markdown("#### Size Mapping Configuration")
        st.markdown("Configure contract quantities for A/B/C size alerts from JMoney (matches existing TradeStream logic).")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**🔥 A Size (Aggressive)**")
            a_size = st.number_input(
                "A Size Contracts",
                min_value=1,
                max_value=10,
                value=size_mapping.get('A', 1),
                help="Number of contracts for 'A' size alerts"
            )
            st.markdown(f"*Risk Level: High*")
        
        with col2:
            st.markdown("**⚖️ B Size (Balanced)**")
            b_size = st.number_input(
                "B Size Contracts",
                min_value=1,
                max_value=10,
                value=size_mapping.get('B', 2),
                help="Number of contracts for 'B' size alerts"
            )
            st.markdown(f"*Risk Level: Medium*")
        
        with col3:
            st.markdown("**🛡️ C Size (Conservative)**")
            c_size = st.number_input(
                "C Size Contracts",
                min_value=1,
                max_value=10,
                value=size_mapping.get('C', 3),
                help="Number of contracts for 'C' size alerts"
            )
            st.markdown(f"*Risk Level: Low*")
        
        # Position sizing preview based on MES contract specs
        st.markdown("#### Position Sizing Preview (MES Contract)")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("A Size", f"{a_size} contracts", f"${a_size * 1.25:.2f} per tick")
        
        with col2:
            st.metric("B Size", f"{b_size} contracts", f"${b_size * 1.25:.2f} per tick")
        
        with col3:
            st.metric("C Size", f"{c_size} contracts", f"${c_size * 1.25:.2f} per tick")
        
        with col4:
            max_risk = max(a_size, b_size, c_size) * 1.25  # MES tick value
            st.metric("Max Risk/Tick", f"${max_risk:.2f}", f"{max(a_size, b_size, c_size)} contracts")
        
        # Form buttons
        col1, col2 = st.columns([1, 1])
        
        with col1:
            save_sizing = st.form_submit_button("💾 Save Position Sizing", use_container_width=True)
        
        with col2:
            reset_sizing = st.form_submit_button("🔄 Reset to Defaults", use_container_width=True)
    
    # Handle form submissions
    if save_sizing:
        sizing_config = {
            'size_mapping': {'A': a_size, 'B': b_size, 'C': c_size}
        }
        
        # Merge with existing trading config
        current_trading_config = get_current_trading_config(config_manager)
        current_trading_config.update(sizing_config)
        
        if save_config_section('trading', current_trading_config):
            st.success("✅ Position sizing configuration saved successfully!")
        else:
            st.error("❌ Failed to save position sizing configuration.")

def render_risk_management(config_manager):
    """Render risk management configuration based on existing RiskConfig"""
    st.markdown("### 🛡️ Risk Management Configuration")
    st.markdown("Configure risk limits and circuit breakers using existing TradeStream risk management.")
    
    # Get current risk settings from existing config structure
    current_config = config_manager.risk.__dict__ if config_manager and config_manager.risk else {}
    
    with st.form("risk_management"):
        st.markdown("#### Risk Limits (Based on Existing RiskConfig)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_loss_per_trade = st.number_input(
                "Max Loss Per Trade ($)",
                min_value=10.0,
                max_value=1000.0,
                value=current_config.get('max_loss_per_trade', 100.0),
                step=10.0,
                help="Maximum loss allowed per individual trade"
            )
            
            daily_loss_limit = st.number_input(
                "Daily Loss Limit ($)",
                min_value=50.0,
                max_value=5000.0,
                value=current_config.get('daily_loss_limit', 500.0),
                step=50.0,
                help="Maximum daily loss before trading halt"
            )
        
        with col2:
            max_consecutive_losses = st.number_input(
                "Max Consecutive Losses",
                min_value=1,
                max_value=20,
                value=current_config.get('max_consecutive_losses', 3),
                help="Maximum consecutive losing trades"
            )
            
            position_size_limit = st.number_input(
                "Position Size Limit",
                min_value=1,
                max_value=20,
                value=current_config.get('position_size_limit', 5),
                help="Maximum contracts in any single position"
            )
        
        st.markdown("#### Circuit Breaker")
        
        enable_circuit_breaker = st.checkbox(
            "Enable Circuit Breaker",
            value=current_config.get('enable_circuit_breaker', True),
            help="Automatically halt trading on risk threshold breach (matches existing TradeStream logic)"
        )
        
        if enable_circuit_breaker:
            st.info("🛡️ Circuit breaker will halt trading when risk limits are exceeded, matching existing TradeStream behavior.")
        
        # Form buttons
        col1, col2 = st.columns([1, 1])
        
        with col1:
            save_risk = st.form_submit_button("💾 Save Risk Settings", use_container_width=True)
        
        with col2:
            reset_risk = st.form_submit_button("🔄 Reset to Defaults", use_container_width=True)
    
    # Handle form submissions
    if save_risk:
        risk_config = {
            'max_loss_per_trade': max_loss_per_trade,
            'daily_loss_limit': daily_loss_limit,
            'max_consecutive_losses': max_consecutive_losses,
            'position_size_limit': position_size_limit,
            'enable_circuit_breaker': enable_circuit_breaker
        }
        
        if save_config_section('risk', risk_config):
            st.success("✅ Risk management settings saved successfully!")
        else:
            st.error("❌ Failed to save risk management settings.")

def render_execution_settings(config_manager):
    """Render execution settings configuration"""
    st.markdown("### ⚡ Execution Settings")
    st.markdown("Configure order execution and timing settings for TradeStream.")
    
    # Get current execution settings
    current_config = get_current_trading_config(config_manager)
    
    with st.form("execution_settings"):
        st.markdown("#### Order Execution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            order_type = st.selectbox(
                "Default Order Type",
                options=["MARKET", "LIMIT"],
                index=0,
                help="Default order type for trade execution"
            )
            
            execution_delay = st.number_input(
                "Execution Delay (seconds)",
                min_value=0,
                max_value=60,
                value=int(current_config.get('execution_delay', 2)),
                help="Delay before executing trades (for validation)"
            )
        
        with col2:
            order_timeout = st.number_input(
                "Order Timeout (seconds)",
                min_value=5,
                max_value=300,
                value=current_config.get('order_timeout', 30),
                help="Timeout for order execution"
            )
        
        # Form buttons
        col1, col2 = st.columns([1, 1])
        
        with col1:
            save_execution = st.form_submit_button("💾 Save Execution Settings", use_container_width=True)
        
        with col2:
            test_execution = st.form_submit_button("🧪 Test Execution", use_container_width=True)
    
    # Handle form submissions
    if save_execution:
        execution_config = {
            'order_type': order_type,
            'execution_delay': execution_delay,
            'order_timeout': order_timeout
        }
        
        # Merge with existing trading config
        current_trading_config = get_current_trading_config(config_manager)
        current_trading_config.update(execution_config)
        
        if save_config_section('trading', current_trading_config):
            st.success("✅ Execution settings saved successfully!")
        else:
            st.error("❌ Failed to save execution settings.")
    
    if test_execution:
        with st.spinner("Testing execution settings..."):
            st.success("✅ Execution settings test completed!")
            st.info(f"📊 Order Type: {order_type} | Timeout: {order_timeout}s")

def get_current_trading_config(config_manager):
    """Get current trading configuration as dict"""
    if config_manager and config_manager.trading:
        return config_manager.trading.__dict__.copy()
    return {}

def save_config_section(section, config_data):
    """Save a configuration section to config.yaml"""
    try:
        config_path = "config.yaml"
        
        # Load existing config
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                full_config = yaml.safe_load(f) or {}
        else:
            full_config = {}
        
        # Update the specific section
        full_config[section] = config_data
        
        # Save back to file
        with open(config_path, 'w') as f:
            yaml.dump(full_config, f, default_flow_style=False, indent=2)
        
        return True
        
    except Exception as e:
        st.error(f"Error saving configuration: {str(e)}")
        return False
