"""
Utility functions for microservices monitoring
"""

import time
import functools
import threading
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta
import uuid
import hashlib
import json


class HealthCheckEndpoint:
    """Provides a standardized health check endpoint for services"""
    
    def __init__(self):
        self.checks = {}
        self.status = "healthy"
        self.last_check = None
    
    def add_check(self, name: str, check_function: Callable[[], bool], critical: bool = False):
        """Add a health check"""
        self.checks[name] = {
            'function': check_function,
            'critical': critical,
            'last_result': None,
            'last_check': None
        }
    
    def run_checks(self) -> Dict[str, Any]:
        """Run all health checks and return results"""
        results = {}
        overall_healthy = True
        
        for name, check in self.checks.items():
            try:
                start_time = time.time()
                result = check['function']()
                duration = time.time() - start_time
                
                check['last_result'] = result
                check['last_check'] = datetime.now()
                
                results[name] = {
                    'status': 'pass' if result else 'fail',
                    'time': check['last_check'].isoformat(),
                    'duration': f"{duration:.3f}s"
                }
                
                if not result and check['critical']:
                    overall_healthy = False
                    
            except Exception as e:
                check['last_result'] = False
                check['last_check'] = datetime.now()
                
                results[name] = {
                    'status': 'fail',
                    'time': check['last_check'].isoformat(),
                    'error': str(e)
                }
                
                if check['critical']:
                    overall_healthy = False
        
        self.status = "healthy" if overall_healthy else "unhealthy"
        self.last_check = datetime.now()
        
        return {
            'status': self.status,
            'timestamp': self.last_check.isoformat(),
            'checks': results,
            'version': '1.0.0'
        }


class MetricsCollector:
    """Thread-safe metrics collection utilities"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._counters = {}
        self._gauges = {}
        self._histograms = {}
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] = self._counters.get(key, 0) + value
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe a value for histogram metric"""
        with self._lock:
            key = self._make_key(name, labels)
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        with self._lock:
            return {
                'counters': dict(self._counters),
                'gauges': dict(self._gauges),
                'histograms': {
                    key: {
                        'count': len(values),
                        'sum': sum(values),
                        'min': min(values) if values else 0,
                        'max': max(values) if values else 0,
                        'avg': sum(values) / len(values) if values else 0
                    }
                    for key, values in self._histograms.items()
                }
            }
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create a unique key for metric with labels"""
        if not labels:
            return name
        
        label_str = ','.join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


class CircuitBreaker:
    """Circuit breaker pattern implementation for resilient service calls"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 timeout_duration: int = 60,
                 expected_exception: Exception = Exception):
        self.failure_threshold = failure_threshold
        self.timeout_duration = timeout_duration
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func):
        """Decorator to apply circuit breaker to a function"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
                
            except self.expected_exception as e:
                self._on_failure()
                raise e
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (time.time() - self.last_failure_time) >= self.timeout_duration
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, max_tokens: int, refill_rate: float):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = max_tokens
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens from the bucket"""
        with self._lock:
            now = time.time()
            
            # Refill tokens based on time passed
            time_passed = now - self.last_refill
            new_tokens = time_passed * self.refill_rate
            self.tokens = min(self.max_tokens, self.tokens + new_tokens)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def __call__(self, func):
        """Decorator to apply rate limiting to a function"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.acquire():
                raise Exception("Rate limit exceeded")
            return func(*args, **kwargs)
        
        return wrapper


class TraceContext:
    """Distributed tracing context manager"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.trace_id = None
        self.span_id = None
        self.parent_span_id = None
        self.spans = []
    
    def start_trace(self, operation_name: str) -> str:
        """Start a new trace"""
        self.trace_id = self._generate_id()
        self.span_id = self._generate_id()
        self.parent_span_id = None
        
        span = {
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'parent_span_id': self.parent_span_id,
            'service_name': self.service_name,
            'operation_name': operation_name,
            'start_time': time.time(),
            'tags': {},
            'logs': []
        }
        
        self.spans.append(span)
        return self.trace_id
    
    def start_span(self, operation_name: str, parent_span_id: str = None) -> str:
        """Start a new span in the current trace"""
        if not self.trace_id:
            return self.start_trace(operation_name)
        
        span_id = self._generate_id()
        
        span = {
            'trace_id': self.trace_id,
            'span_id': span_id,
            'parent_span_id': parent_span_id or self.span_id,
            'service_name': self.service_name,
            'operation_name': operation_name,
            'start_time': time.time(),
            'tags': {},
            'logs': []
        }
        
        self.spans.append(span)
        return span_id
    
    def finish_span(self, span_id: str, tags: Dict[str, str] = None):
        """Finish a span"""
        for span in self.spans:
            if span['span_id'] == span_id:
                span['end_time'] = time.time()
                span['duration'] = span['end_time'] - span['start_time']
                if tags:
                    span['tags'].update(tags)
                break
    
    def add_log(self, span_id: str, message: str, level: str = 'INFO'):
        """Add a log entry to a span"""
        for span in self.spans:
            if span['span_id'] == span_id:
                span['logs'].append({
                    'timestamp': time.time(),
                    'level': level,
                    'message': message
                })
                break
    
    def get_trace_data(self) -> Dict[str, Any]:
        """Get complete trace data"""
        return {
            'trace_id': self.trace_id,
            'service_name': self.service_name,
            'spans': self.spans
        }
    
    def _generate_id(self) -> str:
        """Generate a unique ID"""
        return str(uuid.uuid4()).replace('-', '')[:16]


