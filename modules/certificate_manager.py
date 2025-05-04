import os
import logging
import subprocess
import datetime
import tempfile
import shutil
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from modules.config import config
from modules.logger import log_system

# Set up logger for the certbot process
certbot_logger = logging.getLogger("certbot")


class CertificateManager:
    """
    Certificate Manager class for handling Let's Encrypt certificate operations.
    Provides methods for certificate issuance, renewal, and checking status.
    """
    _instance = None
    _scheduler = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CertificateManager, cls).__new__(cls)
            cls._initialize()
        return cls._instance
    
    @classmethod
    def _initialize(cls):
        """Initialize the certificate manager with configuration"""
        cls._letsencrypt_config = config.get('security', 'letsencrypt', {})
        cls._https_config = config.get('security', 'https', {})
        cls._cert_dir = cls._letsencrypt_config.get('cert_dir', './certs')
        cls._email = cls._letsencrypt_config.get('email', '')
        cls._domains = cls._letsencrypt_config.get('domains', [])
        cls._staging = cls._letsencrypt_config.get('staging', True)
        cls._challenge_type = cls._letsencrypt_config.get('challenge_type', 'http-01')
        cls._auto_renew = cls._letsencrypt_config.get('auto_renew', True)
        cls._renew_before_days = cls._letsencrypt_config.get('renew_before_days', 30)
        
        # Create the certificate directory if it doesn't exist
        os.makedirs(cls._cert_dir, exist_ok=True)
        
        # Initialize the scheduler for certificate renewal
        cls._scheduler = AsyncIOScheduler()
    
    @classmethod
    async def start(cls):
        """Start the certificate manager and initialize automatic renewal"""
        log_system("Starting Certificate Manager", level="INFO")
        
        # Check if Let's Encrypt is enabled
        if not cls._letsencrypt_config.get('enabled', False):
            log_system("Let's Encrypt is disabled. Certificate Manager not started.", level="INFO")
            return
        
        # Load initial certificates
        await cls.update_cert_paths()
        
        # Check if certificates exist and their expiry
        has_certs, days_remaining = cls.check_cert_status()
        
        # Schedule certificate renewal if auto-renew is enabled
        if cls._auto_renew:
            # If certificates are valid, schedule renewal before expiry
            if has_certs and days_remaining > 0:
                # Schedule renewal for N days before expiry
                renewal_days = min(days_remaining - 1, cls._renew_before_days)
                renewal_date = datetime.datetime.now() + datetime.timedelta(days=renewal_days)
                
                log_system(
                    f"Scheduling certificate renewal for {renewal_date.strftime('%Y-%m-%d')} "
                    f"({renewal_days} days from now)", 
                    level="INFO"
                )
                
                cls._scheduler.add_job(
                    cls.renew_certificates,
                    'date',
                    run_date=renewal_date,
                    id='certificate_renewal'
                )
            else:
                # Schedule daily check for certificate validity
                log_system("Scheduling daily certificate check", level="INFO")
                cls._scheduler.add_job(
                    cls.check_and_renew_if_needed,
                    'interval',
                    days=1,
                    id='certificate_check'
                )
            
            # Start the scheduler
            if not cls._scheduler.running:
                cls._scheduler.start()
                log_system("Certificate renewal scheduler started", level="INFO")
    
    @classmethod
    async def stop(cls):
        """Stop the certificate manager and shutdown scheduler"""
        if cls._scheduler and cls._scheduler.running:
            cls._scheduler.shutdown()
            log_system("Certificate renewal scheduler stopped", level="INFO")
    
    @classmethod
    async def issue_certificate(cls, domains: Optional[List[str]] = None, 
                               email: Optional[str] = None, 
                               staging: Optional[bool] = None,
                               force_renewal: bool = False) -> Dict[str, Any]:
        """
        Issue a new Let's Encrypt certificate for the specified domains
        
        Args:
            domains: List of domain names to include in the certificate
            email: Email address for Let's Encrypt registration
            staging: Whether to use Let's Encrypt staging environment
            force_renewal: Force certificate renewal even if not needed
            
        Returns:
            Dict containing the result of the certificate issuance
        """
        # Use provided values or fall back to configuration
        email = email or cls._email
        domains = domains or cls._domains
        staging = staging if staging is not None else cls._staging
        
        # Validate required parameters
        if not email:
            error_msg = "Email address is required for Let's Encrypt registration"
            log_system(error_msg, level="ERROR")
            return {"success": False, "message": error_msg}
        
        if not domains:
            error_msg = "At least one domain name is required for the certificate"
            log_system(error_msg, level="ERROR")
            return {"success": False, "message": error_msg}
        
        # Prepare the certbot command
        certbot_cmd = [
            "certbot", "certonly",
            "--non-interactive",
            f"--{cls._challenge_type}",
            "--agree-tos",
            f"--email={email}"
        ]
        
        # Add staging flag if requested
        if staging:
            certbot_cmd.append("--staging")
        
        # Add domains
        for domain in domains:
            certbot_cmd.append(f"-d {domain}")
        
        # Add force-renewal flag if requested
        if force_renewal:
            certbot_cmd.append("--force-renewal")
        
        # Add webroot plugin options if using http-01
        if cls._challenge_type == "http-01":
            # Create a temporary directory for webroot
            with tempfile.TemporaryDirectory() as webroot_path:
                certbot_cmd.extend([
                    "--webroot",
                    f"--webroot-path={webroot_path}",
                ])
                
                log_system(f"Running certbot with command: {' '.join(certbot_cmd)}", level="INFO")
                
                try:
                    # Run certbot command
                    process = subprocess.run(
                        certbot_cmd,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    
                    if process.returncode == 0:
                        # Certificate issued successfully
                        log_system(
                            f"Successfully issued Let's Encrypt certificate for domains: {', '.join(domains)}",
                            level="INFO"
                        )
                        
                        # Find and copy the certificates to our certificate directory
                        await cls._copy_certbot_certificates(domains[0])
                        
                        # Update certificate paths in configuration
                        await cls.update_cert_paths()
                        
                        return {
                            "success": True,
                            "message": "Certificate issued successfully",
                            "domains": domains,
                            "is_staging": staging,
                            "expiry": cls.get_cert_expiry_date()
                        }
                    else:
                        # Certificate issuance failed
                        error_msg = f"Failed to issue certificate: {process.stderr}"
                        log_system(error_msg, level="ERROR")
                        return {"success": False, "message": error_msg}
                        
                except Exception as e:
                    error_msg = f"Error issuing certificate: {str(e)}"
                    log_system(error_msg, level="ERROR")
                    return {"success": False, "message": error_msg}
        else:
            # For other challenge types
            log_system(f"Running certbot with command: {' '.join(certbot_cmd)}", level="INFO")
            
            try:
                # Run certbot command
                process = subprocess.run(
                    certbot_cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if process.returncode == 0:
                    # Certificate issued successfully
                    log_system(
                        f"Successfully issued Let's Encrypt certificate for domains: {', '.join(domains)}",
                        level="INFO"
                    )
                    
                    # Find and copy the certificates to our certificate directory
                    await cls._copy_certbot_certificates(domains[0])
                    
                    # Update certificate paths in configuration
                    await cls.update_cert_paths()
                    
                    return {
                        "success": True,
                        "message": "Certificate issued successfully",
                        "domains": domains,
                        "is_staging": staging,
                        "expiry": cls.get_cert_expiry_date()
                    }
                else:
                    # Certificate issuance failed
                    error_msg = f"Failed to issue certificate: {process.stderr}"
                    log_system(error_msg, level="ERROR")
                    return {"success": False, "message": error_msg}
                    
            except Exception as e:
                error_msg = f"Error issuing certificate: {str(e)}"
                log_system(error_msg, level="ERROR")
                return {"success": False, "message": error_msg}
    
    @classmethod
    async def _copy_certbot_certificates(cls, primary_domain: str) -> bool:
        """
        Copy certificates from certbot's directory to our certificate directory
        
        Args:
            primary_domain: The primary domain for which the certificate was issued
            
        Returns:
            bool indicating if the operation was successful
        """
        try:
            # Default certbot live directory
            certbot_live_dir = f"/etc/letsencrypt/live/{primary_domain}"
            
            # Check if the directory exists
            if not os.path.exists(certbot_live_dir):
                log_system(
                    f"Certbot live directory not found at {certbot_live_dir}",
                    level="ERROR"
                )
                return False
            
            # Define source and destination paths
            fullchain_src = os.path.join(certbot_live_dir, "fullchain.pem")
            privkey_src = os.path.join(certbot_live_dir, "privkey.pem")
            
            fullchain_dst = os.path.join(cls._cert_dir, "server.crt")
            privkey_dst = os.path.join(cls._cert_dir, "server.key")
            
            # Copy the certificates
            shutil.copy2(fullchain_src, fullchain_dst)
            shutil.copy2(privkey_src, privkey_dst)
            
            # Set proper permissions
            os.chmod(fullchain_dst, 0o644)
            os.chmod(privkey_dst, 0o600)
            
            log_system(f"Certificates copied to {cls._cert_dir}", level="INFO")
            return True
            
        except Exception as e:
            log_system(f"Error copying certificates: {str(e)}", level="ERROR")
            return False
    
    @classmethod
    async def renew_certificates(cls) -> Dict[str, Any]:
        """
        Renew Let's Encrypt certificates
        
        Returns:
            Dict containing the result of the certificate renewal
        """
        try:
            log_system("Starting certificate renewal process", level="INFO")
            
            # Prepare the certbot command for renewal
            certbot_cmd = [
                "certbot", "renew",
                "--non-interactive"
            ]
            
            # Run certbot command
            process = subprocess.run(
                certbot_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if process.returncode == 0:
                # Check if any certificates were actually renewed
                if "No renewals were attempted" in process.stdout:
                    log_system("No certificates needed renewal", level="INFO")
                    return {
                        "success": True,
                        "message": "No certificates needed renewal",
                        "renewed": False
                    }
                else:
                    # Certificates were renewed, copy them to our directory
                    primary_domain = cls._domains[0] if cls._domains else None
                    if primary_domain:
                        await cls._copy_certbot_certificates(primary_domain)
                        
                    # Update certificate paths in configuration
                    await cls.update_cert_paths()
                    
                    # Schedule next renewal
                    days_remaining = cls.get_days_remaining()
                    renewal_days = min(days_remaining - 1, cls._renew_before_days)
                    renewal_date = datetime.datetime.now() + datetime.timedelta(days=renewal_days)
                    
                    # Reschedule renewal job
                    if cls._scheduler.running:
                        try:
                            cls._scheduler.remove_job('certificate_renewal')
                        except:
                            pass
                        
                        cls._scheduler.add_job(
                            cls.renew_certificates,
                            'date',
                            run_date=renewal_date,
                            id='certificate_renewal'
                        )
                        
                        log_system(
                            f"Scheduled next certificate renewal for {renewal_date.strftime('%Y-%m-%d')}",
                            level="INFO"
                        )
                    
                    log_system("Certificates successfully renewed", level="INFO")
                    return {
                        "success": True,
                        "message": "Certificates successfully renewed",
                        "renewed": True,
                        "next_renewal": renewal_date.isoformat(),
                        "expiry": cls.get_cert_expiry_date()
                    }
            else:
                # Certificate renewal failed
                error_msg = f"Failed to renew certificates: {process.stderr}"
                log_system(error_msg, level="ERROR")
                return {"success": False, "message": error_msg}
                
        except Exception as e:
            error_msg = f"Error renewing certificates: {str(e)}"
            log_system(error_msg, level="ERROR")
            return {"success": False, "message": error_msg}
    
    @classmethod
    async def check_and_renew_if_needed(cls) -> Dict[str, Any]:
        """
        Check if certificates need renewal and renew if necessary
        
        Returns:
            Dict containing the result of the check and any renewal
        """
        has_certs, days_remaining = cls.check_cert_status()
        
        if not has_certs:
            log_system("No certificates found. Issuing new certificates.", level="INFO")
            return await cls.issue_certificate()
        
        if days_remaining <= cls._renew_before_days:
            log_system(f"Certificates expire in {days_remaining} days. Renewing now.", level="INFO")
            return await cls.renew_certificates()
        
        log_system(f"Certificates valid for {days_remaining} days. No renewal needed.", level="INFO")
        return {
            "success": True,
            "message": f"Certificates valid for {days_remaining} days",
            "days_remaining": days_remaining,
            "expiry": cls.get_cert_expiry_date()
        }
    
    @classmethod
    def check_cert_status(cls) -> Tuple[bool, int]:
        """
        Check if certificates exist and are valid
        
        Returns:
            Tuple of (has_certificates, days_remaining)
        """
        cert_path = os.path.join(cls._cert_dir, "server.crt")
        key_path = os.path.join(cls._cert_dir, "server.key")
        
        # Check if certificate files exist
        if not os.path.exists(cert_path) or not os.path.exists(key_path):
            return False, 0
        
        # Check certificate expiry
        try:
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
                
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            expiry_date = cert.not_valid_after
            now = datetime.datetime.now()
            
            # Calculate days remaining until expiry
            days_remaining = (expiry_date - now.replace(tzinfo=None)).days
            
            return True, days_remaining
            
        except Exception as e:
            log_system(f"Error checking certificate status: {str(e)}", level="ERROR")
            return False, 0
    
    @classmethod
    def get_days_remaining(cls) -> int:
        """
        Get days remaining until certificate expiry
        
        Returns:
            int: Days remaining, or 0 if certificate is invalid or missing
        """
        has_certs, days_remaining = cls.check_cert_status()
        return days_remaining if has_certs else 0
    
    @classmethod
    def get_cert_expiry_date(cls) -> Optional[str]:
        """
        Get the certificate expiry date
        
        Returns:
            str: Expiry date in ISO format, or None if certificate is invalid or missing
        """
        cert_path = os.path.join(cls._cert_dir, "server.crt")
        
        if not os.path.exists(cert_path):
            return None
        
        try:
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
                
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            expiry_date = cert.not_valid_after
            
            return expiry_date.isoformat()
            
        except Exception as e:
            log_system(f"Error getting certificate expiry date: {str(e)}", level="ERROR")
            return None
    
    @classmethod
    def get_cert_info(cls) -> Dict[str, Any]:
        """
        Get detailed information about the current certificate
        
        Returns:
            Dict containing certificate information
        """
        cert_path = os.path.join(cls._cert_dir, "server.crt")
        
        if not os.path.exists(cert_path):
            return {
                "has_cert": False,
                "message": "No certificate found"
            }
        
        try:
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
                
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # Extract certificate information
            issuer = cert.issuer.rfc4514_string()
            subject = cert.subject.rfc4514_string()
            not_before = cert.not_valid_before
            not_after = cert.not_valid_after
            
            # Extract Subject Alternative Names (domains)
            san = None
            for ext in cert.extensions:
                if ext.oid.dotted_string == '2.5.29.17':  # subjectAltName
                    san = ext.value
                    break
            
            domains = []
            if san:
                for name in san:
                    if isinstance(name, x509.DNSName):
                        domains.append(name.value)
            
            # Calculate days remaining
            now = datetime.datetime.now()
            days_remaining = (not_after - now.replace(tzinfo=None)).days
            
            return {
                "has_cert": True,
                "issuer": issuer,
                "subject": subject,
                "domains": domains,
                "not_before": not_before.isoformat(),
                "not_after": not_after.isoformat(),
                "days_remaining": days_remaining,
                "is_valid": days_remaining > 0
            }
            
        except Exception as e:
            log_system(f"Error getting certificate info: {str(e)}", level="ERROR")
            return {
                "has_cert": True,
                "error": str(e),
                "message": "Error parsing certificate"
            }
    
    @classmethod
    async def update_cert_paths(cls) -> None:
        """Update certificate paths in configuration based on actual files"""
        cert_path = os.path.join(cls._cert_dir, "server.crt")
        key_path = os.path.join(cls._cert_dir, "server.key")
        
        # Update configuration if files exist
        if os.path.exists(cert_path) and os.path.exists(key_path):
            cls._https_config['cert_file'] = cert_path
            cls._https_config['key_file'] = key_path
            log_system(f"Updated certificate paths in configuration", level="INFO")


# Create a global instance for convenient access
certificate_manager = CertificateManager()