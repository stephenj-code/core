# Microservices Monitoring with Python

This repository provides a comprehensive monitoring solution for microservices using Python. It includes health checks, metrics collection, alerting, centralized logging, distributed tracing, and a web-based dashboard.

## 🌟 Features

### Core Monitoring Capabilities
- **Health Checks**: HTTP endpoint monitoring, TCP port checks, and custom health validators
- **Metrics Collection**: System metrics (CPU, memory, disk, network) and custom application metrics
- **Alerting**: Multi-channel notifications (Slack, email, webhooks, PagerDuty)
- **Centralized Logging**: Structured logging with Elasticsearch integration and distributed tracing
- **Dashboard**: Real-time web dashboard with charts and service status visualization
- **Distributed Tracing**: Request tracing across microservices with span correlation

### Reliability Patterns
- **Circuit Breaker**: Automatic failure detection and recovery
- **Rate Limiting**: Token bucket rate limiting for API protection
- **Retry Logic**: Exponential backoff retry mechanisms
- **Service Discovery**: Simple service registry for dynamic service location

### Infrastructure Integration
- **Prometheus Integration**: Metrics export in Prometheus format
- **Elasticsearch**: Log aggregation and search capabilities
- **InfluxDB**: Time-series metrics storage
- **Grafana**: Advanced visualization and alerting

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Microservice  │    │   Microservice  │    │   Microservice  │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │Monitoring   │ │    │ │Monitoring   │ │    │ │Monitoring   │ │
│ │Agent        │ │    │ │Agent        │ │    │ │Agent        │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────▼───────────────────────┐
         │             Monitoring Dashboard              │
         │                                               │
         │  ┌─────────────┐  ┌─────────────┐            │
         │  │  Alerting   │  │  Metrics    │            │
         │  │  Manager    │  │  Collector  │            │
         │  └─────────────┘  └─────────────┘            │
         └───────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Elasticsearch │    │   Prometheus    │    │    InfluxDB     │
│   (Logging)     │    │   (Metrics)     │    │   (Metrics)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Docker (optional, for external dependencies)
- Linux system (for production deployment)

### Basic Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd core/monitoring
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure monitoring:**
```bash
cp config/monitoring_config.yaml /etc/monitoring/monitoring_config.yaml
# Edit configuration as needed
```

4. **Start the example service:**
```bash
python example_service.py
```

### Production Deployment

For production deployment, use the provided deployment script:

```bash
sudo chmod +x deploy.sh
sudo ./deploy.sh deploy
```

This will:
- Create a dedicated monitoring user
- Set up systemd services
- Configure log rotation
- Set up Nginx reverse proxy
- Start all monitoring components

## 📊 Monitoring Components

### 1. Health Checks

```python
from utils.monitoring_utils import HealthCheckEndpoint

health = HealthCheckEndpoint()

def check_database():
    # Your database connectivity check
    return True

health.add_check("database", check_database, critical=True)
result = health.run_checks()
```

### 2. Metrics Collection

```python
from utils.monitoring_utils import MetricsCollector

metrics = MetricsCollector()

# Counter metrics
metrics.increment_counter("requests_total", labels={"method": "GET"})

# Gauge metrics
metrics.set_gauge("memory_usage_bytes", 1024*1024*100)

# Histogram metrics
metrics.observe_histogram("request_duration_seconds", 0.25)
```

### 3. Alerting

```python
from alerting.alert_manager import AlertManager, AlertSeverity

config = {
    'channels': [
        {
            'type': 'slack',
            'webhook_url': 'https://hooks.slack.com/services/...',
            'channel': '#alerts'
        }
    ]
}

alert_manager = AlertManager(config)

alert = alert_manager.create_alert(
    title="High CPU Usage",
    description="CPU usage exceeded 90%",
    severity=AlertSeverity.HIGH,
    service_name="api-server"
)

alert_manager.send_alert(alert)
```

### 4. Structured Logging

```python
from logging.logging_manager import LoggingManager

config = {
    'service_name': 'my-service',
    'elasticsearch': {
        'url': 'http://localhost:9200'
    }
}

logging_manager = LoggingManager(config)
logger = logging_manager.setup_logging()

logger.info("Service started successfully")
```

### 5. Distributed Tracing

```python
from utils.monitoring_utils import TraceContext

tracer = TraceContext('my-service')
trace_id = tracer.start_trace('process_request')
span_id = tracer.start_span('database_query')

# Your operation here

tracer.finish_span(span_id, tags={'db.table': 'users'})
```

## 🔧 Configuration

### Monitoring Configuration

The monitoring system uses a YAML configuration file located at `/etc/monitoring/monitoring_config.yaml`:

```yaml
services:
  - name: "api-server"
    health_check_url: "http://localhost:5000/health"
    expected_status: 200
    critical: true

alerting:
  enabled: true
  channels:
    - type: "slack"
      webhook_url: "https://hooks.slack.com/services/..."
      channel: "#alerts"

metrics:
  enabled: true
  port: 8000
  backends:
    - type: "prometheus"
    - type: "elasticsearch"
      url: "http://localhost:9200"

logging:
  level: "INFO"
  file_path: "/var/log/monitoring.log"
```

### Environment Variables

