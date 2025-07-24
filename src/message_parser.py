"""
Message Parser for JMoney Discord Alert Trading System
Parses JMoney's "ES LONG" alert messages and extracts trading parameters
"""

import re
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ParsedAlert:
    """Data class for parsed alert information"""
    is_valid: bool = False
    raw_message: str = ""
    price: Optional[float] = None
    size: Optional[str] = None
    stop: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'is_valid': self.is_valid,
            'raw_message': self.raw_message,
            'price': self.price,
            'size': self.size,
            'stop': self.stop,
            'target_1': self.target_1,
            'target_2': self.target_2,
            'error_message': self.error_message
        }


class JMoneyMessageParser:
    """Parser for JMoney's Discord alert messages"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Regex patterns for parsing JMoney alerts
        # Based on our analysis: "🚨 ES long 6326: A\nStop: 6316"
        self.alert_pattern = re.compile(
            r'🚨\s*ES\s+long\s+(\d+):\s*([ABC])(?:\s+GAMMA)?',
            re.IGNORECASE | re.MULTILINE
        )
        
        self.stop_pattern = re.compile(
            r'Stop:\s*(\d+)',
            re.IGNORECASE | re.MULTILINE
        )
        
        # Target calculation constants (based on our successful analysis)
        self.TARGET_1_POINTS = 7   # Target 1 = Entry + 7 points
        self.TARGET_2_POINTS = 12  # Target 2 = Entry + 12 points
    
    def parse_message(self, message_content: str, author: str = "") -> ParsedAlert:
        """
        Parse a Discord message for JMoney trading alerts
        
        Args:
            message_content: Raw Discord message content
            author: Message author (for validation)
            
        Returns:
            ParsedAlert object with extracted information
        """
        alert = ParsedAlert(raw_message=message_content)
        
        try:
            # Check if message contains ES long alert
            if not self._is_es_long_alert(message_content):
                alert.error_message = "Not an ES LONG alert"
                return alert
            
            # Extract price and size from main alert line
            price, size = self._extract_price_and_size(message_content)
            if price is None or size is None:
                alert.error_message = "Could not extract price and size"
                return alert
            
            # Extract stop loss
            stop = self._extract_stop_loss(message_content)
            if stop is None:
                alert.error_message = "Could not extract stop loss"
                return alert
            
            # Calculate targets
            target_1 = price + self.TARGET_1_POINTS
            target_2 = price + self.TARGET_2_POINTS
            
            # Validate the extracted data
            if not self._validate_alert_data(price, size, stop, target_1, target_2):
                alert.error_message = "Alert data validation failed"
                return alert
            
            # Populate successful parse
            alert.is_valid = True
            alert.price = price
            alert.size = size
            alert.stop = stop
            alert.target_1 = target_1
            alert.target_2 = target_2
            
            self.logger.info(f"Successfully parsed alert: {price} {size}, Stop: {stop}, T1: {target_1}, T2: {target_2}")
            
        except Exception as e:
            alert.error_message = f"Parsing error: {str(e)}"
            self.logger.error(f"Error parsing message: {e}")
        
        return alert
    
    def _is_es_long_alert(self, content: str) -> bool:
        """Check if message is an ES LONG alert"""
        return bool(re.search(r'🚨.*ES.*long', content, re.IGNORECASE))
    
    def _extract_price_and_size(self, content: str) -> Tuple[Optional[float], Optional[str]]:
        """Extract price and size from alert message"""
        try:
            match = self.alert_pattern.search(content)
            if match:
                price = float(match.group(1))
                size = match.group(2).upper()
                return price, size
            return None, None
        except (ValueError, AttributeError) as e:
            self.logger.error(f"Error extracting price/size: {e}")
            return None, None
    
    def _extract_stop_loss(self, content: str) -> Optional[float]:
        """Extract stop loss from alert message"""
        try:
            match = self.stop_pattern.search(content)
            if match:
                return float(match.group(1))
            return None
        except (ValueError, AttributeError) as e:
            self.logger.error(f"Error extracting stop loss: {e}")
            return None
    
    def _validate_alert_data(self, price: float, size: str, stop: float, 
                           target_1: float, target_2: float) -> bool:
        """Validate extracted alert data for reasonableness"""
        try:
            # Check price is reasonable (ES typically trades 4000-7000 range)
            if not (3000 <= price <= 8000):
                self.logger.warning(f"Price {price} outside expected range")
                return False
            
            # Check size is valid
            if size not in ['A', 'B', 'C']:
                self.logger.warning(f"Invalid size: {size}")
                return False
            
            # Check stop is below entry (for long trades)
            if stop >= price:
                self.logger.warning(f"Stop {stop} not below entry price {price}")
                return False
            
            # Check targets are above entry
            if target_1 <= price or target_2 <= price:
                self.logger.warning(f"Targets not above entry: T1={target_1}, T2={target_2}, Entry={price}")
                return False
            
            # Check target order (T2 should be higher than T1)
            if target_2 <= target_1:
                self.logger.warning(f"Target 2 ({target_2}) not higher than Target 1 ({target_1})")
                return False
            
            # Check stop loss is reasonable (not too far from entry)
            stop_distance = price - stop
            if stop_distance > 50:  # More than 50 points seems excessive
                self.logger.warning(f"Stop loss too far from entry: {stop_distance} points")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False
    
    def get_contract_quantity(self, size: str, size_mapping: Dict[str, int]) -> int:
        """Get number of contracts for given size letter"""
        return size_mapping.get(size.upper(), 1)
    
    def calculate_risk_reward(self, entry: float, stop: float, target_1: float, target_2: float) -> Dict[str, float]:
        """Calculate risk/reward metrics for the trade"""
        try:
            risk = entry - stop
            reward_1 = target_1 - entry
            reward_2 = target_2 - entry
            
            return {
                'risk_points': risk,
                'reward_1_points': reward_1,
                'reward_2_points': reward_2,
                'risk_reward_1': reward_1 / risk if risk > 0 else 0,
                'risk_reward_2': reward_2 / risk if risk > 0 else 0
            }
        except Exception as e:
            self.logger.error(f"Error calculating risk/reward: {e}")
            return {}
    
    def format_alert_summary(self, alert: ParsedAlert) -> str:
        """Format alert information for logging/display"""
        if not alert.is_valid:
            return f"INVALID ALERT: {alert.error_message}"
        
        rr_metrics = self.calculate_risk_reward(
            alert.price, alert.stop, alert.target_1, alert.target_2
        )
        
        return (f"ES LONG Alert - Entry: {alert.price}, Size: {alert.size}, "
                f"Stop: {alert.stop}, T1: {alert.target_1}, T2: {alert.target_2}, "
                f"Risk: {rr_metrics.get('risk_points', 0):.1f}pts, "
                f"R/R: {rr_metrics.get('risk_reward_1', 0):.2f}/{rr_metrics.get('risk_reward_2', 0):.2f}")


# Example usage and testing
def test_parser():
    """Test function to validate parser with known message formats"""
    parser = JMoneyMessageParser()
    
    # Test cases based on our analysis
    test_messages = [
        "🚨 ES long 6326: A\nStop: 6316\n@everyone",
        "🚨 ES long 6341: B\nStop: 6332\n@everyone", 
        "🚨 ES long 6352: C GAMMA\nStop: 6344\n@everyone",
        "🚨 ES long 6301: C\nStop: 6291\n@everyone",
        "Invalid message without proper format"
    ]
    
    for i, msg in enumerate(test_messages, 1):
        print(f"\nTest {i}: {msg[:30]}...")
        result = parser.parse_message(msg)
        print(f"Valid: {result.is_valid}")
        if result.is_valid:
            print(parser.format_alert_summary(result))
        else:
            print(f"Error: {result.error_message}")


if __name__ == "__main__":
    # Run tests if script is executed directly
    test_parser()
