import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from routers.logs import router
from modules.logger import log_access, log_security, log_system, get_logs, get_log_counts


class TestLogsRouter:
    
    def test_logs_count_endpoint_requires_auth(self, client):
        """Test that /logs/counts endpoint requires authentication."""
        response = client.get("/api/v1/logs/counts")
        assert response.status_code in (401, 403)
    
    @patch("routers.logs.get_log_counts")
    def test_logs_count_endpoint_with_auth(self, mock_get_log_counts, auth_client):
        """Test that /logs/counts endpoint returns correct data with authentication."""
        # Mock the log counts
        mock_get_log_counts.return_value = {
            "access_logs": 10,
            "security_logs": 5,
            "system_logs": 3
        }
        
        # Call the endpoint
        response = auth_client.get("/api/v1/logs/counts")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "access_logs" in data
        assert "security_logs" in data
        assert "system_logs" in data
        assert "total" in data
        
        # Check values
        assert data["access_logs"] == 10
        assert data["security_logs"] == 5
        assert data["system_logs"] == 3
        assert data["total"] == 18  # Sum of all logs
    
    def test_access_logs_endpoint_requires_auth(self, client):
        """Test that /logs/access endpoint requires authentication."""
        response = client.get("/api/v1/logs/access")
        assert response.status_code in (401, 403)
    
    @patch("routers.logs.get_logs")
    def test_access_logs_endpoint_with_auth(self, mock_get_logs, auth_client):
        """Test that /logs/access endpoint returns correct data with authentication."""
        # Mock the logs data
        current_time = datetime.now().isoformat()
        mock_logs = [
            {
                "id": 1,
                "timestamp": current_time,
                "level": "INFO",
                "client_ip": "127.0.0.1",
                "method": "GET",
                "path": "/api/v1/system/ping",
                "status_code": 200,
                "response_time": 5.5,
                "message": "GET /api/v1/system/ping 200 Success"
            }
        ]
        mock_get_logs.return_value = mock_logs
        
        # Call the endpoint
        response = auth_client.get("/api/v1/logs/access")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
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
    
    @patch("routers.logs.get_logs")
    def test_access_logs_with_filters(self, mock_get_logs, auth_client):
        """Test that /logs/access endpoint applies filters correctly."""
        # Mock the logs
        mock_get_logs.return_value = []
        
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
        
        # Verify that filters were passed to get_logs
        mock_get_logs.assert_called_once_with(
            log_type="access",
            limit=50,
            offset=10,
            level="ERROR",
            start_date=filters["start_date"],
            end_date=filters["end_date"],
            search="error message"
        )
    
    def test_security_logs_endpoint_requires_auth(self, client):
        """Test that /logs/security endpoint requires authentication."""
        response = client.get("/api/v1/logs/security")
        assert response.status_code in (401, 403)
    
    @patch("routers.logs.get_logs")
    def test_security_logs_endpoint_with_auth(self, mock_get_logs, auth_client):
        """Test that /logs/security endpoint returns correct data with authentication."""
        # Mock the logs data
        current_time = datetime.now().isoformat()
        mock_logs = [
            {
                "id": 1,
                "timestamp": current_time,
                "level": "INFO",
                "client_ip": "127.0.0.1",
                "username": "test_user",
                "action": "login",
                "success": True,
                "message": "User login successful"
            }
        ]
        mock_get_logs.return_value = mock_logs
        
        # Call the endpoint
        response = auth_client.get("/api/v1/logs/security")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert isinstance(data, list)
        assert len(data) == 1
        
        log_entry = data[0]
        assert "id" in log_entry
        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "message" in log_entry
        assert "client_ip" in log_entry
        assert "username" in log_entry
        assert "action" in log_entry
        assert "success" in log_entry
        
        # Check values
        assert log_entry["id"] == 1
        assert log_entry["level"] == "INFO"
        assert log_entry["client_ip"] == "127.0.0.1"
        assert log_entry["username"] == "test_user"
        assert log_entry["action"] == "login"
        assert log_entry["success"] is True
    
    def test_system_logs_endpoint_requires_auth(self, client):
        """Test that /logs/system endpoint requires authentication."""
        response = client.get("/api/v1/logs/system")
        assert response.status_code in (401, 403)
    
    @patch("routers.logs.get_logs")
    def test_system_logs_endpoint_with_auth(self, mock_get_logs, auth_client):
        """Test that /logs/system endpoint returns correct data with authentication."""
        # Mock the logs data
        current_time = datetime.now().isoformat()
        mock_logs = [
            {
                "id": 1,
                "timestamp": current_time,
                "level": "INFO",
                "module": "main",
                "function": "startup",
                "message": "Application starting"
            }
        ]
        mock_get_logs.return_value = mock_logs
        
        # Call the endpoint
        response = auth_client.get("/api/v1/logs/system")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert isinstance(data, list)
        assert len(data) == 1
        
        log_entry = data[0]
        assert "id" in log_entry
        assert "timestamp" in log_entry
        assert "level" in log_entry
        assert "message" in log_entry
        assert "module" in log_entry
        assert "function" in log_entry
        
        # Check values
        assert log_entry["id"] == 1
        assert log_entry["level"] == "INFO"
        assert log_entry["module"] == "main"
        assert log_entry["function"] == "startup"
    
    @patch("routers.logs.get_logs")
    def test_logs_error_handling(self, mock_get_logs, auth_client):
        """Test that the logs endpoints handle errors correctly."""
        # Make get_logs raise an exception
        mock_get_logs.side_effect = Exception("Database error")
        
        # Call the endpoint
        response = auth_client.get("/api/v1/logs/system")
        
        # Verify the error response
        assert response.status_code == 500
        data = response.json()
        
        # Check structure
        assert "detail" in data
        
        # Check that the error message is included
        assert "Database error" in data["detail"]