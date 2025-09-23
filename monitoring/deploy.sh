#!/bin/bash

# Deployment script for microservices monitoring

set -e

echo "🚀 Deploying Microservices Monitoring System"
echo "============================================="

# Configuration
MONITORING_HOME="/opt/monitoring"
PYTHON_ENV="/opt/monitoring/venv"
SERVICE_USER="monitoring"
CONFIG_DIR="/etc/monitoring"
LOG_DIR="/var/log/monitoring"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    print_status "Checking system requirements..."
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root"
        exit 1
    fi
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    
    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [[ "$(printf '%s\n' "3.7" "$python_version" | sort -V | head -n1)" != "3.7" ]]; then
        print_error "Python 3.7 or higher is required (found $python_version)"
        exit 1
    fi
    
    print_status "Python $python_version found ✓"
}

create_user() {
    print_status "Creating monitoring user..."
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -s /bin/false -d $MONITORING_HOME $SERVICE_USER
        print_status "Created user: $SERVICE_USER"
    else
        print_status "User $SERVICE_USER already exists"
    fi
}

create_directories() {
    print_status "Creating directories..."
    
    mkdir -p $MONITORING_HOME
    mkdir -p $CONFIG_DIR
    mkdir -p $LOG_DIR
    mkdir -p $MONITORING_HOME/bin
    mkdir -p $MONITORING_HOME/lib
    
    chown -R $SERVICE_USER:$SERVICE_USER $MONITORING_HOME
    chown -R $SERVICE_USER:$SERVICE_USER $LOG_DIR
    
    print_status "Directories created"
}

install_python_dependencies() {
    print_status "Setting up Python virtual environment..."
    
    # Create virtual environment
    python3 -m venv $PYTHON_ENV
    chown -R $SERVICE_USER:$SERVICE_USER $PYTHON_ENV
    
    # Activate and install dependencies
    source $PYTHON_ENV/bin/activate
    pip install --upgrade pip
    
    # Install monitoring dependencies
    pip install -r requirements.txt
    
    print_status "Python dependencies installed"
}

copy_application_files() {
    print_status "Copying application files..."
    
    # Copy monitoring modules
    cp -r agents/ $MONITORING_HOME/lib/
    cp -r alerting/ $MONITORING_HOME/lib/
    cp -r config/ $MONITORING_HOME/lib/
    cp -r dashboard/ $MONITORING_HOME/lib/
    cp -r logging/ $MONITORING_HOME/lib/
    cp -r utils/ $MONITORING_HOME/lib/
    
    # Copy main application
    cp example_service.py $MONITORING_HOME/bin/
    
    # Copy configuration
    cp config/monitoring_config.yaml $CONFIG_DIR/
    
    # Set permissions
    chown -R $SERVICE_USER:$SERVICE_USER $MONITORING_HOME/lib
    chown -R $SERVICE_USER:$SERVICE_USER $CONFIG_DIR
    chmod +x $MONITORING_HOME/bin/example_service.py
    
    print_status "Application files copied"
}

create_systemd_services() {
    print_status "Creating systemd service files..."
    
    # Monitoring Agent Service
    cat > /etc/systemd/system/monitoring-agent.service << EOF
[Unit]
Description=Microservices Monitoring Agent
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$MONITORING_HOME
Environment=PATH=$PYTHON_ENV/bin
Environment=PYTHONPATH=$MONITORING_HOME/lib
Environment=MONITORING_CONFIG_PATH=$CONFIG_DIR/monitoring_config.yaml
ExecStart=$PYTHON_ENV/bin/python -m agents.monitoring_agent
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Dashboard Service
    cat > /etc/systemd/system/monitoring-dashboard.service << EOF
[Unit]
Description=Microservices Monitoring Dashboard
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$MONITORING_HOME
Environment=PATH=$PYTHON_ENV/bin
Environment=PYTHONPATH=$MONITORING_HOME/lib
Environment=FLASK_APP=dashboard.dashboard_app
Environment=FLASK_ENV=production
ExecStart=$PYTHON_ENV/bin/python -m dashboard.dashboard_app
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Example Service
    cat > /etc/systemd/system/example-api.service << EOF
[Unit]
Description=Example API Service with Monitoring
After=network.target monitoring-agent.service
Wants=network.target
Requires=monitoring-agent.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$MONITORING_HOME
Environment=PATH=$PYTHON_ENV/bin
Environment=PYTHONPATH=$MONITORING_HOME/lib
Environment=MONITORING_CONFIG_PATH=$CONFIG_DIR/monitoring_config.yaml
ExecStart=$PYTHON_ENV/bin/python bin/example_service.py
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload
    
    print_status "Systemd services created"
}

