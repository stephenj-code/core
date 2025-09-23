#!/usr/bin/env python3
"""
Simple demonstration script showing basic monitoring concepts
without requiring external dependencies
"""

import sys
import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any

def setup_basic_logging():
    """Setup basic logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('demo')

class SimpleHealthChecker:
    """Simple health checker without external dependencies"""
    
    def __init__(self):
        self.checks = {}
    
    def add_check(self, name: str, check_func, critical: bool = False):
        self.checks[name] = {
            'function': check_func,
            'critical': critical
        }
    
    def run_checks(self):
        results = {}
        overall_healthy = True
        
        for name, check in self.checks.items():
            try:
                result = check['function']()
                results[name] = {
                    'status': 'pass' if result else 'fail',
                    'timestamp': datetime.now().isoformat()
                }
                
                if not result and check['critical']:
                    overall_healthy = False
                    
            except Exception as e:
                results[name] = {
                    'status': 'fail',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                
                if check['critical']:
                    overall_healthy = False
        
        return {
            'status': 'healthy' if overall_healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'checks': results
        }

class SimpleMetricsCollector:
    """Simple metrics collector"""
    
    def __init__(self):
        self.counters = {}
        self.gauges = {}
        self.histograms = {}
    
    def increment_counter(self, name: str, labels: Dict[str, str] = None):
        key = self._make_key(name, labels)
        self.counters[key] = self.counters.get(key, 0) + 1
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        key = self._make_key(name, labels)
        self.gauges[key] = value
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        key = self._make_key(name, labels)
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)
    
    def get_metrics(self):
        histogram_stats = {}
        for key, values in self.histograms.items():
            histogram_stats[key] = {
                'count': len(values),
                'sum': sum(values),
                'min': min(values) if values else 0,
                'max': max(values) if values else 0,
                'avg': sum(values) / len(values) if values else 0
            }
        
        return {
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'histograms': histogram_stats
        }
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        if not labels:
            return name
        label_str = ','.join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

class SimpleAlertManager:
    """Simple alert manager for demonstration"""
    
    def __init__(self):
        self.alerts_sent = 0
        self.alert_history = []
    
    def send_alert(self, title: str, description: str, severity: str = "medium"):
        alert = {
            'id': f"alert-{len(self.alert_history) + 1}",
            'title': title,
            'description': description,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        }
        
        self.alert_history.append(alert)
        self.alerts_sent += 1
        
        # In a real system, this would send to Slack, email, etc.
        print(f"   🚨 ALERT: {title} (Severity: {severity})")
        return True
    
    def get_stats(self):
        return {
            'total_alerts_sent': self.alerts_sent,
            'recent_alerts': self.alert_history[-5:]  # Last 5 alerts
        }

def main():
    print("🚀 Microservices Monitoring Demo (Simplified)")
    print("==============================================")
    
    # 1. Setup basic logging
    print("\n1. Setting up logging...")
    logger = setup_basic_logging()
    logger.info("Demo application starting")
    print("   ✓ Basic logging configured")
    
    # 2. Setup health checks
    print("\n2. Setting up health checks...")
    health_checker = SimpleHealthChecker()
    
    def demo_database_check():
        # Simulate database check
        import random
        return random.random() > 0.3  # 70% healthy
    
    def demo_api_check():
        # Simulate API check
        import random
        return random.random() > 0.1  # 90% healthy
    
    health_checker.add_check("database", demo_database_check, critical=True)
    health_checker.add_check("external_api", demo_api_check, critical=False)
    print("   ✓ Health checks configured")
    
    # 3. Setup metrics collection
    print("\n3. Setting up metrics collection...")
    metrics = SimpleMetricsCollector()
    print("   ✓ Metrics collector initialized")
    
    # 4. Setup alerting
    print("\n4. Setting up alerting...")
    alert_manager = SimpleAlertManager()
    print("   ✓ Alert manager configured")
    
    # 5. Demonstrate monitoring in action
    print("\n5. Running monitoring demonstration...")
    
    for i in range(5):
        print(f"\n   Cycle {i+1}/5:")
        
        # Check health
        health_result = health_checker.run_checks()
        print(f"   • Health status: {health_result['status']}")
        logger.info(f"Health check completed: {health_result['status']}")
        
        # Show individual check results
        for check_name, result in health_result['checks'].items():
            status_emoji = "✅" if result['status'] == 'pass' else "❌"
            print(f"     {status_emoji} {check_name}: {result['status']}")
        
        # Collect some metrics
        metrics.increment_counter("demo_requests_total", labels={"method": "GET", "status": "200"})
        metrics.increment_counter("demo_requests_total", labels={"method": "POST", "status": "201"})
        metrics.set_gauge("demo_active_connections", (i + 1) * 10)
        metrics.set_gauge("demo_memory_usage_mb", 256 + (i * 32))
        metrics.observe_histogram("demo_response_time_ms", 100 + (i * 25))
        print(f"   • Metrics updated (cycle {i+1})")
        
        # Send an alert if health is bad
        if health_result['status'] != 'healthy':
            alert_manager.send_alert(
                title="Service Health Degraded",
                description=f"One or more health checks failed on cycle {i+1}",
                severity="medium"
            )
            logger.warning("Health alert sent")
        
        # Simulate occasional high load alert
        if i == 3:  # Trigger alert on cycle 4
            alert_manager.send_alert(
                title="High Response Time",
                description="Average response time exceeded 200ms threshold",
                severity="high"
            )
            logger.warning("Performance alert sent")
        
        # Log some activity
        logger.info(f"Completed monitoring cycle {i+1}")
        
        if i < 4:  # Don't sleep on last iteration
            time.sleep(1)
    
    # 6. Show final metrics
    print("\n6. Final metrics summary:")
    final_metrics = metrics.get_metrics()
    
    print(f"   📊 Counters ({len(final_metrics['counters'])} metrics):")
    for name, value in final_metrics['counters'].items():
        print(f"     • {name}: {value}")
    
    print(f"   📈 Gauges ({len(final_metrics['gauges'])} metrics):")
    for name, value in final_metrics['gauges'].items():
        print(f"     • {name}: {value}")
    
    print(f"   📉 Histograms ({len(final_metrics['histograms'])} metrics):")
    for name, stats in final_metrics['histograms'].items():
        print(f"     • {name}: count={stats['count']}, avg={stats['avg']:.1f}ms")
    
    # 7. Show alerting stats
    print("\n7. Alerting summary:")
    alert_stats = alert_manager.get_stats()
    print(f"   🚨 Total alerts sent: {alert_stats['total_alerts_sent']}")
    
    if alert_stats['recent_alerts']:
        print("   📜 Recent alerts:")
        for alert in alert_stats['recent_alerts']:
            print(f"     • {alert['title']} ({alert['severity']}) - {alert['timestamp']}")
    
    # 8. Generate sample monitoring report
    print("\n8. Sample monitoring report:")
    report = {
        'timestamp': datetime.now().isoformat(),
        'system_health': health_result,
        'metrics_summary': {
            'total_requests': sum(v for k, v in final_metrics['counters'].items() if 'requests_total' in k),
            'active_connections': final_metrics['gauges'].get('demo_active_connections', 0),
            'avg_response_time': next(iter(final_metrics['histograms'].values()))['avg'] if final_metrics['histograms'] else 0
        },
        'alerts_summary': alert_stats
    }
    
    print(f"   📄 Report generated: {len(json.dumps(report, indent=2))} characters")
    
    logger.info("Demo application completed successfully")
    print("\n✅ Monitoring demonstration completed!")
    
    print("\n📚 Next Steps:")
    print("   • Install full dependencies: pip install -r requirements.txt")
    print("   • Run complete example: python example_service.py")
    print("   • Deploy to production: sudo ./deploy.sh deploy")
    print("   • View dashboard: http://localhost:5000/")
    
    # Save sample report
    with open('monitoring_report_sample.json', 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n💾 Sample report saved to: monitoring_report_sample.json")


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