#!/usr/bin/env python3
"""
Simple demonstration script showing how to use the monitoring system
"""

import sys
import os
import time
import logging
from datetime import datetime

# Add monitoring modules to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

import importlib.util

# Import monitoring modules directly
agents_spec = importlib.util.spec_from_file_location("monitoring_agent", "agents/monitoring_agent.py")
agents_module = importlib.util.module_from_spec(agents_spec)
agents_spec.loader.exec_module(agents_module)
MonitoringAgent = agents_module.MonitoringAgent

config_spec = importlib.util.spec_from_file_location("config_manager", "config/config_manager.py")
config_module = importlib.util.module_from_spec(config_spec)
config_spec.loader.exec_module(config_module)
ConfigManager = config_module.ConfigManager

alerting_spec = importlib.util.spec_from_file_location("alert_manager", "alerting/alert_manager.py")
alerting_module = importlib.util.module_from_spec(alerting_spec)
alerting_spec.loader.exec_module(alerting_module)
AlertManager = alerting_module.AlertManager
AlertSeverity = alerting_module.AlertSeverity

logging_spec = importlib.util.spec_from_file_location("logging_manager", "logging/logging_manager.py")
logging_module = importlib.util.module_from_spec(logging_spec)
logging_spec.loader.exec_module(logging_module)
LoggingManager = logging_module.LoggingManager

utils_spec = importlib.util.spec_from_file_location("monitoring_utils", "utils/monitoring_utils.py")
utils_module = importlib.util.module_from_spec(utils_spec)
utils_spec.loader.exec_module(utils_module)
HealthCheckEndpoint = utils_module.HealthCheckEndpoint
MetricsCollector = utils_module.MetricsCollector

def main():
    print("🚀 Microservices Monitoring Demo")
    print("=================================")
    
    # 1. Setup Configuration
    print("\n1. Setting up configuration...")
    config_manager = ConfigManager()
    config = config_manager.load_config()
    print(f"   ✓ Configuration loaded for {len(config.services)} services")
    
    # 2. Setup Logging
    print("\n2. Setting up structured logging...")
    logging_config = {
        'service_name': 'demo-service',
        'log_level': 'INFO',
        'console_logging': True
    }
    
    logging_manager = LoggingManager(logging_config)
    logger = logging_manager.setup_logging()
    logger.info("Demo application starting")
    print("   ✓ Structured logging configured")
    
    # 3. Setup Health Checks
    print("\n3. Setting up health checks...")
    health = HealthCheckEndpoint()
    
    def demo_database_check():
        # Simulate database check
        import random
        return random.random() > 0.2  # 80% healthy
    
    def demo_cache_check():
        # Simulate cache check
        return True
    
    health.add_check("database", demo_database_check, critical=True)
    health.add_check("cache", demo_cache_check, critical=False)
    print("   ✓ Health checks configured")
    
    # 4. Setup Metrics Collection
    print("\n4. Setting up metrics collection...")
    metrics = MetricsCollector()
    print("   ✓ Metrics collector initialized")
    
    # 5. Setup Alerting
    print("\n5. Setting up alerting...")
    alert_config = {
        'channels': [
            {
                'type': 'webhook',
                'url': 'https://httpbin.org/post',  # Test webhook
                'headers': {'Content-Type': 'application/json'}
            }
        ],
        'cooldown_minutes': 1
    }
    
    alert_manager = AlertManager(alert_config)
    print("   ✓ Alert manager configured")
    
    # 6. Demonstrate monitoring in action
    print("\n6. Running monitoring demonstration...")
    
    for i in range(5):
        print(f"\n   Cycle {i+1}/5:")
        
        # Check health
        health_result = health.run_checks()
        print(f"   • Health status: {health_result['status']}")
        logger.info(f"Health check completed: {health_result['status']}")
        
        # Collect some metrics
        metrics.increment_counter("demo_requests_total", labels={"method": "GET"})
        metrics.set_gauge("demo_active_connections", i * 10)
        metrics.observe_histogram("demo_processing_time", 0.1 + (i * 0.05))
        print(f"   • Metrics updated (requests: {i+1})")
        
        # Send an alert if health is bad
        if health_result['status'] != 'healthy':
            alert = alert_manager.create_alert(
                title="Service Health Degraded",
                description=f"Service health check failed on cycle {i+1}",
                severity=AlertSeverity.MEDIUM,
                service_name="demo-service",
                labels={'cycle': str(i+1)}
            )
            
            if alert_manager.send_alert(alert):
                print("   • Alert sent successfully")
                logger.warning("Health alert sent")
            else:
                print("   • Failed to send alert")
        
        # Log some activity
        logger.info(f"Completed monitoring cycle {i+1}")
        
        if i < 4:  # Don't sleep on last iteration
            time.sleep(2)
    
    # 7. Show final metrics
    print("\n7. Final metrics summary:")
    final_metrics = metrics.get_metrics()
    
    print(f"   • Counters: {len(final_metrics['counters'])} metrics")
    for name, value in final_metrics['counters'].items():
        print(f"     - {name}: {value}")
    
    print(f"   • Gauges: {len(final_metrics['gauges'])} metrics")
    for name, value in final_metrics['gauges'].items():
        print(f"     - {name}: {value}")
    
    print(f"   • Histograms: {len(final_metrics['histograms'])} metrics")
    for name, stats in final_metrics['histograms'].items():
        print(f"     - {name}: count={stats['count']}, avg={stats['avg']:.3f}")
    
    # 8. Show alerting stats
    print("\n8. Alerting statistics:")
    alert_stats = alert_manager.get_alert_stats()
    print(f"   • Total alerts sent: {alert_stats['total_alerts_sent']}")
    print(f"   • Unique alerts: {alert_stats['unique_alerts']}")
    print(f"   • Configured channels: {alert_stats['channels_configured']}")
    
    logger.info("Demo application completed successfully")
    print("\n✅ Monitoring demonstration completed!")
    print("\nTo see this in action with a real web service, run:")
    print("   python example_service.py")
    print("\nThen visit:")
    print("   • Dashboard: http://localhost:5000/")
    print("   • Health check: http://localhost:5000/health")
    print("   • Metrics: http://localhost:8000/metrics")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error running demo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)