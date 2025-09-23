"""
Alerting system for microservices monitoring

Supports multiple notification channels including Slack, email, webhooks, and PagerDuty.
"""

import json
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import requests
import logging
from jinja2 import Template


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    FIRING = "firing"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """Represents an alert"""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    service_name: str
    timestamp: datetime
    labels: Dict[str, str]
    annotations: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'severity': self.severity.value,
            'status': self.status.value,
            'service_name': self.service_name,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels,
            'annotations': self.annotations
        }


class AlertChannel:
    """Base class for alert notification channels"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def send_alert(self, alert: Alert) -> bool:
        """Send an alert notification"""
        raise NotImplementedError
    
    def test_connection(self) -> bool:
        """Test the connection to the notification channel"""
        raise NotImplementedError


class SlackChannel(AlertChannel):
    """Slack notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config['webhook_url']
        self.channel = config.get('channel', '#alerts')
        self.username = config.get('username', 'MonitoringBot')
    
    def send_alert(self, alert: Alert) -> bool:
        """Send alert to Slack"""
        try:
            # Choose color based on severity
            color_map = {
                AlertSeverity.LOW: '#36a64f',      # green
                AlertSeverity.MEDIUM: '#ff9500',   # orange
                AlertSeverity.HIGH: '#ff4444',     # red
                AlertSeverity.CRITICAL: '#8b0000'  # dark red
            }
            
            # Create Slack message
            attachment = {
                'color': color_map.get(alert.severity, '#36a64f'),
                'title': alert.title,
                'text': alert.description,
                'fields': [
                    {
                        'title': 'Service',
                        'value': alert.service_name,
                        'short': True
                    },
                    {
                        'title': 'Severity',
                        'value': alert.severity.value.upper(),
                        'short': True
                    },
                    {
                        'title': 'Status',
                        'value': alert.status.value.upper(),
                        'short': True
                    },
                    {
                        'title': 'Time',
                        'value': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                        'short': True
                    }
                ],
                'footer': 'Microservices Monitoring',
                'ts': int(alert.timestamp.timestamp())
            }
            
            # Add labels as fields
            for key, value in alert.labels.items():
                attachment['fields'].append({
                    'title': key.title(),
                    'value': value,
                    'short': True
                })
            
            payload = {
                'channel': self.channel,
                'username': self.username,
                'attachments': [attachment]
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            self.logger.info(f"Alert sent to Slack: {alert.title}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send alert to Slack: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test Slack webhook connection"""
        try:
            test_payload = {
                'channel': self.channel,
                'username': self.username,
                'text': 'Test message from monitoring system',
                'attachments': [{
                    'color': '#36a64f',
                    'text': 'This is a test message to verify the Slack integration is working.'
                }]
            }
            
            response = requests.post(self.webhook_url, json=test_payload, timeout=10)
            response.raise_for_status()
            return True
            
        except Exception as e:
            self.logger.error(f"Slack connection test failed: {e}")
            return False


class EmailChannel(AlertChannel):
    """Email notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_server = config['smtp_server']
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.from_email = config['from_email']
        self.to_emails = config['to_emails']
        self.use_tls = config.get('use_tls', True)
    
    def send_alert(self, alert: Alert) -> bool:
        """Send alert via email"""
        try:
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # Create HTML email body
            html_template = Template("""
            <html>
            <head></head>
            <body>
                <h2 style="color: {{ color }};">{{ title }}</h2>
                <p><strong>Description:</strong> {{ description }}</p>
                
                <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
                    <tr><td><strong>Service</strong></td><td>{{ service_name }}</td></tr>
                    <tr><td><strong>Severity</strong></td><td>{{ severity }}</td></tr>
                    <tr><td><strong>Status</strong></td><td>{{ status }}</td></tr>
                    <tr><td><strong>Time</strong></td><td>{{ timestamp }}</td></tr>
                    {% for key, value in labels.items() %}
                    <tr><td><strong>{{ key.title() }}</strong></td><td>{{ value }}</td></tr>
                    {% endfor %}
                </table>
                
                {% if annotations %}
                <h3>Additional Information:</h3>
                <ul>
                {% for key, value in annotations.items() %}
                    <li><strong>{{ key.title() }}:</strong> {{ value }}</li>
                {% endfor %}
                </ul>
                {% endif %}
                
                <p><em>Generated by Microservices Monitoring System</em></p>
            </body>
            </html>
            """)
            
            color_map = {
                AlertSeverity.LOW: 'green',
                AlertSeverity.MEDIUM: 'orange',
                AlertSeverity.HIGH: 'red',
                AlertSeverity.CRITICAL: 'darkred'
            }
            
            html_body = html_template.render(
                title=alert.title,
                description=alert.description,
                service_name=alert.service_name,
                severity=alert.severity.value.upper(),
                status=alert.status.value.upper(),
                timestamp=alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                labels=alert.labels,
                annotations=alert.annotations,
                color=color_map.get(alert.severity, 'black')
            )
            
            # Create plain text version
            text_body = f"""
Alert: {alert.title}

Description: {alert.description}
Service: {alert.service_name}
Severity: {alert.severity.value.upper()}
Status: {alert.status.value.upper()}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

Labels:
{chr(10).join(f"  {k}: {v}" for k, v in alert.labels.items())}

Generated by Microservices Monitoring System
            """
            
            # Attach both versions
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                
                server.send_message(msg)
            
            self.logger.info(f"Alert sent via email: {alert.title}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send alert via email: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test email server connection"""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
            return True
            
        except Exception as e:
            self.logger.error(f"Email connection test failed: {e}")
            return False


class WebhookChannel(AlertChannel):
    """Generic webhook notification channel"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config['url']
        self.headers = config.get('headers', {'Content-Type': 'application/json'})
        self.method = config.get('method', 'POST')
        self.auth = config.get('auth')
    
    def send_alert(self, alert: Alert) -> bool:
        """Send alert to webhook"""
        try:
            payload = alert.to_dict()
            
            kwargs = {
                'url': self.url,
                'headers': self.headers,
                'timeout': 10
            }
            
            if self.method.upper() == 'POST':
                kwargs['json'] = payload
            elif self.method.upper() == 'GET':
                kwargs['params'] = payload
            
            if self.auth:
                if self.auth['type'] == 'basic':
                    kwargs['auth'] = (self.auth['username'], self.auth['password'])
                elif self.auth['type'] == 'bearer':
                    kwargs['headers']['Authorization'] = f"Bearer {self.auth['token']}"
            
            response = requests.request(self.method, **kwargs)
            response.raise_for_status()
            
            self.logger.info(f"Alert sent to webhook: {alert.title}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send alert to webhook: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test webhook connection"""
        try:
            test_payload = {
                'test': True,
                'message': 'Test message from monitoring system',
                'timestamp': datetime.now().isoformat()
            }
            
            kwargs = {
                'url': self.url,
                'headers': self.headers,
                'timeout': 10
            }
            
            if self.method.upper() == 'POST':
                kwargs['json'] = test_payload
            elif self.method.upper() == 'GET':
                kwargs['params'] = test_payload
            
            if self.auth:
                if self.auth['type'] == 'basic':
                    kwargs['auth'] = (self.auth['username'], self.auth['password'])
                elif self.auth['type'] == 'bearer':
                    kwargs['headers']['Authorization'] = f"Bearer {self.auth['token']}"
            
            response = requests.request(self.method, **kwargs)
            response.raise_for_status()
            return True
            
        except Exception as e:
            self.logger.error(f"Webhook connection test failed: {e}")
            return False


class AlertManager:
    """Manages alert notifications and channels"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.channels = []
        self.alert_history = {}
        self.cooldown_minutes = config.get('cooldown_minutes', 15)
        self.logger = logging.getLogger(__name__)
        
        self._setup_channels()
    
    def _setup_channels(self):
        """Setup notification channels from configuration"""
        for channel_config in self.config.get('channels', []):
            try:
                channel_type = channel_config['type']
                
                if channel_type == 'slack':
                    channel = SlackChannel(channel_config)
                elif channel_type == 'email':
                    channel = EmailChannel(channel_config)
                elif channel_type == 'webhook':
                    channel = WebhookChannel(channel_config)
                else:
                    self.logger.warning(f"Unknown channel type: {channel_type}")
                    continue
                
                self.channels.append(channel)
                self.logger.info(f"Configured {channel_type} notification channel")
                
            except Exception as e:
                self.logger.error(f"Failed to setup channel {channel_config.get('type')}: {e}")
    
    def send_alert(self, alert: Alert) -> bool:
        """Send alert through all configured channels"""
        if not self.channels:
            self.logger.warning("No notification channels configured")
            return False
        
        # Check cooldown
        if self._is_in_cooldown(alert):
            self.logger.info(f"Alert {alert.id} is in cooldown period, skipping notification")
            return False
        
        success_count = 0
        
        for channel in self.channels:
            try:
                if channel.send_alert(alert):
                    success_count += 1
            except Exception as e:
                self.logger.error(f"Error sending alert through {channel.__class__.__name__}: {e}")
        
        # Update alert history
        self.alert_history[alert.id] = {
            'last_sent': datetime.now(),
            'count': self.alert_history.get(alert.id, {}).get('count', 0) + 1
        }
        
        return success_count > 0
    
    def _is_in_cooldown(self, alert: Alert) -> bool:
        """Check if alert is in cooldown period"""
        if alert.id not in self.alert_history:
            return False
        
        last_sent = self.alert_history[alert.id]['last_sent']
        cooldown_period = timedelta(minutes=self.cooldown_minutes)
        
        return datetime.now() - last_sent < cooldown_period
    
    def test_all_channels(self) -> Dict[str, bool]:
        """Test all configured notification channels"""
        results = {}
        
        for channel in self.channels:
            channel_name = channel.__class__.__name__
            try:
                results[channel_name] = channel.test_connection()
            except Exception as e:
                self.logger.error(f"Error testing {channel_name}: {e}")
                results[channel_name] = False
        
        return results
    
    def create_alert(self, 
                    title: str, 
                    description: str, 
                    severity: AlertSeverity, 
                    service_name: str,
                    labels: Dict[str, str] = None,
                    annotations: Dict[str, str] = None) -> Alert:
        """Create a new alert"""
        import uuid
        
        alert_id = str(uuid.uuid4())
        
        return Alert(
            id=alert_id,
            title=title,
            description=description,
            severity=severity,
            status=AlertStatus.FIRING,
            service_name=service_name,
            timestamp=datetime.now(),
            labels=labels or {},
            annotations=annotations or {}
        )
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        # This would typically update the alert in a database
        # For now, we'll just log it
        self.logger.info(f"Alert {alert_id} marked as resolved")
        return True
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alerting statistics"""
        return {
            'total_alerts_sent': sum(info['count'] for info in self.alert_history.values()),
            'unique_alerts': len(self.alert_history),
            'channels_configured': len(self.channels),
            'cooldown_minutes': self.cooldown_minutes
        }


# Alert rule engine
class AlertRule:
    """Represents an alerting rule"""
    
    def __init__(self, 
                 name: str, 
                 condition: str, 
                 severity: AlertSeverity,
                 message_template: str = None):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.message_template = message_template or "{service} is {status}"
    
    def evaluate(self, metrics: Dict[str, Any]) -> Optional[Alert]:
        """Evaluate rule against metrics"""
        try:
            # Simple condition evaluation
            # In a real implementation, you'd use a proper expression parser
            if self._evaluate_condition(metrics):
                alert_manager = AlertManager({})  # This should be injected
                return alert_manager.create_alert(
                    title=f"Alert: {self.name}",
                    description=self._format_message(metrics),
                    severity=self.severity,
                    service_name=metrics.get('service_name', 'unknown')
                )
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error evaluating rule {self.name}: {e}")
        
        return None
    
    def _evaluate_condition(self, metrics: Dict[str, Any]) -> bool:
        """Evaluate the condition against metrics"""
        # This is a simplified implementation
        # In production, you'd want a proper expression evaluator
        try:
            # Replace metric names with values
            condition = self.condition
            for key, value in metrics.items():
                condition = condition.replace(f"{{{key}}}", str(value))
            
            # Evaluate the condition
            return eval(condition)
            
        except Exception:
            return False
    
    def _format_message(self, metrics: Dict[str, Any]) -> str:
        """Format alert message using template"""
        try:
            template = Template(self.message_template)
            return template.render(**metrics)
        except Exception:
            return f"Alert triggered for rule: {self.name}"


if __name__ == "__main__":
    # Example usage
    config = {
        'channels': [
            {
                'type': 'slack',
                'webhook_url': 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK',
                'channel': '#alerts'
            }
        ],
        'cooldown_minutes': 15
    }
    
    alert_manager = AlertManager(config)
    
    # Test channels
    results = alert_manager.test_all_channels()
    print("Channel test results:", results)
    
    # Create and send a test alert
    alert = alert_manager.create_alert(
        title="High CPU Usage",
        description="CPU usage has exceeded 90% for the last 5 minutes",
        severity=AlertSeverity.HIGH,
        service_name="api-server",
        labels={'environment': 'production', 'team': 'backend'},
        annotations={'runbook': 'https://wiki.company.com/runbooks/high-cpu'}
    )
    
    alert_manager.send_alert(alert)