- `MONITORING_CONFIG_PATH`: Path to configuration file
- `MONITORING_LOG_LEVEL`: Override log level
- `MONITORING_METRICS_PORT`: Override metrics port

## 📈 Dashboard

The monitoring dashboard provides real-time visualization:

- **Service Health Overview**: Visual status of all monitored services
- **System Metrics**: CPU, memory, disk, and network usage charts
- **Recent Alerts**: Latest alerts with severity indicators
- **Request Metrics**: Response times and request rates

Access the dashboard at: `http://localhost:5000/`

## 🚨 Alerting Channels

### Slack Integration

```yaml
alerting:
  channels:
    - type: "slack"
      webhook_url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
      channel: "#alerts"
      username: "MonitoringBot"
```

### Email Notifications

```yaml
alerting:
  channels:
    - type: "email"
      smtp_server: "smtp.gmail.com"
      smtp_port: 587
      from_email: "alerts@yourcompany.com"
      to_emails:
        - "team@yourcompany.com"
```

### Webhook Integration

```yaml
alerting:
  channels:
    - type: "webhook"
      url: "https://api.pagerduty.com/incidents"
      headers:
        Authorization: "Token token=YOUR_TOKEN"
```

## 🔍 API Endpoints

### Health Check
```bash
GET /health
```
Returns service health status and dependency checks.

### Metrics
```bash
GET /metrics
```
Returns Prometheus-formatted metrics.

### Dashboard API
```bash
GET /api/services        # Service overview
GET /api/metrics         # Current metrics
GET /api/alerts          # Recent alerts
GET /api/metrics/history # Historical data
```

## 🧪 Testing

### Unit Tests
```bash
python -m pytest tests/
```

### Integration Tests
```bash
python -m pytest tests/integration/
```

### Load Testing
```bash
# Use the built-in stress test endpoint
curl "http://localhost:5000/api/stress-test?duration=60&rate=10"
```

## 🐳 Docker Support

### Using Docker Compose

```yaml
version: '3.8'
services:
  monitoring:
    build: .
    ports:
      - "5000:5000"
      - "8000:8000"
    volumes:
      - ./config:/etc/monitoring
      - ./logs:/var/log/monitoring
    environment:
      - MONITORING_CONFIG_PATH=/etc/monitoring/monitoring_config.yaml
  
  elasticsearch:
    image: elasticsearch:7.15.0
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"
  
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY monitoring/ ./monitoring/
COPY config/ ./config/

EXPOSE 5000 8000

CMD ["python", "monitoring/example_service.py"]
```

## 📝 Best Practices

### 1. Service Implementation
- Always include health check endpoints
- Use structured logging with correlation IDs
- Implement circuit breakers for external dependencies
- Add rate limiting to protect against abuse

### 2. Monitoring Strategy
- Monitor business metrics, not just technical metrics
- Set up alerts with appropriate thresholds
- Use dashboards for trend analysis
- Implement SLI/SLO monitoring

### 3. Alert Management
- Avoid alert fatigue with proper thresholds
- Use alert grouping and de-duplication
- Implement escalation policies
- Document runbooks for common alerts

### 4. Performance Considerations
- Use async logging for high-throughput services
- Batch metrics where possible
- Configure appropriate retention policies
- Monitor the monitoring system itself

## 🛠️ Extending the System

### Adding Custom Metrics

```python
class CustomMetricsCollector(MetricsCollector):
    def collect_business_metrics(self):
        # Collect business-specific metrics
        orders_count = get_orders_count()
        self.set_gauge("orders_total", orders_count)
        
        revenue = get_revenue()
        self.set_gauge("revenue_dollars", revenue)
```

### Custom Alert Channels

```python
class CustomChannel(AlertChannel):
    def send_alert(self, alert: Alert) -> bool:
        # Implement your custom notification logic
        return True
    
    def test_connection(self) -> bool:
        # Test your channel connectivity
        return True
```

### Custom Health Checks

```python
def custom_health_check():
    try:
        # Your custom health check logic
        response = external_api.ping()
        return response.status_code == 200
    except Exception:
        return False

health.add_check("external_api", custom_health_check, critical=False)
```

## 🔧 Troubleshooting

### Common Issues

1. **Services not starting:**
   - Check system logs: `journalctl -u monitoring-agent -f`
   - Verify configuration file syntax
   - Check file permissions

2. **Metrics not appearing:**
   - Verify Prometheus scraping configuration
   - Check firewall settings for port 8000
   - Ensure metrics endpoint is accessible

3. **Alerts not firing:**
   - Test alert channels with test endpoints
   - Check alert thresholds and conditions
   - Verify webhook URLs and credentials

4. **Dashboard not loading:**
   - Check if Flask application is running
   - Verify database connections
   - Check browser console for errors

### Debug Mode

Enable debug logging:
```bash
export MONITORING_LOG_LEVEL=DEBUG
systemctl restart monitoring-agent
```

View detailed logs:
```bash
journalctl -u monitoring-agent -f --no-pager
```

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Elasticsearch Guide](https://www.elastic.co/guide/)
- [Grafana Documentation](https://grafana.com/docs/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For questions and support:
- Create an issue in the repository
- Check the troubleshooting section
- Review the configuration examples

---

**Happy Monitoring! 🎉**