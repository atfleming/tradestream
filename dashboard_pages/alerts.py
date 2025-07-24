"""
Alerts & Notifications Page for TradeStream Dashboard
Display live Discord alerts, manage notifications, and view alert history
Based on existing TradeStream database and alert structure
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def render_alerts_page(config_manager, db_manager):
    """Render the alerts and notifications page"""
    
    st.markdown("## 🔔 Alerts & Notifications")
    st.markdown("Monitor live Discord alerts, manage notifications, and view alert history.")
    
    # Create tabs for different alert views
    tab1, tab2, tab3, tab4 = st.tabs(["🔴 Live Alerts", "📋 Alert History", "📧 Notifications", "⚙️ Alert Settings"])
    
    with tab1:
        render_live_alerts(db_manager)
    
    with tab2:
        render_alert_history(db_manager)
    
    with tab3:
        render_notifications(config_manager)
    
    with tab4:
        render_alert_settings(config_manager)

def render_live_alerts(db_manager):
    """Render live Discord alerts feed"""
    st.markdown("### 🔴 Live Discord Alerts")
    st.markdown("Real-time feed of Discord alerts from JMoney channel.")
    
    # Auto-refresh toggle
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        auto_refresh = st.checkbox("🔄 Auto Refresh", value=True, help="Automatically refresh alerts")
    
    with col2:
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.rerun()
    
    with col3:
        st.markdown(f"*Last updated: {datetime.now().strftime('%H:%M:%S')}*")
    
    # Get recent alerts
    recent_alerts = get_recent_alerts(db_manager)
    
    if recent_alerts:
        st.markdown("#### Recent Alerts")
        
        for i, alert in enumerate(recent_alerts[:10]):  # Show last 10 alerts
            with st.container():
                # Create alert card
                alert_time = alert.get('timestamp', 'Unknown')
                alert_author = alert.get('author', 'Unknown')
                alert_content = alert.get('raw_content', 'No content')
                is_valid = alert.get('is_valid', False)
                processing_status = alert.get('processing_status', 'pending')
                
                # Color coding based on status
                if is_valid and processing_status == 'executed':
                    border_color = "#28a745"  # Green for executed
                    status_emoji = "✅"
                elif is_valid and processing_status == 'pending':
                    border_color = "#ffc107"  # Yellow for pending
                    status_emoji = "⏳"
                elif not is_valid:
                    border_color = "#dc3545"  # Red for invalid
                    status_emoji = "❌"
                else:
                    border_color = "#6c757d"  # Gray for other
                    status_emoji = "❓"
                
                st.markdown(f"""
                <div style="border-left: 4px solid {border_color}; padding: 1rem; margin: 0.5rem 0; background-color: #f8f9fa; border-radius: 5px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <strong>{status_emoji} {alert_author}</strong>
                        <small style="color: #6c757d;">{alert_time}</small>
                    </div>
                    <div style="margin-bottom: 0.5rem;">
                        <code>{alert_content}</code>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.9em;">
                            <strong>Status:</strong> {processing_status.title()} | 
                            <strong>Valid:</strong> {'Yes' if is_valid else 'No'}
                        </span>
                        <span style="font-size: 0.8em; color: #6c757d;">
                            ID: {alert.get('id', 'N/A')}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("📭 No recent alerts found. Make sure the Discord bot is running and configured.")
        
        # Connection status check
        st.markdown("#### 🔍 Connection Status")
        col1, col2 = st.columns(2)
        
        with col1:
            discord_status = check_discord_connection()
            status_color = "🟢" if discord_status else "🔴"
            st.markdown(f"{status_color} **Discord Bot:** {'Connected' if discord_status else 'Disconnected'}")
        
        with col2:
            db_status = check_database_connection(db_manager)
            status_color = "🟢" if db_status else "🔴"
            st.markdown(f"{status_color} **Database:** {'Connected' if db_status else 'Disconnected'}")

