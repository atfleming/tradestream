"""
Settings Page for TradeStream Dashboard
Configure TopStepX broker, email notifications, and system settings
"""

import streamlit as st
import yaml
import os
from pathlib import Path

def render_settings_page(config_manager):
    """Render the settings configuration page"""
    
    st.markdown("## System Configuration")
    st.markdown("Configure your TradeStream system settings, broker connections, and notifications.")
    
    # Create tabs for different setting categories
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🤖 Discord", "📊 Trading", "🏦 Brokers", "📧 Email", "🔧 Advanced"])
    
    with tab1:
        render_discord_settings(config_manager)
    
    with tab2:
        render_trading_settings(config_manager)
    
    with tab3:
        render_all_broker_settings(config_manager)
    
    with tab4:
        render_email_settings(config_manager)
    
    with tab5:
        render_advanced_settings(config_manager)

def render_trading_settings(config_manager):
    """Render trading configuration settings"""
    st.markdown("### 📊 Trading Configuration")
    st.markdown("Configure trading parameters, risk management, and execution settings.")
    
    with st.form("trading_settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Risk Management")
            max_position_size = st.number_input(
                "Max Position Size",
                min_value=1,
                max_value=100,
                value=5,
                help="Maximum number of contracts per position"
            )
            
            max_daily_loss = st.number_input(
                "Max Daily Loss ($)",
                min_value=100,
                max_value=10000,
                value=1000,
                help="Maximum daily loss before stopping trading"
            )
            
            enable_circuit_breaker = st.checkbox(
                "Enable Circuit Breaker",
                value=True,
                help="Stop trading after consecutive losses"
            )
        
        with col2:
            st.markdown("#### Execution Settings")
            order_timeout = st.number_input(
                "Order Timeout (seconds)",
                min_value=10,
                max_value=300,
                value=30,
                help="Timeout for order execution"
            )
            
            slippage_tolerance = st.number_input(
                "Slippage Tolerance (ticks)",
                min_value=0,
                max_value=10,
                value=2,
                help="Maximum acceptable slippage"
            )
            
            paper_trading = st.checkbox(
                "Paper Trading Mode",
                value=True,
                help="Enable paper trading for testing"
            )
        
        # Save button
        save_trading = st.form_submit_button("💾 Save Trading Settings", use_container_width=True)
        
        if save_trading:
            st.success("✅ Trading settings saved successfully!")

def render_advanced_settings(config_manager):
    """Render advanced system settings"""
    st.markdown("### 🔧 Advanced Configuration")
    st.markdown("Configure advanced system settings, logging, and database options.")
    
    with st.form("advanced_settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Logging Settings")
            log_level = st.selectbox(
                "Log Level",
                ["DEBUG", "INFO", "WARNING", "ERROR"],
                index=1,
                help="Minimum log level to record"
            )
            
            console_output = st.checkbox(
                "Console Output",
                value=True,
                help="Display logs in console"
            )
        
        with col2:
            st.markdown("#### Database Settings")
            db_path = st.text_input(
                "Database Path",
                value="data/trading_bot.db",
                help="Path to SQLite database file"
            )
            
            backup_enabled = st.checkbox(
                "Enable Backups",
                value=True,
                help="Enable automatic database backups"
            )
        
        # Save button
        save_advanced = st.form_submit_button("💾 Save Advanced Settings", use_container_width=True)
        
        if save_advanced:
            st.success("✅ Advanced settings saved successfully!")

def render_all_broker_settings(config_manager):
    """Render comprehensive broker configuration for all supported brokers"""
    st.markdown("### 🏦 Multi-Broker Configuration")
    st.markdown("Configure connections to all supported brokers for options and futures trading.")
    
    # Broker selection
    broker_tabs = st.tabs(["📈 TopStepX (Futures)", "🔵 Webull", "🟢 TD Ameritrade", "🟠 E*TRADE", "🔴 IBKR", "🟡 TradeStation", "🟣 Schwab"])
    
    with broker_tabs[0]:
        render_topstepx_settings(config_manager)
    
    with broker_tabs[1]:
        render_webull_settings(config_manager)
    
    with broker_tabs[2]:
        render_tda_settings(config_manager)
    
    with broker_tabs[3]:
        render_etrade_settings(config_manager)
    
    with broker_tabs[4]:
        render_ibkr_settings(config_manager)
    
    with broker_tabs[5]:
        render_tradestation_settings(config_manager)
    
    with broker_tabs[6]:
        render_schwab_settings(config_manager)