configure_nginx() {
    print_status "Configuring Nginx reverse proxy..."
    
    if command -v nginx &> /dev/null; then
        cat > /etc/nginx/sites-available/monitoring << EOF
server {
    listen 80;
    server_name monitoring.yourdomain.com;
    
    # Dashboard
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Metrics endpoint
    location /metrics {
        proxy_pass http://localhost:8000/metrics;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://localhost:5000/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
        
        # Enable the site
        ln -sf /etc/nginx/sites-available/monitoring /etc/nginx/sites-enabled/
        nginx -t && systemctl reload nginx
        
        print_status "Nginx configured"
    else
        print_warning "Nginx not found, skipping reverse proxy configuration"
    fi
}

setup_logrotate() {
    print_status "Setting up log rotation..."
    
    cat > /etc/logrotate.d/monitoring << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
    postrotate
        systemctl reload monitoring-agent monitoring-dashboard example-api
    endscript
}
EOF

    print_status "Log rotation configured"
}

start_services() {
    print_status "Starting monitoring services..."
    
    # Enable and start services
    systemctl enable monitoring-agent
    systemctl enable monitoring-dashboard
    systemctl enable example-api
    
    systemctl start monitoring-agent
    sleep 5
    systemctl start monitoring-dashboard
    sleep 5
    systemctl start example-api
    
    print_status "Services started"
}

verify_deployment() {
    print_status "Verifying deployment..."
    
    # Check service status
    services=("monitoring-agent" "monitoring-dashboard" "example-api")
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet $service; then
            print_status "$service is running ✓"
        else
            print_error "$service is not running ✗"
        fi
    done
    
    # Check endpoints
    sleep 10
    
    if curl -s http://localhost:5000/health > /dev/null; then
        print_status "Health check endpoint accessible ✓"
    else
        print_warning "Health check endpoint not accessible"
    fi
    
    if curl -s http://localhost:8000/metrics > /dev/null; then
        print_status "Metrics endpoint accessible ✓"
    else
        print_warning "Metrics endpoint not accessible"
    fi
    
    if curl -s http://localhost:5000/ > /dev/null; then
        print_status "Dashboard accessible ✓"
    else
        print_warning "Dashboard not accessible"
    fi
}

show_summary() {
    echo ""
    echo "🎉 Deployment Complete!"
    echo "======================"
    echo ""
    echo "Services:"
    echo "  • Monitoring Agent: http://localhost:8000/metrics"
    echo "  • Dashboard: http://localhost:5000/"
    echo "  • Example API: http://localhost:5000/api/"
    echo "  • Health Check: http://localhost:5000/health"
    echo ""
    echo "Configuration:"
    echo "  • Config file: $CONFIG_DIR/monitoring_config.yaml"
    echo "  • Log directory: $LOG_DIR"
    echo "  • Service user: $SERVICE_USER"
    echo ""
    echo "Management commands:"
    echo "  • View logs: journalctl -u monitoring-agent -f"
    echo "  • Restart services: systemctl restart monitoring-agent"
    echo "  • Check status: systemctl status monitoring-agent"
    echo ""
    print_status "Monitoring system is ready!"
}

# Main deployment flow
main() {
    check_requirements
    create_user
    create_directories
    install_python_dependencies
    copy_application_files
    create_systemd_services
    configure_nginx
    setup_logrotate
    start_services
    verify_deployment
    show_summary
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "uninstall")
        print_status "Uninstalling monitoring system..."
        systemctl stop monitoring-agent monitoring-dashboard example-api || true
        systemctl disable monitoring-agent monitoring-dashboard example-api || true
        rm -f /etc/systemd/system/monitoring-*.service
        rm -f /etc/systemd/system/example-api.service
        systemctl daemon-reload
        userdel $SERVICE_USER || true
        rm -rf $MONITORING_HOME
        rm -rf $CONFIG_DIR
        print_status "Uninstallation complete"
        ;;
    "restart")
        print_status "Restarting monitoring services..."
        systemctl restart monitoring-agent monitoring-dashboard example-api
        print_status "Services restarted"
        ;;
    "status")
        print_status "Checking service status..."
        systemctl status monitoring-agent monitoring-dashboard example-api
        ;;
    *)
        echo "Usage: $0 {deploy|uninstall|restart|status}"
        exit 1
        ;;
esac