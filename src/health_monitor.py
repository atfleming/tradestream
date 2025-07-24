"""
System Health Monitoring for JMoney Discord Alert Trading System
Comprehensive system health checks, performance monitoring, and alerting
"""

import asyncio
import logging
import psutil
import time
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json

try:
    from .config import ConfigManager
    from .database import DatabaseManager
    from .email_notifier import EmailNotifier
except ImportError:
    from config import ConfigManager
    from database import DatabaseManager
    from email_notifier import EmailNotifier


@dataclass
class HealthMetric:
    """System health metric"""
    name: str
    value: float
    unit: str
    status: str  # "HEALTHY", "WARNING", "CRITICAL"
    threshold_warning: float
    threshold_critical: float
    timestamp: datetime
    message: str = ""


@dataclass
class SystemHealth:
    """Overall system health status"""
    overall_status: str  # "HEALTHY", "WARNING", "CRITICAL"
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_status: str
    database_status: str
    component_statuses: Dict[str, str]
    uptime_seconds: int
    last_alert_time: Optional[datetime]
    performance_score: float  # 0-100


class HealthMonitor:
    """Comprehensive system health monitoring"""
    
    def __init__(self, config: ConfigManager, db: DatabaseManager, email_notifier: Optional[EmailNotifier] = None):
        """Initialize health monitor"""
        self.config = config
        self.db = db
        self.email_notifier = email_notifier
        self.logger = logging.getLogger(__name__)
        
        # Health monitoring state
        self.start_time = datetime.now(timezone.utc)
        self.last_health_check = None
        self.health_history: List[SystemHealth] = []
        self.component_health: Dict[str, str] = {}
        
        # Health thresholds
        self.cpu_warning_threshold = 80.0  # %
        self.cpu_critical_threshold = 95.0  # %
        self.memory_warning_threshold = 80.0  # %
        self.memory_critical_threshold = 95.0  # %
        self.disk_warning_threshold = 85.0  # %
        self.disk_critical_threshold = 95.0  # %
        
        # Monitoring intervals
        self.health_check_interval = 60  # seconds
        self.performance_history_limit = 1440  # Keep 24 hours of minute-by-minute data
        
        # Alert cooldown
        self.alert_cooldown_minutes = 15
        self.last_alert_sent = {}
        
        # Component monitoring
        self.monitored_components = [
            "discord_monitor",
            "trade_executor", 
            "paper_trader",
            "tsx_api",
            "email_notifier",
            "database",
            "config_manager"
        ]
    
    async def initialize(self) -> bool:
        """Initialize health monitoring system"""
        try:
            self.logger.info("🏥 Initializing health monitoring system...")
            
            # Perform initial health check
            await self.perform_health_check()
            
            # Start background monitoring
            asyncio.create_task(self._health_monitoring_loop())
            
            self.logger.info("✅ Health monitoring system initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize health monitoring: {e}")
            return False
    
    async def perform_health_check(self) -> SystemHealth:
        """Perform comprehensive system health check"""
        try:
            self.logger.debug("🔍 Performing system health check...")
            
            # System resource metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            # Network connectivity check
            network_status = await self._check_network_connectivity()
            
            # Database health check
            database_status = await self._check_database_health()
            
            # Component health checks
            component_statuses = await self._check_component_health()
            
            # Calculate uptime
            uptime_seconds = int((datetime.now(timezone.utc) - self.start_time).total_seconds())
            
            # Determine overall status
            overall_status = self._calculate_overall_status(
                cpu_usage, memory.percent, disk.percent, 
                network_status, database_status, component_statuses
            )
            
            # Calculate performance score
            performance_score = self._calculate_performance_score(
                cpu_usage, memory.percent, disk.percent, component_statuses
            )
            
            # Create health status
            health_status = SystemHealth(
                overall_status=overall_status,
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                network_status=network_status,
                database_status=database_status,
                component_statuses=component_statuses,
                uptime_seconds=uptime_seconds,
                last_alert_time=self.last_health_check,
                performance_score=performance_score
            )
            
            # Store health history
            self.health_history.append(health_status)
            if len(self.health_history) > self.performance_history_limit:
                self.health_history.pop(0)
            
            # Check for alerts
            await self._check_health_alerts(health_status)
            
            self.last_health_check = datetime.now(timezone.utc)
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"❌ Health check failed: {e}")
            return SystemHealth(
                overall_status="CRITICAL",
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_status="UNKNOWN",
                database_status="UNKNOWN",
                component_statuses={},
                uptime_seconds=0,
                last_alert_time=None,
                performance_score=0.0
            )
    
    async def _check_network_connectivity(self) -> str:
        """Check network connectivity"""
        try:
            # Simple connectivity check
            import socket
            
            # Try to connect to a reliable external service
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('8.8.8.8', 53))  # Google DNS
            sock.close()
            
            return "HEALTHY" if result == 0 else "CRITICAL"
            
        except Exception as e:
            self.logger.warning(f"Network connectivity check failed: {e}")
            return "UNKNOWN"
    
    async def _check_database_health(self) -> str:
        """Check database health and connectivity"""
        try:
            if not self.db:
                return "CRITICAL"
            
            # Test database connection
            cursor = self.db.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            # Check database integrity
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            if result[0] != "ok":
                return "CRITICAL"
            
            # Check database size and performance
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            db_size_mb = (page_count * page_size) / (1024 * 1024)
            
            # Warn if database is getting large
            if db_size_mb > 1000:  # 1GB
                return "WARNING"
            
            return "HEALTHY"
            
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return "CRITICAL"
    
    async def _check_component_health(self) -> Dict[str, str]:
        """Check health of all system components"""
        component_statuses = {}
        
        for component in self.monitored_components:
            try:
                status = await self._check_individual_component(component)
                component_statuses[component] = status
                self.component_health[component] = status
                
            except Exception as e:
                self.logger.error(f"Failed to check {component} health: {e}")
                component_statuses[component] = "UNKNOWN"
        
        return component_statuses
    
    async def _check_individual_component(self, component: str) -> str:
        """Check health of individual component"""
        try:
            # This would be expanded based on actual component interfaces
            # For now, we'll do basic checks
            
            if component == "database":
                return await self._check_database_health()
            
            elif component == "discord_monitor":
                # Check if Discord monitor is running and connected
                return "HEALTHY"  # Placeholder
            
            elif component == "trade_executor":
                # Check if trade executor is responsive
                return "HEALTHY"  # Placeholder
            
            elif component == "paper_trader":
                # Check paper trading simulator
                return "HEALTHY"  # Placeholder
            
            elif component == "tsx_api":
                # Check TopStepX API connection
                return "HEALTHY"  # Placeholder
            
            elif component == "email_notifier":
                # Check email system
                return "HEALTHY" if self.email_notifier else "DISABLED"
            
            else:
                return "UNKNOWN"
                
        except Exception as e:
            self.logger.error(f"Component {component} health check failed: {e}")
            return "CRITICAL"
    
    def _calculate_overall_status(self, cpu_usage: float, memory_usage: float, 
                                disk_usage: float, network_status: str, 
                                database_status: str, component_statuses: Dict[str, str]) -> str:
        """Calculate overall system health status"""
        
        # Check for critical conditions
        if (cpu_usage > self.cpu_critical_threshold or 
            memory_usage > self.memory_critical_threshold or
            disk_usage > self.disk_critical_threshold or
            network_status == "CRITICAL" or
            database_status == "CRITICAL"):
            return "CRITICAL"
        
        # Check component statuses
        critical_components = [status for status in component_statuses.values() if status == "CRITICAL"]
        if critical_components:
            return "CRITICAL"
        
        # Check for warning conditions
        if (cpu_usage > self.cpu_warning_threshold or 
            memory_usage > self.memory_warning_threshold or
            disk_usage > self.disk_warning_threshold or
            network_status == "WARNING" or
            database_status == "WARNING"):
            return "WARNING"
        
        # Check component warnings
        warning_components = [status for status in component_statuses.values() if status == "WARNING"]
        if warning_components:
            return "WARNING"
        
        return "HEALTHY"
    
    def _calculate_performance_score(self, cpu_usage: float, memory_usage: float, 
                                   disk_usage: float, component_statuses: Dict[str, str]) -> float:
        """Calculate overall performance score (0-100)"""
        
        # Resource utilization score (lower usage = higher score)
        cpu_score = max(0, 100 - cpu_usage)
        memory_score = max(0, 100 - memory_usage)
        disk_score = max(0, 100 - disk_usage)
        
        # Component health score
        healthy_components = len([s for s in component_statuses.values() if s == "HEALTHY"])
        total_components = len(component_statuses)
        component_score = (healthy_components / total_components * 100) if total_components > 0 else 0
        
        # Weighted average
        performance_score = (
            cpu_score * 0.3 +
            memory_score * 0.3 +
            disk_score * 0.2 +
            component_score * 0.2
        )
        
        return round(performance_score, 1)
    
    async def _check_health_alerts(self, health_status: SystemHealth):
        """Check if health alerts should be sent"""
        try:
            alerts_to_send = []
            
            # CPU alert
            if health_status.cpu_usage > self.cpu_critical_threshold:
                alerts_to_send.append(f"🚨 CRITICAL: CPU usage at {health_status.cpu_usage:.1f}%")
            elif health_status.cpu_usage > self.cpu_warning_threshold:
                alerts_to_send.append(f"⚠️ WARNING: CPU usage at {health_status.cpu_usage:.1f}%")
            
            # Memory alert
            if health_status.memory_usage > self.memory_critical_threshold:
                alerts_to_send.append(f"🚨 CRITICAL: Memory usage at {health_status.memory_usage:.1f}%")
            elif health_status.memory_usage > self.memory_warning_threshold:
                alerts_to_send.append(f"⚠️ WARNING: Memory usage at {health_status.memory_usage:.1f}%")
            
            # Disk alert
            if health_status.disk_usage > self.disk_critical_threshold:
                alerts_to_send.append(f"🚨 CRITICAL: Disk usage at {health_status.disk_usage:.1f}%")
            elif health_status.disk_usage > self.disk_warning_threshold:
                alerts_to_send.append(f"⚠️ WARNING: Disk usage at {health_status.disk_usage:.1f}%")
            
            # Component alerts
            for component, status in health_status.component_statuses.items():
                if status == "CRITICAL":
                    alerts_to_send.append(f"🚨 CRITICAL: {component} is in critical state")
                elif status == "WARNING":
                    alerts_to_send.append(f"⚠️ WARNING: {component} has issues")
            
            # Send alerts if any and not in cooldown
            if alerts_to_send:
                await self._send_health_alerts(alerts_to_send, health_status)
            
        except Exception as e:
            self.logger.error(f"Error checking health alerts: {e}")
    
    async def _send_health_alerts(self, alerts: List[str], health_status: SystemHealth):
        """Send health alert notifications"""
        try:
            # Check cooldown
            now = datetime.now(timezone.utc)
            last_alert = self.last_alert_sent.get("health", datetime.min.replace(tzinfo=timezone.utc))
            
            if (now - last_alert).total_seconds() < (self.alert_cooldown_minutes * 60):
                return  # Still in cooldown
            
            # Log alerts
            for alert in alerts:
                if "CRITICAL" in alert:
                    self.logger.critical(alert)
                else:
                    self.logger.warning(alert)
            
            # Send email alert if configured
            if self.email_notifier and self.config.email and self.config.email.enabled:
                subject = f"🏥 JMoney Trading Bot - System Health Alert"
                
                body = f"""
System Health Alert - {health_status.overall_status}

Alerts:
{chr(10).join(f"• {alert}" for alert in alerts)}

System Status:
• Overall Status: {health_status.overall_status}
• Performance Score: {health_status.performance_score:.1f}/100
• CPU Usage: {health_status.cpu_usage:.1f}%
• Memory Usage: {health_status.memory_usage:.1f}%
• Disk Usage: {health_status.disk_usage:.1f}%
• Uptime: {health_status.uptime_seconds // 3600}h {(health_status.uptime_seconds % 3600) // 60}m

Component Status:
{chr(10).join(f"• {comp}: {status}" for comp, status in health_status.component_statuses.items())}

Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
                
                await self.email_notifier.send_email(subject, body, is_html=False)
                self.last_alert_sent["health"] = now
            
        except Exception as e:
            self.logger.error(f"Failed to send health alerts: {e}")
    
    async def _health_monitoring_loop(self):
        """Background health monitoring loop"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self.perform_health_check()
                
            except Exception as e:
                self.logger.error(f"Health monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary"""
        try:
            if not self.health_history:
                return {"status": "NO_DATA"}
            
            latest_health = self.health_history[-1]
            
            # Calculate averages over last hour
            recent_health = [h for h in self.health_history if 
                           (datetime.now(timezone.utc) - datetime.fromtimestamp(time.time() - 3600, timezone.utc)).total_seconds() < 3600]
            
            avg_cpu = sum(h.cpu_usage for h in recent_health) / len(recent_health) if recent_health else 0
            avg_memory = sum(h.memory_usage for h in recent_health) / len(recent_health) if recent_health else 0
            avg_performance = sum(h.performance_score for h in recent_health) / len(recent_health) if recent_health else 0
            
            return {
                "current_status": {
                    "overall": latest_health.overall_status,
                    "performance_score": latest_health.performance_score,
                    "cpu_usage": latest_health.cpu_usage,
                    "memory_usage": latest_health.memory_usage,
                    "disk_usage": latest_health.disk_usage,
                    "uptime_hours": latest_health.uptime_seconds // 3600
                },
                "averages_last_hour": {
                    "cpu_usage": round(avg_cpu, 1),
                    "memory_usage": round(avg_memory, 1),
                    "performance_score": round(avg_performance, 1)
                },
                "component_status": latest_health.component_statuses,
                "last_check": self.last_health_check.isoformat() if self.last_health_check else None,
                "data_points": len(self.health_history)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting health summary: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def get_performance_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get performance history for specified hours"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Filter history to requested timeframe
            # Note: This is a simplified implementation
            # In a real system, you'd store timestamps with each health record
            
            recent_history = self.health_history[-min(len(self.health_history), hours * 60):]  # Approximate
            
            return [
                {
                    "cpu_usage": h.cpu_usage,
                    "memory_usage": h.memory_usage,
                    "disk_usage": h.disk_usage,
                    "performance_score": h.performance_score,
                    "overall_status": h.overall_status
                }
                for h in recent_history
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting performance history: {e}")
            return []
    
    async def run_diagnostic(self) -> Dict[str, Any]:
        """Run comprehensive system diagnostic"""
        try:
            self.logger.info("🔧 Running system diagnostic...")
            
            diagnostic_results = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "system_info": {
                    "python_version": psutil.sys.version,
                    "platform": psutil.os.name,
                    "cpu_count": psutil.cpu_count(),
                    "total_memory_gb": round(psutil.virtual_memory().total / (1024**3), 2)
                },
                "current_health": await self.perform_health_check(),
                "database_diagnostic": await self._run_database_diagnostic(),
                "performance_analysis": self._analyze_performance_trends(),
                "recommendations": self._generate_health_recommendations()
            }
            
            self.logger.info("✅ System diagnostic completed")
            return diagnostic_results
            
        except Exception as e:
            self.logger.error(f"System diagnostic failed: {e}")
            return {"error": str(e)}
    
    async def _run_database_diagnostic(self) -> Dict[str, Any]:
        """Run database-specific diagnostic"""
        try:
            if not self.db:
                return {"status": "NO_DATABASE"}
            
            cursor = self.db.connection.cursor()
            
            # Database size
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            db_size_mb = (page_count * page_size) / (1024 * 1024)
            
            # Table information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            table_info = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_info[table] = count
            
            return {
                "status": "HEALTHY",
                "size_mb": round(db_size_mb, 2),
                "page_count": page_count,
                "page_size": page_size,
                "tables": table_info
            }
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends"""
        try:
            if len(self.health_history) < 10:
                return {"status": "INSUFFICIENT_DATA"}
            
            recent_scores = [h.performance_score for h in self.health_history[-60:]]  # Last hour
            
            trend = "STABLE"
            if len(recent_scores) > 5:
                early_avg = sum(recent_scores[:len(recent_scores)//2]) / (len(recent_scores)//2)
                late_avg = sum(recent_scores[len(recent_scores)//2:]) / (len(recent_scores) - len(recent_scores)//2)
                
                if late_avg > early_avg + 5:
                    trend = "IMPROVING"
                elif late_avg < early_avg - 5:
                    trend = "DEGRADING"
            
            return {
                "trend": trend,
                "current_score": recent_scores[-1] if recent_scores else 0,
                "average_score": round(sum(recent_scores) / len(recent_scores), 1) if recent_scores else 0,
                "min_score": min(recent_scores) if recent_scores else 0,
                "max_score": max(recent_scores) if recent_scores else 0
            }
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
    
    def _generate_health_recommendations(self) -> List[str]:
        """Generate health improvement recommendations"""
        recommendations = []
        
        if not self.health_history:
            return ["Insufficient data for recommendations"]
        
        latest = self.health_history[-1]
        
        if latest.cpu_usage > 80:
            recommendations.append("Consider optimizing CPU-intensive operations")
        
        if latest.memory_usage > 80:
            recommendations.append("Monitor memory usage and consider increasing available RAM")
        
        if latest.disk_usage > 85:
            recommendations.append("Clean up disk space or expand storage capacity")
        
        if latest.performance_score < 70:
            recommendations.append("System performance is below optimal - review resource usage")
        
        critical_components = [comp for comp, status in latest.component_statuses.items() if status == "CRITICAL"]
        if critical_components:
            recommendations.append(f"Address critical issues in: {', '.join(critical_components)}")
        
        if not recommendations:
            recommendations.append("System is operating within normal parameters")
        
        return recommendations


# Global instance (will be initialized by main application)
health_monitor: Optional[HealthMonitor] = None
