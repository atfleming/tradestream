"""
Discord Monitor for JMoney Alert Trading System
Monitors Discord channel for JMoney's trading alerts and processes them
"""

import discord
import asyncio
import logging
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime

from .config import ConfigManager
from .alert_parser import AlertParser, ParsedAlert
from .options_parser import OptionsAlertParser, ParsedOptionsAlert
from .database import DatabaseManager


class DiscordMonitor:
    """Discord bot to monitor multiple channels for trading alerts"""
    
    def __init__(self, config: ConfigManager, db: DatabaseManager, 
                 on_valid_futures_alert: Optional[Callable[[ParsedAlert, Dict[str, Any]], None]] = None,
                 on_valid_options_alert: Optional[Callable[[ParsedOptionsAlert, Dict[str, Any]], None]] = None):
        """
        Initialize Discord monitor
        
        Args:
            config: Configuration manager instance
            db: Database manager instance
            on_valid_futures_alert: Callback function for valid futures alerts
            on_valid_options_alert: Callback function for valid options alerts
        """
        self.config = config
        self.db = db
        self.futures_parser = AlertParser()
        self.options_parser = OptionsAlertParser()
        self.on_valid_futures_alert = on_valid_futures_alert
        self.on_valid_options_alert = on_valid_options_alert
        
        self.logger = logging.getLogger(__name__)
        self.client: Optional[discord.Client] = None
        self.is_running = False
        self.reconnect_attempts = 0
        
        # Statistics
        self.stats = {
            'messages_processed': 0,
            'valid_alerts': 0,
            'invalid_alerts': 0,
            'connection_errors': 0,
            'last_alert_time': None
        }
    
    async def start_monitoring(self) -> bool:
        """Start Discord monitoring"""
        try:
            if not self.config.discord or not self.config.discord.token:
                self.logger.error("Discord configuration not available")
                return False
            
            # Set up Discord client with intents
            intents = discord.Intents.default()
            intents.message_content = True  # Required to read message content
            
            self.client = discord.Client(intents=intents)
            
            # Set up event handlers
            self._setup_event_handlers()
            
            # Start the bot
            self.logger.info("Starting Discord monitoring...")
            await self.client.start(self.config.discord.token)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting Discord monitor: {e}")
            return False
    
    async def stop_monitoring(self):
        """Stop Discord monitoring"""
        try:
            self.is_running = False
            if self.client and not self.client.is_closed():
                await self.client.close()
            self.logger.info("Discord monitoring stopped")
        except Exception as e:
            self.logger.error(f"Error stopping Discord monitor: {e}")
    
    def _setup_event_handlers(self):
        """Set up Discord client event handlers"""
        
        @self.client.event
        async def on_ready():
            """Called when the bot is ready"""
            self.logger.info(f"Discord bot logged in as {self.client.user}")
            self.is_running = True
            self.reconnect_attempts = 0
            
            # Log connection to database
            self.db.log_system_event(
                level="INFO",
                component="discord_monitor",
                message="Discord bot connected successfully",
                details=f"User: {self.client.user}"
            )
        
        @self.client.event
        async def on_disconnect():
            """Called when the bot disconnects"""
            self.logger.warning("Discord bot disconnected")
            self.is_running = False
            
            self.db.log_system_event(
                level="WARNING",
                component="discord_monitor", 
                message="Discord bot disconnected"
            )
        
        @self.client.event
        async def on_error(event, *args, **kwargs):
            """Called when an error occurs"""
            self.logger.error(f"Discord error in {event}: {args}")
            self.stats['connection_errors'] += 1
            
            self.db.log_system_event(
                level="ERROR",
                component="discord_monitor",
                message=f"Discord error in {event}",
                details=str(args)
            )
        
        @self.client.event
        async def on_message(message):
            """Called when a message is received"""
            await self._handle_message(message)
    
    async def _handle_message(self, message: discord.Message):
        """Handle incoming Discord messages from multiple channels"""
        try:
            # Skip messages from the bot itself
            if message.author == self.client.user:
                return
            
            # Check if message is from one of our monitored channels
            channel_name = self._get_channel_name(message.channel.id)
            if not channel_name:
                return
            
            # Check if message is from one of our target authors
            if not self._is_target_author(message.author.display_name):
                return
            
            # Route message to appropriate parser based on channel
            if channel_name == "TWI_Futures":
                await self._handle_futures_message(message, channel_name)
            elif channel_name == "TWI_Options":
                await self._handle_options_message(message, channel_name)
            else:
                # Log all messages for monitoring
                await self._log_message(message, channel_name)
                return
            
            self.stats['messages_processed'] += 1
            
            self.logger.info(f"Processing message from {message.author.display_name}: {message.content[:100]}...")
            
            # Parse the message
            parsed_alert = self.parser.parse_message(
                message_content=message.content,
                author=message.author.display_name
            )
            
            # Store alert in database
            alert_id = self.db.insert_alert(
                discord_message_id=str(message.id),
                author=message.author.display_name,
                channel_id=message.channel.id,
                raw_content=message.content,
                parsed_price=parsed_alert.price,
                parsed_size=parsed_alert.size,
                parsed_stop=parsed_alert.stop,
                target_1=parsed_alert.target_1,
                target_2=parsed_alert.target_2,
                is_valid=parsed_alert.is_valid
            )
            
            if parsed_alert.is_valid:
                self.stats['valid_alerts'] += 1
                self.stats['last_alert_time'] = datetime.now(timezone.utc)
                
                self.logger.info(f"Valid alert detected: {self.parser.format_alert_summary(parsed_alert)}")
                
                # Log successful parse
                self.db.log_system_event(
                    level="INFO",
                    component="discord_monitor",
                    message="Valid trading alert detected",
                    details=self.parser.format_alert_summary(parsed_alert),
                    alert_id=alert_id
                )
                
                # Call callback if provided
                if self.on_valid_alert:
                    message_data = {
                        'message_id': str(message.id),
                        'author': message.author.display_name,
                        'channel_id': message.channel.id,
                        'timestamp': message.created_at,
                        'alert_id': alert_id
                    }
                    
                    try:
                        await self._safe_callback(parsed_alert, message_data)
                    except Exception as e:
                        self.logger.error(f"Error in alert callback: {e}")
            else:
                self.stats['invalid_alerts'] += 1
                self.logger.warning(f"Invalid alert: {parsed_alert.error_message}")
                
                # Log invalid parse
                self.db.log_system_event(
                    level="WARNING",
                    component="discord_monitor",
                    message="Invalid trading alert detected",
                    details=f"Error: {parsed_alert.error_message}",
                    alert_id=alert_id
                )
        
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            self.stats['connection_errors'] += 1
    
    async def _safe_callback(self, alert: ParsedAlert, message_data: Dict[str, Any]):
        """Safely execute callback function"""
        try:
            if asyncio.iscoroutinefunction(self.on_valid_alert):
                await self.on_valid_alert(alert, message_data)
            else:
                self.on_valid_alert(alert, message_data)
        except Exception as e:
            self.logger.error(f"Callback execution error: {e}")
            raise
    
    async def reconnect(self) -> bool:
        """Attempt to reconnect to Discord"""
        if not self.config.discord:
            return False
        
        max_attempts = self.config.discord.reconnect_attempts
        delay = self.config.discord.reconnect_delay
        
        while self.reconnect_attempts < max_attempts:
            try:
                self.reconnect_attempts += 1
                self.logger.info(f"Reconnection attempt {self.reconnect_attempts}/{max_attempts}")
                
                await asyncio.sleep(delay)
                
                if self.client and not self.client.is_closed():
                    await self.client.close()
                
                # Create new client and restart
                intents = discord.Intents.default()
                intents.message_content = True
                self.client = discord.Client(intents=intents)
                self._setup_event_handlers()
                
                await self.client.start(self.config.discord.token)
                return True
                
            except Exception as e:
                self.logger.error(f"Reconnection attempt {self.reconnect_attempts} failed: {e}")
                
                if self.reconnect_attempts >= max_attempts:
                    self.logger.error("Max reconnection attempts reached")
                    break
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current monitor status"""
        return {
            'is_running': self.is_running,
            'is_connected': self.client and not self.client.is_closed() if self.client else False,
            'reconnect_attempts': self.reconnect_attempts,
            'stats': self.stats.copy(),
            'target_channel': self.config.discord.channel_id if self.config.discord else None,
            'target_author': self.config.discord.target_author if self.config.discord else None
        }
    
    def reset_stats(self):
        """Reset monitoring statistics"""
        self.stats = {
            'messages_processed': 0,
            'valid_alerts': 0,
            'invalid_alerts': 0,
            'connection_errors': 0,
            'last_alert_time': None
        }
        self.logger.info("Monitor statistics reset")


# Example usage
async def example_alert_handler(alert: ParsedAlert, message_data: Dict[str, Any]):
    """Example callback function for handling valid alerts"""
    print(f"New alert received!")
    print(f"Entry: {alert.price}, Size: {alert.size}, Stop: {alert.stop}")
    print(f"Targets: {alert.target_1}, {alert.target_2}")
    print(f"Message ID: {message_data['message_id']}")


async def main():
    """Example main function for testing"""
    try:
        from .config import config
        from .database import db
    except ImportError:
        from config import config
        from database import db
    
    # Initialize database
    if not db.initialize_database():
        print("Failed to initialize database")
        return
    
    # Load configuration
    if not config.load_config():
        print("Failed to load configuration")
        return
    
    # Create monitor
    monitor = DiscordMonitor(config, db, example_alert_handler)
    
    try:
        # Start monitoring
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        print("Stopping monitor...")
        await monitor.stop_monitoring()


if __name__ == "__main__":
    # Run example if script is executed directly
    asyncio.run(main())
