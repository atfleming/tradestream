#!/usr/bin/env python3
"""
JMoney Discord Alert Trading System - Main Application
Integrates all components for automated MES trading with paper/live modes
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.config import ConfigManager
from src.database import DatabaseManager
from src.message_parser import JMoneyMessageParser
from src.discord_monitor import DiscordMonitor
from src.tsx_integration import TopStepXIntegration
from src.paper_trading import PaperTradingSimulator
from src.trade_executor import TradeExecutor
from src.email_notifier import EmailNotifier
from src.trade_tracker import TradeTracker
from src.status_dashboard import StatusDashboard
from src.config_manager import AdvancedConfigManager
from src.risk_manager import RiskManager
from src.backup_system import BackupSystem
from src.health_monitor import HealthMonitor


class JMoneyTradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(self, config_file: str = "config.yaml"):
        """Initialize the trading bot"""
        self.config_file = config_file
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.config: Optional[ConfigManager] = None
        self.advanced_config: Optional[AdvancedConfigManager] = None
        self.db: Optional[DatabaseManager] = None
        self.parser: Optional[JMoneyMessageParser] = None
        self.discord_monitor: Optional[DiscordMonitor] = None
        self.email_notifier: Optional[EmailNotifier] = None
        
        # Trading components
        self.paper_trader: Optional[PaperTradingSimulator] = None
        self.tsx_api: Optional[TopStepXIntegration] = None
        self.trade_executor: Optional[TradeExecutor] = None
        
        # Phase 3 components - Tracking and Monitoring
        self.trade_tracker: Optional[TradeTracker] = None
        self.status_dashboard: Optional[StatusDashboard] = None
        
        # Phase 4 components - Enhancement and Optimization
        self.risk_manager: Optional[RiskManager] = None
        self.backup_system: Optional[BackupSystem] = None
        self.health_monitor: Optional[HealthMonitor] = None
        
        # System state
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
    async def initialize(self) -> bool:
        """Initialize all components"""
        try:
            self.logger.info("🚀 Initializing JMoney Trading Bot...")
            self.logger.info("=" * 60)
            
            # 1. Load configuration with hot-reload support
            self.logger.info("📋 Loading configuration...")
            self.advanced_config = AdvancedConfigManager(self.config_file)
            if not await self.advanced_config.initialize():
                self.logger.error("❌ Failed to initialize advanced configuration")
                return False
            
            self.config = self.advanced_config.get_config()
            self.logger.info("✅ Configuration loaded with hot-reload support")
            
            # 2. Initialize database
            self.logger.info("🗄️ Initializing database...")
            self.db = DatabaseManager(self.config)
            if not self.db.initialize_database():
                self.logger.error("❌ Failed to initialize database")
                return False
            
            self.logger.info("✅ Database initialized")
            
            # 3. Initialize message parser
            self.logger.info("📝 Initializing message parser...")
            self.parser = JMoneyMessageParser()
            self.logger.info("✅ Message parser initialized")
            
            # 4. Initialize email notifier (if enabled)
            if self.config.email and self.config.email.enabled:
                self.logger.info("📧 Initializing email notifier...")
                self.email_notifier = EmailNotifier(self.config, self.db)
                if not await self.email_notifier.initialize():
                    self.logger.warning("⚠️ Email notifier initialization failed")
                else:
                    self.logger.info("✅ Email notifier initialized")
            
            # 5. Initialize trading systems based on configuration
            await self._initialize_trading_systems()
            
            # 6. Initialize trade executor
            self.logger.info("⚙️ Initializing trade executor...")
            self.trade_executor = TradeExecutor(
                config=self.config,
                db=self.db,
                tsx_api=self.tsx_api,
                paper_trader=self.paper_trader,
                email_notifier=self.email_notifier
            )
            
            if not await self.trade_executor.initialize():
                self.logger.error("❌ Failed to initialize trade executor")
                return False
            
            self.logger.info("✅ Trade executor initialized")
            
            # 7. Initialize Discord monitor
            self.logger.info("🤖 Initializing Discord monitor...")
            self.discord_monitor = DiscordMonitor(
                config=self.config,
                db=self.db,
                parser=self.parser,
                alert_callback=self._handle_trading_alert
            )
            
            if not await self.discord_monitor.initialize():
                self.logger.error("❌ Failed to initialize Discord monitor")
                return False
            
            self.logger.info("✅ Discord monitor initialized")
            
            # 8. Initialize Phase 3 components - Tracking and Monitoring
            await self._initialize_phase3_components()
            
            # 9. Initialize Phase 4 components - Enhancement and Optimization
            await self._initialize_phase4_components()
            
            # 10. Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            self.logger.info("=" * 60)
            self.logger.info("🎉 JMoney Trading Bot initialized successfully!")
            self._log_system_status()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize trading bot: {e}")
            return False
    
    async def _initialize_trading_systems(self):
        """Initialize trading systems based on configuration"""
        if not self.config.trading:
            self.logger.warning("⚠️ No trading configuration found")
            return
        
        # Initialize paper trading if enabled
        if self.config.trading.paper_trading_enabled:
            self.logger.info("🎯 Initializing paper trading simulator...")
            self.paper_trader = PaperTradingSimulator(self.config, self.db)
            if not await self.paper_trader.initialize():
                self.logger.error("❌ Failed to initialize paper trading")
            else:
                self.logger.info("✅ Paper trading simulator initialized")
        
        # Initialize live trading if enabled
        if self.config.trading.live_trading_enabled:
            self.logger.info("🚀 Initializing live trading (TopStepX API)...")
            self.tsx_api = TopStepXIntegration(self.config, self.db)
            if not await self.tsx_api.initialize():
                self.logger.error("❌ Failed to initialize TopStepX API")
            else:
                self.logger.info("✅ TopStepX API initialized")
        
        # Validate trading mode configuration
        if not self.config.trading.paper_trading_enabled and not self.config.trading.live_trading_enabled:
            self.logger.warning("⚠️ No trading modes enabled - bot will only log alerts")
        elif self.config.trading.concurrent_trading and self.paper_trader and self.tsx_api:
            self.logger.info("⚡ Concurrent trading mode: Both paper and live trading enabled")
    
    async def _handle_trading_alert(self, alert, message_data):
        """Handle incoming trading alerts from Discord"""
        try:
            self.logger.info(f"📢 New trading alert received: {alert.size} @ {alert.price}")
            
            # Execute the alert through trade executor
            if self.trade_executor:
                success = await self.trade_executor.execute_alert(alert)
                if success:
                    self.logger.info("✅ Alert execution initiated successfully")
                else:
                    self.logger.warning("⚠️ Alert execution failed or skipped")
            else:
                self.logger.warning("⚠️ Trade executor not available - alert logged only")
            
        except Exception as e:
            self.logger.error(f"❌ Error handling trading alert: {e}")
    
    async def _initialize_phase3_components(self):
        """Initialize Phase 3 tracking and monitoring components"""
        try:
            self.logger.info("📊 Initializing Phase 3 components...")
            
            # Initialize trade tracker
            self.logger.info("📈 Initializing trade tracker...")
            self.trade_tracker = TradeTracker(self.config, self.db)
            self.logger.info("✅ Trade tracker initialized")
            
            # Initialize status dashboard
            self.logger.info("📊 Initializing status dashboard...")
            self.status_dashboard = StatusDashboard(
                config=self.config,
                db=self.db,
                trade_tracker=self.trade_tracker,
                trade_executor=self.trade_executor,
                paper_trader=self.paper_trader,
                tsx_api=self.tsx_api
            )
            self.logger.info("✅ Status dashboard initialized")
            
            # Register configuration change callbacks
            if self.advanced_config:
                self.advanced_config.register_change_callback(
                    'trading.size_mapping',
                    self._on_size_mapping_changed
                )
                self.logger.info("✅ Configuration callbacks registered")
            
            self.logger.info("✅ Phase 3 components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Phase 3 components: {e}")
    
    async def _on_size_mapping_changed(self, setting_path: str, new_value: dict):
        """Handle size mapping configuration changes"""
        try:
            self.logger.info(f"📊 Size mapping updated: {new_value}")
            
            # Update trade executor if available
            if self.trade_executor:
                # Trade executor will use the updated config automatically
                self.logger.info("✅ Trade executor will use new size mapping")
            
        except Exception as e:
            self.logger.error(f"Error handling size mapping change: {e}")
    
    async def _initialize_phase4_components(self):
        """Initialize Phase 4 enhancement and optimization components"""
        try:
            self.logger.info("🚀 Initializing Phase 4 components...")
            
            # Initialize risk manager
            self.logger.info("📈 Initializing risk manager...")
            self.risk_manager = RiskManager(self.config, self.db, self.trade_tracker)
            self.logger.info("✅ Risk manager initialized")
            
            # Initialize backup system
            self.logger.info("💾 Initializing backup system...")
            self.backup_system = BackupSystem(self.config, self.db)
            if await self.backup_system.initialize():
                self.logger.info("✅ Backup system initialized")
            else:
                self.logger.warning("⚠️ Backup system initialization failed")
            
            # Initialize health monitor
            self.logger.info("🏥 Initializing health monitor...")
            self.health_monitor = HealthMonitor(self.config, self.db, self.email_notifier)
            if await self.health_monitor.initialize():
                self.logger.info("✅ Health monitor initialized")
            else:
                self.logger.warning("⚠️ Health monitor initialization failed")
            
            # Update status dashboard with Phase 4 components
            if self.status_dashboard:
                # The dashboard will automatically pick up the new components
                self.logger.info("✅ Status dashboard updated with Phase 4 components")
            
            self.logger.info("✅ Phase 4 components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Phase 4 components: {e}")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"📡 Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _log_system_status(self):
        """Log current system status and configuration"""
        self.logger.info("📊 System Status:")
        self.logger.info(f"   • Configuration File: {self.config_file}")
        self.logger.info(f"   • Database: {self.config.database.file_path if self.config.database else 'Not configured'}")
        
        if self.config.trading:
            self.logger.info(f"   • Trading Symbol: {self.config.trading.symbol}")
            self.logger.info(f"   • Paper Trading: {'✅ Enabled' if self.config.trading.paper_trading_enabled else '❌ Disabled'}")
            self.logger.info(f"   • Live Trading: {'✅ Enabled' if self.config.trading.live_trading_enabled else '❌ Disabled'}")
            self.logger.info(f"   • Auto Trading: {'✅ Enabled' if self.config.trading.enable_auto_trading else '❌ Disabled'}")
        
        if self.config.discord:
            self.logger.info(f"   • Discord Channel: {self.config.discord.channel_id}")
            self.logger.info(f"   • Target Author: {self.config.discord.target_author}")
        
        if self.config.email:
            self.logger.info(f"   • Email Notifications: {'✅ Enabled' if self.config.email.enabled else '❌ Disabled'}")
    
    async def run(self, show_dashboard: bool = True):
        """Main application loop"""
        try:
            self.is_running = True
            self.logger.info("🔄 Starting main application loop...")
            
            # Start status dashboard if requested
            dashboard_task = None
            if show_dashboard and self.status_dashboard:
                self.logger.info("📊 Starting status dashboard...")
                dashboard_task = asyncio.create_task(self.status_dashboard.start())
            
            # Start Discord monitoring
            if self.discord_monitor:
                await self.discord_monitor.start()
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Stop dashboard if running
            if dashboard_task and not dashboard_task.done():
                self.status_dashboard.stop()
                try:
                    await asyncio.wait_for(dashboard_task, timeout=5.0)
                except asyncio.TimeoutError:
                    dashboard_task.cancel()
            
        except Exception as e:
            self.logger.error(f"❌ Error in main application loop: {e}")
        finally:
            self.is_running = False
    
    async def shutdown(self):
        """Graceful shutdown of all components"""
        try:
            self.logger.info("🛑 Initiating graceful shutdown...")
            
            # Stop Discord monitoring
            if self.discord_monitor:
                await self.discord_monitor.stop()
                self.logger.info("✅ Discord monitor stopped")
            
            # Stop Phase 4 components
            if self.health_monitor:
                # Health monitor doesn't need explicit shutdown
                self.logger.info("✅ Health monitor stopped")
            
            if self.backup_system:
                # Backup system doesn't need explicit shutdown
                self.logger.info("✅ Backup system stopped")
            
            # Stop Phase 3 components
            if self.status_dashboard:
                self.status_dashboard.stop()
                self.logger.info("✅ Status dashboard stopped")
            
            if self.advanced_config:
                await self.advanced_config.shutdown()
                self.logger.info("✅ Advanced configuration manager shutdown")
            
            # Shutdown trade executor
            if self.trade_executor:
                await self.trade_executor.shutdown()
                self.logger.info("✅ Trade executor shutdown")
            
            # Disconnect trading systems
            if self.tsx_api:
                await self.tsx_api.disconnect()
                self.logger.info("✅ TopStepX API disconnected")
            
            if self.paper_trader:
                await self.paper_trader.disconnect()
                self.logger.info("✅ Paper trading simulator disconnected")
            
            # Close database connection
            if self.db:
                self.db.close()
                self.logger.info("✅ Database connection closed")
            
            # Signal shutdown complete
            self.shutdown_event.set()
            self.logger.info("🏁 Shutdown complete")
            
        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}")
    
    async def get_status(self) -> dict:
        """Get current system status"""
        status = {
            'is_running': self.is_running,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'components': {
                'config': self.config is not None,
                'database': self.db is not None,
                'discord_monitor': self.discord_monitor is not None,
                'trade_executor': self.trade_executor is not None,
                'paper_trader': self.paper_trader is not None,
                'tsx_api': self.tsx_api is not None,
                'email_notifier': self.email_notifier is not None
            }
        }
        
        # Add trading statistics if available
        if self.trade_executor:
            status['trading'] = {
                'active_positions': len(self.trade_executor.get_active_positions()),
                'daily_pnl': self.trade_executor.get_daily_pnl(),
                'daily_trades': self.trade_executor.get_daily_trade_count()
            }
        
        # Add paper trading statistics if available
        if self.paper_trader:
            status['paper_trading'] = self.paper_trader.get_paper_statistics()
        
        return status


async def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/trading_bot.log', mode='a')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Create logs directory if it doesn't exist
        Path("logs").mkdir(exist_ok=True)
        
        logger.info("🚀 Starting JMoney Discord Alert Trading System")
        logger.info(f"📅 Started at: {datetime.now(timezone.utc)}")
        
        # Initialize and run the trading bot
        bot = JMoneyTradingBot()
        
        if await bot.initialize():
            await bot.run()
        else:
            logger.error("❌ Failed to initialize trading bot")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("👋 Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        logger.info("🏁 JMoney Trading Bot terminated")


if __name__ == "__main__":
    # Run the main application
    asyncio.run(main())
