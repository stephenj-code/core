"""
Web-based monitoring dashboard for microservices

Provides real-time visualization of service health, metrics, and alerts.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, jsonify, request, send_from_directory
import requests
from prometheus_client.parser import text_string_to_metric_families
import logging

app = Flask(__name__)


class DashboardAPI:
    """API layer for the monitoring dashboard"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics_endpoints = config.get('metrics_endpoints', [])
        self.health_endpoints = config.get('health_endpoints', [])
        self.logger = logging.getLogger(__name__)
    
    def get_services_overview(self) -> Dict[str, Any]:
        """Get overview of all monitored services"""
        services = []
        
        for endpoint in self.health_endpoints:
            try:
                service_health = self._check_service_health(endpoint)
                services.append(service_health)
            except Exception as e:
                self.logger.error(f"Error checking health for {endpoint['name']}: {e}")
                services.append({
                    'name': endpoint['name'],
                    'status': 'unknown',
                    'response_time': 0,
                    'last_checked': datetime.now().isoformat(),
                    'error': str(e)
                })
        
        # Calculate overall system health
        healthy_count = sum(1 for s in services if s['status'] == 'healthy')
        total_count = len(services)
        overall_health = 'healthy' if healthy_count == total_count else 'degraded' if healthy_count > 0 else 'unhealthy'
        
        return {
            'overall_health': overall_health,
            'healthy_services': healthy_count,
            'total_services': total_count,
            'services': services,
            'last_updated': datetime.now().isoformat()
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        metrics = {}
        
        for endpoint in self.metrics_endpoints:
            try:
                endpoint_metrics = self._fetch_prometheus_metrics(endpoint['url'])
                metrics[endpoint['name']] = endpoint_metrics
            except Exception as e:
                self.logger.error(f"Error fetching metrics from {endpoint['name']}: {e}")
                metrics[endpoint['name']] = {'error': str(e)}
        
        return metrics
    
    def get_historical_metrics(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical metrics data"""
        # This would typically query a time-series database
        # For demo purposes, we'll generate sample data
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        data_points = []
        current_time = start_time
        
        while current_time <= end_time:
            # Generate sample data based on metric type
            if 'cpu' in metric_name.lower():
                value = 20 + (hash(str(current_time)) % 60)  # 20-80% CPU
            elif 'memory' in metric_name.lower():
                value = 30 + (hash(str(current_time)) % 50)  # 30-80% Memory
            elif 'response_time' in metric_name.lower():
                value = 100 + (hash(str(current_time)) % 400)  # 100-500ms
            else:
                value = hash(str(current_time)) % 100
            
            data_points.append({
                'timestamp': current_time.isoformat(),
                'value': value
            })
            
            current_time += timedelta(minutes=5)
        
        return data_points
    
    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        # This would typically query an alerts database
        # For demo purposes, we'll return sample alerts
        sample_alerts = [
            {
                'id': 'alert-001',
                'title': 'High CPU Usage',
                'description': 'CPU usage exceeded 90% threshold',
                'severity': 'high',
                'service': 'api-server',
                'status': 'firing',
                'timestamp': (datetime.now() - timedelta(minutes=30)).isoformat()
            },
            {
                'id': 'alert-002',
                'title': 'Database Connection Error',
                'description': 'Failed to connect to primary database',
                'severity': 'critical',
                'service': 'database',
                'status': 'resolved',
                'timestamp': (datetime.now() - timedelta(hours=2)).isoformat()
            }
        ]
        
        return sample_alerts[:limit]
    
    def _check_service_health(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """Check health of a single service"""
        start_time = time.time()
        
        try:
            response = requests.get(
                endpoint['url'], 
                timeout=endpoint.get('timeout', 5)
            )
            response_time = (time.time() - start_time) * 1000
            
            status = 'healthy' if response.status_code == 200 else 'unhealthy'
            
            return {
                'name': endpoint['name'],
                'status': status,
                'response_time': round(response_time, 2),
                'status_code': response.status_code,
                'last_checked': datetime.now().isoformat(),
                'url': endpoint['url']
            }
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                'name': endpoint['name'],
                'status': 'unhealthy',
                'response_time': round(response_time, 2),
                'error': str(e),
                'last_checked': datetime.now().isoformat(),
                'url': endpoint['url']
            }
    
    def _fetch_prometheus_metrics(self, url: str) -> Dict[str, Any]:
        """Fetch metrics from Prometheus endpoint"""
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        metrics = {}
        
        # Parse Prometheus metrics format
        for family in text_string_to_metric_families(response.text):
            for sample in family.samples:
                metric_name = sample.name
                if metric_name not in metrics:
                    metrics[metric_name] = []
                
                metrics[metric_name].append({
                    'labels': sample.labels,
                    'value': sample.value,
                    'timestamp': datetime.now().isoformat()
                })
        
        return metrics


# Initialize dashboard API
dashboard_config = {
    'health_endpoints': [
        {'name': 'API Server', 'url': 'http://localhost:8080/health'},
        {'name': 'Database', 'url': 'http://localhost:5432/health'},
        {'name': 'Cache', 'url': 'http://localhost:6379/health'}
    ],
    'metrics_endpoints': [
        {'name': 'application', 'url': 'http://localhost:8000/metrics'}
    ]
}

dashboard_api = DashboardAPI(dashboard_config)


# Flask routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/services')
def api_services():
    """API endpoint for services overview"""
    return jsonify(dashboard_api.get_services_overview())


@app.route('/api/metrics')
def api_metrics():
    """API endpoint for current metrics"""
    return jsonify(dashboard_api.get_system_metrics())


@app.route('/api/metrics/history')
def api_metrics_history():
    """API endpoint for historical metrics"""
    metric_name = request.args.get('metric', 'cpu_percent')
    hours = int(request.args.get('hours', 24))
    
    data = dashboard_api.get_historical_metrics(metric_name, hours)
    return jsonify(data)


@app.route('/api/alerts')
def api_alerts():
    """API endpoint for alerts"""
    limit = int(request.args.get('limit', 50))
    return jsonify(dashboard_api.get_alerts(limit))


@app.route('/health')
def health_check():
    """Health check endpoint for the dashboard itself"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


# Create the HTML template
dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Microservices Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .card h3 {
            margin-bottom: 1rem;
            color: #555;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-healthy { background-color: #4CAF50; }
        .status-unhealthy { background-color: #f44336; }
        .status-degraded { background-color: #ff9800; }
        .status-unknown { background-color: #9e9e9e; }
        
        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }
        
        .metric-label {
            color: #666;
            font-size: 0.9rem;
        }
        
        .service-list {
            list-style: none;
        }
        
        .service-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #eee;
        }
        
        .service-item:last-child {
            border-bottom: none;
        }
        
        .response-time {
            font-size: 0.8rem;
            color: #666;
        }
        
        .alert {
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 4px;
            border-left: 4px solid;
        }
        
        .alert-critical { border-left-color: #f44336; background-color: #ffebee; }
        .alert-high { border-left-color: #ff9800; background-color: #fff3e0; }
        .alert-medium { border-left-color: #2196f3; background-color: #e3f2fd; }
        .alert-low { border-left-color: #4caf50; background-color: #e8f5e8; }
        
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 1rem;
        }
        
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
        }
        
        .refresh-btn:hover {
            background: #5a67d8;
        }
        
        .last-updated {
            font-size: 0.8rem;
            color: #666;
            margin-top: 1rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>Microservices Monitoring Dashboard</h1>
            <p>Real-time monitoring and alerting for your microservices</p>
        </div>
    </div>
    
    <div class="container">
        <div class="grid">
            <!-- System Overview -->
            <div class="card">
                <h3>System Overview</h3>
                <div id="system-overview">
                    <div class="metric-value" id="healthy-services">-</div>
                    <div class="metric-label">Healthy Services</div>
                    <div style="margin-top: 1rem;">
                        <span class="status-indicator" id="overall-status"></span>
                        <span id="overall-status-text">Loading...</span>
                    </div>
                </div>
                <button class="refresh-btn" onclick="refreshData()">Refresh</button>
                <div class="last-updated" id="last-updated">Loading...</div>
            </div>
            
            <!-- Services Status -->
            <div class="card">
                <h3>Services Status</h3>
                <ul class="service-list" id="services-list">
                    <li>Loading services...</li>
                </ul>
            </div>
            
            <!-- Recent Alerts -->
            <div class="card">
                <h3>Recent Alerts</h3>
                <div id="alerts-list">
                    <p>Loading alerts...</p>
                </div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="grid">
            <div class="card">
                <h3>CPU Usage (24h)</h3>
                <div class="chart-container">
                    <canvas id="cpu-chart"></canvas>
                </div>
            </div>
            
            <div class="card">
                <h3>Memory Usage (24h)</h3>
                <div class="chart-container">
                    <canvas id="memory-chart"></canvas>
                </div>
            </div>
            
            <div class="card">
                <h3>Response Time (24h)</h3>
                <div class="chart-container">
                    <canvas id="response-chart"></canvas>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let charts = {};
        
        async function fetchData(endpoint) {
            try {
                const response = await fetch(endpoint);
                return await response.json();
            } catch (error) {
                console.error(`Error fetching ${endpoint}:`, error);
                return null;
            }
        }
        
        async function updateSystemOverview() {
            const data = await fetchData('/api/services');
            if (!data) return;
            
            document.getElementById('healthy-services').textContent = 
                `${data.healthy_services}/${data.total_services}`;
            
            const statusIndicator = document.getElementById('overall-status');
            const statusText = document.getElementById('overall-status-text');
            
            statusIndicator.className = `status-indicator status-${data.overall_health}`;
            statusText.textContent = data.overall_health.charAt(0).toUpperCase() + 
                                   data.overall_health.slice(1);
            
            document.getElementById('last-updated').textContent = 
                `Last updated: ${new Date(data.last_updated).toLocaleTimeString()}`;
        }
        
        async function updateServicesList() {
            const data = await fetchData('/api/services');
            if (!data) return;
            
            const servicesList = document.getElementById('services-list');
            servicesList.innerHTML = '';
            
            data.services.forEach(service => {
                const li = document.createElement('li');
                li.className = 'service-item';
                li.innerHTML = `
                    <div>
                        <span class="status-indicator status-${service.status}"></span>
                        ${service.name}
                    </div>
                    <div class="response-time">${service.response_time}ms</div>
                `;
                servicesList.appendChild(li);
            });
        }
        
        async function updateAlerts() {
            const data = await fetchData('/api/alerts');
            if (!data) return;
            
            const alertsList = document.getElementById('alerts-list');
            alertsList.innerHTML = '';
            
            if (data.length === 0) {
                alertsList.innerHTML = '<p>No recent alerts</p>';
                return;
            }
            
            data.slice(0, 5).forEach(alert => {
                const div = document.createElement('div');
                div.className = `alert alert-${alert.severity}`;
                div.innerHTML = `
                    <strong>${alert.title}</strong><br>
                    <small>${alert.service} - ${new Date(alert.timestamp).toLocaleString()}</small><br>
                    ${alert.description}
                `;
                alertsList.appendChild(div);
            });
        }
        
        async function createChart(canvasId, metricName, label, color) {
            const data = await fetchData(`/api/metrics/history?metric=${metricName}&hours=24`);
            if (!data) return;
            
            const ctx = document.getElementById(canvasId).getContext('2d');
            
            if (charts[canvasId]) {
                charts[canvasId].destroy();
            }
            
            charts[canvasId] = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(point => new Date(point.timestamp).toLocaleTimeString()),
                    datasets: [{
                        label: label,
                        data: data.map(point => point.value),
                        borderColor: color,
                        backgroundColor: color + '20',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }
        
        async function updateCharts() {
            await createChart('cpu-chart', 'cpu_percent', 'CPU %', '#ff6384');
            await createChart('memory-chart', 'memory_percent', 'Memory %', '#36a2eb');
            await createChart('response-chart', 'response_time', 'Response Time (ms)', '#4bc0c0');
        }
        
        async function refreshData() {
            await Promise.all([
                updateSystemOverview(),
                updateServicesList(),
                updateAlerts(),
                updateCharts()
            ]);
        }
        
        // Initial load and auto-refresh
        refreshData();
        setInterval(refreshData, 30000); // Refresh every 30 seconds
    </script>
</body>
</html>
"""

# Save the HTML template
import os
os.makedirs('/home/runner/work/core/core/monitoring/dashboard/templates', exist_ok=True)

with open('/home/runner/work/core/core/monitoring/dashboard/templates/dashboard.html', 'w') as f:
    f.write(dashboard_html)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)