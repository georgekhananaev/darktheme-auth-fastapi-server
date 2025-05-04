import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from modules.config import config


class TestHTTPSecurity:
    
    def test_http_enabled_by_default(self, client):
        """Test that HTTP is enabled by default."""
        # Make a simple request (HTTP is the default for TestClient)
        response = client.get("/api/v1/system/ping")
        assert response.status_code == 200
        
        # Verify the response contains the expected data
        data = response.json()
        assert data["message"] == "pong"
    
    def test_http_to_https_redirect(self, client):
        """Test HTTP to HTTPS redirection when enabled."""
        # Patch the config to enable HTTP to HTTPS redirection
        with patch("modules.middleware.config.is_http_to_https_redirect_enabled", return_value=True), \
             patch("modules.middleware.config.is_https_enabled", return_value=True):
            
            # Make a request with HTTP scheme
            client.headers["X-Forwarded-Proto"] = "http"
            client.headers["host"] = "testserver:8000"
            
            # The first request should be a redirect to HTTPS
            response = client.get("/api/v1/system/ping", follow_redirects=False)
            
            # Check that we got a redirect
            assert response.status_code == 301
            assert response.headers["location"].startswith("https://")
    
    def test_http_disabled(self, client_with_http_disabled):
        """Test that HTTP is blocked when disabled."""
        # Make a request with HTTP disabled
        with patch("modules.middleware.config.is_http_enabled", return_value=False):
            response = client_with_http_disabled.get("/api/v1/system/ping")
            
            # Should be blocked with 403 Forbidden
            assert response.status_code == 403
            assert "HTTP requests are disabled" in response.json()["detail"]
    
    def test_https_requests_allowed_when_http_disabled(self, client_with_http_disabled):
        """Test that HTTPS requests are allowed even when HTTP is disabled."""
        with patch("modules.middleware.config.is_http_enabled", return_value=False):
            # Simulate HTTPS request by changing the header
            client_with_http_disabled.headers["X-Forwarded-Proto"] = "https"
            
            # Make the request
            response = client_with_http_disabled.get("/api/v1/system/ping")
            
            # Should be allowed
            assert response.status_code == 200
            assert response.json()["message"] == "pong"