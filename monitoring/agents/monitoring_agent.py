"""
Microservices Monitoring Agent

This module provides comprehensive monitoring capabilities for microservices
including health checks, metrics collection, logging, and alerting.
"""

import time
import json
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
import psutil
import requests
from prometheus_client import start_http_server, Gauge, Counter, Histogram
from prometheus_client.core import CollectorRegistry


@dataclass
class ServiceHealth:
    """Represents the health status of a service"""
    service_name: str
    status: str  # 'healthy', 'unhealthy', 'degraded'
    timestamp: datetime
    response_time_ms: float
    details: Dict = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class SystemMetrics:
    """System-level metrics"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class HealthChecker:
    """Performs health checks on services"""
    
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
    
    def check_http_endpoint(self, url: str, expected_status: int = 200) -> ServiceHealth:
        """Check HTTP endpoint health"""
        start_time = time.time()
        service_name = self._extract_service_name(url)
        
        try:
            response = requests.get(url, timeout=self.timeout)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == expected_status:
                status = 'healthy'
                details = {'status_code': response.status_code}
            else:
                status = 'unhealthy'
                details = {
                    'status_code': response.status_code,
                    'expected': expected_status
                }
                
        except requests.exceptions.RequestException as e:
            response_time = (time.time() - start_time) * 1000
            status = 'unhealthy'
            details = {'error': str(e)}
        
        return ServiceHealth(
            service_name=service_name,
            status=status,
            timestamp=datetime.now(),
            response_time_ms=response_time,
            details=details
        )
    
    def check_tcp_port(self, host: str, port: int) -> ServiceHealth:
        """Check TCP port connectivity"""
        import socket
        start_time = time.time()
        service_name = f"{host}:{port}"
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            response_time = (time.time() - start_time) * 1000
            
            if result == 0:
                status = 'healthy'
                details = {'port_open': True}
            else:
                status = 'unhealthy'
                details = {'port_open': False, 'error_code': result}
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            status = 'unhealthy'
            details = {'error': str(e)}
        
        return ServiceHealth(
            service_name=service_name,
            status=status,
            timestamp=datetime.now(),
            response_time_ms=response_time,
            details=details
        )
    
    def _extract_service_name(self, url: str) -> str:
        """Extract service name from URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.hostname}:{parsed.port or 80}"


