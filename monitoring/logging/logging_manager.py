"""
Centralized logging system for microservices monitoring

Provides structured logging, log aggregation, and log analysis capabilities.
"""

import json
import logging
import logging.handlers
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from queue import Queue
from elasticsearch import Elasticsearch
import requests


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: datetime
    level: str
    service: str
    message: str
    logger_name: str
    module: str
    function: str
    line_number: int
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    extra_fields: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def __init__(self, service_name: str, include_trace: bool = True):
        super().__init__()
        self.service_name = service_name
        self.include_trace = include_trace
    
    def format(self, record: logging.LogRecord) -> str:
        # Extract trace information if available
        trace_id = getattr(record, 'trace_id', None)
        span_id = getattr(record, 'span_id', None)
        user_id = getattr(record, 'user_id', None)
        request_id = getattr(record, 'request_id', None)
        
        # Create structured log entry
        log_entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created),
            level=record.levelname,
            service=self.service_name,
            message=record.getMessage(),
            logger_name=record.name,
            module=record.module,
            function=record.funcName,
            line_number=record.lineno,
            trace_id=trace_id,
            span_id=span_id,
            user_id=user_id,
            request_id=request_id,
            extra_fields=getattr(record, 'extra_fields', {})
        )
        
        return log_entry.to_json()


class ElasticsearchHandler(logging.Handler):
    """Custom logging handler for Elasticsearch"""
    
    def __init__(self, 
                 elasticsearch_url: str,
                 index_pattern: str = "logs-{date}",
                 batch_size: int = 100,
                 flush_interval: int = 5):
        super().__init__()
        self.es = Elasticsearch([elasticsearch_url])
        self.index_pattern = index_pattern
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self.log_queue = Queue()
        self.batch = []
        self.last_flush = time.time()
        
        # Start background thread for batch processing
        self.flush_thread = threading.Thread(target=self._flush_worker, daemon=True)
        self.flush_thread.start()
    
    def emit(self, record: logging.LogRecord):
        """Add log record to queue for batch processing"""
        try:
            log_data = json.loads(self.format(record))
            self.log_queue.put(log_data)
        except Exception:
            self.handleError(record)
    
    def _flush_worker(self):
        """Background worker for flushing logs to Elasticsearch"""
        while True:
            try:
                # Collect logs from queue
                while not self.log_queue.empty() and len(self.batch) < self.batch_size:
                    self.batch.append(self.log_queue.get_nowait())
                
                # Flush if batch is full or interval has passed
                current_time = time.time()
                if (len(self.batch) >= self.batch_size or 
                    (self.batch and current_time - self.last_flush >= self.flush_interval)):
                    self._flush_batch()
                    self.last_flush = current_time
                
                time.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                print(f"Error in flush worker: {e}")
    
    def _flush_batch(self):
        """Flush current batch to Elasticsearch"""
        if not self.batch:
            return
        
        try:
            # Prepare bulk insert data
            bulk_data = []
            for log_entry in self.batch:
                # Generate index name based on date
                index_name = self.index_pattern.format(
                    date=datetime.fromisoformat(log_entry['timestamp']).strftime('%Y.%m.%d')
                )
                
                bulk_data.append({
                    "index": {
                        "_index": index_name,
                        "_type": "_doc"
                    }
                })
                bulk_data.append(log_entry)
            
            # Send to Elasticsearch
            if bulk_data:
                self.es.bulk(body=bulk_data)
            
            self.batch.clear()
            
        except Exception as e:
            print(f"Error flushing logs to Elasticsearch: {e}")
            self.batch.clear()  # Clear batch to prevent endless retries


class WebhookHandler(logging.Handler):
    """Custom logging handler for webhook notifications"""
    
    def __init__(self, webhook_url: str, headers: Dict[str, str] = None):
        super().__init__()
        self.webhook_url = webhook_url
        self.headers = headers or {'Content-Type': 'application/json'}
    
    def emit(self, record: logging.LogRecord):
        """Send log record to webhook"""
        try:
            log_data = json.loads(self.format(record))
            requests.post(
                self.webhook_url,
                json=log_data,
                headers=self.headers,
                timeout=5
            )
        except Exception:
            self.handleError(record)