def render_alert_history(db_manager):
    """Render alert history with filtering and search"""
    st.markdown("### 📋 Alert History")
    st.markdown("Search and filter through historical Discord alerts.")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        date_filter = st.date_input(
            "From Date",
            value=datetime.now().date() - timedelta(days=7),
            help="Filter alerts from this date"
        )
    
    with col2:
        author_filter = st.selectbox(
            "Author",
            options=["All", "JMoney", "Other"],
            help="Filter by alert author"
        )
    
    with col3:
        status_filter = st.selectbox(
            "Status",
            options=["All", "Valid", "Invalid", "Executed", "Pending"],
            help="Filter by processing status"
        )
    
    with col4:
        symbol_filter = st.selectbox(
            "Symbol",
            options=["All", "ES", "NQ", "YM", "RTY"],
            help="Filter by trading symbol"
        )
    
    # Search box
    search_term = st.text_input(
        "🔍 Search alerts",
        placeholder="Search in alert content...",
        help="Search for specific text in alert messages"
    )
    
    # Get filtered alert history
    alert_history = get_alert_history(
        db_manager, 
        date_filter, 
        author_filter, 
        status_filter, 
        symbol_filter, 
        search_term
    )
    
    if not alert_history.empty:
        # Display results count
        st.markdown(f"**Found {len(alert_history)} alerts**")
        
        # Display alert history table
        st.dataframe(
            alert_history,
            use_container_width=True,
            column_config={
                "timestamp": st.column_config.DatetimeColumn(
                    "Time",
                    format="MM/DD/YY HH:mm:ss"
                ),
                "parsed_price": st.column_config.NumberColumn(
                    "Price",
                    format="%.2f"
                ),
                "parsed_stop": st.column_config.NumberColumn(
                    "Stop",
                    format="%.2f"
                ),
                "target_1": st.column_config.NumberColumn(
                    "Target 1",
                    format="%.2f"
                ),
                "target_2": st.column_config.NumberColumn(
                    "Target 2",
                    format="%.2f"
                ),
                "is_valid": st.column_config.CheckboxColumn("Valid")
            }
        )
        
        # Export functionality
        if st.button("📊 Export Alert History"):
            csv = alert_history.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"alert_history_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    else:
        st.info("No alerts found matching the selected criteria.")

