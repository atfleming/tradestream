#!/usr/bin/env python3
"""
Test Script for JMoney Discord Alert Trading System
Tests all components: configuration, database, message parser, and email notifications
"""

import sys
import os
import logging
import random
from datetime import datetime, date
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import ConfigManager
from database import DatabaseManager
from message_parser import JMoneyMessageParser, ParsedAlert
from email_notifier import EmailNotifier


def setup_logging():
    """Set up logging for the test"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/test_system.log')
        ]
    )
    return logging.getLogger(__name__)


def test_configuration(logger):
    """Test configuration loading"""
    logger.info("=" * 50)
    logger.info("TESTING CONFIGURATION")
    logger.info("=" * 50)
    
    try:
        # Use test configuration file
        config = ConfigManager('config_test.yaml')
        
        # Load configuration
        if not config.load_config():
            logger.error("❌ Failed to load configuration")
            return False, None
        
        logger.info("✅ Configuration loaded successfully")
        
        # Validate configuration
        if not config.validate_config():
            logger.error("❌ Configuration validation failed")
            return False, None
        
        logger.info("✅ Configuration validated successfully")
        
        # Display key settings (without sensitive data)
        logger.info(f"Discord Channel ID: {config.discord.channel_id if config.discord else 'Not set'}")
        logger.info(f"Target Author: {config.discord.target_author if config.discord else 'Not set'}")
        logger.info(f"Trading Symbol: {config.trading.symbol if config.trading else 'Not set'}")
        logger.info(f"Auto Trading: {config.trading.enable_auto_trading if config.trading else 'Not set'}")
        logger.info(f"Email Enabled: {config.email.enabled if config.email else 'Not set'}")
        logger.info(f"Email Recipients: {len(config.email.to_addresses) if config.email else 0} addresses")
        
        return True, config
        
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False, None


def test_database(logger):
    """Test database initialization and operations"""
    logger.info("=" * 50)
    logger.info("TESTING DATABASE")
    logger.info("=" * 50)
    
    try:
        db = DatabaseManager()
        
        # Initialize database
        if not db.initialize_database():
            logger.error("❌ Failed to initialize database")
            return False, None
        
        logger.info("✅ Database initialized successfully")
        
        # Test basic operations
        # Test database operations with unique message ID
        unique_message_id = random.randint(100000, 999999)
        
        alert_id = db.insert_alert(
            discord_message_id=unique_message_id,
            author="TestUser",
            channel_id=123456789,
            raw_content="🚨 ES long 6300: B\nStop: 6290\n@everyone",
            parsed_price=6300.0,
            parsed_size="B",
            parsed_stop=6290.0,
            target_1=6307.0,
            target_2=6312.0,
            is_valid=True
        )
        
        if alert_id:
            logger.info(f"✅ Test alert inserted with ID: {alert_id}")
        else:
            logger.error("❌ Failed to insert test alert")
            return False, None
        
        # Test retrieval
        alert = db.get_alert(alert_id)
        if alert:
            logger.info("✅ Test alert retrieved successfully")
        else:
            logger.error("❌ Failed to retrieve test alert")
            return False, None
        
        # Get system stats
        stats = db.get_system_stats()
        logger.info(f"Database stats: {stats}")
        
        return True, db
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False, None


def test_message_parser(logger):
    """Test message parser with sample JMoney alerts"""
    logger.info("=" * 50)
    logger.info("TESTING MESSAGE PARSER")
    logger.info("=" * 50)
    
    try:
        parser = JMoneyMessageParser()
        
        # Test cases from our analysis
        test_messages = [
            {
                'content': "🚨 ES long 6326: A\nStop: 6316\n@everyone",
                'expected_valid': True,
                'expected_price': 6326,
                'expected_size': 'A',
                'expected_stop': 6316
            },
            {
                'content': "🚨 ES long 6341: B\nStop: 6332\n@everyone",
                'expected_valid': True,
                'expected_price': 6341,
                'expected_size': 'B',
                'expected_stop': 6332
            },
            {
                'content': "🚨 ES long 6352: C GAMMA\nStop: 6344\n@everyone",
                'expected_valid': True,
                'expected_price': 6352,
                'expected_size': 'C',
                'expected_stop': 6344
            },
            {
                'content': "Invalid message without proper format",
                'expected_valid': False
            }
        ]
        
        passed_tests = 0
        total_tests = len(test_messages)
        
        for i, test_case in enumerate(test_messages, 1):
            logger.info(f"Test {i}: {test_case['content'][:30]}...")
            
            result = parser.parse_message(test_case['content'])
            
            if result.is_valid == test_case['expected_valid']:
                if result.is_valid:
                    # Check parsed values
                    if (result.price == test_case['expected_price'] and
                        result.size == test_case['expected_size'] and
                        result.stop == test_case['expected_stop'] and
                        result.target_1 == test_case['expected_price'] + 7 and
                        result.target_2 == test_case['expected_price'] + 12):
                        logger.info(f"✅ Test {i} passed: {parser.format_alert_summary(result)}")
                        passed_tests += 1
                    else:
                        logger.error(f"❌ Test {i} failed: Incorrect parsed values")
                else:
                    logger.info(f"✅ Test {i} passed: Correctly identified as invalid")
                    passed_tests += 1
            else:
                logger.error(f"❌ Test {i} failed: Expected valid={test_case['expected_valid']}, got {result.is_valid}")
        
        logger.info(f"Parser tests: {passed_tests}/{total_tests} passed")
        
        if passed_tests == total_tests:
            logger.info("✅ All message parser tests passed")
            return True, parser
        else:
            logger.error("❌ Some message parser tests failed")
            return False, None
        
    except Exception as e:
        logger.error(f"❌ Message parser test failed: {e}")
        return False, None


def test_email_system(logger, config, db, parser):
    """Test email notification system"""
    logger.info("=" * 50)
    logger.info("TESTING EMAIL SYSTEM")
    logger.info("=" * 50)
    
    try:
        # Check if email is configured
        if not config.email or not config.email.enabled:
            logger.warning("⚠️ Email notifications are disabled in configuration")
            logger.info("To test emails, update config.yaml with your email settings and set enabled: true")
            return True, None
        
        if not config.email.username or not config.email.password:
            logger.warning("⚠️ Email credentials not configured")
            logger.info("To test emails, set your email username/password in config.yaml or environment variables")
            return True, None
        
        # Initialize email notifier
        email_notifier = EmailNotifier(config, db)
        
        # Test 1: Connection test
        logger.info("Testing email connection...")
        if email_notifier.test_email_connection():
            logger.info("✅ Email connection test successful")
        else:
            logger.error("❌ Email connection test failed")
            return False, None
        
        # Test 2: Alert confirmation email
        logger.info("Testing alert confirmation email...")
        
        # Create a sample parsed alert
        sample_alert = ParsedAlert(
            is_valid=True,
            raw_message="🚨 ES long 6300: B\nStop: 6290\n@everyone",
            price=6300.0,
            size="B",
            stop=6290.0,
            target_1=6307.0,
            target_2=6312.0
        )
        
        sample_message_data = {
            'message_id': 'test_123456',
            'author': 'JMoney',
            'channel_id': 123456789,
            'timestamp': datetime.now(),
            'alert_id': 1
        }
        
        if email_notifier.send_alert_confirmation(sample_alert, sample_message_data, account_balance=10000.0):
            logger.info("✅ Alert confirmation email sent successfully")
        else:
            logger.error("❌ Alert confirmation email failed")
            return False, None
        
        # Test 3: Trade execution email
        logger.info("Testing trade execution email...")
        
        if email_notifier.send_trade_execution(
            trade_type="BUY",
            symbol="MES",
            quantity=2,
            price=6300.0,
            order_id="ORD123456",
            account_balance=9950.0,
            pnl=0.0
        ):
            logger.info("✅ Trade execution email sent successfully")
        else:
            logger.error("❌ Trade execution email failed")
            return False, None
        
        # Test 4: Daily summary email
        logger.info("Testing daily summary email...")
        
        if email_notifier.send_daily_summary(date.today(), account_balance=10150.0):
            logger.info("✅ Daily summary email sent successfully")
        else:
            logger.error("❌ Daily summary email failed")
            return False, None
        
        logger.info("✅ All email tests passed")
        return True, email_notifier
        
    except Exception as e:
        logger.error(f"❌ Email system test failed: {e}")
        return False, None


def main():
    """Main test function"""
    # Ensure directories exist
    Path('logs').mkdir(exist_ok=True)
    Path('data').mkdir(exist_ok=True)
    
    logger = setup_logging()
    
    logger.info("🚀 Starting JMoney Trading System Tests")
    logger.info(f"Test started at: {datetime.now()}")
    
    # Test results
    results = {
        'configuration': False,
        'database': False,
        'message_parser': False,
        'email_system': False
    }
    
    # Test configuration
    config_success, config = test_configuration(logger)
    results['configuration'] = config_success
    
    if not config_success:
        logger.error("❌ Configuration test failed - stopping tests")
        return False
    
    # Test database
    db_success, db = test_database(logger)
    results['database'] = db_success
    
    if not db_success:
        logger.error("❌ Database test failed - stopping tests")
        return False
    
    # Test message parser
    parser_success, parser = test_message_parser(logger)
    results['message_parser'] = parser_success
    
    if not parser_success:
        logger.error("❌ Message parser test failed - stopping tests")
        return False
    
    # Test email system
    email_success, email_notifier = test_email_system(logger, config, db, parser)
    results['email_system'] = email_success
    
    # Final results
    logger.info("=" * 50)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("=" * 50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("🎉 ALL TESTS PASSED! System is ready for Phase 2.")
    else:
        logger.error("❌ Some tests failed. Please fix issues before proceeding.")
    
    logger.info(f"Test completed at: {datetime.now()}")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