class LoggingManager:
    """Manages logging configuration and setup for microservices"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.service_name = config.get('service_name', 'unknown-service')
        self.loggers = {}
    
    def setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        # Get or create logger for this service
        logger = logging.getLogger(self.service_name)
        
        if logger.hasHandlers():
            return logger  # Already configured
        
        # Set log level
        log_level = getattr(logging, self.config.get('log_level', 'INFO').upper())
        logger.setLevel(log_level)
        
        # Setup handlers based on configuration
        handlers = self._create_handlers()
        
        for handler in handlers:
            logger.addHandler(handler)
        
        # Prevent propagation to root logger to avoid duplicate logs
        logger.propagate = False
        
        self.loggers[self.service_name] = logger
        return logger
    
    def _create_handlers(self) -> List[logging.Handler]:
        """Create logging handlers based on configuration"""
        handlers = []
        
        # Console handler
        if self.config.get('console_logging', True):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                StructuredFormatter(self.service_name)
            )
            handlers.append(console_handler)
        
        # File handler
        if 'file_path' in self.config:
            file_handler = logging.handlers.RotatingFileHandler(
                self.config['file_path'],
                maxBytes=self.config.get('max_file_size', 100 * 1024 * 1024),  # 100MB
                backupCount=self.config.get('backup_count', 5)
            )
            file_handler.setFormatter(
                StructuredFormatter(self.service_name)
            )
            handlers.append(file_handler)
        
        # Elasticsearch handler
        if 'elasticsearch' in self.config:
            es_config = self.config['elasticsearch']
            es_handler = ElasticsearchHandler(
                elasticsearch_url=es_config['url'],
                index_pattern=es_config.get('index_pattern', 'logs-{date}'),
                batch_size=es_config.get('batch_size', 100),
                flush_interval=es_config.get('flush_interval', 5)
            )
            es_handler.setFormatter(
                StructuredFormatter(self.service_name)
            )
            handlers.append(es_handler)
        
        # Webhook handler
        if 'webhook' in self.config:
            webhook_config = self.config['webhook']
            webhook_handler = WebhookHandler(
                webhook_url=webhook_config['url'],
                headers=webhook_config.get('headers', {})
            )
            webhook_handler.setFormatter(
                StructuredFormatter(self.service_name)
            )
            handlers.append(webhook_handler)
        
        return handlers
    
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """Get a logger instance"""
        logger_name = name or self.service_name
        
        if logger_name not in self.loggers:
            self.loggers[logger_name] = self.setup_logging()
        
        return self.loggers[logger_name]
    
    def add_trace_context(self, 
                         logger: logging.Logger,
                         trace_id: str,
                         span_id: str,
                         user_id: Optional[str] = None,
                         request_id: Optional[str] = None):
        """Add tracing context to logger"""
        # Create a logger adapter that adds trace context
        return TracingLoggerAdapter(logger, {
            'trace_id': trace_id,
            'span_id': span_id,
            'user_id': user_id,
            'request_id': request_id
        })


class TracingLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds tracing context to log records"""
    
    def process(self, msg, kwargs):
        # Add extra fields to the log record
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        kwargs['extra'].update(self.extra)
        return msg, kwargs


