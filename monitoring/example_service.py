"""
Example microservice with comprehensive monitoring integration

This demonstrates how to integrate all monitoring components into a real microservice.
"""

import time
import json
import random
from datetime import datetime
from flask import Flask, request, jsonify, g
from threading import Thread
import logging
import os
import sys

# Add monitoring modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.config_manager import ConfigManager, load_monitoring_config
from agents.monitoring_agent import MonitoringAgent, monitor_endpoint
from alerting.alert_manager import AlertManager, AlertSeverity
from logging.logging_manager import LoggingManager
from utils.monitoring_utils import (
    HealthCheckEndpoint, MetricsCollector, CircuitBreaker, 
    RateLimiter, TraceContext, timing_decorator, retry_decorator
)

# Initialize Flask app
app = Flask(__name__)

# Global monitoring components
monitoring_config = None
monitoring_agent = None
alert_manager = None
logging_manager = None
health_endpoint = None
metrics_collector = None
tracer = None
logger = None


def initialize_monitoring():
    """Initialize all monitoring components"""
    global monitoring_config, monitoring_agent, alert_manager
    global logging_manager, health_endpoint, metrics_collector, tracer, logger
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        monitoring_config = config_manager.load_config()
        
        # Setup logging
        logging_config = {
            'service_name': 'example-api',
            'log_level': monitoring_config.logging.level,
            'console_logging': True,
            'file_path': monitoring_config.logging.file_path,
            'elasticsearch': {
                'url': 'http://localhost:9200',
                'index_pattern': 'logs-{date}'
            }
        }
        
        logging_manager = LoggingManager(logging_config)
        logger = logging_manager.setup_logging()
        
        # Setup metrics collector
        metrics_collector = MetricsCollector()
        
        # Setup health checks
        health_endpoint = HealthCheckEndpoint()
        health_endpoint.add_check("database", check_database_health, critical=True)
        health_endpoint.add_check("cache", check_cache_health, critical=False)
        health_endpoint.add_check("external_api", check_external_api_health, critical=False)
        
        # Setup alerting
        alert_config = {
            'channels': monitoring_config.alerting.channels,
            'cooldown_minutes': monitoring_config.alerting.cooldown_minutes
        }
        alert_manager = AlertManager(alert_config)
        
        # Setup distributed tracing
        tracer = TraceContext('example-api')
        
        # Setup monitoring agent
        agent_config = {
            "metrics_port": monitoring_config.metrics.port,
            "metrics_interval": monitoring_config.metrics.interval_seconds,
            "health_check_interval": 60,
            "collect_system_metrics": True,
            "health_checks": [
                {
                    "type": "http",
                    "url": "http://localhost:5000/health",
                    "expected_status": 200
                }
            ]
        }
        
        monitoring_agent = MonitoringAgent(agent_config)
        
        # Start monitoring agent in background
        monitoring_thread = Thread(target=monitoring_agent.start, daemon=True)
        monitoring_thread.start()
        
        logger.info("Monitoring system initialized successfully")
        
    except Exception as e:
        print(f"Error initializing monitoring: {e}")
        if logger:
            logger.error(f"Error initializing monitoring: {e}")


def check_database_health() -> bool:
    """Simulate database health check"""
    # In a real application, this would check actual database connectivity
    return random.random() > 0.1  # 90% healthy


def check_cache_health() -> bool:
    """Simulate cache health check"""
    # In a real application, this would check Redis/Memcached connectivity
    return random.random() > 0.05  # 95% healthy


def check_external_api_health() -> bool:
    """Simulate external API health check"""
    # In a real application, this would check external dependencies
    return random.random() > 0.2  # 80% healthy


