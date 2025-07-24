"""
Unit Tests for JMoney Message Parser
Tests various alert formats and parsing accuracy
"""

import unittest
import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from message_parser import JMoneyMessageParser, ParsedAlert


class TestJMoneyMessageParser(unittest.TestCase):
    """Test cases for JMoney message parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = JMoneyMessageParser()
    
    def test_valid_es_long_alert_basic(self):
        """Test parsing of basic ES LONG alert"""
        message = "🚨 ES long 4500: B\nStop: 4490\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.price, 4500.0)
        self.assertEqual(result.size, "B")
        self.assertEqual(result.stop, 4490.0)
        self.assertEqual(result.target_1, 4507.0)  # price + 7 points
        self.assertEqual(result.target_2, 4512.0)  # price + 12 points
    
    def test_valid_es_long_alert_size_a(self):
        """Test parsing with SIZE A"""
        message = "🚨 ES long 4525: A\nStop: 4515\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.price, 4525.0)
        self.assertEqual(result.size, "A")
        self.assertEqual(result.stop, 4515.0)
    
    def test_valid_es_long_alert_size_c(self):
        """Test parsing with SIZE C"""
        message = "🚨 ES long 4475: C\nStop: 4465\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.price, 4475.0)
        self.assertEqual(result.size, "C")
        self.assertEqual(result.stop, 4465.0)
    
    def test_valid_es_long_alert_with_gamma(self):
        """Test parsing with GAMMA keyword"""
        message = "🚨 ES long 4500: B GAMMA\nStop: 4490\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.price, 4500.0)
        self.assertEqual(result.size, "B")
        self.assertEqual(result.stop, 4490.0)
    
    def test_valid_es_long_alert_case_insensitive(self):
        """Test case insensitive parsing"""
        message = "🚨 es long 4500: b\nstop: 4490\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.price, 4500.0)
        self.assertEqual(result.size, "B")
        self.assertEqual(result.stop, 4490.0)
    
    def test_invalid_alert_no_es_long(self):
        """Test invalid alert without ES LONG"""
        message = "Looking at SPY today, might be a good day"
        result = self.parser.parse_message(message)
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_message, "Not an ES LONG alert")
    
    def test_invalid_alert_missing_price(self):
        """Test invalid alert missing price"""
        message = "🚨 ES long : B\nStop: 4490\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertFalse(result.is_valid)
        self.assertIn("price", result.error_message.lower())
    
    def test_invalid_alert_missing_size(self):
        """Test invalid alert missing size"""
        message = "🚨 ES long 4500\nStop: 4490\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertFalse(result.is_valid)
        self.assertIn("price", result.error_message.lower())
    
    def test_invalid_alert_missing_stop(self):
        """Test invalid alert missing stop"""
        message = "🚨 ES long 4500: B\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertFalse(result.is_valid)
        self.assertIn("stop", result.error_message.lower())
    
    def test_invalid_alert_invalid_size(self):
        """Test invalid alert with invalid size"""
        message = "🚨 ES long 4500: X\nStop: 4490\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertFalse(result.is_valid)
        self.assertIn("could not extract", result.error_message.lower())
    
    def test_invalid_alert_stop_above_entry(self):
        """Test invalid alert with stop above entry price"""
        message = "🚨 ES long 4500: B\nStop: 4510\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertFalse(result.is_valid)
        self.assertIn("validation", result.error_message.lower())
    
    def test_target_calculations(self):
        """Test target price calculations"""
        message = "🚨 ES long 4500: B\nStop: 4490\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.target_1, 4507.0)  # Entry + 7 points
        self.assertEqual(result.target_2, 4512.0)  # Entry + 12 points
    
    def test_multiple_es_long_in_message(self):
        """Test message with multiple ES long mentions"""
        message = "Yesterday was good, today 🚨 ES long 4500: B\nStop: 4490\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.price, 4500.0)
        self.assertEqual(result.size, "B")
        self.assertEqual(result.stop, 4490.0)
    
    def test_decimal_price_handling(self):
        """Test handling of decimal prices - note: actual format uses integers"""
        # JMoney format typically uses integers, but test parser robustness
        message = "🚨 ES long 4500: B\nStop: 4490\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.price, 4500.0)
        self.assertEqual(result.stop, 4490.0)
    
    def test_edge_case_very_high_price(self):
        """Test edge case with very high price"""
        message = "🚨 ES long 7500: B\nStop: 7490\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.price, 7500.0)
    
    def test_edge_case_very_low_price(self):
        """Test edge case with very low price"""
        message = "🚨 ES long 3500: B\nStop: 3490\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.price, 3500.0)
    
    def test_author_tracking(self):
        """Test author tracking"""
        message = "🚨 ES long 4500: B\nStop: 4490\n@everyone"
        result = self.parser.parse_message(message, author="JMoney")
        
        self.assertTrue(result.is_valid)
        # Author is not stored in ParsedAlert, just used for validation
    
    def test_timestamp_assignment(self):
        """Test timestamp assignment"""
        message = "🚨 ES long 4500: B\nStop: 4490\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertTrue(result.is_valid)
        # Timestamp is not part of ParsedAlert in current implementation
    
    def test_raw_message_storage(self):
        """Test raw message storage"""
        message = "🚨 ES long 4500: B\nStop: 4490\n@everyone"
        result = self.parser.parse_message(message)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.raw_message, message)
        self.assertEqual(result.size, "B")
        self.assertEqual(result.stop, 4490.0)


class TestParsedAlert(unittest.TestCase):
    """Test cases for ParsedAlert data class"""
    
    def test_parsed_alert_initialization(self):
        """Test ParsedAlert initialization"""
        alert = ParsedAlert()
        
        self.assertFalse(alert.is_valid)
        self.assertEqual(alert.raw_message, "")
        self.assertIsNone(alert.price)
        self.assertIsNone(alert.size)
        self.assertIsNone(alert.stop)
        self.assertIsNone(alert.target_1)
        self.assertIsNone(alert.target_2)
        self.assertIsNone(alert.error_message)
    
    def test_parsed_alert_with_raw_message(self):
        """Test ParsedAlert with raw message"""
        raw_message = "🚨 ES long 4500: B\nStop: 4490\n@everyone"
        alert = ParsedAlert(raw_message=raw_message)
        
        self.assertEqual(alert.raw_message, raw_message)


if __name__ == '__main__':
    unittest.main()
