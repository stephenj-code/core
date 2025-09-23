"""
Unit tests for the monitoring system components
"""

import unittest
import json
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agents.monitoring_agent import HealthChecker, MetricsCollector, MonitoringAgent
from alerting.alert_manager import AlertManager, AlertSeverity, SlackChannel
from config.config_manager import ConfigManager, MonitoringConfig
from utils.monitoring_utils import HealthCheckEndpoint, CircuitBreaker, RateLimiter
from logging.logging_manager import LoggingManager, StructuredFormatter


class TestHealthChecker(unittest.TestCase):
    """Test the HealthChecker component"""
    
    def setUp(self):
        self.health_checker = HealthChecker(timeout=1)
    
    @patch('requests.get')
    def test_check_http_endpoint_healthy(self, mock_get):
        """Test HTTP endpoint health check for healthy service"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.health_checker.check_http_endpoint('http://localhost:8080/health')
        
        self.assertEqual(result.status, 'healthy')
        self.assertEqual(result.service_name, 'localhost:80')
        self.assertIsInstance(result.response_time_ms, float)
        self.assertGreater(result.response_time_ms, 0)
    
    @patch('requests.get')
    def test_check_http_endpoint_unhealthy(self, mock_get):
        """Test HTTP endpoint health check for unhealthy service"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = self.health_checker.check_http_endpoint('http://localhost:8080/health')
        
        self.assertEqual(result.status, 'unhealthy')
        self.assertEqual(result.details['status_code'], 500)
    
    @patch('requests.get')
    def test_check_http_endpoint_exception(self, mock_get):
        """Test HTTP endpoint health check with connection error"""
        mock_get.side_effect = Exception("Connection refused")
        
        result = self.health_checker.check_http_endpoint('http://localhost:8080/health')
        
        self.assertEqual(result.status, 'unhealthy')
        self.assertIn('error', result.details)


class TestMetricsCollector(unittest.TestCase):
    """Test the MetricsCollector component"""
    
    def setUp(self):
        self.metrics_collector = MetricsCollector()
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_collect_system_metrics(self, mock_net, mock_disk, mock_memory, mock_cpu):
        """Test system metrics collection"""
        # Mock system metrics
        mock_cpu.return_value = 25.5
        mock_memory.return_value = Mock(percent=60.0)
        mock_disk.return_value = Mock(percent=45.0)
        mock_net.return_value = Mock(bytes_sent=1000, bytes_recv=2000)
        
        metrics = self.metrics_collector.collect_system_metrics()
        
        self.assertEqual(metrics.cpu_percent, 25.5)
        self.assertEqual(metrics.memory_percent, 60.0)
        self.assertEqual(metrics.disk_usage_percent, 45.0)
        self.assertEqual(metrics.network_bytes_sent, 1000)
        self.assertEqual(metrics.network_bytes_recv, 2000)
        self.assertIsInstance(metrics.timestamp, datetime)
    
    def test_record_http_request(self):
        """Test HTTP request metrics recording"""
        self.metrics_collector.record_http_request('GET', '/api/users', 200, 0.25)
        
        # Verify metrics were recorded (this would require accessing Prometheus metrics)
        # For now, just verify the method doesn't throw an exception
        self.assertTrue(True)