@app.before_request
def before_request():
    """Setup request tracing and timing"""
    g.request_start_time = time.time()
    g.trace_id = tracer.start_trace(f"{request.method} {request.path}")
    g.span_id = tracer.start_span(f"handle_request", g.trace_id)
    
    # Add request details to trace
    tracer.add_log(g.span_id, f"Received {request.method} request to {request.path}")
    
    # Setup traced logger for this request
    g.traced_logger = logging_manager.add_trace_context(
        logger,
        trace_id=g.trace_id,
        span_id=g.span_id,
        request_id=request.headers.get('X-Request-ID', 'unknown')
    )


@app.after_request
def after_request(response):
    """Record request metrics and finish tracing"""
    duration = time.time() - g.request_start_time
    
    # Record metrics
    metrics_collector.increment_counter(
        "http_requests_total",
        labels={
            "method": request.method,
            "endpoint": request.endpoint or "unknown",
            "status": str(response.status_code)
        }
    )
    
    metrics_collector.observe_histogram(
        "http_request_duration_seconds",
        duration,
        labels={
            "method": request.method,
            "endpoint": request.endpoint or "unknown"
        }
    )
    
    # Finish tracing
    tracer.add_log(g.span_id, f"Returning {response.status_code} response")
    tracer.finish_span(g.span_id, tags={
        "http.method": request.method,
        "http.url": request.url,
        "http.status_code": response.status_code,
        "response.size": len(response.get_data())
    })
    
    # Log request
    g.traced_logger.info(
        f"{request.method} {request.path} - {response.status_code} - {duration:.3f}s"
    )
    
    return response


# API Endpoints
@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        result = health_endpoint.run_checks()
        status_code = 200 if result['status'] == 'healthy' else 503
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/metrics')
def metrics_endpoint():
    """Metrics endpoint (Prometheus format would be better in production)"""
    try:
        return jsonify(metrics_collector.get_metrics())
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/users')
@timing_decorator(metrics_collector)
def get_users():
    """Example API endpoint - Get users"""
    try:
        # Simulate database operation
        db_span = tracer.start_span("database_query", g.span_id)
        
        # Simulate some processing time
        time.sleep(random.uniform(0.01, 0.1))
        
        # Check if we should simulate an error
        if random.random() < 0.05:  # 5% error rate
            tracer.add_log(db_span, "Database query failed", level="ERROR")
            tracer.finish_span(db_span, tags={"error": True})
            raise Exception("Database connection failed")
        
        tracer.add_log(db_span, "Successfully fetched users from database")
        tracer.finish_span(db_span, tags={"db.rows": 10})
        
        # Simulate user data
        users = [
            {"id": i, "name": f"User {i}", "email": f"user{i}@example.com"}
            for i in range(1, 11)
        ]
        
        return jsonify({"users": users, "count": len(users)})
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        
        # Send alert for critical errors
        if "Database" in str(e):
            alert = alert_manager.create_alert(
                title="Database Connection Error",
                description=f"Failed to connect to database: {e}",
                severity=AlertSeverity.CRITICAL,
                service_name="example-api",
                labels={"endpoint": "/api/users", "error_type": "database"}
            )
            alert_manager.send_alert(alert)
        
        return jsonify({"error": str(e)}), 500


@app.route('/api/users/<int:user_id>')
@timing_decorator(metrics_collector)
@retry_decorator(max_retries=2, delay=0.1)
def get_user(user_id):
    """Example API endpoint - Get specific user"""
    try:
        # Start span for this operation
        span_id = tracer.start_span("get_user_by_id", g.span_id)
        tracer.add_log(span_id, f"Looking up user {user_id}")
        
        # Simulate processing
        time.sleep(random.uniform(0.005, 0.05))
        
        # Simulate user not found
        if user_id > 100:
            tracer.add_log(span_id, f"User {user_id} not found", level="WARN")
            tracer.finish_span(span_id, tags={"found": False})
            return jsonify({"error": "User not found"}), 404
        
        # Simulate occasional service unavailable
        if random.random() < 0.02:  # 2% error rate
            tracer.add_log(span_id, "Service temporarily unavailable", level="ERROR")
            tracer.finish_span(span_id, tags={"error": True})
            raise Exception("Service temporarily unavailable")
        
        user = {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
            "created_at": datetime.now().isoformat()
        }
        
        tracer.add_log(span_id, f"Successfully found user {user_id}")
        tracer.finish_span(span_id, tags={"found": True, "user.id": user_id})
        
        return jsonify(user)
        
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        return jsonify({"error": str(e)}), 503


