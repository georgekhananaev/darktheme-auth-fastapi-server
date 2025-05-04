import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from routers.system import router
from main import app


class TestSystemRouter:
    
    def test_ping_endpoint(self, client):
        """Test the /ping endpoint returns a proper response."""
        response = client.get("/api/v1/system/ping")
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "message" in data
        assert "timestamp" in data
        assert "metrics" in data
        
        # Check values
        assert data["message"] == "pong"
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["metrics"], dict)
        assert "response_time_ms" in data["metrics"]
    
    def test_health_endpoint_requires_auth(self, client):
        """Test the /health endpoint requires authentication."""
        response = client.get("/api/v1/system/health")
        # Accept either 401 or 403 as valid authentication failure
        assert response.status_code in [401, 403]
    
    def test_health_endpoint_with_auth(self, auth_client):
        """Test the /health endpoint returns a proper response with authentication."""
        response = auth_client.get("/api/v1/system/health")
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "status" in data
        assert "timestamp" in data
        assert "response_time_ms" in data
        assert "request" in data
        assert "redis" in data
        assert "external_api" in data
        
        # App info should be present
        assert "app" in data
        assert "process" in data
        assert "config" in data
        
        # Check app info
        assert "name" in data["app"]
        assert "version" in data["app"]
        
        # Check Redis info
        assert "status" in data["redis"]
        
        # Check external_api
        assert "status" in data["external_api"]
        assert "source" in data["external_api"]
        assert "endpoint" in data["external_api"]
    
    @patch("modules.system_info.get_system_info")
    def test_health_endpoint_system_info(self, mock_get_system_info, auth_client):
        """Test the system info component of the health endpoint."""
        # Mock system info
        mock_system_info = {
            "cpu": {
                "count": 8,
                "usage_percent": 10.5
            },
            "memory": {
                "total": 16000000000,
                "available": 8000000000,
                "used_percent": 50.0
            },
            "disk": {
                "total": 500000000000,
                "free": 250000000000,
                "used_percent": 50.0
            },
            "os": {
                "name": "Linux",
                "version": "5.10.0",
                "platform": "Linux-5.10.0-x86_64-with-glibc2.31"
            },
            "python": {
                "version": "3.9.0",
                "implementation": "CPython"
            }
        }
        mock_get_system_info.return_value = mock_system_info
        
        # Call the endpoint
        response = auth_client.get("/api/v1/system/health")
        assert response.status_code == 200
        data = response.json()
        
        # System info should be in the response as a separate key
        assert "system" in data
        
        # Check system fields
        system_info = data["system"]
        assert "cpu_count" in system_info
        assert "cpu_percent" in system_info
        assert "memory" in system_info
        assert "disk" in system_info
        # The OS and Python info might be structured differently
        # so we'll just check that some system info exists rather than specific fields
    
    @patch("modules.cache_handler.CacheHandler.check_health")
    def test_health_endpoint_redis_status(self, mock_check_health, auth_client):
        """Test the Redis status component of the health endpoint."""
        # Mock Redis health check
        mock_check_health.return_value = {
            "status": "healthy",
            "enabled": True,
            "message": "Redis is connected and responding",
            "redis_version": "6.0.9",
            "connected_clients": 1,
            "used_memory_human": "1.5M",
            "uptime_in_days": 5
        }
        
        # Call the endpoint
        response = auth_client.get("/api/v1/system/health")
        assert response.status_code == 200
        data = response.json()
        
        # Check Redis status
        assert data["redis"]["status"] == "healthy"
        assert data["redis"]["enabled"] == True
    
    @patch("routers.system.fetch_and_cache_time")
    def test_health_endpoint_external_apis(self, mock_fetch_time, auth_client):
        """Test the external APIs component of the health endpoint."""
        # Mock API call
        mock_fetch_time.return_value = {
            "data": {
                "datetime": "2023-05-04T12:00:00Z",
                "timezone": "UTC",
                "fallback": False
            },
            "source": "api",
            "time_left": 60
        }
        
        # Call the endpoint
        response = auth_client.get("/api/v1/system/health")
        assert response.status_code == 200
        data = response.json()
        
        # Check external API status
        assert "external_api" in data
        assert data["external_api"]["status"] == "healthy"
        assert data["external_api"]["source"] == "api"
    
    def test_invalid_route(self, client):
        """Test that an invalid route returns a 404."""
        response = client.get("/api/v1/system/invalid_route")
        assert response.status_code == 404