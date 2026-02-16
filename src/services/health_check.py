"""
Health Check Service - Gold Tier
Comprehensive health checking with endpoints for all services
"""
import asyncio
import time
import logging
import psutil
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.utils import get_current_iso_timestamp
from lib.event_bus import get_event_bus, EventType, publish_event


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: get_current_iso_timestamp())
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
            "details": self.details
        }


@dataclass
class SystemHealth:
    """Overall system health status."""
    status: HealthStatus
    timestamp: str
    checks: Dict[str, HealthCheckResult]
    uptime_seconds: float
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "checks": {k: v.to_dict() for k, v in self.checks.items()},
            "uptime_seconds": self.uptime_seconds,
            "version": self.version
        }


class HealthChecker:
    """
    Base class for health checkers.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"HealthChecker.{name}")
    
    async def check(self) -> HealthCheckResult:
        """Perform health check. Override in subclass."""
        raise NotImplementedError


class ServiceHealthChecker(HealthChecker):
    """Health checker for a service."""
    
    def __init__(self, name: str, service: Any):
        super().__init__(name)
        self.service = service
    
    async def check(self) -> HealthCheckResult:
        """Check service health."""
        start_time = time.time()
        
        try:
            # Check if service has health_check method
            if hasattr(self.service, 'health_check'):
                health_check = getattr(self.service, 'health_check')
                if asyncio.iscoroutinefunction(health_check):
                    is_healthy = await health_check()
                else:
                    is_healthy = health_check()
                
                latency_ms = (time.time() - start_time) * 1000
                
                if is_healthy:
                    # Get metrics if available
                    details = {}
                    if hasattr(self.service, 'get_metrics'):
                        get_metrics = getattr(self.service, 'get_metrics')
                        if asyncio.iscoroutinefunction(get_metrics):
                            details = await get_metrics()
                        else:
                            details = get_metrics()
                    
                    return HealthCheckResult(
                        name=self.name,
                        status=HealthStatus.HEALTHY,
                        message="Service is healthy",
                        latency_ms=latency_ms,
                        details=details
                    )
                else:
                    return HealthCheckResult(
                        name=self.name,
                        status=HealthStatus.UNHEALTHY,
                        message="Service health check failed",
                        latency_ms=latency_ms
                    )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNKNOWN,
                    message="No health check method available",
                    latency_ms=(time.time() - start_time) * 1000
                )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(e)}",
                latency_ms=(time.time() - start_time) * 1000
            )


class DatabaseHealthChecker(HealthChecker):
    """Health checker for database/file system."""
    
    def __init__(self, name: str, path: str):
        super().__init__(name)
        self.path = Path(path)
    
    async def check(self) -> HealthCheckResult:
        """Check database/file system health."""
        start_time = time.time()
        
        try:
            # Check if path exists and is writable
            if not self.path.exists():
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Path does not exist: {self.path}",
                    latency_ms=(time.time() - start_time) * 1000
                )
            
            # Check write access
            test_file = self.path / ".health_check"
            try:
                test_file.write_text(get_current_iso_timestamp())
                test_file.unlink()
            except Exception as e:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Write access failed: {str(e)}",
                    latency_ms=(time.time() - start_time) * 1000
                )
            
            # Check disk space
            try:
                usage = psutil.disk_usage(str(self.path))
                disk_free_gb = usage.free / (1024 ** 3)
                
                if disk_free_gb < 1:
                    status = HealthStatus.DEGRADED
                    message = f"Low disk space: {disk_free_gb:.2f} GB free"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Disk space OK: {disk_free_gb:.2f} GB free"
                
                return HealthCheckResult(
                    name=self.name,
                    status=status,
                    message=message,
                    latency_ms=(time.time() - start_time) * 1000,
                    details={
                        "disk_free_gb": disk_free_gb,
                        "disk_total_gb": usage.total / (1024 ** 3),
                        "disk_used_percent": usage.percent
                    }
                )
            except Exception as e:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.DEGRADED,
                    message=f"Could not check disk space: {str(e)}",
                    latency_ms=(time.time() - start_time) * 1000
                )
                
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(e)}",
                latency_ms=(time.time() - start_time) * 1000
            )


class APIHealthChecker(HealthChecker):
    """Health checker for external APIs."""
    
    def __init__(self, name: str, url: str, timeout: float = 5.0):
        super().__init__(name)
        self.url = url
        self.timeout = timeout
    
    async def check(self) -> HealthCheckResult:
        """Check API health."""
        start_time = time.time()
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url, timeout=self.timeout) as response:
                    latency_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        return HealthCheckResult(
                            name=self.name,
                            status=HealthStatus.HEALTHY,
                            message=f"API responded with status {response.status}",
                            latency_ms=latency_ms,
                            details={"status_code": response.status}
                        )
                    else:
                        return HealthCheckResult(
                            name=self.name,
                            status=HealthStatus.DEGRADED,
                            message=f"API responded with status {response.status}",
                            latency_ms=latency_ms,
                            details={"status_code": response.status}
                        )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"API request timed out after {self.timeout}s",
                latency_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"API health check failed: {str(e)}",
                latency_ms=(time.time() - start_time) * 1000
            )


class SystemHealthChecker(HealthChecker):
    """Health checker for system resources."""
    
    def __init__(self):
        super().__init__("system")
    
    async def check(self) -> HealthCheckResult:
        """Check system resource health."""
        start_time = time.time()
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Process info
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info().rss / (1024 * 1024)  # MB
            
            # Determine status
            if cpu_percent > 90 or memory_percent > 90:
                status = HealthStatus.UNHEALTHY
            elif cpu_percent > 70 or memory_percent > 70:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return HealthCheckResult(
                name="system",
                status=status,
                message=f"CPU: {cpu_percent}%, Memory: {memory_percent}%",
                latency_ms=(time.time() - start_time) * 1000,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "memory_available_mb": memory.available / (1024 * 1024),
                    "process_memory_mb": process_memory,
                    "open_files": len(process.open_files()),
                    "threads": process.num_threads()
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name="system",
                status=HealthStatus.UNHEALTHY,
                message=f"System health check failed: {str(e)}",
                latency_ms=(time.time() - start_time) * 1000
            )


class HealthCheckService:
    """
    Central health check service for the system.
    """
    
    def __init__(self, vault_path: str = "./AI_Employee_Vault"):
        self.vault_path = vault_path
        self.logger = logging.getLogger("HealthCheckService")
        self.event_bus = get_event_bus()
        
        # Registered checkers
        self._checkers: Dict[str, HealthChecker] = {}
        self._services: Dict[str, Any] = {}
        
        # Health cache
        self._last_health: Optional[SystemHealth] = None
        self._cache_ttl = 10  # seconds
        self._cache_time = 0
        
        # Start time for uptime
        self._start_time = time.time()
        
        # Register default checkers
        self._register_default_checkers()
        
        self.logger.info("HealthCheckService initialized")
    
    def _register_default_checkers(self):
        """Register default health checkers."""
        # System resources
        self._checkers["system"] = SystemHealthChecker()
        
        # Vault/file system
        self._checkers["vault"] = DatabaseHealthChecker("vault", self.vault_path)
    
    def register_service(self, name: str, service: Any):
        """Register a service for health checking."""
        self._services[name] = service
        self._checkers[name] = ServiceHealthChecker(name, service)
        self.logger.info(f"Registered service for health checking: {name}")
    
    def unregister_service(self, name: str):
        """Unregister a service from health checking."""
        if name in self._services:
            del self._services[name]
        if name in self._checkers:
            del self._checkers[name]
    
    async def check_all(self, use_cache: bool = True) -> SystemHealth:
        """
        Perform health checks on all registered checkers.
        
        Args:
            use_cache: Use cached result if not expired
            
        Returns:
            System health status
        """
        # Check cache
        now = time.time()
        if use_cache and self._last_health and (now - self._cache_time) < self._cache_ttl:
            return self._last_health
        
        # Run all checks concurrently
        results = await asyncio.gather(
            *[checker.check() for checker in self._checkers.values()],
            return_exceptions=True
        )
        
        # Process results
        checks: Dict[str, HealthCheckResult] = {}
        worst_status = HealthStatus.HEALTHY
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                checker_name = list(self._checkers.keys())[i]
                checks[checker_name] = HealthCheckResult(
                    name=checker_name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check exception: {str(result)}"
                )
                worst_status = HealthStatus.UNHEALTHY
            elif isinstance(result, HealthCheckResult):
                checks[result.name] = result
                
                # Track worst status
                status_priority = {
                    HealthStatus.HEALTHY: 0,
                    HealthStatus.DEGRADED: 1,
                    HealthStatus.UNHEALTHY: 2,
                    HealthStatus.UNKNOWN: 3
                }
                if status_priority.get(result.status, 3) > status_priority.get(worst_status, 0):
                    worst_status = result.status
        
        # Build system health
        system_health = SystemHealth(
            status=worst_status,
            timestamp=get_current_iso_timestamp(),
            checks=checks,
            uptime_seconds=time.time() - self._start_time
        )
        
        # Update cache
        self._last_health = system_health
        self._cache_time = now
        
        # Publish health status event
        publish_event(
            EventType.HEALTH_STATUS,
            system_health.to_dict(),
            source="health_check_service"
        )
        
        return system_health
    
    async def check_single(self, name: str) -> Optional[HealthCheckResult]:
        """Check health of a single component."""
        checker = self._checkers.get(name)
        if checker:
            return await checker.check()
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current health status (may be cached)."""
        if self._last_health:
            return self._last_health.to_dict()
        return {
            "status": HealthStatus.UNKNOWN.value,
            "message": "No health check performed yet"
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get health summary."""
        return {
            "status": self._last_health.status.value if self._last_health else "unknown",
            "timestamp": get_current_iso_timestamp(),
            "uptime_seconds": time.time() - self._start_time,
            "check_count": len(self._checkers),
            "services": list(self._services.keys())
        }


# HTTP Health Endpoints (for API exposure)
class HealthEndpoints:
    """
    Health check HTTP endpoints.
    Can be integrated with any web framework.
    """
    
    def __init__(self, health_service: HealthCheckService):
        self.health_service = health_service
        self.logger = logging.getLogger("HealthEndpoints")
    
    async def handle_health(self) -> Dict[str, Any]:
        """
        GET /health
        
        Basic health check endpoint.
        Returns overall system status.
        """
        health = await self.health_service.check_all()
        return {
            "status": health.status.value,
            "timestamp": health.timestamp,
            "version": health.version
        }
    
    async def handle_health_detailed(self) -> Dict[str, Any]:
        """
        GET /health/detailed
        
        Detailed health check endpoint.
        Returns status of all components.
        """
        health = await self.health_service.check_all()
        return health.to_dict()
    
    async def handle_health_live(self) -> Dict[str, Any]:
        """
        GET /health/live
        
        Liveness probe - is the service running?
        Always returns healthy if service is up.
        """
        return {
            "status": "healthy",
            "timestamp": get_current_iso_timestamp()
        }
    
    async def handle_health_ready(self) -> Dict[str, Any]:
        """
        GET /health/ready
        
        Readiness probe - is the service ready to accept requests?
        Returns healthy only if all critical components are healthy.
        """
        health = await self.health_service.check_all(use_cache=False)
        
        # Check critical components
        critical_checks = ["system", "vault"]
        for check_name in critical_checks:
            check = health.checks.get(check_name)
            if check and check.status == HealthStatus.UNHEALTHY:
                return {
                    "status": "unhealthy",
                    "timestamp": health.timestamp,
                    "failed_check": check_name,
                    "message": check.message
                }
        
        return {
            "status": "healthy",
            "timestamp": health.timestamp
        }
    
    async def handle_metrics(self) -> str:
        """
        GET /metrics
        
        Prometheus-format metrics endpoint.
        """
        from lib.metrics import get_metrics_collector
        collector = get_metrics_collector()
        return collector.get_prometheus_format()


# Factory function
def create_health_check_service(vault_path: str = "./AI_Employee_Vault") -> HealthCheckService:
    """Factory function to create HealthCheckService."""
    return HealthCheckService(vault_path)
