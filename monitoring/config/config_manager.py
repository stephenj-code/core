"""
Configuration management for microservices monitoring
"""

import os
import yaml
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ServiceConfig:
    """Configuration for a monitored service"""
    name: str
    health_check_url: str
    expected_status: int = 200
    timeout: int = 5
    critical: bool = False
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertingConfig:
    """Configuration for alerting"""
    enabled: bool = True
    channels: list = field(default_factory=list)
    thresholds: Dict[str, float] = field(default_factory=dict)
    cooldown_minutes: int = 15


@dataclass
class MetricsConfig:
    """Configuration for metrics collection"""
    enabled: bool = True
    port: int = 8000
    interval_seconds: int = 30
    backends: list = field(default_factory=list)
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoggingConfig:
    """Configuration for logging"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_size_mb: int = 100
    backup_count: int = 5


@dataclass
class MonitoringConfig:
    """Main monitoring configuration"""
    services: list = field(default_factory=list)
    alerting: AlertingConfig = field(default_factory=AlertingConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    environment: str = "development"
    region: str = "us-east-1"


class ConfigManager:
    """Manages configuration loading and validation"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = None
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration path"""
        # Check environment variable first
        if 'MONITORING_CONFIG_PATH' in os.environ:
            return os.environ['MONITORING_CONFIG_PATH']
        
        # Check common locations
        possible_paths = [
            '/etc/monitoring/config.yaml',
            '/opt/monitoring/config.yaml',
            './config/monitoring.yaml',
            './monitoring.yaml'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Return default path in current directory
        return './monitoring_config.yaml'
    
    def load_config(self) -> MonitoringConfig:
        """Load configuration from file"""
        if not os.path.exists(self.config_path):
            return self._create_default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            self.config = self._parse_config(data)
            return self.config
            
        except Exception as e:
            raise ValueError(f"Error loading config from {self.config_path}: {e}")
    
    def save_config(self, config: MonitoringConfig):
        """Save configuration to file"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Convert to dict
        config_dict = self._config_to_dict(config)
        
        try:
            with open(self.config_path, 'w') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_dict, f, indent=2)
                    
        except Exception as e:
            raise ValueError(f"Error saving config to {self.config_path}: {e}")
    
    def _create_default_config(self) -> MonitoringConfig:
        """Create default configuration"""
        config = MonitoringConfig(
            services=[
                {
                    "name": "example-api",
                    "health_check_url": "http://localhost:8080/health",
                    "expected_status": 200,
                    "timeout": 5,
                    "critical": True,
                    "tags": {"team": "backend", "env": "production"}
                }
            ],
            alerting=AlertingConfig(
                enabled=True,
                channels=[
                    {
                        "type": "slack",
                        "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
                        "channel": "#alerts"
                    },
                    {
                        "type": "email",
                        "smtp_server": "smtp.gmail.com",
                        "smtp_port": 587,
                        "from_email": "alerts@yourcompany.com",
                        "to_emails": ["team@yourcompany.com"]
                    }
                ],
                thresholds={
                    "cpu_percent": 80.0,
                    "memory_percent": 85.0,
                    "disk_percent": 90.0,
                    "response_time_ms": 5000.0
                },
                cooldown_minutes=15
            ),
            metrics=MetricsConfig(
                enabled=True,
                port=8000,
                interval_seconds=30,
                backends=[
                    {
                        "type": "prometheus",
                        "port": 8000
                    },
                    {
                        "type": "elasticsearch",
                        "url": "http://localhost:9200",
                        "index_pattern": "monitoring-{date}"
                    }
                ]
            ),
            logging=LoggingConfig(
                level="INFO",
                file_path="/var/log/monitoring.log"
            ),
            environment="development",
            region="us-east-1"
        )
        
        # Save the default config
        self.save_config(config)
        return config
    
    def _parse_config(self, data: Dict[str, Any]) -> MonitoringConfig:
        """Parse configuration data into MonitoringConfig object"""
        services = []
        for service_data in data.get('services', []):
            services.append(ServiceConfig(**service_data))
        
        alerting_data = data.get('alerting', {})
        alerting = AlertingConfig(
            enabled=alerting_data.get('enabled', True),
            channels=alerting_data.get('channels', []),
            thresholds=alerting_data.get('thresholds', {}),
            cooldown_minutes=alerting_data.get('cooldown_minutes', 15)
        )
        
        metrics_data = data.get('metrics', {})
        metrics = MetricsConfig(
            enabled=metrics_data.get('enabled', True),
            port=metrics_data.get('port', 8000),
            interval_seconds=metrics_data.get('interval_seconds', 30),
            backends=metrics_data.get('backends', []),
            custom_metrics=metrics_data.get('custom_metrics', {})
        )
        
        logging_data = data.get('logging', {})
        logging_config = LoggingConfig(
            level=logging_data.get('level', 'INFO'),
            format=logging_data.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            file_path=logging_data.get('file_path'),
            max_size_mb=logging_data.get('max_size_mb', 100),
            backup_count=logging_data.get('backup_count', 5)
        )
        
        return MonitoringConfig(
            services=services,
            alerting=alerting,
            metrics=metrics,
            logging=logging_config,
            environment=data.get('environment', 'development'),
            region=data.get('region', 'us-east-1')
        )
    
    def _config_to_dict(self, config: MonitoringConfig) -> Dict[str, Any]:
        """Convert MonitoringConfig object to dictionary"""
        return {
            'services': [
                {
                    'name': service.name,
                    'health_check_url': service.health_check_url,
                    'expected_status': service.expected_status,
                    'timeout': service.timeout,
                    'critical': service.critical,
                    'tags': service.tags
                }
                for service in config.services
            ],
            'alerting': {
                'enabled': config.alerting.enabled,
                'channels': config.alerting.channels,
                'thresholds': config.alerting.thresholds,
                'cooldown_minutes': config.alerting.cooldown_minutes
            },
            'metrics': {
                'enabled': config.metrics.enabled,
                'port': config.metrics.port,
                'interval_seconds': config.metrics.interval_seconds,
                'backends': config.metrics.backends,
                'custom_metrics': config.metrics.custom_metrics
            },
            'logging': {
                'level': config.logging.level,
                'format': config.logging.format,
                'file_path': config.logging.file_path,
                'max_size_mb': config.logging.max_size_mb,
                'backup_count': config.logging.backup_count
            },
            'environment': config.environment,
            'region': config.region
        }
    
    def validate_config(self, config: MonitoringConfig) -> bool:
        """Validate configuration"""
        errors = []
        
        # Validate services
        for service in config.services:
            if not service.name:
                errors.append("Service name cannot be empty")
            if not service.health_check_url:
                errors.append(f"Health check URL required for service {service.name}")
        
        # Validate alerting
        if config.alerting.enabled and not config.alerting.channels:
            errors.append("At least one alerting channel required when alerting is enabled")
        
        # Validate metrics
        if config.metrics.enabled:
            if config.metrics.port < 1 or config.metrics.port > 65535:
                errors.append("Metrics port must be between 1 and 65535")
            if config.metrics.interval_seconds < 1:
                errors.append("Metrics interval must be at least 1 second")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        return True
    
    def get_service_config(self, service_name: str) -> Optional[ServiceConfig]:
        """Get configuration for a specific service"""
        if not self.config:
            self.load_config()
        
        for service in self.config.services:
            if service.name == service_name:
                return service
        
        return None
    
    def update_service_config(self, service_name: str, updates: Dict[str, Any]):
        """Update configuration for a specific service"""
        if not self.config:
            self.load_config()
        
        for i, service in enumerate(self.config.services):
            if service.name == service_name:
                # Update the service configuration
                for key, value in updates.items():
                    if hasattr(service, key):
                        setattr(service, key, value)
                
                self.save_config(self.config)
                return
        
        raise ValueError(f"Service {service_name} not found in configuration")


def load_monitoring_config(config_path: Optional[str] = None) -> MonitoringConfig:
    """Convenience function to load monitoring configuration"""
    manager = ConfigManager(config_path)
    return manager.load_config()


if __name__ == "__main__":
    # Example usage
    manager = ConfigManager("./monitoring_config.yaml")
    config = manager.load_config()
    
    print(f"Loaded configuration for {len(config.services)} services")
    print(f"Metrics enabled: {config.metrics.enabled}")
    print(f"Alerting enabled: {config.alerting.enabled}")