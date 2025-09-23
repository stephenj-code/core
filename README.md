# Core Infrastructure & Monitoring

This repository contains core infrastructure components and comprehensive monitoring solutions for microservices.

## 🏗️ Infrastructure

The repository includes Terraform configurations for AWS infrastructure setup:
- VPC with public and private subnets
- EC2 instances with security groups
- NAT Gateway and Internet Gateway
- Network routing and associations

## 📊 Microservices Monitoring

A complete Python-based monitoring solution for microservices including:

### Key Features
- **Health Checks**: HTTP endpoint monitoring and TCP port connectivity checks
- **Metrics Collection**: System metrics (CPU, memory, disk, network) and custom application metrics
- **Alerting**: Multi-channel notifications (Slack, email, webhooks)
- **Centralized Logging**: Structured logging with Elasticsearch integration
- **Dashboard**: Real-time web dashboard with service status and metrics visualization
- **Distributed Tracing**: Request tracing across microservices
- **Reliability Patterns**: Circuit breakers, rate limiting, retry logic

### Quick Start

```bash
# Navigate to monitoring directory
cd monitoring/

# Install dependencies
pip install -r requirements.txt

# Run the demo
python demo.py

# Start the full example service
python example_service.py

# Access the dashboard
open http://localhost:5000/
```

### Production Deployment

```bash
# Deploy with automated script
sudo ./monitoring/deploy.sh deploy

# Check service status
sudo ./monitoring/deploy.sh status
```

### Architecture

The monitoring system provides a comprehensive approach to observing microservices:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Service A     │    │   Service B     │    │   Service C     │
│  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
│  │Monitoring │  │    │  │Monitoring │  │    │  │Monitoring │  │
│  │Agent      │  │    │  │Agent      │  │    │  │Agent      │  │
│  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────▼───────────────────────┐
         │           Monitoring Dashboard                │
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
│   Elasticsearch │    │   Prometheus    │    │      Slack      │
│   (Logging)     │    │   (Metrics)     │    │   (Alerting)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Monitoring Components

1. **Health Monitoring**: Automated service health checks with configurable endpoints
2. **Metrics Collection**: Real-time system and application metrics with Prometheus integration
3. **Alert Management**: Intelligent alerting with multiple notification channels and cooldown periods
4. **Structured Logging**: JSON-formatted logs with distributed tracing support
5. **Web Dashboard**: Real-time visualization of service health and performance metrics

### Integration Examples

```python
# Health Check Integration
from utils.monitoring_utils import HealthCheckEndpoint

health = HealthCheckEndpoint()
health.add_check("database", check_db_connection, critical=True)

# Metrics Collection
from utils.monitoring_utils import MetricsCollector

metrics = MetricsCollector()
metrics.increment_counter("requests_total", labels={"method": "GET"})

# Alerting
from alerting.alert_manager import AlertManager, AlertSeverity

alert = alert_manager.create_alert(
    title="High CPU Usage",
    description="CPU usage exceeded 90%",
    severity=AlertSeverity.HIGH,
    service_name="api-server"
)
```

## 📁 Directory Structure

```
├── main.tf              # Terraform infrastructure configuration
├── vars.tf              # Terraform variables
├── locals.tf            # Terraform local values
└── monitoring/          # Comprehensive monitoring solution
    ├── agents/          # Monitoring agents and collectors
    ├── alerting/        # Alert management and notification channels
    ├── config/          # Configuration management
    ├── dashboard/       # Web-based monitoring dashboard
    ├── logging/         # Centralized logging system
    ├── utils/           # Monitoring utilities and patterns
    ├── tests/           # Unit and integration tests
    ├── deploy.sh        # Production deployment script
    ├── demo.py          # Interactive demonstration
    ├── example_service.py # Complete example microservice
    └── README.md        # Detailed monitoring documentation
```

## 🚀 Getting Started

1. **Infrastructure Setup**: Use Terraform to deploy AWS infrastructure
2. **Monitoring Setup**: Deploy the monitoring system using the provided scripts
3. **Service Integration**: Integrate monitoring into your microservices using the provided libraries
4. **Dashboard Access**: Monitor your services through the web dashboard

For detailed monitoring documentation, see: [monitoring/README.md](monitoring/README.md)