class LogAnalyzer:
    """Analyzes logs for patterns, errors, and insights"""
    
    def __init__(self, elasticsearch_url: str):
        self.es = Elasticsearch([elasticsearch_url])
    
    def get_error_summary(self, 
                         service: Optional[str] = None,
                         hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period"""
        # Build Elasticsearch query
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "timestamp": {
                                    "gte": f"now-{hours}h"
                                }
                            }
                        },
                        {
                            "terms": {
                                "level": ["ERROR", "CRITICAL"]
                            }
                        }
                    ]
                }
            },
            "aggs": {
                "services": {
                    "terms": {
                        "field": "service.keyword",
                        "size": 10
                    }
                },
                "error_messages": {
                    "terms": {
                        "field": "message.keyword",
                        "size": 20
                    }
                },
                "timeline": {
                    "date_histogram": {
                        "field": "timestamp",
                        "calendar_interval": "1h"
                    }
                }
            }
        }
        
        if service:
            query["query"]["bool"]["must"].append({
                "term": {"service.keyword": service}
            })
        
        try:
            response = self.es.search(
                index="logs-*",
                body=query,
                size=0  # We only want aggregations
            )
            
            return {
                'total_errors': response['hits']['total']['value'],
                'services': [
                    {'service': bucket['key'], 'count': bucket['doc_count']}
                    for bucket in response['aggregations']['services']['buckets']
                ],
                'top_errors': [
                    {'message': bucket['key'], 'count': bucket['doc_count']}
                    for bucket in response['aggregations']['error_messages']['buckets']
                ],
                'timeline': [
                    {
                        'timestamp': bucket['key_as_string'],
                        'count': bucket['doc_count']
                    }
                    for bucket in response['aggregations']['timeline']['buckets']
                ]
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def search_logs(self, 
                   query: str,
                   service: Optional[str] = None,
                   level: Optional[str] = None,
                   hours: int = 24,
                   size: int = 100) -> List[Dict[str, Any]]:
        """Search logs with flexible query"""
        # Build Elasticsearch query
        es_query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "timestamp": {
                                    "gte": f"now-{hours}h"
                                }
                            }
                        }
                    ]
                }
            },
            "sort": [
                {"timestamp": {"order": "desc"}}
            ],
            "size": size
        }
        
        # Add text search
        if query:
            es_query["query"]["bool"]["must"].append({
                "multi_match": {
                    "query": query,
                    "fields": ["message", "logger_name", "module", "function"]
                }
            })
        
        # Add service filter
        if service:
            es_query["query"]["bool"]["must"].append({
                "term": {"service.keyword": service}
            })
        
        # Add level filter
        if level:
            es_query["query"]["bool"]["must"].append({
                "term": {"level.keyword": level.upper()}
            })
        
        try:
            response = self.es.search(
                index="logs-*",
                body=es_query
            )
            
            return [hit['_source'] for hit in response['hits']['hits']]
            
        except Exception as e:
            return []


# Decorators for automatic logging
def log_function_calls(logger: logging.Logger):
    """Decorator to automatically log function calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger.info(f"Calling {func.__name__} with args={args[:3]}... kwargs={list(kwargs.keys())}")
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"Completed {func.__name__} in {duration:.3f}s")
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Error in {func.__name__} after {duration:.3f}s: {e}")
                raise
        
        return wrapper
    return decorator


def log_errors(logger: logging.Logger):
    """Decorator to automatically log errors"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                raise
        
        return wrapper
    return decorator


# Example usage and configuration
if __name__ == "__main__":
    # Example logging configuration
    logging_config = {
        'service_name': 'api-server',
        'log_level': 'INFO',
        'console_logging': True,
        'file_path': '/var/log/api-server.log',
        'max_file_size': 100 * 1024 * 1024,  # 100MB
        'backup_count': 5,
        'elasticsearch': {
            'url': 'http://localhost:9200',
            'index_pattern': 'logs-{date}',
            'batch_size': 100,
            'flush_interval': 5
        }
    }
    
    # Setup logging
    logging_manager = LoggingManager(logging_config)
    logger = logging_manager.setup_logging()
    
    # Example usage
    logger.info("Application started")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Example with tracing context
    traced_logger = logging_manager.add_trace_context(
        logger,
        trace_id="trace-123",
        span_id="span-456",
        user_id="user-789",
        request_id="req-101112"
    )
    
    traced_logger.info("Processing user request")
    
    # Example decorator usage
    @log_function_calls(logger)
    @log_errors(logger)
    def example_function(x, y):
        if x < 0:
            raise ValueError("x must be positive")
        return x + y
    
    example_function(5, 10)
    
    try:
        example_function(-1, 10)
    except ValueError:
        pass