@app.route('/api/users', methods=['POST'])
@timing_decorator(metrics_collector)
@RateLimiter(max_tokens=10, refill_rate=2.0)  # 10 requests max, refill 2 per second
def create_user():
    """Example API endpoint - Create user (rate limited)"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'email' not in data:
            return jsonify({"error": "Missing required fields: name, email"}), 400
        
        # Start span for user creation
        span_id = tracer.start_span("create_user", g.span_id)
        tracer.add_log(span_id, f"Creating user {data['name']}")
        
        # Simulate user creation processing
        time.sleep(random.uniform(0.02, 0.1))
        
        # Simulate validation errors
        if len(data['name']) < 2:
            tracer.add_log(span_id, "Validation failed: name too short", level="WARN")
            tracer.finish_span(span_id, tags={"validation_error": True})
            return jsonify({"error": "Name must be at least 2 characters"}), 400
        
        user_id = random.randint(1000, 9999)
        user = {
            "id": user_id,
            "name": data['name'],
            "email": data['email'],
            "created_at": datetime.now().isoformat()
        }
        
        tracer.add_log(span_id, f"Successfully created user {user_id}")
        tracer.finish_span(span_id, tags={"user.id": user_id, "success": True})
        
        # Increment user creation counter
        metrics_collector.increment_counter("users_created_total")
        
        return jsonify(user), 201
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/simulate-error')
def simulate_error():
    """Endpoint to simulate various error conditions for testing"""
    error_type = request.args.get('type', 'generic')
    
    if error_type == 'database':
        # Simulate database error
        alert = alert_manager.create_alert(
            title="Simulated Database Error",
            description="This is a test database error for monitoring testing",
            severity=AlertSeverity.HIGH,
            service_name="example-api",
            labels={"test": "true", "error_type": "database"}
        )
        alert_manager.send_alert(alert)
        return jsonify({"error": "Database connection failed"}), 500
        
    elif error_type == 'timeout':
        # Simulate timeout
        time.sleep(10)
        return jsonify({"message": "This should have timed out"})
        
    elif error_type == 'memory':
        # Simulate high memory usage
        big_data = ['x' * 1000000 for _ in range(100)]  # ~100MB
        metrics_collector.set_gauge("memory_usage_simulation", len(big_data))
        return jsonify({"message": "High memory usage simulated"})
        
    else:
        # Generic error
        logger.error("Simulated generic error for testing")
        return jsonify({"error": "Generic error occurred"}), 500


@app.route('/api/stress-test')
def stress_test():
    """Endpoint for stress testing the monitoring system"""
    duration = int(request.args.get('duration', 10))  # seconds
    rate = int(request.args.get('rate', 10))  # requests per second
    
    start_time = time.time()
    request_count = 0
    
    while time.time() - start_time < duration:
        # Simulate processing
        time.sleep(1.0 / rate)
        request_count += 1
        
        # Record metrics
        metrics_collector.increment_counter("stress_test_requests")
        
        # Occasionally simulate errors
        if random.random() < 0.1:  # 10% error rate
            metrics_collector.increment_counter("stress_test_errors")
    
    return jsonify({
        "message": f"Stress test completed",
        "duration": duration,
        "requests_sent": request_count,
        "rate": rate
    })


if __name__ == '__main__':
    # Initialize monitoring
    initialize_monitoring()
    
    # Start the Flask application
    logger.info("Starting example API server")
    app.run(host='0.0.0.0', port=5000, debug=False)