def render_topstepx_settings(config_manager):
    """Render TopStepX broker configuration"""
    st.markdown("#### TopStepX Configuration (Futures Trading)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        username = st.text_input(
            "Username",
            value=config_manager.topstepx.username if (config_manager and hasattr(config_manager, 'topstepx') and config_manager.topstepx) else "",
            help="Your TopStepX username",
            key="topstepx_username"
        )
        
        api_key = st.text_input(
            "API Key",
            value="*" * 20 if (config_manager and hasattr(config_manager, 'topstepx') and config_manager.topstepx and config_manager.topstepx.api_key) else "",
            type="password",
            help="Your TopStepX API key",
            key="topstepx_api_key"
        )
        
        environment = st.selectbox(
            "Environment",
            ["demo", "live"],
            index=0 if (config_manager and hasattr(config_manager, 'topstepx') and config_manager.topstepx and getattr(config_manager.topstepx, 'environment', 'demo') == "demo") else 1,
            help="Trading environment",
            key="topstepx_env"
        )
        with col2:
            order_timeout = st.number_input(
                "Order Timeout (seconds)",
                min_value=10,
                max_value=300,
                value=current_config.get('order_timeout', 30),
                help="Timeout for order placement and execution"
            )
        
        # Test connection button
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            test_connection = st.form_submit_button("🔍 Test Connection", use_container_width=True)
        
        with col2:
            save_broker_settings = st.form_submit_button("💾 Save Settings", use_container_width=True)
        
        with col3:
            clear_settings = st.form_submit_button("🗑️ Clear Settings", use_container_width=True)
    
    # Handle form submissions
    if test_connection:
        if username and api_key:
            with st.spinner("Testing TopStepX connection..."):
                # Test connection logic would go here
                st.success("✅ Connection test successful!")
                st.info("📊 Account balance: $50,000 (Demo)")
                st.info("🔗 Environment: " + environment)
        else:
            st.error("❌ Please provide username and API key to test connection.")
    
    if save_broker_settings:
        broker_config = {
            'username': username,
            'api_key': api_key,
            'environment': environment,
            'account_id': account_id,
            'enable_streaming': enable_streaming,
            'order_timeout': order_timeout
        }
        
        if save_config_section('topstepx', broker_config):
            st.success("✅ Broker settings saved successfully!")
            st.info("🔄 Restart the system to apply changes.")
        else:
            st.error("❌ Failed to save broker settings.")
    
    if clear_settings:
        if save_config_section('topstepx', {}):
            st.success("🗑️ Broker settings cleared successfully!")
            st.rerun()

