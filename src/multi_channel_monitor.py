"""
Multi-Channel Discord Monitor for TradeStream
Monitors multiple Discord channels for both futures and options trading alerts
Supports TWI_Futures and TWI_Options channels with different parsing logic
"""

import discord
import asyncio
import logging
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime

from .config import ConfigManager
from .message_parser import JMoneyMessageParser, ParsedAlert
from .options_parser import OptionsAlertParser, ParsedOptionsAlert
from .database import DatabaseManager


class MultiChannelDiscordMonitor:
    """Discord bot to monitor multiple channels for trading alerts"""
    
    def __init__(self, config: ConfigManager, db: DatabaseManager, 
                 on_valid_futures_alert: Optional[Callable[[ParsedAlert, Dict[str, Any]], None]] = None,
                 on_valid_options_alert: Optional[Callable[[ParsedOptionsAlert, Dict[str, Any]], None]] = None):
        """
        Initialize multi-channel Discord monitor
        
        Args:
            config: Configuration manager instance
            db: Database manager instance
            on_valid_futures_alert: Callback function for valid futures alerts
            on_valid_options_alert: Callback function for valid options alerts
        """
        self.config = config
        self.db = db
        self.futures_parser = JMoneyMessageParser()
        self.options_parser = OptionsAlertParser()
        self.on_valid_futures_alert = on_valid_futures_alert
        self.on_valid_options_alert = on_valid_options_alert
        
        self.logger = logging.getLogger(__name__)
        self.client: Optional[discord.Client] = None
        self.is_running = False
        self.reconnect_attempts = 0
        
        # Enhanced statistics for multi-channel monitoring
        self.stats = {
            'messages_processed': 0,
            'futures_alerts_valid': 0,
            'options_alerts_valid': 0,
            'invalid_alerts': 0,
            'connection_errors': 0,
            'last_futures_alert_time': None,
            'last_options_alert_time': None,
            'channels_monitored': list(self.config.discord.channels.keys()) if self.config.discord else []
        }
        
        # Channel mapping for easy lookup
        self.channel_map = {}
        if self.config.discord and self.config.discord.channels:
            for name, channel_id in self.config.discord.channels.items():
                self.channel_map[channel_id] = name
    
    async def start(self):
        """Start the Discord monitor"""
        if self.is_running:
            self.logger.warning("Discord monitor is already running")
            return
        
        if not self.config.discord or not self.config.discord.token:
            raise ValueError("Discord configuration not found or token missing")
        
        self.logger.info("Starting multi-channel Discord monitor...")
        
        # Create Discord client with intents
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        
        # Set up event handlers
        self._setup_event_handlers()
        
        try:
            # Start the bot
            await self.client.start(self.config.discord.token)
        except Exception as e:
            self.logger.error(f"Failed to start Discord bot: {str(e)}")
            self.is_running = False
            raise
    
    async def stop(self):
        """Stop the Discord monitor"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping multi-channel Discord monitor...")
        self.is_running = False
        
        if self.client:
            await self.client.close()
            self.client = None
        
        self.logger.info("Discord monitor stopped")
    
    def _setup_event_handlers(self):
        """Set up Discord event handlers"""
        
        @self.client.event
        async def on_ready():
            """Called when the bot is ready"""
            self.logger.info(f"Discord bot logged in as {self.client.user}")
            self.is_running = True
            self.reconnect_attempts = 0
            
            # Log monitored channels
            monitored_channels = []
            for channel_id in self.channel_map.keys():
                channel = self.client.get_channel(channel_id)
                if channel:
                    monitored_channels.append(f"{channel.name} ({channel_id})")
                else:
                    self.logger.warning(f"Could not find channel with ID: {channel_id}")
            
            self.logger.info(f"Monitoring channels: {', '.join(monitored_channels)}")
            
            # Log connection to database
            self.db.log_system_event(
                level="INFO",
                component="multi_channel_discord_monitor",
                message="Multi-channel Discord bot connected successfully",
                details=f"User: {self.client.user}, Channels: {monitored_channels}"
            )
        
        @self.client.event
        async def on_disconnect():
            """Called when the bot disconnects"""
            self.logger.warning("Discord bot disconnected")
            self.is_running = False
            
            self.db.log_system_event(
                level="WARNING",
                component="multi_channel_discord_monitor", 
                message="Multi-channel Discord bot disconnected"
            )
        
        @self.client.event
        async def on_error(event, *args, **kwargs):
            """Called when an error occurs"""
            self.logger.error(f"Discord error in {event}: {args}")
            self.stats['connection_errors'] += 1
            
            self.db.log_system_event(
                level="ERROR",
                component="multi_channel_discord_monitor",
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
                # Still log all messages for monitoring purposes
                await self._log_message(message, channel_name, is_target_author=False)
                return
            
            self.stats['messages_processed'] += 1
            
            # Route message to appropriate parser based on channel
            if channel_name == "TWI_Futures":
                await self._handle_futures_message(message, channel_name)
            elif channel_name == "TWI_Options":
                await self._handle_options_message(message, channel_name)
            else:
                # Log message from unknown channel type
                await self._log_message(message, channel_name, is_target_author=True)
            
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            self.stats['connection_errors'] += 1
    
    async def _handle_futures_message(self, message: discord.Message, channel_name: str):
        """Handle futures trading alerts from TWI_Futures channel"""
        try:
            # Parse the message for futures alert
            parsed_alert = self.futures_parser.parse_alert(
                message.content,
                message.author.display_name,
                message.created_at,
                channel_name
            )
            
            if parsed_alert and parsed_alert.is_valid:
                self.stats['futures_alerts_valid'] += 1
                self.stats['last_futures_alert_time'] = datetime.now()
                
                # Store alert in database
                alert_id = self.db.store_alert(
                    raw_content=message.content,
                    author=message.author.display_name,
                    channel=channel_name,
                    timestamp=message.created_at,
                    parsed_data=parsed_alert.__dict__,
                    is_valid=True
                )
                parsed_alert.alert_id = alert_id
                
                self.logger.info(f"Valid futures alert: {parsed_alert.symbol} {parsed_alert.trade_type}")
                
                # Call callback if provided
                if self.on_valid_futures_alert:
                    message_data = {
                        'id': message.id,
                        'channel_id': message.channel.id,
                        'channel_name': channel_name,
                        'author': message.author.display_name,
                        'timestamp': message.created_at,
                        'content': message.content
                    }
                    await self.on_valid_futures_alert(parsed_alert, message_data)
            else:
                self.stats['invalid_alerts'] += 1
                
                # Store invalid alert for analysis
                self.db.store_alert(
                    raw_content=message.content,
                    author=message.author.display_name,
                    channel=channel_name,
                    timestamp=message.created_at,
                    parsed_data=parsed_alert.__dict__ if parsed_alert else {},
                    is_valid=False
                )
                
                self.logger.debug(f"Invalid futures alert: {message.content}")
        
        except Exception as e:
            self.logger.error(f"Error processing futures message: {str(e)}")
            self.stats['invalid_alerts'] += 1
    
    async def _handle_options_message(self, message: discord.Message, channel_name: str):
        """Handle options trading alerts from TWI_Options channel"""
        try:
            # Parse the message for options alert
            parsed_alert = self.options_parser.parse_alert(
                message.content,
                message.author.display_name,
                message.created_at,
                channel_name
            )
            
            if parsed_alert and parsed_alert.is_valid:
                self.stats['options_alerts_valid'] += 1
                self.stats['last_options_alert_time'] = datetime.now()
                
                # Store alert in database (extend database to handle options)
                alert_id = self.db.store_alert(
                    raw_content=message.content,
                    author=message.author.display_name,
                    channel=channel_name,
                    timestamp=message.created_at,
                    parsed_data=parsed_alert.__dict__,
                    is_valid=True
                )
                parsed_alert.alert_id = alert_id
                
                self.logger.info(f"Valid options alert: {parsed_alert.option_symbol} {parsed_alert.action.value}")
                
                # Call callback if provided
                if self.on_valid_options_alert:
                    message_data = {
                        'id': message.id,
                        'channel_id': message.channel.id,
                        'channel_name': channel_name,
                        'author': message.author.display_name,
                        'timestamp': message.created_at,
                        'content': message.content
                    }
                    await self.on_valid_options_alert(parsed_alert, message_data)
            else:
                self.stats['invalid_alerts'] += 1
                
                # Store invalid alert for analysis
                self.db.store_alert(
                    raw_content=message.content,
                    author=message.author.display_name,
                    channel=channel_name,
                    timestamp=message.created_at,
                    parsed_data=parsed_alert.__dict__ if parsed_alert else {},
                    is_valid=False
                )
                
                self.logger.debug(f"Invalid options alert: {message.content}")
        
        except Exception as e:
            self.logger.error(f"Error processing options message: {str(e)}")
            self.stats['invalid_alerts'] += 1
    
    async def _log_message(self, message: discord.Message, channel_name: str, is_target_author: bool = True):
        """Log message for monitoring purposes"""
        try:
            # Store message in database for analysis
            self.db.log_system_event(
                level="INFO",
                component="multi_channel_discord_monitor",
                message=f"Message from {channel_name}",
                details={
                    'author': message.author.display_name,
                    'channel': channel_name,
                    'content': message.content,
                    'is_target_author': is_target_author,
                    'timestamp': message.created_at.isoformat()
                }
            )
        except Exception as e:
            self.logger.error(f"Error logging message: {str(e)}")
    
    def _get_channel_name(self, channel_id: int) -> Optional[str]:
        """Get channel name from channel ID"""
        return self.channel_map.get(channel_id)
    
    def _is_target_author(self, author_name: str) -> bool:
        """Check if author is one of our target authors"""
        if not self.config.discord or not self.config.discord.target_authors:
            return False
        
        author_lower = author_name.lower()
        for target_author in self.config.discord.target_authors:
            if target_author.lower() in author_lower or author_lower in target_author.lower():
                return True
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current monitor status"""
        return {
            'is_running': self.is_running,
            'is_connected': self.client and not self.client.is_closed() if self.client else False,
            'reconnect_attempts': self.reconnect_attempts,
            'stats': self.stats.copy(),
            'monitored_channels': self.channel_map,
            'target_authors': self.config.discord.target_authors if self.config.discord else []
        }
    
    def reset_stats(self):
        """Reset monitoring statistics"""
        self.stats = {
            'messages_processed': 0,
            'futures_alerts_valid': 0,
            'options_alerts_valid': 0,
            'invalid_alerts': 0,
            'connection_errors': 0,
            'last_futures_alert_time': None,
            'last_options_alert_time': None,
            'channels_monitored': list(self.config.discord.channels.keys()) if self.config.discord else []
        }
        self.logger.info("Multi-channel monitor statistics reset")


# Example usage
async def example_futures_alert_handler(alert: ParsedAlert, message_data: Dict[str, Any]):
    """Example callback function for handling valid futures alerts"""
    print(f"New futures alert: {alert.symbol} {alert.trade_type} @ {alert.parsed_price}")


async def example_options_alert_handler(alert: ParsedOptionsAlert, message_data: Dict[str, Any]):
    """Example callback function for handling valid options alerts"""
    print(f"New options alert: {alert.option_symbol} {alert.action.value} @ ${alert.price}")