class MetricsCollector:
    """Collects system and application metrics"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self.logger = logging.getLogger(__name__)
        
        # Prometheus metrics
        self.cpu_gauge = Gauge('system_cpu_percent', 'CPU usage percentage', registry=self.registry)
        self.memory_gauge = Gauge('system_memory_percent', 'Memory usage percentage', registry=self.registry)
        self.disk_gauge = Gauge('system_disk_percent', 'Disk usage percentage', registry=self.registry)
        self.network_sent_counter = Counter('system_network_bytes_sent_total', 'Network bytes sent', registry=self.registry)
        self.network_recv_counter = Counter('system_network_bytes_recv_total', 'Network bytes received', registry=self.registry)
        
        # Service metrics
        self.http_requests_total = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'], registry=self.registry)
        self.http_request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'], registry=self.registry)
        self.service_health_gauge = Gauge('service_health_status', 'Service health status (1=healthy, 0=unhealthy)', ['service'], registry=self.registry)
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_usage_percent=disk.percent,
            network_bytes_sent=network.bytes_sent,
            network_bytes_recv=network.bytes_recv,
            timestamp=datetime.now()
        )
        
        # Update Prometheus metrics
        self.cpu_gauge.set(cpu_percent)
        self.memory_gauge.set(memory.percent)
        self.disk_gauge.set(disk.percent)
        
        return metrics
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        self.http_requests_total.labels(method=method, endpoint=endpoint, status=status_code).inc()
        self.http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def update_service_health(self, service_name: str, is_healthy: bool):
        """Update service health metric"""
        self.service_health_gauge.labels(service=service_name).set(1 if is_healthy else 0)


class MonitoringAgent:
    """Main monitoring agent that orchestrates all monitoring activities"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.health_checker = HealthChecker(timeout=config.get('health_check_timeout', 5))
        self.metrics_collector = MetricsCollector()
        self.logger = self._setup_logging()
        self.running = False
        self.threads = []
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def start(self):
        """Start the monitoring agent"""
        self.running = True
        self.logger.info("Starting monitoring agent...")
        
        # Start Prometheus metrics server
        metrics_port = self.config.get('metrics_port', 8000)
        start_http_server(metrics_port, registry=self.metrics_collector.registry)
        self.logger.info(f"Prometheus metrics server started on port {metrics_port}")
        
        # Start monitoring threads
        if self.config.get('collect_system_metrics', True):
            thread = threading.Thread(target=self._system_metrics_loop)
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
        
        if self.config.get('health_checks', []):
            thread = threading.Thread(target=self._health_check_loop)
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
        
        self.logger.info("Monitoring agent started successfully")
    
    def stop(self):
        """Stop the monitoring agent"""
        self.running = False
        self.logger.info("Stopping monitoring agent...")
        
        for thread in self.threads:
            thread.join(timeout=5)
        
        self.logger.info("Monitoring agent stopped")
    
    def _system_metrics_loop(self):
        """Continuous system metrics collection"""
        interval = self.config.get('metrics_interval', 30)
        
        while self.running:
            try:
                metrics = self.metrics_collector.collect_system_metrics()
                self.logger.debug(f"Collected system metrics: {metrics}")
                
                # Send metrics to configured backends
                self._send_metrics_to_backends(metrics)
                
            except Exception as e:
                self.logger.error(f"Error collecting system metrics: {e}")
            
            time.sleep(interval)
    
    def _health_check_loop(self):
        """Continuous health checking"""
        interval = self.config.get('health_check_interval', 60)
        
        while self.running:
            try:
                for check_config in self.config.get('health_checks', []):
                    health = self._perform_health_check(check_config)
                    self.logger.info(f"Health check result: {health}")
                    
                    # Update metrics
                    is_healthy = health.status == 'healthy'
                    self.metrics_collector.update_service_health(health.service_name, is_healthy)
                    
                    # Send to backends
                    self._send_health_to_backends(health)
                    
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
            
            time.sleep(interval)
    
    def _perform_health_check(self, check_config: Dict) -> ServiceHealth:
        """Perform a single health check"""
        check_type = check_config.get('type', 'http')
        
        if check_type == 'http':
            return self.health_checker.check_http_endpoint(
                check_config['url'],
                check_config.get('expected_status', 200)
            )
        elif check_type == 'tcp':
            return self.health_checker.check_tcp_port(
                check_config['host'],
                check_config['port']
            )
        else:
            raise ValueError(f"Unknown health check type: {check_type}")
    
    def _send_metrics_to_backends(self, metrics: SystemMetrics):
        """Send metrics to configured backends"""
        backends = self.config.get('metrics_backends', [])
        
        for backend in backends:
            try:
                if backend['type'] == 'elasticsearch':
                    self._send_to_elasticsearch(backend, 'system_metrics', metrics.to_dict())
                elif backend['type'] == 'influxdb':
                    self._send_to_influxdb(backend, 'system_metrics', metrics.to_dict())
                elif backend['type'] == 'webhook':
                    self._send_to_webhook(backend, metrics.to_dict())
                    
            except Exception as e:
                self.logger.error(f"Error sending metrics to {backend['type']}: {e}")
    
    def _send_health_to_backends(self, health: ServiceHealth):
        """Send health status to configured backends"""
        backends = self.config.get('health_backends', [])
        
        for backend in backends:
            try:
                if backend['type'] == 'elasticsearch':
                    self._send_to_elasticsearch(backend, 'health_checks', health.to_dict())
                elif backend['type'] == 'webhook':
                    self._send_to_webhook(backend, health.to_dict())
                    
            except Exception as e:
                self.logger.error(f"Error sending health data to {backend['type']}: {e}")
    
    def _send_to_elasticsearch(self, config: Dict, index: str, data: Dict):
        """Send data to Elasticsearch"""
        from elasticsearch import Elasticsearch
        
        es = Elasticsearch([config['url']])
        es.index(index=index, body=data)
    
    def _send_to_influxdb(self, config: Dict, measurement: str, data: Dict):
        """Send data to InfluxDB"""
        from influxdb_client import InfluxDBClient, Point
        from influxdb_client.client.write_api import SYNCHRONOUS
        
        client = InfluxDBClient(
            url=config['url'],
            token=config['token'],
            org=config['org']
        )
        
        write_api = client.write_api(write_options=SYNCHRONOUS)
        
        point = Point(measurement)
        for field, value in data.items():
            if field != 'timestamp':
                point.field(field, value)
        
        write_api.write(bucket=config['bucket'], record=point)
        client.close()
    
    def _send_to_webhook(self, config: Dict, data: Dict):
        """Send data to webhook endpoint"""
        requests.post(
            config['url'],
            json=data,
            headers=config.get('headers', {}),
            timeout=10
        )


# Decorator for automatic HTTP request monitoring
def monitor_endpoint(metrics_collector: MetricsCollector):
    """Decorator to automatically monitor HTTP endpoints"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            method = kwargs.get('method', 'GET')
            endpoint = func.__name__
            
            try:
                result = func(*args, **kwargs)
                status_code = getattr(result, 'status_code', 200)
                duration = time.time() - start_time
                
                metrics_collector.record_http_request(method, endpoint, status_code, duration)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_http_request(method, endpoint, 500, duration)
                raise
        
        return wrapper
    return decorator


if __name__ == "__main__":
    # Example configuration
    config = {
        "metrics_port": 8000,
        "metrics_interval": 30,
        "health_check_interval": 60,
        "health_check_timeout": 5,
        "collect_system_metrics": True,
        "health_checks": [
            {
                "type": "http",
                "url": "http://localhost:8080/health",
                "expected_status": 200
            },
            {
                "type": "tcp",
                "host": "localhost",
                "port": 5432
            }
        ],
        "metrics_backends": [
            {
                "type": "elasticsearch",
                "url": "http://localhost:9200"
            }
        ]
    }
    
    agent = MonitoringAgent(config)
    
    try:
        agent.start()
        
        # Keep the agent running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        agent.stop()