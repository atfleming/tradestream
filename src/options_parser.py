"""
Options Alert Parser for TradeStream
Parses Discord alerts from TWI_Options channel for options trading
Handles "BOUGHT" (BTO) and "SOLD" (STC) terminology
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum

class OptionsAction(Enum):
    """Options trading actions"""
    BTO = "BTO"  # Buy to Open (BOUGHT)
    STC = "STC"  # Sell to Close (SOLD)
    BTC = "BTC"  # Buy to Close
    STO = "STO"  # Sell to Open

class OptionsType(Enum):
    """Options types"""
    CALL = "CALL"
    PUT = "PUT"

@dataclass
class ParsedOptionsAlert:
    """Parsed options alert data"""
    # Basic alert info
    raw_content: str
    timestamp: datetime
    author: str
    channel: str
    
    # Options specific fields
    action: OptionsAction  # BTO, STC, etc.
    symbol: str  # Underlying symbol (e.g., SPY, AAPL)
    option_type: OptionsType  # CALL or PUT
    strike_price: float
    expiration_date: datetime
    quantity: int
    price: Optional[float] = None
    
    # Additional fields
    is_valid: bool = True
    error_message: Optional[str] = None
    confidence_score: float = 1.0
    
    # Metadata
    alert_id: Optional[str] = None
    processing_status: str = "pending"
    
    @property
    def option_symbol(self) -> str:
        """Generate standard option symbol"""
        exp_str = self.expiration_date.strftime("%y%m%d")
        option_code = "C" if self.option_type == OptionsType.CALL else "P"
        strike_str = f"{int(self.strike_price * 1000):08d}"
        return f"{self.symbol}{exp_str}{option_code}{strike_str}"

class OptionsAlertParser:
    """Parser for options alerts from Discord"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common patterns for options alerts
        self.patterns = {
            # Pattern for "BOUGHT SPY 01/31 480 CALLS @ 2.50"
            'bought_sold_pattern': re.compile(
                r'(BOUGHT|SOLD)\s+([A-Z]+)\s+(\d{1,2}/\d{1,2})\s+(\d+(?:\.\d+)?)\s+(CALLS?|PUTS?)\s*(?:@|at)?\s*(\d+(?:\.\d+)?)?',
                re.IGNORECASE
            ),
            
            # Pattern for "BTO SPY 480C 1/31 @ 2.50"
            'bto_stc_pattern': re.compile(
                r'(BTO|STC|BTC|STO)\s+([A-Z]+)\s+(\d+(?:\.\d+)?)(C|P)\s+(\d{1,2}/\d{1,2})\s*(?:@|at)?\s*(\d+(?:\.\d+)?)?',
                re.IGNORECASE
            ),
            
            # Pattern for quantity extraction
            'quantity_pattern': re.compile(r'(\d+)x?\s*(?:contracts?)?', re.IGNORECASE),
            
            # Pattern for price extraction
            'price_pattern': re.compile(r'(?:@|at|for)\s*\$?(\d+(?:\.\d+)?)', re.IGNORECASE)
        }
    
    def parse_alert(self, message_content: str, author: str, timestamp: datetime, channel: str) -> Optional[ParsedOptionsAlert]:
        """Parse a Discord message for options alert information"""
        try:
            # Clean the message content
            content = message_content.strip()
            
            # Try different parsing patterns
            parsed_alert = None
            
            # Try BOUGHT/SOLD pattern first
            parsed_alert = self._parse_bought_sold_pattern(content, author, timestamp, channel)
            
            # If that fails, try BTO/STC pattern
            if not parsed_alert:
                parsed_alert = self._parse_bto_stc_pattern(content, author, timestamp, channel)
            
            if parsed_alert:
                # Extract additional information
                self._extract_quantity(parsed_alert, content)
                self._extract_price(parsed_alert, content)
                
                # Validate the parsed alert
                self._validate_alert(parsed_alert)
                
                self.logger.info(f"Successfully parsed options alert: {parsed_alert.option_symbol}")
                return parsed_alert
            
            # If no pattern matched, return invalid alert
            return ParsedOptionsAlert(
                raw_content=content,
                timestamp=timestamp,
                author=author,
                channel=channel,
                action=OptionsAction.BTO,  # Default
                symbol="UNKNOWN",
                option_type=OptionsType.CALL,  # Default
                strike_price=0.0,
                expiration_date=datetime.now(),
                quantity=0,
                is_valid=False,
                error_message="No valid options pattern found",
                confidence_score=0.0
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing options alert: {str(e)}")
            return ParsedOptionsAlert(
                raw_content=message_content,
                timestamp=timestamp,
                author=author,
                channel=channel,
                action=OptionsAction.BTO,
                symbol="ERROR",
                option_type=OptionsType.CALL,
                strike_price=0.0,
                expiration_date=datetime.now(),
                quantity=0,
                is_valid=False,
                error_message=f"Parsing error: {str(e)}",
                confidence_score=0.0
            )
    
    def _parse_bought_sold_pattern(self, content: str, author: str, timestamp: datetime, channel: str) -> Optional[ParsedOptionsAlert]:
        """Parse BOUGHT/SOLD pattern: 'BOUGHT SPY 01/31 480 CALLS @ 2.50'"""
        match = self.patterns['bought_sold_pattern'].search(content)
        if not match:
            return None
        
        action_str, symbol, exp_date_str, strike_str, option_type_str, price_str = match.groups()
        
        # Map BOUGHT/SOLD to BTO/STC
        action_mapping = {
            'BOUGHT': OptionsAction.BTO,
            'SOLD': OptionsAction.STC
        }
        action = action_mapping.get(action_str.upper(), OptionsAction.BTO)
        
        # Parse option type
        option_type = OptionsType.CALL if 'CALL' in option_type_str.upper() else OptionsType.PUT
        
        # Parse strike price
        strike_price = float(strike_str)
        
        # Parse expiration date
        expiration_date = self._parse_expiration_date(exp_date_str)
        
        # Parse price if available
        price = float(price_str) if price_str else None
        
        return ParsedOptionsAlert(
            raw_content=content,
            timestamp=timestamp,
            author=author,
            channel=channel,
            action=action,
            symbol=symbol.upper(),
            option_type=option_type,
            strike_price=strike_price,
            expiration_date=expiration_date,
            quantity=1,  # Default, will be updated by quantity extraction
            price=price,
            is_valid=True,
            confidence_score=0.9
        )
    
    def _parse_bto_stc_pattern(self, content: str, author: str, timestamp: datetime, channel: str) -> Optional[ParsedOptionsAlert]:
        """Parse BTO/STC pattern: 'BTO SPY 480C 1/31 @ 2.50'"""
        match = self.patterns['bto_stc_pattern'].search(content)
        if not match:
            return None
        
        action_str, symbol, strike_str, option_type_char, exp_date_str, price_str = match.groups()
        
        # Parse action
        try:
            action = OptionsAction(action_str.upper())
        except ValueError:
            action = OptionsAction.BTO  # Default
        
        # Parse option type
        option_type = OptionsType.CALL if option_type_char.upper() == 'C' else OptionsType.PUT
        
        # Parse strike price
        strike_price = float(strike_str)
        
        # Parse expiration date
        expiration_date = self._parse_expiration_date(exp_date_str)
        
        # Parse price if available
        price = float(price_str) if price_str else None
        
        return ParsedOptionsAlert(
            raw_content=content,
            timestamp=timestamp,
            author=author,
            channel=channel,
            action=action,
            symbol=symbol.upper(),
            option_type=option_type,
            strike_price=strike_price,
            expiration_date=expiration_date,
            quantity=1,  # Default, will be updated by quantity extraction
            price=price,
            is_valid=True,
            confidence_score=0.9
        )
    
    def _parse_expiration_date(self, exp_date_str: str) -> datetime:
        """Parse expiration date from string like '01/31' or '1/31'"""
        try:
            # Assume current year if not specified
            current_year = datetime.now().year
            
            # Handle different formats
            if '/' in exp_date_str:
                month_str, day_str = exp_date_str.split('/')
                month = int(month_str)
                day = int(day_str)
                
                # Create expiration date
                exp_date = datetime(current_year, month, day)
                
                # If the date is in the past, assume next year
                if exp_date < datetime.now():
                    exp_date = datetime(current_year + 1, month, day)
                
                return exp_date
            
        except Exception as e:
            self.logger.warning(f"Error parsing expiration date '{exp_date_str}': {str(e)}")
        
        # Default to next Friday if parsing fails
        return self._get_next_friday()
    
    def _get_next_friday(self) -> datetime:
        """Get the next Friday (typical options expiration)"""
        today = datetime.now()
        days_ahead = 4 - today.weekday()  # Friday is 4
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    
    def _extract_quantity(self, alert: ParsedOptionsAlert, content: str):
        """Extract quantity from the message content"""
        quantity_match = self.patterns['quantity_pattern'].search(content)
        if quantity_match:
            try:
                alert.quantity = int(quantity_match.group(1))
            except ValueError:
                alert.quantity = 1
        else:
            alert.quantity = 1
    
    def _extract_price(self, alert: ParsedOptionsAlert, content: str):
        """Extract price from the message content if not already set"""
        if alert.price is None:
            price_match = self.patterns['price_pattern'].search(content)
            if price_match:
                try:
                    alert.price = float(price_match.group(1))
                except ValueError:
                    pass
    
    def _validate_alert(self, alert: ParsedOptionsAlert):
        """Validate the parsed alert and set confidence score"""
        issues = []
        
        # Check required fields
        if not alert.symbol or alert.symbol == "UNKNOWN":
            issues.append("Invalid symbol")
        
        if alert.strike_price <= 0:
            issues.append("Invalid strike price")
        
        if alert.quantity <= 0:
            issues.append("Invalid quantity")
        
        # Check expiration date
        if alert.expiration_date < datetime.now():
            issues.append("Expiration date in the past")
        
        # Update validity and confidence
        if issues:
            alert.is_valid = False
            alert.error_message = "; ".join(issues)
            alert.confidence_score = 0.0
        else:
            alert.is_valid = True
            alert.confidence_score = min(1.0, alert.confidence_score)
    
    def is_options_alert(self, message_content: str) -> bool:
        """Check if a message contains options alert keywords"""
        content_upper = message_content.upper()
        
        # Check for options keywords
        options_keywords = [
            'BOUGHT', 'SOLD', 'BTO', 'STC', 'BTC', 'STO',
            'CALL', 'CALLS', 'PUT', 'PUTS',
            'STRIKE', 'EXPIRATION', 'EXP'
        ]
        
        # Check for date patterns
        date_patterns = [
            r'\d{1,2}/\d{1,2}',  # MM/DD format
            r'\d{1,2}-\d{1,2}',  # MM-DD format
        ]
        
        # Must have at least one options keyword and one date pattern
        has_keyword = any(keyword in content_upper for keyword in options_keywords)
        has_date = any(re.search(pattern, message_content) for pattern in date_patterns)
        
        return has_keyword and has_date

# Example usage and testing
if __name__ == "__main__":
    parser = OptionsAlertParser()
    
    # Test messages
    test_messages = [
        "BOUGHT SPY 01/31 480 CALLS @ 2.50",
        "SOLD AAPL 02/15 150 PUTS @ 3.25",
        "BTO QQQ 380C 1/31 @ 1.75",
        "STC TSLA 250P 2/7 @ 4.50",
        "5x BOUGHT SPY 01/31 480 CALLS @ 2.50"
    ]
    
    for msg in test_messages:
        result = parser.parse_alert(msg, "TestUser", datetime.now(), "TWI_Options")
        if result:
            print(f"Parsed: {result.action.value} {result.option_symbol} @ ${result.price}")
        else:
            print(f"Failed to parse: {msg}")
