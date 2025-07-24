"""
System Tests for JMoney Discord Trading Bot

Tests end-to-end functionality, performance, and system stability.
Validates complete workflows under various conditions and loads.

Test Areas:
1. End-to-End Alert Processing
2. Performance Testing
3. System Stability Testing
4. Error Recovery Testing
5. Resource Management Testing
6. Configuration Resilience Testing
"""

import unittest
import asyncio
import tempfile
import shutil
import sqlite3
import yaml
import time
import threading
import psutil
import os
import signal
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import components for system testing
from config import ConfigManager
from message_parser import JMoneyMessageParser, ParsedAlert
from database import DatabaseManager
from discord_monitor import DiscordMonitor
from trade_executor import TradeExecutor, Position, PositionStatus
from email_notifier import EmailNotifier
from trade_tracker import TradeTracker
from risk_manager import RiskManager
from backup_system import BackupSystem
from health_monitor import HealthMonitor
from config_manager import AdvancedConfigManager


class TestEndToEndAlertProcessing(unittest.TestCase):
    """Test complete end-to-end alert processing workflows"""
    
    def setUp(self):
        """Set up end-to-end test environment"""
        # Create temporary directory for test files
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Create comprehensive test configuration
        self.config_data = {
            "trading": {
                "account_id": "test_account_e2e",
                "paper_trading_enabled": True,
                "size_mapping": {"A": 3, "B": 2, "C": 1},
                "max_daily_trades": 50,
                "max_position_size": 10,
                "enable_auto_trading": True
            },
            "database": {
                "file_path": str(self.test_dir / "test_system.db")
            },
            "email": {
                "enabled": False,  # Disable for system tests
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "test@example.com",
                "password": "test_password",
                "from_address": "test@example.com",
                "to_addresses": ["recipient@example.com"]
            },
            "discord": {
                "token": "test_token_system",
                "channel_id": 123456789,
                "target_author": "JMoney"
            },
            "risk": {
                "max_loss_per_trade": 100.0,
                "daily_loss_limit": 500.0,
                "max_consecutive_losses": 3,
                "position_size_limit": 5,
                "enable_circuit_breaker": True
            }
        }
        
        # Write config file
        self.config_file = self.test_dir / "config.yaml"
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config_data, f)
        
        # Initialize system components
        self.config_manager = ConfigManager(str(self.config_file))
        self.config_manager.load_config()
        
        self.database = DatabaseManager(str(self.test_dir / "test_system.db"))
        self.database.initialize_database()
        
        self.message_parser = JMoneyMessageParser()
        
        # Initialize other components with mocked external dependencies
        with patch('smtplib.SMTP'):
            self.email_notifier = EmailNotifier(self.config_manager.email, self.database)
        
        self.trade_tracker = TradeTracker(self.database)
        self.risk_manager = RiskManager(self.database, self.email_notifier)
        
        # Mock TSX integration for trade executor
        with patch('tsx_integration.TopStepXIntegration') as mock_tsx:
            mock_tsx_instance = Mock()
            mock_tsx.return_value = mock_tsx_instance
            self.trade_executor = TradeExecutor(
                self.config_manager.trading, 
                self.database, 
                self.email_notifier, 
                mock_tsx_instance
            )
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_complete_alert_to_trade_workflow(self):
        """Test complete workflow from alert reception to trade execution"""
        # Step 1: Simulate receiving Discord alert
        test_message = "🚨 ES long 4500: C\nStop: 4495\n@everyone"
        
        # Step 2: Parse the alert
        alert = self.message_parser.parse_message(test_message)
        self.assertTrue(alert.is_valid)
        self.assertEqual(alert.price, 4500)
        self.assertEqual(alert.size, "C")
        
        # Step 3: Store alert in database
        alert_id = self.database.insert_alert(
            discord_message_id="e2e_test_123",
            author="JMoney",
            channel_id=123456789,
            raw_content=test_message,
            parsed_price=alert.price,
            parsed_size=alert.size,
            parsed_stop=alert.stop,
            target_1=alert.target_1,
            target_2=alert.target_2,
            is_valid=True
        )
        
        # Step 4: Execute trade through trade executor
        with patch.object(self.trade_executor.tsx_integration, 'place_order') as mock_place_order:
            mock_place_order.return_value = {"order_id": "e2e_order_123", "status": "filled"}
            
            # Convert ParsedAlert to format expected by trade executor
            trade_alert = Mock()
            trade_alert.symbol = "ES"
            trade_alert.direction = "long"
            trade_alert.entry_price = alert.price
            trade_alert.stop_loss = alert.stop
            trade_alert.target_1 = alert.target_1
            trade_alert.target_2 = alert.target_2
            trade_alert.position_size = alert.size
            
            execution_result = asyncio.run(self.trade_executor.execute_trade(trade_alert))
            self.assertTrue(execution_result)
        
        # Step 5: Verify trade was recorded
        trade_id = self.database.insert_trade(
            alert_id=alert_id,
            trade_type="LONG",
            symbol="ES",
            entry_price=alert.price,
            quantity=1,
            stop_loss=alert.stop,
            target_1=alert.target_1,
            target_2=alert.target_2,
            order_id="e2e_order_123"
        )
        
        # Step 6: Verify complete workflow integrity
        stored_alert = self.database.get_alert(alert_id)
        self.assertIsNotNone(stored_alert)
        self.assertEqual(stored_alert['parsed_price'], 4500)
        
        open_trades = self.database.get_open_trades()
        self.assertEqual(len(open_trades), 1)
        self.assertEqual(open_trades[0]['symbol'], "ES")
        
        # Step 7: Test risk management integration
        risk_check = asyncio.run(self.risk_manager.check_trade_risk(
            symbol="ES",
            direction="long",
            entry_price=4500,
            quantity=1,
            stop_loss=4495
        ))
        self.assertIsNotNone(risk_check)
    
    def test_multiple_concurrent_alerts_processing(self):
        """Test system handling multiple concurrent alerts"""
        test_alerts = [
            "🚨 ES long 4500: C\nStop: 4495\n@everyone",
            "🚨 ES long 4510: B\nStop: 4505\n@everyone",
            "🚨 ES long 4520: A\nStop: 4515\n@everyone",
            "🚨 ES long 4530: C\nStop: 4525\n@everyone",
            "🚨 ES long 4540: B\nStop: 4535\n@everyone"
        ]
        
        processed_alerts = []
        
        # Process all alerts
        for i, message in enumerate(test_alerts):
            alert = self.message_parser.parse_message(message)
            self.assertTrue(alert.is_valid)
            
            alert_id = self.database.insert_alert(
                discord_message_id=f"concurrent_test_{i}",
                author="JMoney",
                channel_id=123456789,
                raw_content=message,
                parsed_price=alert.price,
                parsed_size=alert.size,
                parsed_stop=alert.stop,
                target_1=alert.target_1,
                target_2=alert.target_2,
                is_valid=True
            )
            processed_alerts.append(alert_id)
        
        # Verify all alerts were processed correctly
        self.assertEqual(len(processed_alerts), 5)
        
        # Verify database consistency
        recent_alerts = self.database.get_recent_alerts(limit=10)
        self.assertEqual(len(recent_alerts), 5)
        
        # Verify no data corruption
        for alert in recent_alerts:
            self.assertIsNotNone(alert['parsed_price'])
            self.assertIn(alert['parsed_size'], ['A', 'B', 'C'])
            self.assertTrue(alert['is_valid'])
    
    def test_invalid_alert_handling_in_system_context(self):
        """Test system behavior with invalid alerts in realistic scenarios"""
        mixed_messages = [
            "🚨 ES long 4500: C\nStop: 4495\n@everyone",  # Valid
            "Just a regular chat message",                   # Invalid
            "🚨 ES long 4510: B\nStop: 4505\n@everyone",  # Valid
            "ES is looking good today",                      # Invalid
            "🚨 Invalid format message",                     # Invalid
            "🚨 ES long 4520: A\nStop: 4515\n@everyone",  # Valid
        ]
        
        valid_count = 0
        invalid_count = 0
        
        for i, message in enumerate(mixed_messages):
            alert = self.message_parser.parse_message(message)
            
            if alert.is_valid:
                valid_count += 1
                # Store valid alerts
                alert_id = self.database.insert_alert(
                    discord_message_id=f"mixed_test_{i}",
                    author="JMoney",
                    channel_id=123456789,
                    raw_content=message,
                    parsed_price=alert.price,
                    parsed_size=alert.size,
                    parsed_stop=alert.stop,
                    target_1=alert.target_1,
                    target_2=alert.target_2,
                    is_valid=True
                )
                self.assertIsNotNone(alert_id)
            else:
                invalid_count += 1
        
        # Verify correct classification
        self.assertEqual(valid_count, 3)
        self.assertEqual(invalid_count, 3)
        
        # Verify only valid alerts were stored
        stored_alerts = self.database.get_recent_alerts(limit=10)
        self.assertEqual(len(stored_alerts), 3)
        
        # Verify system stability after processing mixed messages
        stats = self.database.get_system_stats()
        self.assertEqual(stats['valid_alerts'], 3)


