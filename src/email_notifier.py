"""
Email Notification System for JMoney Discord Alert Trading System
Sends email alerts for trading activities, confirmations, and daily summaries
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

try:
    from .message_parser import ParsedAlert
    from .database import DatabaseManager
    from .config import ConfigManager
except ImportError:
    # Fallback for direct execution
    from message_parser import ParsedAlert
    from database import DatabaseManager
    from config import ConfigManager


@dataclass
class EmailConfig:
    """Email configuration settings"""
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    from_address: str
    to_addresses: List[str]
    enabled: bool = True


class EmailNotifier:
    """Email notification system for trading alerts and summaries"""
    
    def __init__(self, config: ConfigManager, db: DatabaseManager):
        """
        Initialize email notifier
        
        Args:
            config: Configuration manager instance
            db: Database manager instance
        """
        self.config = config
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.email_config: Optional[EmailConfig] = None
        
        # Load email configuration
        self._load_email_config()
    
    def _load_email_config(self):
        """Load email configuration from config manager"""
        try:
            # This will be populated from config.yaml
            email_data = getattr(self.config, 'email', None)
            if email_data:
                self.email_config = EmailConfig(
                    smtp_server=email_data.smtp_server,
                    smtp_port=email_data.smtp_port,
                    username=email_data.username,
                    password=email_data.password,
                    from_address=email_data.from_address,
                    to_addresses=email_data.to_addresses,
                    enabled=email_data.enabled
                )
        except Exception as e:
            self.logger.error(f"Error loading email configuration: {e}")
            self.email_config = None
    
    def _send_email(self, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        """
        Send email with HTML content
        
        Args:
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text fallback (optional)
            
        Returns:
            True if email sent successfully
        """
        if not self.email_config or not self.email_config.enabled:
            self.logger.info("Email notifications disabled")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_config.from_address
            msg['To'] = ', '.join(self.email_config.to_addresses)
            
            # Add text and HTML parts
            if text_body:
                text_part = MIMEText(text_body, 'plain')
                msg.attach(text_part)
            
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.email_config.smtp_server, self.email_config.smtp_port) as server:
                server.starttls()
                server.login(self.email_config.username, self.email_config.password)
                server.send_message(msg)
            
            self.logger.info(f"Email sent successfully: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False
    
    def send_alert_confirmation(self, alert: ParsedAlert, message_data: Dict[str, Any], 
                              account_balance: Optional[float] = None) -> bool:
        """
        Send email confirmation when JMoney alert is received
        
        Args:
            alert: Parsed alert information
            message_data: Discord message metadata
            account_balance: Current account balance
            
        Returns:
            True if email sent successfully
        """
        if not alert.is_valid:
            return False
        
        try:
            # Calculate risk/reward metrics
            from message_parser import JMoneyMessageParser
            parser = JMoneyMessageParser()
            rr_metrics = parser.calculate_risk_reward(
                alert.price, alert.stop, alert.target_1, alert.target_2
            )
            
            # Create subject
            subject = f"🚨 JMoney Alert Received - ES LONG {alert.price} ({alert.size})"
            
            # Format account balance for display
            balance_display = f"${account_balance:.2f}" if account_balance is not None else "N/A"
            
            # Create HTML body
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .header {{ background-color: #2E8B57; color: white; padding: 15px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .alert-box {{ background-color: #f0f8f0; border: 2px solid #2E8B57; padding: 15px; margin: 10px 0; }}
                    .metrics {{ background-color: #f9f9f9; padding: 10px; margin: 10px 0; }}
                    .footer {{ background-color: #f5f5f5; padding: 10px; text-align: center; font-size: 12px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>JMoney Trading Alert Confirmed</h2>
                    <p>Alert received and parsed successfully</p>
                </div>
                
                <div class="content">
                    <div class="alert-box">
                        <h3>🎯 Trade Setup</h3>
                        <table>
                            <tr><th>Symbol</th><td>ES (Micro Futures)</td></tr>
                            <tr><th>Direction</th><td>LONG</td></tr>
                            <tr><th>Entry Price</th><td>{alert.price}</td></tr>
                            <tr><th>Position Size</th><td>{alert.size}</td></tr>
                            <tr><th>Stop Loss</th><td>{alert.stop}</td></tr>
                            <tr><th>Target 1</th><td>{alert.target_1}</td></tr>
                            <tr><th>Target 2</th><td>{alert.target_2}</td></tr>
                        </table>
                    </div>
                    
                    <div class="metrics">
                        <h3>📊 Risk/Reward Analysis</h3>
                        <table>
                            <tr><th>Risk (Points)</th><td>{rr_metrics.get('risk_points', 0):.1f}</td></tr>
                            <tr><th>Reward T1 (Points)</th><td>{rr_metrics.get('reward_1_points', 0):.1f}</td></tr>
                            <tr><th>Reward T2 (Points)</th><td>{rr_metrics.get('reward_2_points', 0):.1f}</td></tr>
                            <tr><th>Risk/Reward T1</th><td>{rr_metrics.get('risk_reward_1', 0):.2f}:1</td></tr>
                            <tr><th>Risk/Reward T2</th><td>{rr_metrics.get('risk_reward_2', 0):.2f}:1</td></tr>
                        </table>
                    </div>
                    
                    <div class="metrics">
                        <h3>💰 Account Information</h3>
                        <table>
                            <tr><th>Current Balance</th><td>{balance_display}</td></tr>
                            <tr><th>Alert Time</th><td>{message_data.get('timestamp', 'N/A')}</td></tr>
                            <tr><th>Message ID</th><td>{message_data.get('message_id', 'N/A')}</td></tr>
                        </table>
                    </div>
                </div>
                
                <div class="footer">
                    <p>JMoney Alert Trading System | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EST</p>
                </div>
            </body>
            </html>
            """
            
            return self._send_email(subject, html_body)
            
        except Exception as e:
            self.logger.error(f"Error sending alert confirmation email: {e}")
            return False
    
    def send_trade_execution(self, trade_type: str, symbol: str, quantity: int, 
                           price: Optional[float], order_id: Optional[str],
                           account_balance: Optional[float] = None,
                           pnl: Optional[float] = None) -> bool:
        """
        Send email when trade is executed
        
        Args:
            trade_type: 'BUY' or 'SELL'
            symbol: Trading symbol
            quantity: Number of contracts
            price: Execution price
            order_id: Order ID from broker
            account_balance: Updated account balance
            pnl: Profit/Loss for the trade
            
        Returns:
            True if email sent successfully
        """
        try:
            # Create subject
            action = "🟢 ENTRY" if trade_type == "BUY" else "🔴 EXIT"
            subject = f"{action} - {symbol} {quantity} contracts @ {price}"
            
            # Format values for display
            balance_display = f"${account_balance:.2f}" if account_balance is not None else "N/A"
            pnl_display = f"${pnl:.2f}" if pnl is not None else "N/A"
            pnl_class = "profit" if pnl and pnl > 0 else "loss"
            
            # Create HTML body
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .header {{ background-color: {'#2E8B57' if trade_type == 'BUY' else '#DC143C'}; color: white; padding: 15px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .trade-box {{ background-color: {'#f0f8f0' if trade_type == 'BUY' else '#fff0f0'}; border: 2px solid {'#2E8B57' if trade_type == 'BUY' else '#DC143C'}; padding: 15px; margin: 10px 0; }}
                    .metrics {{ background-color: #f9f9f9; padding: 10px; margin: 10px 0; }}
                    .footer {{ background-color: #f5f5f5; padding: 10px; text-align: center; font-size: 12px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .profit {{ color: #2E8B57; font-weight: bold; }}
                    .loss {{ color: #DC143C; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>Trade Execution Confirmed</h2>
                    <p>{action} - {trade_type} Order Filled</p>
                </div>
                
                <div class="content">
                    <div class="trade-box">
                        <h3>📋 Execution Details</h3>
                        <table>
                            <tr><th>Action</th><td>{trade_type}</td></tr>
                            <tr><th>Symbol</th><td>{symbol}</td></tr>
                            <tr><th>Quantity</th><td>{quantity} contracts</td></tr>
                            <tr><th>Fill Price</th><td>{price if price else 'Pending'}</td></tr>
                            <tr><th>Order ID</th><td>{order_id if order_id else 'N/A'}</td></tr>
                            <tr><th>Execution Time</th><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EST</td></tr>
                        </table>
                    </div>
                    
                    <div class="metrics">
                        <h3>💰 Account Update</h3>
                        <table>
                            <tr><th>Current Balance</th><td>{balance_display}</td></tr>
                            <tr><th>Trade P&L</th><td class="{pnl_class}">{pnl_display}</td></tr>
                        </table>
                    </div>
                </div>
                
                <div class="footer">
                    <p>JMoney Alert Trading System | Automated Trade Execution</p>
                </div>
            </body>
            </html>
            """
            
            return self._send_email(subject, html_body)
            
        except Exception as e:
            self.logger.error(f"Error sending trade execution email: {e}")
            return False
    
    def send_daily_summary(self, summary_date: date, account_balance: Optional[float] = None) -> bool:
        """
        Send daily trading summary email
        
        Args:
            summary_date: Date for the summary
            account_balance: Current account balance
            
        Returns:
            True if email sent successfully
        """
        try:
            # Get daily performance data from database
            performance_data = self._get_daily_performance(summary_date)
            trades_data = self._get_daily_trades(summary_date)
            
            # Create subject
            subject = f"📊 Daily Trading Summary - {summary_date.strftime('%Y-%m-%d')}"
            
            # Format account balance for display
            balance_display = f"${account_balance:.2f}" if account_balance is not None else "N/A"
            
            # Create HTML body
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .header {{ background-color: #4169E1; color: white; padding: 15px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .summary-box {{ background-color: #f0f4ff; border: 2px solid #4169E1; padding: 15px; margin: 10px 0; }}
                    .metrics {{ background-color: #f9f9f9; padding: 10px; margin: 10px 0; }}
                    .footer {{ background-color: #f5f5f5; padding: 10px; text-align: center; font-size: 12px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .profit {{ color: #2E8B57; font-weight: bold; }}
                    .loss {{ color: #DC143C; font-weight: bold; }}
                    .neutral {{ color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>Daily Trading Summary</h2>
                    <p>{summary_date.strftime('%A, %B %d, %Y')}</p>
                </div>
                
                <div class="content">
                    <div class="summary-box">
                        <h3>📈 Performance Overview</h3>
                        <table>
                            <tr><th>Total Trades</th><td>{performance_data.get('total_trades', 0)}</td></tr>
                            <tr><th>Winning Trades</th><td class="profit">{performance_data.get('winning_trades', 0)}</td></tr>
                            <tr><th>Losing Trades</th><td class="loss">{performance_data.get('losing_trades', 0)}</td></tr>
                            <tr><th>Win Rate</th><td>{performance_data.get('win_rate', 0):.1f}%</td></tr>
                            <tr><th>Net P&L</th><td class="{'profit' if performance_data.get('net_pnl', 0) >= 0 else 'loss'}">${performance_data.get('net_pnl', 0):.2f}</td></tr>
                        </table>
                    </div>
                    
                    <div class="metrics">
                        <h3>💰 Account Status</h3>
                        <table>
                            <tr><th>Current Balance</th><td>{balance_display}</td></tr>
                            <tr><th>Gross Profit</th><td class="profit">${performance_data.get('gross_profit', 0):.2f}</td></tr>
                            <tr><th>Gross Loss</th><td class="loss">${performance_data.get('gross_loss', 0):.2f}</td></tr>
                            <tr><th>Commission Paid</th><td>${performance_data.get('commission_paid', 0):.2f}</td></tr>
                        </table>
                    </div>
                    
                    <div class="metrics">
                        <h3>📋 Trade Details</h3>
                        <table>
                            <tr><th>Time</th><th>Symbol</th><th>Action</th><th>Qty</th><th>Price</th><th>P&L</th></tr>
                            {self._format_trades_table(trades_data)}
                        </table>
                    </div>
                </div>
                
                <div class="footer">
                    <p>JMoney Alert Trading System | Daily Summary Report</p>
                    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EST</p>
                </div>
            </body>
            </html>
            """
            
            return self._send_email(subject, html_body)
            
        except Exception as e:
            self.logger.error(f"Error sending daily summary email: {e}")
            return False
    
    def _get_daily_performance(self, summary_date: date) -> Dict[str, Any]:
        """Get daily performance metrics from database"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM performance WHERE date = ?
                ''', (summary_date.isoformat(),))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                else:
                    return {
                        'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
                        'win_rate': 0.0, 'net_pnl': 0.0, 'gross_profit': 0.0,
                        'gross_loss': 0.0, 'commission_paid': 0.0
                    }
        except Exception as e:
            self.logger.error(f"Error getting daily performance: {e}")
            return {}
    
    def _get_daily_trades(self, summary_date: date) -> List[Dict[str, Any]]:
        """Get daily trades from database"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM trades 
                    WHERE DATE(created_at) = ? 
                    ORDER BY created_at
                ''', (summary_date.isoformat(),))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting daily trades: {e}")
            return []
    
    def _format_trades_table(self, trades_data: List[Dict[str, Any]]) -> str:
        """Format trades data for HTML table"""
        if not trades_data:
            return '<tr><td colspan="6" style="text-align: center;">No trades today</td></tr>'
        
        rows = []
        for trade in trades_data:
            pnl_class = 'profit' if trade.get('pnl', 0) >= 0 else 'loss'
            rows.append(f'''
                <tr>
                    <td>{trade.get('fill_timestamp', 'N/A')}</td>
                    <td>{trade.get('symbol', 'N/A')}</td>
                    <td>{trade.get('trade_type', 'N/A')}</td>
                    <td>{trade.get('quantity', 'N/A')}</td>
                    <td>{trade.get('fill_price', 'N/A')}</td>
                    <td class="{pnl_class}">${trade.get('pnl', 0):.2f}</td>
                </tr>
            ''')
        
        return ''.join(rows)
    
    def test_email_connection(self) -> bool:
        """Test email connection and send test email"""
        try:
            subject = "🧪 JMoney Trading System - Email Test"
            html_body = """
            <html>
            <body>
                <h2>Email Test Successful!</h2>
                <p>Your JMoney Alert Trading System email notifications are working correctly.</p>
                <p>You will receive emails for:</p>
                <ul>
                    <li>Alert confirmations</li>
                    <li>Trade executions</li>
                    <li>Daily summaries</li>
                </ul>
                <p><em>Test sent at: {}</em></p>
            </body>
            </html>
            """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            return self._send_email(subject, html_body)
            
        except Exception as e:
            self.logger.error(f"Email test failed: {e}")
            return False
