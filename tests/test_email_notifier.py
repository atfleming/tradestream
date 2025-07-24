"""
Unit tests for Email Notifier module
Tests email notifications for alerts, trades, and daily summaries
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from dataclasses import dataclass

# Add src to path for imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_notifier import EmailNotifier, EmailConfig
from message_parser import ParsedAlert
from database import DatabaseManager
from config import ConfigManager


@dataclass
class MockEmailData:
    """Mock email configuration data"""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = "test@example.com"
    password: str = "test_password"
    from_address: str = "test@example.com"
    to_addresses: list = None
    enabled: bool = True
    
    def __post_init__(self):
        if self.to_addresses is None:
            self.to_addresses = ["recipient@example.com"]


class TestEmailNotifier(unittest.TestCase):
    """Test cases for EmailNotifier class"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Initialize database
        self.db = DatabaseManager(self.db_path)
        self.db.initialize_database()
        
        # Create test configuration
        self.config_manager = ConfigManager()
        self.config_manager.email = MockEmailData()
        
        # Initialize email notifier
        self.email_notifier = EmailNotifier(
            config=self.config_manager,
            db=self.db
        )
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_email_notifier_initialization(self):
        """Test email notifier initialization"""
        self.assertIsNotNone(self.email_notifier.config)
        self.assertIsNotNone(self.email_notifier.db)
        self.assertIsNotNone(self.email_notifier.email_config)
        self.assertEqual(self.email_notifier.email_config.smtp_server, "smtp.gmail.com")
        self.assertEqual(self.email_notifier.email_config.smtp_port, 587)
        self.assertEqual(self.email_notifier.email_config.username, "test@example.com")
        self.assertEqual(self.email_notifier.email_config.from_address, "test@example.com")
        self.assertEqual(self.email_notifier.email_config.to_addresses, ["recipient@example.com"])
        self.assertTrue(self.email_notifier.email_config.enabled)
    
    def test_email_config_dataclass(self):
        """Test EmailConfig dataclass functionality"""
        config = EmailConfig(
            smtp_server="smtp.test.com",
            smtp_port=465,
            username="user@test.com",
            password="password123",
            from_address="from@test.com",
            to_addresses=["to1@test.com", "to2@test.com"],
            enabled=False
        )
        
        self.assertEqual(config.smtp_server, "smtp.test.com")
        self.assertEqual(config.smtp_port, 465)
        self.assertEqual(config.username, "user@test.com")
        self.assertEqual(config.password, "password123")
        self.assertEqual(config.from_address, "from@test.com")
        self.assertEqual(config.to_addresses, ["to1@test.com", "to2@test.com"])
        self.assertFalse(config.enabled)
    
    def test_load_email_config_missing(self):
        """Test loading email config when config is missing"""
        # Create notifier without email config
        config_manager = ConfigManager()
        # Don't set email attribute
        
        notifier = EmailNotifier(config_manager, self.db)
        self.assertIsNone(notifier.email_config)
    
    def test_load_email_config_error_handling(self):
        """Test error handling in email config loading"""
        # Create config with invalid email data
        config_manager = ConfigManager()
        config_manager.email = "invalid_data"  # Not a proper object
        
        notifier = EmailNotifier(config_manager, self.db)
        self.assertIsNone(notifier.email_config)
    
    @patch('email_notifier.smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending"""
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        subject = "Test Subject"
        html_body = "<html><body><h1>Test Email</h1></body></html>"
        text_body = "Test Email"
        
        result = self.email_notifier._send_email(subject, html_body, text_body)
        
        self.assertTrue(result)
        mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "test_password")
        mock_server.send_message.assert_called_once()
    
    @patch('email_notifier.smtplib.SMTP')
    def test_send_email_html_only(self, mock_smtp):
        """Test sending email with HTML only (no text fallback)"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        subject = "HTML Only Test"
        html_body = "<html><body><p>HTML only email</p></body></html>"
        
        result = self.email_notifier._send_email(subject, html_body)
        
        self.assertTrue(result)
        mock_server.send_message.assert_called_once()
    
    def test_send_email_disabled(self):
        """Test email sending when notifications are disabled"""
        # Disable email notifications
        self.email_notifier.email_config.enabled = False
        
        result = self.email_notifier._send_email("Test", "<html></html>")
        
        self.assertFalse(result)
    
    def test_send_email_no_config(self):
        """Test email sending when no config is available"""
        # Remove email config
        self.email_notifier.email_config = None
        
        result = self.email_notifier._send_email("Test", "<html></html>")
        
        self.assertFalse(result)
    
    @patch('email_notifier.smtplib.SMTP')
    def test_send_email_smtp_error(self, mock_smtp):
        """Test email sending with SMTP error"""
        # Mock SMTP to raise exception
        mock_smtp.side_effect = Exception("SMTP connection failed")
        
        result = self.email_notifier._send_email("Test", "<html></html>")
        
        self.assertFalse(result)
    
    @patch.object(EmailNotifier, '_send_email')
    def test_send_alert_confirmation_valid(self, mock_send_email):
        """Test sending alert confirmation for valid alert"""
        mock_send_email.return_value = True
        
        # Create valid alert
        alert = ParsedAlert(
            raw_message="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            is_valid=True,
            price=4500.0,
            size="B",
            stop=4490.0,
            target_1=4510.0,
            target_2=4520.0
        )
        
        message_data = {
            'timestamp': '2024-01-15 10:30:00',
            'message_id': 'msg_123',
            'author': 'JMoney'
        }
        
        result = self.email_notifier.send_alert_confirmation(
            alert, message_data, account_balance=50000.0
        )
        
        self.assertTrue(result)
        mock_send_email.assert_called_once()
        
        # Check that the email was called with correct subject pattern
        call_args = mock_send_email.call_args
        subject = call_args[0][0]
        html_body = call_args[0][1]
        
        self.assertIn("JMoney Alert Received", subject)
        self.assertIn("ES LONG 4500", subject)
        self.assertIn("(B)", subject)
        self.assertIn("4500.0", html_body)
        self.assertIn("4490.0", html_body)
        self.assertIn("4510.0", html_body)
        self.assertIn("4520.0", html_body)
        self.assertIn("$50000.00", html_body)
    
    @patch.object(EmailNotifier, '_send_email')
    def test_send_alert_confirmation_invalid(self, mock_send_email):
        """Test sending alert confirmation for invalid alert"""
        # Create invalid alert
        alert = ParsedAlert(
            raw_message="Invalid message",
            is_valid=False
        )
        
        message_data = {'timestamp': '2024-01-15 10:30:00'}
        
        result = self.email_notifier.send_alert_confirmation(alert, message_data)
        
        self.assertFalse(result)
        mock_send_email.assert_not_called()
    
    @patch.object(EmailNotifier, '_send_email')
    def test_send_alert_confirmation_error_handling(self, mock_send_email):
        """Test error handling in alert confirmation"""
        # Mock _send_email to raise exception
        mock_send_email.side_effect = Exception("Email sending failed")
        
        alert = ParsedAlert(
            raw_message="🚨 ES long 4500: B\nStop: 4490\n@everyone",
            is_valid=True,
            price=4500.0,
            size="B",
            stop=4490.0
        )
        
        result = self.email_notifier.send_alert_confirmation(alert, {})
        
        self.assertFalse(result)
    
    @patch.object(EmailNotifier, '_send_email')
    def test_send_trade_execution_buy(self, mock_send_email):
        """Test sending trade execution email for BUY order"""
        mock_send_email.return_value = True
        
        result = self.email_notifier.send_trade_execution(
            trade_type="BUY",
            symbol="MES",
            quantity=2,
            price=4500.0,
            order_id="ORDER_123",
            account_balance=49000.0,
            pnl=None  # Entry trade, no P&L yet
        )
        
        self.assertTrue(result)
        mock_send_email.assert_called_once()
        
        # Check email content
        call_args = mock_send_email.call_args
        subject = call_args[0][0]
        html_body = call_args[0][1]
        
        self.assertIn("🟢 ENTRY", subject)
        self.assertIn("MES 2 contracts @ 4500.0", subject)
        self.assertIn("BUY", html_body)
        self.assertIn("MES", html_body)
        self.assertIn("2 contracts", html_body)
        self.assertIn("4500.0", html_body)
        self.assertIn("ORDER_123", html_body)
        self.assertIn("$49000.00", html_body)
    
    @patch.object(EmailNotifier, '_send_email')
    def test_send_trade_execution_sell(self, mock_send_email):
        """Test sending trade execution email for SELL order"""
        mock_send_email.return_value = True
        
        result = self.email_notifier.send_trade_execution(
            trade_type="SELL",
            symbol="MES",
            quantity=2,
            price=4510.0,
            order_id="ORDER_124",
            account_balance=49025.0,
            pnl=25.0
        )
        
        self.assertTrue(result)
        mock_send_email.assert_called_once()
        
        # Check email content
        call_args = mock_send_email.call_args
        subject = call_args[0][0]
        html_body = call_args[0][1]
        
        self.assertIn("🔴 EXIT", subject)
        self.assertIn("MES 2 contracts @ 4510.0", subject)
        self.assertIn("SELL", html_body)
        self.assertIn("$25.00", html_body)  # P&L
        self.assertIn("profit", html_body)  # Should show profit class
    
    @patch.object(EmailNotifier, '_send_email')
    def test_send_trade_execution_loss(self, mock_send_email):
        """Test sending trade execution email with loss"""
        mock_send_email.return_value = True
        
        result = self.email_notifier.send_trade_execution(
            trade_type="SELL",
            symbol="MES",
            quantity=2,
            price=4490.0,
            order_id="ORDER_125",
            account_balance=49975.0,
            pnl=-25.0
        )
        
        self.assertTrue(result)
        
        # Check email content shows loss
        call_args = mock_send_email.call_args
        html_body = call_args[0][1]
        
        self.assertIn("$-25.00", html_body)
        self.assertIn("loss", html_body)  # Should show loss class
    
    @patch.object(EmailNotifier, '_send_email')
    def test_send_trade_execution_error_handling(self, mock_send_email):
        """Test error handling in trade execution email"""
        mock_send_email.side_effect = Exception("Email failed")
        
        result = self.email_notifier.send_trade_execution(
            "BUY", "MES", 1, 4500.0, "ORDER_123"
        )
        
        self.assertFalse(result)
    
    @patch.object(EmailNotifier, '_send_email')
    @patch.object(EmailNotifier, '_get_daily_performance')
    @patch.object(EmailNotifier, '_get_daily_trades')
    def test_send_daily_summary(self, mock_get_trades, mock_get_performance, mock_send_email):
        """Test sending daily summary email"""
        mock_send_email.return_value = True
        mock_get_performance.return_value = {
            'total_trades': 5,
            'winning_trades': 3,
            'losing_trades': 2,
            'win_rate': 60.0,
            'net_pnl': 125.50,
            'gross_profit': 200.0,
            'gross_loss': -74.50,
            'commission_paid': 12.50
        }
        mock_get_trades.return_value = [
            {
                'fill_timestamp': '2024-01-15 10:30:00',
                'symbol': 'MES',
                'trade_type': 'BUY',
                'quantity': 2,
                'fill_price': 4500.0,
                'pnl': 25.0
            },
            {
                'fill_timestamp': '2024-01-15 11:15:00',
                'symbol': 'MES',
                'trade_type': 'SELL',
                'quantity': 1,
                'fill_price': 4490.0,
                'pnl': -12.50
            }
        ]
        
        summary_date = date(2024, 1, 15)
        result = self.email_notifier.send_daily_summary(
            summary_date, account_balance=50125.50
        )
        
        self.assertTrue(result)
        mock_send_email.assert_called_once()
        mock_get_performance.assert_called_once_with(summary_date)
        mock_get_trades.assert_called_once_with(summary_date)
        
        # Check email content
        call_args = mock_send_email.call_args
        subject = call_args[0][0]
        html_body = call_args[0][1]
        
        self.assertIn("Daily Trading Summary", subject)
        self.assertIn("2024-01-15", subject)
        self.assertIn("5", html_body)  # total trades
        self.assertIn("60.0%", html_body)  # win rate
        self.assertIn("$125.50", html_body)  # net P&L
        self.assertIn("$50125.50", html_body)  # account balance
        self.assertIn("MES", html_body)  # trade data
    
    @patch.object(EmailNotifier, '_send_email')
    @patch.object(EmailNotifier, '_get_daily_performance')
    @patch.object(EmailNotifier, '_get_daily_trades')
    def test_send_daily_summary_no_trades(self, mock_get_trades, mock_get_performance, mock_send_email):
        """Test sending daily summary with no trades"""
        mock_send_email.return_value = True
        mock_get_performance.return_value = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'net_pnl': 0.0,
            'gross_profit': 0.0,
            'gross_loss': 0.0,
            'commission_paid': 0.0
        }
        mock_get_trades.return_value = []
        
        summary_date = date(2024, 1, 15)
        result = self.email_notifier.send_daily_summary(summary_date)
        
        self.assertTrue(result)
        
        # Check that email shows no trades
        call_args = mock_send_email.call_args
        html_body = call_args[0][1]
        self.assertIn("No trades today", html_body)
    
    @patch.object(EmailNotifier, '_send_email')
    def test_send_daily_summary_error_handling(self, mock_send_email):
        """Test error handling in daily summary"""
        mock_send_email.side_effect = Exception("Email failed")
        
        result = self.email_notifier.send_daily_summary(date(2024, 1, 15))
        
        self.assertFalse(result)
    
    def test_get_daily_performance_with_data(self):
        """Test getting daily performance data from database"""
        # Insert test performance data
        test_date = date(2024, 1, 15)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO performance (
                    date, total_trades, winning_trades, losing_trades,
                    win_rate, net_pnl, gross_profit, gross_loss, commission_paid
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_date.isoformat(), 3, 2, 1, 66.67, 150.0, 200.0, -50.0, 7.50
            ))
            conn.commit()
        
        performance = self.email_notifier._get_daily_performance(test_date)
        
        self.assertEqual(performance['total_trades'], 3)
        self.assertEqual(performance['winning_trades'], 2)
        self.assertEqual(performance['losing_trades'], 1)
        self.assertEqual(performance['win_rate'], 66.67)
        self.assertEqual(performance['net_pnl'], 150.0)
    
    def test_get_daily_performance_no_data(self):
        """Test getting daily performance when no data exists"""
        test_date = date(2024, 1, 15)
        
        performance = self.email_notifier._get_daily_performance(test_date)
        
        self.assertEqual(performance['total_trades'], 0)
        self.assertEqual(performance['winning_trades'], 0)
        self.assertEqual(performance['net_pnl'], 0.0)
    
    def test_get_daily_trades_with_data(self):
        """Test getting daily trades from database"""
        # Insert test trade data
        test_date = date(2024, 1, 15)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trades (
                    alert_id, trade_type, symbol, entry_price, quantity,
                    created_at, fill_timestamp, fill_price, pnl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                1, "BUY", "MES", 4500.0, 2,
                f"{test_date.isoformat()} 10:30:00",
                f"{test_date.isoformat()} 10:30:05",
                4500.0, 25.0
            ))
            conn.commit()
        
        trades = self.email_notifier._get_daily_trades(test_date)
        
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['symbol'], 'MES')
        self.assertEqual(trades[0]['trade_type'], 'BUY')
        self.assertEqual(trades[0]['quantity'], 2)
        self.assertEqual(trades[0]['pnl'], 25.0)
    
    def test_get_daily_trades_no_data(self):
        """Test getting daily trades when no data exists"""
        test_date = date(2024, 1, 15)
        
        trades = self.email_notifier._get_daily_trades(test_date)
        
        self.assertEqual(len(trades), 0)
    
    def test_format_trades_table_with_data(self):
        """Test formatting trades data into HTML table"""
        trades_data = [
            {
                'fill_timestamp': '2024-01-15 10:30:00',
                'symbol': 'MES',
                'trade_type': 'BUY',
                'quantity': 2,
                'fill_price': 4500.0,
                'pnl': 25.0
            },
            {
                'fill_timestamp': '2024-01-15 11:15:00',
                'symbol': 'MES',
                'trade_type': 'SELL',
                'quantity': 1,
                'fill_price': 4490.0,
                'pnl': -12.50
            }
        ]
        
        html_table = self.email_notifier._format_trades_table(trades_data)
        
        self.assertIn('2024-01-15 10:30:00', html_table)
        self.assertIn('MES', html_table)
        self.assertIn('BUY', html_table)
        self.assertIn('2', html_table)
        self.assertIn('4500.0', html_table)
        self.assertIn('$25.00', html_table)
        self.assertIn('profit', html_table)  # CSS class for profit
        self.assertIn('$-12.50', html_table)
        self.assertIn('loss', html_table)  # CSS class for loss
    
    def test_format_trades_table_no_data(self):
        """Test formatting trades table with no data"""
        html_table = self.email_notifier._format_trades_table([])
        
        self.assertIn('No trades today', html_table)
        self.assertIn('colspan="6"', html_table)
    
    @patch('email_notifier.smtplib.SMTP')
    def test_test_email_connection_success(self, mock_smtp):
        """Test successful email connection test"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        result = self.email_notifier.test_email_connection()
        
        self.assertTrue(result)
        mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "test_password")
        mock_server.send_message.assert_called_once()
    
    @patch('email_notifier.smtplib.SMTP')
    def test_test_email_connection_failure(self, mock_smtp):
        """Test email connection test failure"""
        mock_smtp.side_effect = Exception("Connection failed")
        
        result = self.email_notifier.test_email_connection()
        
        self.assertFalse(result)
    
    def test_multiple_recipients(self):
        """Test email configuration with multiple recipients"""
        # Update config with multiple recipients
        self.config_manager.email.to_addresses = [
            "recipient1@example.com",
            "recipient2@example.com",
            "recipient3@example.com"
        ]
        
        # Reinitialize notifier
        notifier = EmailNotifier(self.config_manager, self.db)
        
        self.assertEqual(len(notifier.email_config.to_addresses), 3)
        self.assertIn("recipient1@example.com", notifier.email_config.to_addresses)
        self.assertIn("recipient2@example.com", notifier.email_config.to_addresses)
        self.assertIn("recipient3@example.com", notifier.email_config.to_addresses)


if __name__ == '__main__':
    unittest.main()