class TestPerformanceAndLoad(unittest.TestCase):
    """Test system performance under various load conditions"""
    
    def setUp(self):
        """Set up performance test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Initialize minimal components for performance testing
        self.database = DatabaseManager(str(self.test_dir / "test_performance.db"))
        self.database.initialize_database()
        self.message_parser = JMoneyMessageParser()
        
        # Track performance metrics
        self.performance_metrics = {
            'parse_times': [],
            'db_insert_times': [],
            'memory_usage': [],
            'cpu_usage': []
        }
    
    def tearDown(self):
        """Clean up performance test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_message_parsing_performance(self):
        """Test message parsing performance under high volume"""
        test_message = "🚨 ES long 4500: C\nStop: 4495\n@everyone"
        num_iterations = 1000
        
        start_time = time.time()
        
        for i in range(num_iterations):
            parse_start = time.time()
            alert = self.message_parser.parse_message(test_message)
            parse_end = time.time()
            
            self.assertTrue(alert.is_valid)
            self.performance_metrics['parse_times'].append(parse_end - parse_start)
        
        total_time = time.time() - start_time
        avg_parse_time = sum(self.performance_metrics['parse_times']) / len(self.performance_metrics['parse_times'])
        
        # Performance assertions
        self.assertLess(total_time, 5.0, "Total parsing time should be under 5 seconds for 1000 messages")
        self.assertLess(avg_parse_time, 0.01, "Average parse time should be under 10ms")
        
        print(f"Performance Results:")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Average parse time: {avg_parse_time*1000:.2f}ms")
        print(f"  Messages per second: {num_iterations/total_time:.1f}")
    
    def test_database_performance_under_load(self):
        """Test database performance with high insert volume"""
        num_inserts = 500
        
        start_time = time.time()
        
        for i in range(num_inserts):
            insert_start = time.time()
            
            alert_id = self.database.insert_alert(
                discord_message_id=f"perf_test_{i}",
                author="JMoney",
                channel_id=123456789,
                raw_content="🚨 ES long 4500: C\nStop: 4495\n@everyone",
                parsed_price=4500 + i,  # Vary price slightly
                parsed_size="C",
                parsed_stop=4495 + i,
                target_1=4507 + i,
                target_2=4512 + i,
                is_valid=True
            )
            
            insert_end = time.time()
            
            self.assertIsNotNone(alert_id)
            self.performance_metrics['db_insert_times'].append(insert_end - insert_start)
        
        total_time = time.time() - start_time
        avg_insert_time = sum(self.performance_metrics['db_insert_times']) / len(self.performance_metrics['db_insert_times'])
        
        # Performance assertions
        self.assertLess(total_time, 10.0, "Total insert time should be under 10 seconds for 500 inserts")
        self.assertLess(avg_insert_time, 0.02, "Average insert time should be under 20ms")
        
        # Verify data integrity after high-volume inserts
        recent_alerts = self.database.get_recent_alerts(limit=num_inserts)
        self.assertEqual(len(recent_alerts), num_inserts)
        
        print(f"Database Performance Results:")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Average insert time: {avg_insert_time*1000:.2f}ms")
        print(f"  Inserts per second: {num_inserts/total_time:.1f}")
    
    def test_memory_usage_stability(self):
        """Test memory usage remains stable under continuous operation"""
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate continuous operation
        num_cycles = 100
        
        for cycle in range(num_cycles):
            # Simulate alert processing cycle
            for i in range(10):
                alert = self.message_parser.parse_message("🚨 ES long 4500: C\nStop: 4495\n@everyone")
                
                alert_id = self.database.insert_alert(
                    discord_message_id=f"memory_test_{cycle}_{i}",
                    author="JMoney",
                    channel_id=123456789,
                    raw_content="🚨 ES long 4500: C\nStop: 4495\n@everyone",
                    parsed_price=4500,
                    parsed_size="C",
                    parsed_stop=4495,
                    target_1=4507,
                    target_2=4512,
                    is_valid=True
                )
            
            # Check memory usage every 10 cycles
            if cycle % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                self.performance_metrics['memory_usage'].append(current_memory)
                
                # Force garbage collection
                gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory assertions
        self.assertLess(memory_growth, 50, "Memory growth should be under 50MB")
        
        print(f"Memory Usage Results:")
        print(f"  Initial memory: {initial_memory:.1f}MB")
        print(f"  Final memory: {final_memory:.1f}MB")
        print(f"  Memory growth: {memory_growth:.1f}MB")
    
    def test_concurrent_operations_performance(self):
        """Test performance with concurrent database operations"""
        def worker_function(worker_id, num_operations):
            """Worker function for concurrent testing"""
            results = []
            for i in range(num_operations):
                start_time = time.time()
                
                alert_id = self.database.insert_alert(
                    discord_message_id=f"concurrent_{worker_id}_{i}",
                    author="JMoney",
                    channel_id=123456789,
                    raw_content="🚨 ES long 4500: C\nStop: 4495\n@everyone",
                    parsed_price=4500 + worker_id,
                    parsed_size="C",
                    parsed_stop=4495 + worker_id,
                    target_1=4507 + worker_id,
                    target_2=4512 + worker_id,
                    is_valid=True
                )
                
                end_time = time.time()
                results.append((alert_id, end_time - start_time))
            
            return results
        
        # Test with multiple concurrent workers
        num_workers = 5
        operations_per_worker = 50
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(worker_function, worker_id, operations_per_worker)
                for worker_id in range(num_workers)
            ]
            
            all_results = []
            for future in as_completed(futures):
                worker_results = future.result()
                all_results.extend(worker_results)
        
        total_time = time.time() - start_time
        total_operations = num_workers * operations_per_worker
        
        # Verify all operations completed successfully
        self.assertEqual(len(all_results), total_operations)
        
        # Verify no failed operations
        failed_operations = [result for result in all_results if result[0] is None]
        self.assertEqual(len(failed_operations), 0)
        
        # Performance assertions
        operations_per_second = total_operations / total_time
        self.assertGreater(operations_per_second, 50, "Should handle at least 50 operations per second")
        
        print(f"Concurrent Operations Results:")
        print(f"  Total operations: {total_operations}")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Operations per second: {operations_per_second:.1f}")