def timing_decorator(metrics_collector: MetricsCollector = None):
    """Decorator to measure function execution time"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                if metrics_collector:
                    metrics_collector.observe_histogram(
                        f"{func.__name__}_duration_seconds",
                        duration,
                        labels={'status': 'success'}
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                if metrics_collector:
                    metrics_collector.observe_histogram(
                        f"{func.__name__}_duration_seconds",
                        duration,
                        labels={'status': 'error'}
                    )
                
                raise e
        
        return wrapper
    return decorator


def retry_decorator(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry function calls with exponential backoff"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        raise e
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
        
        return wrapper
    return decorator


def cache_decorator(ttl: int = 300):
    """Simple in-memory cache decorator with TTL"""
    cache = {}
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key_data = {
                'func': func.__name__,
                'args': args,
                'kwargs': kwargs
            }
            cache_key = hashlib.md5(
                json.dumps(key_data, sort_keys=True, default=str).encode()
            ).hexdigest()
            
            now = time.time()
            
            # Check if cached result exists and is still valid
            if cache_key in cache:
                cached_result, cached_time = cache[cache_key]
                if now - cached_time < ttl:
                    return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[cache_key] = (result, now)
            
            # Clean up expired entries (simple cleanup)
            expired_keys = [
                k for k, (_, t) in cache.items()
                if now - t > ttl
            ]
            for k in expired_keys:
                del cache[k]
            
            return result
        
        return wrapper
    return decorator


class ServiceRegistry:
    """Simple service registry for service discovery"""
    
    def __init__(self):
        self.services = {}
        self._lock = threading.Lock()
    
    def register(self, service_name: str, host: str, port: int, health_check_url: str = None):
        """Register a service"""
        with self._lock:
            self.services[service_name] = {
                'host': host,
                'port': port,
                'health_check_url': health_check_url,
                'registered_at': datetime.now(),
                'last_heartbeat': datetime.now()
            }
    
    def unregister(self, service_name: str):
        """Unregister a service"""
        with self._lock:
            self.services.pop(service_name, None)
    
    def discover(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Discover a service"""
        with self._lock:
            return self.services.get(service_name)
    
    def list_services(self) -> Dict[str, Dict[str, Any]]:
        """List all registered services"""
        with self._lock:
            return dict(self.services)
    
    def heartbeat(self, service_name: str):
        """Update service heartbeat"""
        with self._lock:
            if service_name in self.services:
                self.services[service_name]['last_heartbeat'] = datetime.now()


# Example usage
if __name__ == "__main__":
    # Health check example
    health = HealthCheckEndpoint()
    
    def check_database():
        # Simulate database check
        return True
    
    def check_cache():
        # Simulate cache check
        return True
    
    health.add_check("database", check_database, critical=True)
    health.add_check("cache", check_cache, critical=False)
    
    print("Health check results:")
    print(json.dumps(health.run_checks(), indent=2))
    
    # Metrics collection example
    metrics = MetricsCollector()
    metrics.increment_counter("requests_total", labels={"method": "GET", "status": "200"})
    metrics.set_gauge("memory_usage_bytes", 1024 * 1024 * 100)
    metrics.observe_histogram("request_duration_seconds", 0.25)
    
    print("\nMetrics:")
    print(json.dumps(metrics.get_metrics(), indent=2))
    
    # Circuit breaker example
    @CircuitBreaker(failure_threshold=3, timeout_duration=10)
    def unreliable_service():
        import random
        if random.random() < 0.7:  # 70% failure rate
            raise Exception("Service failed")
        return "Success"
    
    # Rate limiter example
    @RateLimiter(max_tokens=5, refill_rate=1.0)  # 5 requests, refill 1 per second
    def limited_function():
        return "Rate limited function called"
    
    # Tracing example
    tracer = TraceContext("example-service")
    trace_id = tracer.start_trace("process_request")
    span_id = tracer.start_span("database_query")
    
    time.sleep(0.1)  # Simulate work
    
    tracer.add_log(span_id, "Executing SQL query")
    tracer.finish_span(span_id, tags={"db.table": "users"})
    
    print("\nTrace data:")
    print(json.dumps(tracer.get_trace_data(), indent=2, default=str))