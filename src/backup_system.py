"""
Backup and Recovery System for JMoney Discord Alert Trading System
Automated backup, data integrity, and disaster recovery capabilities
"""

import asyncio
import logging
import os
import shutil
import sqlite3
import json
import gzip
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

try:
    from .config import ConfigManager
    from .database import DatabaseManager
except ImportError:
    from config import ConfigManager
    from database import DatabaseManager


class BackupSystem:
    """Comprehensive backup and recovery system"""
    
    def __init__(self, config: ConfigManager, db: DatabaseManager):
        """Initialize backup system"""
        self.config = config
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # Backup configuration
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Backup retention policy
        self.daily_backups_keep = 30  # Keep 30 daily backups
        self.weekly_backups_keep = 12  # Keep 12 weekly backups
        self.monthly_backups_keep = 12  # Keep 12 monthly backups
        
        # Backup scheduling
        self.backup_interval_hours = 6  # Backup every 6 hours
        self.last_backup_time = None
        
        # Data integrity
        self.integrity_check_interval = 24  # Check integrity every 24 hours
        self.last_integrity_check = None
    
    async def initialize(self) -> bool:
        """Initialize backup system"""
        try:
            self.logger.info("🔄 Initializing backup system...")
            
            # Create backup directories
            (self.backup_dir / "daily").mkdir(exist_ok=True)
            (self.backup_dir / "weekly").mkdir(exist_ok=True)
            (self.backup_dir / "monthly").mkdir(exist_ok=True)
            (self.backup_dir / "emergency").mkdir(exist_ok=True)
            
            # Perform initial backup
            await self.create_backup("initialization")
            
            # Start background backup scheduler
            asyncio.create_task(self._backup_scheduler())
            
            self.logger.info("✅ Backup system initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize backup system: {e}")
            return False
    
    async def create_backup(self, backup_type: str = "manual") -> Optional[str]:
        """Create a comprehensive system backup"""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_name = f"jmoney_backup_{backup_type}_{timestamp}"
            backup_path = self.backup_dir / f"{backup_name}.tar.gz"
            
            self.logger.info(f"📦 Creating backup: {backup_name}")
            
            # Create temporary directory for backup staging
            temp_dir = self.backup_dir / f"temp_{timestamp}"
            temp_dir.mkdir(exist_ok=True)
            
            try:
                # Backup database
                await self._backup_database(temp_dir)
                
                # Backup configuration files
                await self._backup_configuration(temp_dir)
                
                # Backup logs
                await self._backup_logs(temp_dir)
                
                # Create backup metadata
                await self._create_backup_metadata(temp_dir, backup_type)
                
                # Create compressed archive
                await self._create_compressed_archive(temp_dir, backup_path)
                
                # Verify backup integrity
                if await self._verify_backup_integrity(backup_path):
                    self.logger.info(f"✅ Backup created successfully: {backup_path}")
                    self.last_backup_time = datetime.now(timezone.utc)
                    
                    # Clean up old backups
                    await self._cleanup_old_backups()
                    
                    return str(backup_path)
                else:
                    self.logger.error(f"❌ Backup integrity verification failed: {backup_path}")
                    return None
                
            finally:
                # Clean up temporary directory
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create backup: {e}")
            return None
    
    async def _backup_database(self, temp_dir: Path):
        """Backup database with integrity checks"""
        try:
            db_backup_dir = temp_dir / "database"
            db_backup_dir.mkdir(exist_ok=True)
            
            # Get database file path
            db_file = Path(self.config.database.file_path)
            
            if db_file.exists():
                # Create database backup
                backup_file = db_backup_dir / "trading_bot.db"
                
                # Use SQLite backup API for consistent backup
                source_conn = sqlite3.connect(str(db_file))
                backup_conn = sqlite3.connect(str(backup_file))
                
                source_conn.backup(backup_conn)
                
                source_conn.close()
                backup_conn.close()
                
                # Create database schema dump
                schema_file = db_backup_dir / "schema.sql"
                await self._dump_database_schema(db_file, schema_file)
                
                # Create data export (JSON format)
                data_file = db_backup_dir / "data.json"
                await self._export_database_data(db_file, data_file)
                
                self.logger.info("✅ Database backup completed")
            else:
                self.logger.warning("⚠️ Database file not found for backup")
                
        except Exception as e:
            self.logger.error(f"❌ Database backup failed: {e}")
            raise
    
    async def _backup_configuration(self, temp_dir: Path):
        """Backup configuration files"""
        try:
            config_backup_dir = temp_dir / "configuration"
            config_backup_dir.mkdir(exist_ok=True)
            
            # Backup main config files
            config_files = ["config.yaml", "config_test.yaml"]
            
            for config_file in config_files:
                if Path(config_file).exists():
                    shutil.copy2(config_file, config_backup_dir / config_file)
            
            # Backup environment variables (without sensitive data)
            env_backup = {
                "BACKUP_TIMESTAMP": datetime.now(timezone.utc).isoformat(),
                "PYTHON_VERSION": os.sys.version,
                "SYSTEM_INFO": {
                    "platform": os.name,
                    "cwd": os.getcwd()
                }
            }
            
            with open(config_backup_dir / "environment.json", "w") as f:
                json.dump(env_backup, f, indent=2)
            
            self.logger.info("✅ Configuration backup completed")
            
        except Exception as e:
            self.logger.error(f"❌ Configuration backup failed: {e}")
            raise
    
    async def _backup_logs(self, temp_dir: Path):
        """Backup recent log files"""
        try:
            logs_backup_dir = temp_dir / "logs"
            logs_backup_dir.mkdir(exist_ok=True)
            
            # Look for log files
            log_patterns = ["*.log", "logs/*.log", "*.log.*"]
            
            for pattern in log_patterns:
                for log_file in Path(".").glob(pattern):
                    if log_file.is_file():
                        # Only backup recent logs (last 7 days)
                        if (datetime.now().timestamp() - log_file.stat().st_mtime) < (7 * 24 * 3600):
                            shutil.copy2(log_file, logs_backup_dir / log_file.name)
            
            self.logger.info("✅ Logs backup completed")
            
        except Exception as e:
            self.logger.error(f"❌ Logs backup failed: {e}")
            # Don't raise - logs backup is not critical
    
    async def _create_backup_metadata(self, temp_dir: Path, backup_type: str):
        """Create backup metadata"""
        try:
            metadata = {
                "backup_info": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": backup_type,
                    "version": "1.0.0",
                    "system": os.name
                },
                "database_info": {
                    "file_path": self.config.database.file_path,
                    "size_bytes": Path(self.config.database.file_path).stat().st_size if Path(self.config.database.file_path).exists() else 0
                },
                "configuration": {
                    "trading_enabled": self.config.trading.enable_auto_trading if self.config.trading else False,
                    "paper_trading": self.config.trading.paper_trading_enabled if self.config.trading else False,
                    "live_trading": self.config.trading.live_trading_enabled if self.config.trading else False
                }
            }
            
            with open(temp_dir / "backup_metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info("✅ Backup metadata created")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create backup metadata: {e}")
            raise
    
    async def _create_compressed_archive(self, temp_dir: Path, backup_path: Path):
        """Create compressed backup archive"""
        try:
            # Use tar with gzip compression
            import tarfile
            
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(temp_dir, arcname="backup")
            
            self.logger.info(f"✅ Compressed archive created: {backup_path}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create compressed archive: {e}")
            raise
    
    async def _verify_backup_integrity(self, backup_path: Path) -> bool:
        """Verify backup file integrity"""
        try:
            import tarfile
            
            # Check if file exists and is readable
            if not backup_path.exists():
                return False
            
            # Try to open and list contents
            with tarfile.open(backup_path, "r:gz") as tar:
                members = tar.getmembers()
                
                # Check for required files
                required_files = ["backup/backup_metadata.json"]
                for required_file in required_files:
                    if not any(member.name == required_file for member in members):
                        self.logger.error(f"Missing required file in backup: {required_file}")
                        return False
            
            # Calculate and store checksum
            checksum = await self._calculate_file_checksum(backup_path)
            checksum_file = backup_path.with_suffix(backup_path.suffix + ".sha256")
            
            with open(checksum_file, "w") as f:
                f.write(f"{checksum}  {backup_path.name}\n")
            
            self.logger.info("✅ Backup integrity verified")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Backup integrity verification failed: {e}")
            return False
    
    async def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    async def _cleanup_old_backups(self):
        """Clean up old backups according to retention policy"""
        try:
            # Get all backup files
            backup_files = list(self.backup_dir.glob("jmoney_backup_*.tar.gz"))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep only the specified number of backups
            if len(backup_files) > self.daily_backups_keep:
                files_to_delete = backup_files[self.daily_backups_keep:]
                
                for file_to_delete in files_to_delete:
                    file_to_delete.unlink()
                    
                    # Also delete checksum file if it exists
                    checksum_file = file_to_delete.with_suffix(file_to_delete.suffix + ".sha256")
                    if checksum_file.exists():
                        checksum_file.unlink()
                
                self.logger.info(f"🗑️ Cleaned up {len(files_to_delete)} old backup files")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to cleanup old backups: {e}")
    
    async def restore_backup(self, backup_path: str) -> bool:
        """Restore system from backup"""
        try:
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                self.logger.error(f"❌ Backup file not found: {backup_path}")
                return False
            
            self.logger.info(f"🔄 Restoring from backup: {backup_path}")
            
            # Verify backup integrity before restore
            if not await self._verify_backup_integrity(backup_file):
                self.logger.error("❌ Backup integrity check failed - aborting restore")
                return False
            
            # Create restore directory
            restore_dir = self.backup_dir / f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            restore_dir.mkdir(exist_ok=True)
            
            try:
                # Extract backup
                import tarfile
                with tarfile.open(backup_file, "r:gz") as tar:
                    tar.extractall(restore_dir)
                
                backup_content_dir = restore_dir / "backup"
                
                # Restore database
                await self._restore_database(backup_content_dir)
                
                # Restore configuration
                await self._restore_configuration(backup_content_dir)
                
                self.logger.info("✅ Backup restored successfully")
                return True
                
            finally:
                # Clean up restore directory
                if restore_dir.exists():
                    shutil.rmtree(restore_dir)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to restore backup: {e}")
            return False
    
    async def _restore_database(self, backup_dir: Path):
        """Restore database from backup"""
        try:
            db_backup_dir = backup_dir / "database"
            backup_db_file = db_backup_dir / "trading_bot.db"
            
            if backup_db_file.exists():
                # Create backup of current database
                current_db = Path(self.config.database.file_path)
                if current_db.exists():
                    backup_current = current_db.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
                    shutil.copy2(current_db, backup_current)
                    self.logger.info(f"📦 Current database backed up to: {backup_current}")
                
                # Restore database
                shutil.copy2(backup_db_file, current_db)
                self.logger.info("✅ Database restored")
            else:
                self.logger.warning("⚠️ No database backup found")
                
        except Exception as e:
            self.logger.error(f"❌ Database restore failed: {e}")
            raise
    
    async def _restore_configuration(self, backup_dir: Path):
        """Restore configuration from backup"""
        try:
            config_backup_dir = backup_dir / "configuration"
            
            if config_backup_dir.exists():
                # Restore config files
                for config_file in config_backup_dir.glob("*.yaml"):
                    target_file = Path(config_file.name)
                    
                    # Backup current config
                    if target_file.exists():
                        backup_current = target_file.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
                        shutil.copy2(target_file, backup_current)
                    
                    # Restore config
                    shutil.copy2(config_file, target_file)
                
                self.logger.info("✅ Configuration restored")
            else:
                self.logger.warning("⚠️ No configuration backup found")
                
        except Exception as e:
            self.logger.error(f"❌ Configuration restore failed: {e}")
            raise
    
    async def _dump_database_schema(self, db_file: Path, schema_file: Path):
        """Dump database schema to SQL file"""
        try:
            conn = sqlite3.connect(str(db_file))
            
            with open(schema_file, "w") as f:
                for line in conn.iterdump():
                    if line.startswith("CREATE"):
                        f.write(f"{line}\n")
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to dump database schema: {e}")
    
    async def _export_database_data(self, db_file: Path, data_file: Path):
        """Export database data to JSON"""
        try:
            conn = sqlite3.connect(str(db_file))
            conn.row_factory = sqlite3.Row
            
            data = {}
            
            # Get all tables
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                
                data[table_name] = [dict(row) for row in rows]
            
            with open(data_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to export database data: {e}")
    
    async def _backup_scheduler(self):
        """Background backup scheduler"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                now = datetime.now(timezone.utc)
                
                # Check if backup is needed
                if (self.last_backup_time is None or 
                    (now - self.last_backup_time).total_seconds() > (self.backup_interval_hours * 3600)):
                    
                    await self.create_backup("scheduled")
                
                # Check if integrity check is needed
                if (self.last_integrity_check is None or 
                    (now - self.last_integrity_check).total_seconds() > (self.integrity_check_interval * 3600)):
                    
                    await self.check_data_integrity()
                    self.last_integrity_check = now
                
            except Exception as e:
                self.logger.error(f"❌ Backup scheduler error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def check_data_integrity(self) -> bool:
        """Check database and system data integrity"""
        try:
            self.logger.info("🔍 Checking data integrity...")
            
            # Check database integrity
            db_file = Path(self.config.database.file_path)
            if db_file.exists():
                conn = sqlite3.connect(str(db_file))
                cursor = conn.cursor()
                
                # Run PRAGMA integrity_check
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                
                if result[0] != "ok":
                    self.logger.error(f"❌ Database integrity check failed: {result[0]}")
                    conn.close()
                    return False
                
                conn.close()
                self.logger.info("✅ Database integrity check passed")
            
            # Check configuration file integrity
            if not Path("config.yaml").exists():
                self.logger.error("❌ Main configuration file missing")
                return False
            
            self.logger.info("✅ Data integrity check completed")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Data integrity check failed: {e}")
            return False
    
    def get_backup_status(self) -> Dict[str, Any]:
        """Get backup system status"""
        try:
            backup_files = list(self.backup_dir.glob("jmoney_backup_*.tar.gz"))
            
            return {
                "last_backup": self.last_backup_time.isoformat() if self.last_backup_time else None,
                "backup_count": len(backup_files),
                "backup_directory": str(self.backup_dir),
                "total_backup_size": sum(f.stat().st_size for f in backup_files),
                "oldest_backup": min(backup_files, key=lambda x: x.stat().st_mtime).name if backup_files else None,
                "newest_backup": max(backup_files, key=lambda x: x.stat().st_mtime).name if backup_files else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting backup status: {e}")
            return {}


# Global instance (will be initialized by main application)
backup_system: Optional[BackupSystem] = None