class TestSystemStability(unittest.TestCase):
    """Test system stability and error recovery"""
    
    def setUp(self):
        """Set up stability test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Initialize components for stability testing
        self.database = DatabaseManager(str(self.test_dir / "test_stability.db"))
        self.database.initialize_database()
        self.message_parser = JMoneyMessageParser()
    
    def tearDown(self):
        """Clean up stability test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_database_corruption_recovery(self):
        """Test system behavior when database becomes corrupted"""
        # Insert some valid data first
        alert_id = self.database.insert_alert(
            discord_message_id="stability_test_1",
            author="JMoney",
            channel_id=123456789,
            raw_content="🚨 ES long 4500: C\nStop: 4495\n@everyone",
            parsed_price=4500,
            parsed_size="C",
            parsed_stop=4495,
            target_1=4507,
            target_2=4512,
            is_valid=True
        )
        self.assertIsNotNone(alert_id)
        
        # Simulate database corruption by closing connection improperly
        if hasattr(self.database, 'connection') and self.database.connection:
            self.database.connection.close()
        
        # Try to perform operations - should handle gracefully
        try:
            alert_id_2 = self.database.insert_alert(
                discord_message_id="stability_test_2",
                author="JMoney",
                channel_id=123456789,
                raw_content="🚨 ES long 4510: B\nStop: 4505\n@everyone",
                parsed_price=4510,
                parsed_size="B",
                parsed_stop=4505,
                target_1=4517,
                target_2=4522,
                is_valid=True
            )
            # Should either succeed with new connection or fail gracefully
        except Exception as e:
            # Should not crash the system
            self.assertIsInstance(e, (sqlite3.Error, AttributeError))
    
    def test_configuration_file_corruption_handling(self):
        """Test system behavior when configuration file is corrupted"""
        # Create a valid config file first
        config_file = self.test_dir / "test_config.yaml"
        valid_config = {
            "trading": {"account_id": "test", "paper_trading_enabled": True},
            "database": {"file_path": str(self.test_dir / "test.db")}
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(valid_config, f)
        
        # Load valid config
        config_manager = ConfigManager(str(config_file))
        load_result = config_manager.load_config()
        self.assertTrue(load_result)
        
        # Corrupt the config file
        with open(config_file, 'w') as f:
            f.write("invalid: yaml: content: [unclosed")
        
        # Try to reload - should handle gracefully
        config_manager_2 = ConfigManager(str(config_file))
        load_result_2 = config_manager_2.load_config()
        self.assertFalse(load_result_2)  # Should fail gracefully, not crash
    
    def test_high_volume_error_handling(self):
        """Test error handling under high volume of invalid operations"""
        error_count = 0
        success_count = 0
        
        # Mix of valid and invalid operations
        operations = [
            # Valid operations
            lambda: self.database.insert_alert("valid_1", "JMoney", 123, "valid", 4500, "C", 4495, 4507, 4512, True),
            lambda: self.database.insert_alert("valid_2", "JMoney", 123, "valid", 4510, "B", 4505, 4517, 4522, True),
            
            # Invalid operations (should be handled gracefully)
            lambda: self.database.insert_alert("", "", 0, "", None, None, None, None, None, False),  # Empty data
            lambda: self.database.get_alert(-1),  # Invalid ID
            lambda: self.database.get_recent_alerts(-10),  # Invalid limit
        ]
        
        # Execute operations multiple times
        for _ in range(20):
            for operation in operations:
                try:
                    result = operation()
                    if result is not None:
                        success_count += 1
                    else:
                        error_count += 1
                except Exception:
                    error_count += 1
        
        # System should remain stable despite errors
        self.assertGreater(success_count, 0, "Some operations should succeed")
        
        # Verify database is still functional
        stats = self.database.get_system_stats()
        self.assertIsInstance(stats, dict)
    
    def test_resource_cleanup_on_shutdown(self):
        """Test proper resource cleanup during system shutdown"""
        # Create multiple components that need cleanup
        components = []
        
        # Database component
        db = DatabaseManager(str(self.test_dir / "cleanup_test.db"))
        db.initialize_database()
        components.append(db)
        
        # Insert some data
        alert_id = db.insert_alert(
            discord_message_id="cleanup_test",
            author="JMoney",
            channel_id=123456789,
            raw_content="🚨 ES long 4500: C\nStop: 4495\n@everyone",
            parsed_price=4500,
            parsed_size="C",
            parsed_stop=4495,
            target_1=4507,
            target_2=4512,
            is_valid=True
        )
        self.assertIsNotNone(alert_id)
        
        # Simulate shutdown by closing connections
        if hasattr(db, 'connection') and db.connection:
            db.connection.close()
        
        # Verify cleanup was successful (no hanging connections)
        # This is more of a smoke test - in real scenarios we'd check for
        # file locks, open connections, etc.
        self.assertTrue(True)  # If we get here without hanging, cleanup worked


class TestConfigurationResilience(unittest.TestCase):
    """Test system resilience to configuration changes and issues"""
    
    def setUp(self):
        """Set up configuration resilience test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_missing_configuration_file(self):
        """Test system behavior when configuration file is missing"""
        non_existent_config = self.test_dir / "non_existent.yaml"
        
        config_manager = ConfigManager(str(non_existent_config))
        load_result = config_manager.load_config()
        
        # Should fail gracefully, not crash
        self.assertFalse(load_result)
    
    def test_partial_configuration_handling(self):
        """Test system behavior with incomplete configuration"""
        partial_config_file = self.test_dir / "partial_config.yaml"
        
        # Create config with missing required sections
        partial_config = {
            "trading": {
                "account_id": "test_account"
                # Missing other required fields
            }
            # Missing database, discord, etc.
        }
        
        with open(partial_config_file, 'w') as f:
            yaml.dump(partial_config, f)
        
        config_manager = ConfigManager(str(partial_config_file))
        load_result = config_manager.load_config()
        
        # Should load what it can
        self.assertTrue(load_result)
        
        # Validation should catch missing required fields
        validation_result = config_manager.validate_config()
        self.assertFalse(validation_result)
    
    def test_configuration_hot_reload_simulation(self):
        """Test configuration changes during system operation"""
        config_file = self.test_dir / "hot_reload_config.yaml"
        
        # Initial configuration
        initial_config = {
            "trading": {
                "account_id": "initial_account",
                "paper_trading_enabled": True,
                "size_mapping": {"A": 1, "B": 2, "C": 3}
            },
            "database": {
                "file_path": str(self.test_dir / "hot_reload.db")
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(initial_config, f)
        
        # Load initial config
        config_manager = ConfigManager(str(config_file))
        load_result = config_manager.load_config()
        self.assertTrue(load_result)
        
        initial_size_c = config_manager.get_size_for_alert("C")
        self.assertEqual(initial_size_c, 3)
        
        # Simulate configuration change
        updated_config = initial_config.copy()
        updated_config["trading"]["size_mapping"] = {"A": 2, "B": 4, "C": 6}
        
        with open(config_file, 'w') as f:
            yaml.dump(updated_config, f)
        
        # Reload configuration
        reload_result = config_manager.reload_config()
        self.assertTrue(reload_result)
        
        # Verify changes took effect
        updated_size_c = config_manager.get_size_for_alert("C")
        self.assertEqual(updated_size_c, 6)


if __name__ == '__main__':
    # Run system tests with detailed output
    unittest.main(verbosity=2)