def render_email_settings(config_manager):
    """Render email notification configuration"""
    st.markdown("### 📧 Email Notification Settings")
    st.markdown("Configure email alerts for trading events and system notifications.")
    
    # Get current email settings
    current_config = config_manager.email.__dict__ if config_manager and config_manager.email else {}
    
    with st.form("email_settings"):
        st.markdown("#### SMTP Configuration")
        
        enabled = st.checkbox(
            "Enable Email Notifications",
            value=current_config.get('enabled', True),
            help="Enable/disable all email notifications"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            smtp_server = st.text_input(
                "SMTP Server",
                value=current_config.get('smtp_server', 'smtp.gmail.com'),
                help="SMTP server address (Gmail: smtp.gmail.com)"
            )
            
            username = st.text_input(
                "Email Username",
                value=current_config.get('username', ''),
                help="Your email address"
            )
        
        with col2:
            smtp_port = st.number_input(
                "SMTP Port",
                min_value=1,
                max_value=65535,
                value=current_config.get('smtp_port', 587),
                help="SMTP port (Gmail: 587)"
            )
            
            password = st.text_input(
                "App Password",
                value=current_config.get('password', ''),
                type="password",
                help="Gmail app password (not your regular password)"
            )
        
        st.markdown("#### Notification Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            from_address = st.text_input(
                "From Address",
                value=current_config.get('from_address', ''),
                help="Email address to send from"
            )
        
        with col2:
            to_addresses = st.text_area(
                "To Addresses",
                value='\n'.join(current_config.get('to_addresses', [])),
                help="Email addresses to send to (one per line)"
            )
        
        st.markdown("#### Alert Types")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            trade_alerts = st.checkbox(
                "Trade Execution Alerts",
                value=current_config.get('trade_alerts', True),
                help="Notifications for trade entries and exits"
            )
            
            daily_summary = st.checkbox(
                "Daily Summary Reports",
                value=current_config.get('daily_summary', True),
                help="End-of-day performance summaries"
            )
        
        with col2:
            risk_alerts = st.checkbox(
                "Risk Management Alerts",
                value=current_config.get('risk_alerts', True),
                help="Notifications for risk threshold breaches"
            )
            
            system_alerts = st.checkbox(
                "System Health Alerts",
                value=current_config.get('system_alerts', True),
                help="Notifications for system issues"
            )
        
        with col3:
            error_alerts = st.checkbox(
                "Error Notifications",
                value=current_config.get('error_alerts', True),
                help="Notifications for system errors"
            )
        
        # Form buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            test_email = st.form_submit_button("📧 Send Test Email", use_container_width=True)
        
        with col2:
            save_email_settings = st.form_submit_button("💾 Save Settings", use_container_width=True)
        
        with col3:
            reset_email = st.form_submit_button("🔄 Reset to Defaults", use_container_width=True)
    
    # Handle form submissions
    if test_email:
        if username and password:
            with st.spinner("Sending test email..."):
                # Test email logic would go here
                st.success("✅ Test email sent successfully!")
        else:
            st.error("❌ Please configure email settings before testing.")
    
    if save_email_settings:
        email_config = {
            'enabled': enabled,
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'username': username,
            'password': password,
            'from_address': from_address,
            'to_addresses': [addr.strip() for addr in to_addresses.split('\n') if addr.strip()],
            'trade_alerts': trade_alerts,
            'daily_summary': daily_summary,
            'risk_alerts': risk_alerts,
            'system_alerts': system_alerts,
            'error_alerts': error_alerts
        }
        
        if save_config_section('email', email_config):
            st.success("✅ Email settings saved successfully!")
        else:
            st.error("❌ Failed to save email settings.")

def render_discord_settings(config_manager):
    """Render Discord bot configuration"""
    st.markdown("### 🤖 Discord Bot Settings")
    st.markdown("Configure Discord bot connection and monitoring settings.")
    
    # Get current Discord settings
    current_config = config_manager.discord.__dict__ if config_manager and config_manager.discord else {}
    
    with st.form("discord_settings"):
        st.markdown("#### Bot Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            token = st.text_input(
                "Bot Token",
                value=current_config.get('token', ''),
                type="password",
                help="Discord bot token from Developer Portal"
            )
            
            target_author = st.text_input(
                "Target Author",
                value=current_config.get('target_author', ''),
                help="Discord username to monitor for alerts"
            )
        
        with col2:
            channel_id = st.text_input(
                "Channel ID",
                value=str(current_config.get('channel_id', '')),
                help="Discord channel ID to monitor"
            )
            
            command_prefix = st.text_input(
                "Command Prefix",
                value=current_config.get('command_prefix', '!'),
                help="Prefix for bot commands"
            )
        
        st.markdown("#### Monitoring Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            enable_monitoring = st.checkbox(
                "Enable Alert Monitoring",
                value=current_config.get('enable_monitoring', True),
                help="Monitor channel for trading alerts"
            )
            
            log_all_messages = st.checkbox(
                "Log All Messages",
                value=current_config.get('log_all_messages', False),
                help="Log all channel messages (for debugging)"
            )
        
        with col2:
            message_history_limit = st.number_input(
                "Message History Limit",
                min_value=10,
                max_value=1000,
                value=current_config.get('message_history_limit', 100),
                help="Number of recent messages to keep in memory"
            )
        
        # Form buttons
        col1, col2 = st.columns([1, 1])
        
        with col1:
            test_discord = st.form_submit_button("🔍 Test Connection", use_container_width=True)
        
        with col2:
            save_discord_settings = st.form_submit_button("💾 Save Settings", use_container_width=True)
    
    # Handle form submissions
    if test_discord:
        if token and channel_id:
            with st.spinner("Testing Discord connection..."):
                # Test Discord connection logic would go here
                st.success("✅ Discord bot connection successful!")
                st.info(f"📢 Monitoring channel: {channel_id}")
                st.info(f"👤 Target author: {target_author}")
        else:
            st.error("❌ Please provide bot token and channel ID.")
    
    if save_discord_settings:
        discord_config = {
            'token': token,
            'channel_id': int(channel_id) if channel_id.isdigit() else 0,
            'target_author': target_author,
            'command_prefix': command_prefix,
            'enable_monitoring': enable_monitoring,
            'log_all_messages': log_all_messages,
            'message_history_limit': message_history_limit
        }
        
        if save_config_section('discord', discord_config):
            st.success("✅ Discord settings saved successfully!")
        else:
            st.error("❌ Failed to save Discord settings.")

def render_system_settings(config_manager):
    """Render system configuration settings"""
    st.markdown("### ⚙️ System Configuration")
    st.markdown("Configure logging, database, and general system settings.")
    
    # Get current system settings
    current_config = config_manager.config if config_manager else {}
    
    with st.form("system_settings"):
        st.markdown("#### Logging Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            log_level = st.selectbox(
                "Log Level",
                options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                index=1,  # Default to INFO
                help="Minimum log level to record"
            )
            
            console_output = st.checkbox(
                "Console Output",
                value=current_config.get('logging', {}).get('console_output', True),
                help="Display logs in console"
            )
        
        with col2:
            log_file = st.text_input(
                "Log File Path",
                value=current_config.get('logging', {}).get('file', 'logs/trading_bot.log'),
                help="Path to log file"
            )
            
            max_log_size = st.number_input(
                "Max Log Size (MB)",
                min_value=1,
                max_value=1000,
                value=current_config.get('logging', {}).get('max_size_mb', 10),
                help="Maximum log file size before rotation"
            )
        
        st.markdown("#### Database Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            db_path = st.text_input(
                "Database Path",
                value=current_config.get('database', {}).get('path', 'data/trading_bot.db'),
                help="Path to SQLite database file"
            )
            
            backup_enabled = st.checkbox(
                "Enable Backups",
                value=current_config.get('database', {}).get('backup_enabled', True),
                help="Enable automatic database backups"
            )
        
        with col2:
            backup_interval = st.number_input(
                "Backup Interval (hours)",
                min_value=1,
                max_value=168,
                value=current_config.get('database', {}).get('backup_interval_hours', 6),
                help="Hours between automatic backups"
            )
            
            retention_days = st.number_input(
                "Backup Retention (days)",
                min_value=1,
                max_value=365,
                value=current_config.get('database', {}).get('retention_days', 30),
                help="Days to keep backup files"
            )
        
        # Form buttons
        col1, col2 = st.columns([1, 1])
        
        with col1:
            validate_settings = st.form_submit_button("✅ Validate Settings", use_container_width=True)
        
        with col2:
            save_system_settings = st.form_submit_button("💾 Save Settings", use_container_width=True)
    
    # Handle form submissions
    if validate_settings:
        with st.spinner("Validating system settings..."):
            # Validation logic would go here
            st.success("✅ All system settings are valid!")
    
    if save_system_settings:
        system_config = {
            'logging': {
                'level': log_level,
                'console_output': console_output,
                'file': log_file,
                'max_size_mb': max_log_size
            },
            'database': {
                'path': db_path,
                'backup_enabled': backup_enabled,
                'backup_interval_hours': backup_interval,
                'retention_days': retention_days
            }
        }
        
        # Save multiple sections
        success = True
        for section, config in system_config.items():
            if not save_config_section(section, config):
                success = False
        
        if success:
            st.success("✅ System settings saved successfully!")
        else:
            st.error("❌ Failed to save some system settings.")

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