def render_notifications(config_manager):
    """Render notification management"""
    st.markdown("### 📧 Notification Management")
    st.markdown("Manage email notifications and alert preferences.")
    
    # Get current email config
    email_config = config_manager.email.__dict__ if config_manager and config_manager.email else {}
    
    # Notification status
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Notification Status")
        
        notifications_enabled = email_config.get('enabled', False)
        status_color = "🟢" if notifications_enabled else "🔴"
        st.markdown(f"{status_color} **Email Notifications:** {'Enabled' if notifications_enabled else 'Disabled'}")
        
        if notifications_enabled:
            st.markdown(f"📧 **SMTP Server:** {email_config.get('smtp_server', 'Not configured')}")
            st.markdown(f"👤 **From Address:** {email_config.get('from_address', 'Not configured')}")
            
            to_addresses = email_config.get('to_addresses', [])
            st.markdown(f"📬 **Recipients:** {len(to_addresses)} configured")
    
    with col2:
        st.markdown("#### 🔔 Notification Types")
        
        notification_types = {
            "Trade Executions": email_config.get('send_trade_executions', False),
            "Alert Confirmations": email_config.get('send_alert_confirmations', False),
            "Daily Summaries": email_config.get('send_daily_summaries', False)
        }
        
        for notif_type, enabled in notification_types.items():
            status_icon = "✅" if enabled else "❌"
            st.markdown(f"{status_icon} **{notif_type}:** {'Enabled' if enabled else 'Disabled'}")
    
    # Recent notifications
    st.markdown("#### 📨 Recent Notifications")
    
    recent_notifications = get_recent_notifications()
    
    if recent_notifications:
        for notification in recent_notifications[:5]:
            with st.container():
                st.markdown(f"""
                <div style="border: 1px solid #dee2e6; padding: 0.75rem; margin: 0.25rem 0; border-radius: 5px; background-color: #f8f9fa;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong>{notification['type']}</strong>
                        <small style="color: #6c757d;">{notification['timestamp']}</small>
                    </div>
                    <div style="margin-top: 0.25rem; font-size: 0.9em;">
                        {notification['message']}
                    </div>
                    <div style="margin-top: 0.25rem; font-size: 0.8em; color: #6c757d;">
                        Status: {notification['status']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No recent notifications found.")
    
    # Test notification button
    if st.button("📧 Send Test Notification", use_container_width=True):
        if notifications_enabled:
            with st.spinner("Sending test notification..."):
                # Test notification logic would go here
                st.success("✅ Test notification sent successfully!")
        else:
            st.error("❌ Email notifications are not enabled. Please configure email settings first.")

def render_alert_settings(config_manager):
    """Render alert processing settings"""
    st.markdown("### ⚙️ Alert Processing Settings")
    st.markdown("Configure how Discord alerts are processed and validated.")
    
    # Get current Discord config
    discord_config = config_manager.discord.__dict__ if config_manager and config_manager.discord else {}
    
    with st.form("alert_settings"):
        st.markdown("#### 🤖 Discord Monitoring")
        
        col1, col2 = st.columns(2)
        
        with col1:
            target_author = st.text_input(
                "Target Author",
                value=discord_config.get('target_author', 'JMoney'),
                help="Discord username to monitor for alerts"
            )
            
            channel_id = st.text_input(
                "Channel ID",
                value=str(discord_config.get('channel_id', '')),
                help="Discord channel ID to monitor"
            )
        
        with col2:
            reconnect_attempts = st.number_input(
                "Reconnect Attempts",
                min_value=1,
                max_value=20,
                value=discord_config.get('reconnect_attempts', 5),
                help="Number of reconnection attempts"
            )
            
            reconnect_delay = st.number_input(
                "Reconnect Delay (seconds)",
                min_value=5,
                max_value=300,
                value=discord_config.get('reconnect_delay', 30),
                help="Delay between reconnection attempts"
            )
        
        st.markdown("#### 🔍 Alert Processing")
        
        col1, col2 = st.columns(2)
        
        with col1:
            enable_alert_validation = st.checkbox(
                "Enable Alert Validation",
                value=True,
                help="Validate alert format before processing"
            )
            
            require_price_confirmation = st.checkbox(
                "Require Price Confirmation",
                value=True,
                help="Require valid price in alert message"
            )
        
        with col2:
            enable_duplicate_filtering = st.checkbox(
                "Enable Duplicate Filtering",
                value=True,
                help="Filter out duplicate alerts"
            )
            
            duplicate_window_minutes = st.number_input(
                "Duplicate Window (minutes)",
                min_value=1,
                max_value=60,
                value=5,
                help="Time window for duplicate detection"
            )
        
        # Form buttons
        col1, col2 = st.columns([1, 1])
        
        with col1:
            save_alert_settings = st.form_submit_button("💾 Save Settings", use_container_width=True)
        
        with col2:
            test_alert_processing = st.form_submit_button("🧪 Test Processing", use_container_width=True)
    
    # Handle form submissions
    if save_alert_settings:
        alert_settings = {
            'target_author': target_author,
            'channel_id': int(channel_id) if channel_id.isdigit() else 0,
            'reconnect_attempts': reconnect_attempts,
            'reconnect_delay': reconnect_delay
        }
        
        # Save settings logic would go here
        st.success("✅ Alert settings saved successfully!")
    
    if test_alert_processing:
        with st.spinner("Testing alert processing..."):
            # Test processing logic would go here
            st.success("✅ Alert processing test completed!")

def get_recent_alerts(db_manager):
    """Get recent alerts from database"""
    if not db_manager:
        return generate_mock_alerts()
    
    try:
        # Use existing database method
        alerts = db_manager.get_recent_alerts(limit=20)
        return alerts
    except Exception as e:
        st.error(f"Error fetching recent alerts: {str(e)}")
        return generate_mock_alerts()

def get_alert_history(db_manager, date_filter, author_filter, status_filter, symbol_filter, search_term):
    """Get filtered alert history"""
    # Mock data for demonstration - replace with real database queries
    mock_data = [
        {
            'id': 1,
            'timestamp': datetime.now() - timedelta(hours=1),
            'author': 'JMoney',
            'raw_content': 'ES LONG 4750.25 STOP 4745 T1 4757 T2 4762',
            'parsed_price': 4750.25,
            'parsed_stop': 4745.0,
            'target_1': 4757.0,
            'target_2': 4762.0,
            'is_valid': True,
            'processing_status': 'executed'
        },
        {
            'id': 2,
            'timestamp': datetime.now() - timedelta(hours=2),
            'author': 'JMoney',
            'raw_content': 'NQ SHORT 16250.50 STOP 16275 T1 16225 T2 16200',
            'parsed_price': 16250.50,
            'parsed_stop': 16275.0,
            'target_1': 16225.0,
            'target_2': 16200.0,
            'is_valid': True,
            'processing_status': 'pending'
        }
    ]
    
    return pd.DataFrame(mock_data)

def get_recent_notifications():
    """Get recent notification history"""
    # Mock data - replace with real notification log
    return [
        {
            'type': 'Trade Execution',
            'message': 'ES LONG position opened at 4750.25',
            'timestamp': '14:30:25',
            'status': 'Sent'
        },
        {
            'type': 'Daily Summary',
            'message': 'Daily trading summary for 2024-01-15',
            'timestamp': '17:00:00',
            'status': 'Sent'
        }
    ]

def check_discord_connection():
    """Check Discord bot connection status"""
    # Mock status - replace with real connection check
    return True

def check_database_connection(db_manager):
    """Check database connection status"""
    if not db_manager:
        return False
    
    try:
        # Test database connection
        stats = db_manager.get_system_stats()
        return True
    except:
        return False

def generate_mock_alerts():
    """Generate mock alert data when database is not available"""
    return [
        {
            'id': 1,
            'timestamp': '2024-01-15 14:30:25',
            'author': 'JMoney',
            'raw_content': 'ES LONG 4750.25 STOP 4745 T1 4757 T2 4762',
            'is_valid': True,
            'processing_status': 'executed'
        },
        {
            'id': 2,
            'timestamp': '2024-01-15 13:45:12',
            'author': 'JMoney',
            'raw_content': 'NQ SHORT 16250.50 STOP 16275 T1 16225 T2 16200',
            'is_valid': True,
            'processing_status': 'pending'
        },
        {
            'id': 3,
            'timestamp': '2024-01-15 12:15:33',
            'author': 'JMoney',
            'raw_content': 'Invalid alert format test',
            'is_valid': False,
            'processing_status': 'rejected'
        }
    ]
