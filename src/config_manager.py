"""
Advanced Configuration Manager with Hot-Reloading
Enhanced configuration management for JMoney Discord Alert Trading System
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    from .config import ConfigManager
except ImportError:
    from config import ConfigManager


class ConfigFileHandler(FileSystemEventHandler):
    """Handle configuration file changes"""
    
    def __init__(self, config_manager: 'AdvancedConfigManager'):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
    
    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory and event.src_path.endswith('.yaml'):
            self.logger.info(f"📋 Configuration file changed: {event.src_path}")
            asyncio.create_task(self.config_manager.reload_config())


class AdvancedConfigManager:
    """Advanced configuration manager with hot-reloading and validation"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.config_path = Path(config_file)
        self.logger = logging.getLogger(__name__)
        
        # Core config manager
        self.config = ConfigManager(config_file)
        
        # Hot-reload settings
        self.hot_reload_enabled = True
        self.last_modified = 0
        self.observer: Optional[Observer] = None
        
        # Callbacks for config changes
        self.change_callbacks: Dict[str, Callable] = {}
        
        # Non-critical settings that can be hot-reloaded
        self.hot_reloadable_settings = {
            'logging.level',
            'trading.max_daily_trades',
            'trading.max_position_size',
            'risk.max_loss_per_trade',
            'risk.daily_loss_limit',
            'email.send_alert_confirmations',
            'email.send_trade_executions',
            'email.send_daily_summaries',
            'trading.paper_trading.commission_per_contract',
            'trading.paper_trading.slippage_ticks'
        }
        
        # Critical settings that require restart
        self.critical_settings = {
            'discord.token',
            'discord.channel_id',
            'trading.account_id',
            'trading.symbol',
            'trading.enable_auto_trading',
            'trading.paper_trading_enabled',
            'trading.live_trading_enabled',
            'database.file_path'
        }
    
    async def initialize(self) -> bool:
        """Initialize the advanced config manager"""
        try:
            # Load initial configuration
            if not self.config.load_config():
                self.logger.error("❌ Failed to load initial configuration")
                return False
            
            if not self.config.validate_config():
                self.logger.error("❌ Initial configuration validation failed")
                return False
            
            # Setup file watching for hot-reload
            if self.hot_reload_enabled:
                await self._setup_file_watcher()
            
            # Update size mapping based on user preference
            await self._update_size_mapping()
            
            self.logger.info("✅ Advanced configuration manager initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize config manager: {e}")
            return False
    
    async def _setup_file_watcher(self):
        """Setup file watcher for hot-reload"""
        try:
            self.observer = Observer()
            handler = ConfigFileHandler(self)
            
            # Watch the directory containing the config file
            watch_dir = self.config_path.parent if self.config_path.parent.exists() else Path('.')
            self.observer.schedule(handler, str(watch_dir), recursive=False)
            self.observer.start()
            
            self.logger.info(f"📁 Watching config directory: {watch_dir}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to setup file watcher: {e}")
    
    async def _update_size_mapping(self):
        """Update size mapping based on user preference (C size, B=2*C, A=3*C)"""
        try:
            if not self.config.trading:
                return
            
            # Get current size mapping
            current_mapping = self.config.trading.size_mapping
            
            # Check if we need to update based on C size
            c_size = current_mapping.get('C', 3)
            expected_b_size = c_size * 2
            expected_a_size = c_size * 3
            
            # Update if needed
            updated = False
            if current_mapping.get('B') != expected_b_size:
                current_mapping['B'] = expected_b_size
                updated = True
            
            if current_mapping.get('A') != expected_a_size:
                current_mapping['A'] = expected_a_size
                updated = True
            
            if updated:
                self.logger.info(f"📊 Updated size mapping: A={expected_a_size}, B={expected_b_size}, C={c_size}")
                
                # Notify callbacks
                await self._notify_callbacks('trading.size_mapping', current_mapping)
            
        except Exception as e:
            self.logger.error(f"❌ Error updating size mapping: {e}")
    
    async def reload_config(self):
        """Reload configuration with hot-reload support"""
        try:
            # Check if file was actually modified
            current_modified = os.path.getmtime(self.config_file)
            if current_modified <= self.last_modified:
                return
            
            self.last_modified = current_modified
            
            # Load new configuration
            new_config = ConfigManager(self.config_file)
            if not new_config.load_config():
                self.logger.error("❌ Failed to reload configuration - keeping current config")
                return
            
            if not new_config.validate_config():
                self.logger.error("❌ New configuration validation failed - keeping current config")
                return
            
            # Compare configurations to determine what changed
            changes = await self._detect_changes(self.config, new_config)
            
            # Check if any critical settings changed
            critical_changes = [change for change in changes if change in self.critical_settings]
            
            if critical_changes:
                self.logger.warning(f"⚠️ Critical settings changed: {critical_changes}")
                self.logger.warning("🔄 System restart required for these changes to take effect")
                
                # Log critical changes but don't apply them
                for change in critical_changes:
                    self.logger.warning(f"   • {change}: restart required")
            
            # Apply hot-reloadable changes
            hot_reload_changes = [change for change in changes if change in self.hot_reloadable_settings]
            
            if hot_reload_changes:
                self.logger.info(f"🔄 Hot-reloading settings: {hot_reload_changes}")
                
                # Update current config with hot-reloadable changes
                await self._apply_hot_reload_changes(new_config, hot_reload_changes)
                
                # Notify callbacks
                for change in hot_reload_changes:
                    await self._notify_callbacks(change, self._get_setting_value(new_config, change))
            
            # Update size mapping
            await self._update_size_mapping()
            
            if changes:
                self.logger.info("✅ Configuration reloaded successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Error reloading configuration: {e}")
    
    async def _detect_changes(self, old_config: ConfigManager, new_config: ConfigManager) -> list:
        """Detect changes between old and new configuration"""
        changes = []
        
        try:
            # Compare trading settings
            if old_config.trading and new_config.trading:
                if old_config.trading.max_daily_trades != new_config.trading.max_daily_trades:
                    changes.append('trading.max_daily_trades')
                if old_config.trading.max_position_size != new_config.trading.max_position_size:
                    changes.append('trading.max_position_size')
                if old_config.trading.enable_auto_trading != new_config.trading.enable_auto_trading:
                    changes.append('trading.enable_auto_trading')
                if old_config.trading.size_mapping != new_config.trading.size_mapping:
                    changes.append('trading.size_mapping')
            
            # Compare risk settings
            if old_config.risk and new_config.risk:
                if old_config.risk.max_loss_per_trade != new_config.risk.max_loss_per_trade:
                    changes.append('risk.max_loss_per_trade')
                if old_config.risk.daily_loss_limit != new_config.risk.daily_loss_limit:
                    changes.append('risk.daily_loss_limit')
            
            # Compare email settings
            if old_config.email and new_config.email:
                if old_config.email.send_alert_confirmations != new_config.email.send_alert_confirmations:
                    changes.append('email.send_alert_confirmations')
                if old_config.email.send_trade_executions != new_config.email.send_trade_executions:
                    changes.append('email.send_trade_executions')
                if old_config.email.send_daily_summaries != new_config.email.send_daily_summaries:
                    changes.append('email.send_daily_summaries')
            
            # Compare logging settings
            if old_config.logging and new_config.logging:
                if old_config.logging.level != new_config.logging.level:
                    changes.append('logging.level')
            
        except Exception as e:
            self.logger.error(f"Error detecting changes: {e}")
        
        return changes
    
    async def _apply_hot_reload_changes(self, new_config: ConfigManager, changes: list):
        """Apply hot-reloadable changes to current configuration"""
        try:
            for change in changes:
                if change.startswith('trading.'):
                    if change == 'trading.max_daily_trades':
                        self.config.trading.max_daily_trades = new_config.trading.max_daily_trades
                    elif change == 'trading.max_position_size':
                        self.config.trading.max_position_size = new_config.trading.max_position_size
                    elif change == 'trading.size_mapping':
                        self.config.trading.size_mapping = new_config.trading.size_mapping
                
                elif change.startswith('risk.'):
                    if change == 'risk.max_loss_per_trade':
                        self.config.risk.max_loss_per_trade = new_config.risk.max_loss_per_trade
                    elif change == 'risk.daily_loss_limit':
                        self.config.risk.daily_loss_limit = new_config.risk.daily_loss_limit
                
                elif change.startswith('email.'):
                    if change == 'email.send_alert_confirmations':
                        self.config.email.send_alert_confirmations = new_config.email.send_alert_confirmations
                    elif change == 'email.send_trade_executions':
                        self.config.email.send_trade_executions = new_config.email.send_trade_executions
                    elif change == 'email.send_daily_summaries':
                        self.config.email.send_daily_summaries = new_config.email.send_daily_summaries
                
                elif change.startswith('logging.'):
                    if change == 'logging.level':
                        self.config.logging.level = new_config.logging.level
                        # Update logger level
                        logging.getLogger().setLevel(getattr(logging, new_config.logging.level.upper()))
            
        except Exception as e:
            self.logger.error(f"Error applying hot-reload changes: {e}")
    
    def _get_setting_value(self, config: ConfigManager, setting_path: str) -> Any:
        """Get setting value by path"""
        try:
            parts = setting_path.split('.')
            obj = config
            
            for part in parts:
                obj = getattr(obj, part)
            
            return obj
            
        except Exception:
            return None
    
    def register_change_callback(self, setting_path: str, callback: Callable):
        """Register callback for configuration changes"""
        self.change_callbacks[setting_path] = callback
        self.logger.info(f"📋 Registered callback for {setting_path}")
    
    async def _notify_callbacks(self, setting_path: str, new_value: Any):
        """Notify callbacks of configuration changes"""
        try:
            if setting_path in self.change_callbacks:
                callback = self.change_callbacks[setting_path]
                if asyncio.iscoroutinefunction(callback):
                    await callback(setting_path, new_value)
                else:
                    callback(setting_path, new_value)
                
                self.logger.info(f"📋 Notified callback for {setting_path}")
            
        except Exception as e:
            self.logger.error(f"Error notifying callback for {setting_path}: {e}")
    
    def get_config(self) -> ConfigManager:
        """Get current configuration"""
        return self.config
    
    def update_size_mapping_from_c_size(self, c_size: int):
        """Update size mapping based on C size (B=2*C, A=3*C)"""
        try:
            if not self.config.trading:
                return
            
            self.config.trading.size_mapping['C'] = c_size
            self.config.trading.size_mapping['B'] = c_size * 2
            self.config.trading.size_mapping['A'] = c_size * 3
            
            self.logger.info(f"📊 Size mapping updated: A={c_size*3}, B={c_size*2}, C={c_size}")
            
        except Exception as e:
            self.logger.error(f"Error updating size mapping: {e}")
    
    async def shutdown(self):
        """Shutdown the config manager"""
        try:
            if self.observer:
                self.observer.stop()
                self.observer.join()
            
            self.logger.info("✅ Advanced configuration manager shutdown")
            
        except Exception as e:
            self.logger.error(f"Error during config manager shutdown: {e}")


# Global instance (will be initialized by main application)
advanced_config_manager: Optional[AdvancedConfigManager] = None
