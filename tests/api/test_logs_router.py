import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from routers.logs import router
from modules.logger import log_access, log_security, log_system


class TestLogsRouter:
    
    def test_logs_count_endpoint_requires_auth(self, client):
        """Test that /logs/counts endpoint requires authentication."""
        response = client.get("/api/v1/logs/counts")
        assert response.status_code in (401, 403)
    
    def test_logs_count_endpoint_with_auth(self, auth_client):
        """Test that /logs/counts endpoint returns correct data with authentication."""
        # Call the endpoint with authentication
        response = auth_client.get("/api/v1/logs/counts")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "access_logs" in data
        assert "security_logs" in data
        assert "system_logs" in data
        
        # Check values
        assert data["access_logs"] == 10
        assert data["security_logs"] == 5
        assert data["system_logs"] == 3
    
    def test_access_logs_endpoint_requires_auth(self, client):
        """Test that /logs/access endpoint requires authentication."""
        response = client.get("/api/v1/logs/access")
        assert response.status_code in (401, 403)
    
    def test_access_logs_endpoint_with_auth(self, auth_client):
        """Test that /logs/access endpoint returns correct data with authentication."""
        # Call the endpoint with authentication
        response = auth_client.get("/api/v1/logs/access")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check that we got logs
        assert isinstance(data, list)
        assert len(data) == 1
        
        log_entry = data[0]
        assert "id" in log_entry
        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "message" in log_entry
        assert "client_ip" in log_entry
        
        # Check values
        assert log_entry["id"] == 1
        assert log_entry["level"] == "INFO"
        assert log_entry["client_ip"] == "127.0.0.1"
    
    def test_access_logs_with_filters(self, auth_client):
        """Test that /logs/access endpoint applies filters correctly."""
        # Call the endpoint with filters
        filters = {
            "limit": 50,
            "offset": 10,
            "level": "ERROR",
            "start_date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
            "search": "error message"
        }
        response = auth_client.get("/api/v1/logs/access", params=filters)
        
        # Verify the response status
        assert response.status_code == 200
        
        # Check we got a valid list response
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
    
    def test_security_logs_endpoint_requires_auth(self, client):
        """Test that /logs/security endpoint requires authentication."""
        response = client.get("/api/v1/logs/security")
        assert response.status_code in (401, 403)
    
    def test_security_logs_endpoint_with_auth(self, auth_client):
        """Test that /logs/security endpoint returns correct data with authentication."""
        # Call the endpoint with authentication
        response = auth_client.get("/api/v1/logs/security")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check that we got logs
        assert isinstance(data, list)
        assert len(data) == 1
        
        # Check log entry structure
        log_entry = data[0]
        assert "id" in log_entry
        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "message" in log_entry
    
    def test_system_logs_endpoint_requires_auth(self, client):
        """Test that /logs/system endpoint requires authentication."""
        response = client.get("/api/v1/logs/system")
        assert response.status_code in (401, 403)
    
    def test_system_logs_endpoint_with_auth(self, auth_client):
        """Test that /logs/system endpoint returns correct data with authentication."""
        # Call the endpoint with authentication
        response = auth_client.get("/api/v1/logs/system")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check that we got logs
        assert isinstance(data, list)
        assert len(data) == 1
        
        # Check log entry structure
        log_entry = data[0]
        assert "id" in log_entry
        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "message" in log_entry
    
    def test_logs_error_handling(self, auth_client):
        """Test error handling in log endpoints."""
        # Call the error endpoint (already defined in conftest.py)
        response = auth_client.get("/api/v1/logs/error")
        
        # Verify the error response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"].lower()
    
    def test_logs_with_api_key_auth(self, api_key_client):
        """Test that logs endpoints work with API key authentication."""
        # Only run this test if API key authentication is enabled
        from modules.config import config
        api_key_enabled = config.get('security', 'api_key', {}).get('enabled', False)
        
        if not api_key_enabled:
            pytest.skip("API key authentication is disabled in config.yaml")
        
        # Call the endpoint with API key authentication
        response = api_key_client.get("/api/v1/logs/access")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check that we got logs
        assert isinstance(data, list)
        assert len(data) == 1