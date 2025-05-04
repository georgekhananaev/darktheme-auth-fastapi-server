import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from modules.certificate_manager import certificate_manager
import sys
import os
import importlib

# Add parent directory to path to import main app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import main


class TestCertificatesRouter:
    
    def test_certificate_info_requires_auth(self, client, mock_letsencrypt_enabled):
        """Test that the certificate info endpoint requires authentication."""
        response = client.get("/api/v1/certificates/info")
        # Accept either 401 or 403 as valid authentication failure
        assert response.status_code in [401, 403]
    
    def test_certificate_info_endpoint(self, auth_client, mock_letsencrypt_enabled):
        """Test the certificate info endpoint returns proper response."""
        # Mock certificate info
        with patch("modules.certificate_manager.certificate_manager.get_cert_info") as mock_get_cert_info:
            mock_get_cert_info.return_value = {
                "has_cert": True,
                "issuer": "CN=Let's Encrypt Authority X3,O=Let's Encrypt,C=US",
                "subject": "CN=example.com",
                "domains": ["example.com", "www.example.com"],
                "not_before": "2023-05-01T00:00:00",
                "not_after": "2023-08-01T00:00:00",
                "days_remaining": 60,
                "is_valid": True
            }
            
            response = auth_client.get("/api/v1/certificates/info")
            assert response.status_code == 200
            
            data = response.json()
            assert data["has_cert"] == True
            assert "issuer" in data
            assert "subject" in data
            assert "domains" in data
            assert "days_remaining" in data
    
    def test_certificate_issue_requires_auth(self, client, mock_letsencrypt_enabled):
        """Test that the certificate issue endpoint requires authentication."""
        response = client.post("/api/v1/certificates/issue", json={})
        # Accept either 401 or 403 as valid authentication failure
        assert response.status_code in [401, 403]
    
    def test_certificate_issue_endpoint(self, auth_client, mock_letsencrypt_enabled):
        """Test the certificate issue endpoint."""
        with patch("modules.certificate_manager.certificate_manager.issue_certificate") as mock_issue_certificate:
            # Create an AsyncMock for the issue_certificate method
            async_mock = AsyncMock()
            async_mock.return_value = {
                "success": True,
                "message": "Certificate issued successfully",
                "domains": ["example.com", "www.example.com"],
                "is_staging": True,
                "expiry": "2023-08-01T00:00:00"
            }
            mock_issue_certificate.side_effect = async_mock
            
            # Create test request data
            request_data = {
                "email": "test@example.com",
                "domains": ["example.com", "www.example.com"],
                "staging": True
            }
            
            response = auth_client.post("/api/v1/certificates/issue", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["success"] == True
            assert "message" in data
            assert "domains" in data
    
    def test_certificate_renew_requires_auth(self, client, mock_letsencrypt_enabled):
        """Test that the certificate renew endpoint requires authentication."""
        response = client.post("/api/v1/certificates/renew", json={})
        # Accept either 401 or 403 as valid authentication failure
        assert response.status_code in [401, 403]
    
    def test_certificate_renew_endpoint(self, auth_client, mock_letsencrypt_enabled):
        """Test the certificate renew endpoint."""
        with patch("modules.certificate_manager.certificate_manager.check_cert_status") as mock_check_cert_status, \
             patch("modules.certificate_manager.certificate_manager.renew_certificates") as mock_renew_certificates:
             
            # Mock certificate status
            mock_check_cert_status.return_value = (True, 25)  # Has certs, 25 days remaining
            
            # Create an AsyncMock for the renew_certificates method
            async_mock = AsyncMock()
            async_mock.return_value = {
                "success": True,
                "message": "Certificates successfully renewed",
                "renewed": True,
                "next_renewal": "2023-07-01T00:00:00",
                "expiry": "2023-08-01T00:00:00"
            }
            mock_renew_certificates.side_effect = async_mock
            
            # The API is looking for the body parameter as specified in the routers/certificates.py
            response = auth_client.post("/api/v1/certificates/renew", json=True)
            assert response.status_code == 200
            
            data = response.json()
            assert data["success"] == True
            assert data["renewed"] == True
    
    def test_certificate_status_requires_auth(self, client, mock_letsencrypt_enabled):
        """Test that the certificate status endpoint requires authentication."""
        response = client.get("/api/v1/certificates/status")
        # Accept either 401 or 403 as valid authentication failure
        assert response.status_code in [401, 403]
    
    def test_certificate_status_endpoint(self, auth_client, mock_letsencrypt_enabled):
        """Test the certificate status endpoint."""
        with patch("modules.certificate_manager.certificate_manager.check_cert_status") as mock_check_cert_status, \
             patch("modules.certificate_manager.certificate_manager.get_cert_expiry_date") as mock_get_cert_expiry_date, \
             patch.object(certificate_manager, '_renew_before_days', 30), \
             patch.object(certificate_manager, '_cert_dir', './certs'), \
             patch.object(certificate_manager, '_challenge_type', 'http-01'), \
             patch.object(certificate_manager, '_auto_renew', True):
             
            # Mock certificate status
            mock_check_cert_status.return_value = (True, 25)  # Has certs, 25 days remaining
            mock_get_cert_expiry_date.return_value = "2023-08-01T00:00:00"
            
            response = auth_client.get("/api/v1/certificates/status")
            assert response.status_code == 200
            
            data = response.json()
            assert data["has_certificate"] == True
            assert data["days_remaining"] == 25
            assert data["expiry_date"] == "2023-08-01T00:00:00"
            assert data["needs_renewal"] == True  # Since days_remaining=25 is less than renew_before_days=30
            assert "config" in data