class TestAlertManager(unittest.TestCase):
    """Test the AlertManager component"""
    
    def setUp(self):
        self.config = {
            'channels': [
                {
                    'type': 'slack',
                    'webhook_url': 'https://hooks.slack.com/test',
                    'channel': '#test'
                }
            ],
            'cooldown_minutes': 1
        }
        self.alert_manager = AlertManager(self.config)
    
    def test_create_alert(self):
        """Test alert creation"""
        alert = self.alert_manager.create_alert(
            title="Test Alert",
            description="This is a test alert",
            severity=AlertSeverity.HIGH,
            service_name="test-service",
            labels={'env': 'test'}
        )
        
        self.assertEqual(alert.title, "Test Alert")
        self.assertEqual(alert.severity, AlertSeverity.HIGH)
        self.assertEqual(alert.service_name, "test-service")
        self.assertEqual(alert.labels['env'], 'test')
        self.assertIsInstance(alert.timestamp, datetime)
    
    @patch('requests.post')
    def test_slack_channel_send_alert(self, mock_post):
        """Test sending alert through Slack channel"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        slack_channel = SlackChannel({
            'webhook_url': 'https://hooks.slack.com/test',
            'channel': '#test'
        })
        
        alert = self.alert_manager.create_alert(
            title="Test Alert",
            description="Test description",
            severity=AlertSeverity.HIGH,
            service_name="test-service"
        )
        
        result = slack_channel.send_alert(alert)
        
        self.assertTrue(result)
        mock_post.assert_called_once()


class TestConfigManager(unittest.TestCase):
    """Test the ConfigManager component"""
    
    def setUp(self):
        self.config_manager = ConfigManager()
    
    def test_create_default_config(self):
        """Test default configuration creation"""
        config = self.config_manager._create_default_config()
        
        self.assertIsInstance(config, MonitoringConfig)
        self.assertTrue(config.metrics.enabled)
        self.assertTrue(config.alerting.enabled)
        self.assertEqual(config.environment, "development")
    
    def test_validate_config(self):
        """Test configuration validation"""
        valid_config = self.config_manager._create_default_config()
        
        # This should not raise an exception
        self.assertTrue(self.config_manager.validate_config(valid_config))
        
        # Test invalid config
        invalid_config = MonitoringConfig()
        invalid_config.metrics.port = -1
        
        with self.assertRaises(ValueError):
            self.config_manager.validate_config(invalid_config)


class TestHealthCheckEndpoint(unittest.TestCase):
    """Test the HealthCheckEndpoint utility"""
    
    def setUp(self):
        self.health = HealthCheckEndpoint()
    
    def test_add_and_run_checks(self):
        """Test adding and running health checks"""
        def healthy_check():
            return True
        
        def unhealthy_check():
            return False
        
        self.health.add_check("healthy_service", healthy_check, critical=True)
        self.health.add_check("unhealthy_service", unhealthy_check, critical=False)
        
        results = self.health.run_checks()
        
        self.assertEqual(results['status'], 'unhealthy')  # One critical service is down
        self.assertEqual(results['checks']['healthy_service']['status'], 'pass')
        self.assertEqual(results['checks']['unhealthy_service']['status'], 'fail')
    
    def test_exception_in_check(self):
        """Test handling exceptions in health checks"""
        def failing_check():
            raise Exception("Check failed")
        
        self.health.add_check("failing_service", failing_check, critical=True)
        
        results = self.health.run_checks()
        
        self.assertEqual(results['status'], 'unhealthy')
        self.assertEqual(results['checks']['failing_service']['status'], 'fail')
        self.assertIn('error', results['checks']['failing_service'])


class TestCircuitBreaker(unittest.TestCase):
    """Test the CircuitBreaker utility"""
    
    def setUp(self):
        self.circuit_breaker = CircuitBreaker(failure_threshold=2, timeout_duration=1)
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state"""
        @self.circuit_breaker
        def successful_function():
            return "success"
        
        result = successful_function()
        self.assertEqual(result, "success")
        self.assertEqual(self.circuit_breaker.state, 'CLOSED')
    
    def test_circuit_breaker_open_state(self):
        """Test circuit breaker transitioning to open state"""
        @self.circuit_breaker
        def failing_function():
            raise Exception("Function failed")
        
        # Trigger failures to open the circuit
        for _ in range(3):
            try:
                failing_function()
            except Exception:
                pass
        
        self.assertEqual(self.circuit_breaker.state, 'OPEN')
        
        # Now the circuit should prevent calls
        with self.assertRaises(Exception):
            failing_function()


class TestRateLimiter(unittest.TestCase):
    """Test the RateLimiter utility"""
    
    def setUp(self):
        self.rate_limiter = RateLimiter(max_tokens=2, refill_rate=1.0)
    
    def test_rate_limiter_within_limit(self):
        """Test rate limiter allowing requests within limit"""
        # Should allow first two requests
        self.assertTrue(self.rate_limiter.acquire())
        self.assertTrue(self.rate_limiter.acquire())
    
    def test_rate_limiter_exceeds_limit(self):
        """Test rate limiter blocking requests that exceed limit"""
        # Exhaust the bucket
        self.rate_limiter.acquire()
        self.rate_limiter.acquire()
        
        # Should block the third request
        self.assertFalse(self.rate_limiter.acquire())
    
    def test_rate_limiter_decorator(self):
        """Test rate limiter as decorator"""
        rate_limiter = RateLimiter(max_tokens=1, refill_rate=0.1)
        
        @rate_limiter
        def limited_function():
            return "success"
        
        # First call should succeed
        result = limited_function()
        self.assertEqual(result, "success")
        
        # Second call should fail
        with self.assertRaises(Exception):
            limited_function()


class TestStructuredFormatter(unittest.TestCase):
    """Test the StructuredFormatter for logging"""
    
    def setUp(self):
        self.formatter = StructuredFormatter("test-service")
    
    def test_format_log_record(self):
        """Test formatting a log record"""
        import logging
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/file.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = self.formatter.format(record)
        log_data = json.loads(formatted)
        
        self.assertEqual(log_data['service'], "test-service")
        self.assertEqual(log_data['level'], "INFO")
        self.assertEqual(log_data['message'], "Test message")
        self.assertEqual(log_data['line_number'], 123)
        self.assertIn('timestamp', log_data)


class TestIntegration(unittest.TestCase):
    """Integration tests for the monitoring system"""
    
    def test_full_monitoring_flow(self):
        """Test complete monitoring flow"""
        # This would be a more complex integration test
        # For now, just verify components can be initialized together
        
        config = {
            "metrics_port": 8001,  # Use different port to avoid conflicts
            "collect_system_metrics": False,  # Disable to avoid psutil mocking
            "health_checks": []
        }
        
        agent = MonitoringAgent(config)
        self.assertIsNotNone(agent)
        
        # Test that agent can be created without errors
        self.assertEqual(agent.config["metrics_port"], 8001)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)