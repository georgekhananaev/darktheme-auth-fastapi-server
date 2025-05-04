from fastapi import APIRouter, Depends, HTTPException, Request, Body
from typing import Dict, List, Optional
from pydantic import BaseModel, EmailStr
from auth.fastapi_auth import create_auth_dependency, AuthOptions
from modules.certificate_manager import certificate_manager
from modules.logger import log_system, log_access

router = APIRouter()


class CertificateRequest(BaseModel):
    """
    Request model for certificate issuance or renewal
    """
    email: Optional[EmailStr] = None
    domains: Optional[List[str]] = None
    staging: Optional[bool] = None
    force_renewal: Optional[bool] = False


@router.get("/info")
async def get_certificate_info(
    request: Request,
    auth_info: Dict = Depends(create_auth_dependency(AuthOptions.REQUIRE_BEARER))
):
    """
    Get information about the current SSL certificate
    
    Returns:
        Dict containing certificate information
    """
    client_ip = auth_info.get("client_ip", "unknown")
    
    log_access(
        "Certificate info request",
        client_ip=client_ip,
        level="INFO"
    )
    
    cert_info = certificate_manager.get_cert_info()
    return cert_info


@router.post("/issue")
async def issue_certificate(
    request: Request,
    cert_request: CertificateRequest = Body(...),
    auth_info: Dict = Depends(create_auth_dependency(AuthOptions.REQUIRE_BEARER))
):
    """
    Issue a new Let's Encrypt certificate
    
    Args:
        cert_request: Certificate issuance request parameters
        
    Returns:
        Dict containing the result of the certificate issuance
    """
    client_ip = auth_info.get("client_ip", "unknown")
    
    log_access(
        "Certificate issuance request",
        client_ip=client_ip,
        level="INFO"
    )
    
    log_system(
        f"Certificate issuance requested for domains: {cert_request.domains}",
        level="INFO"
    )
    
    result = await certificate_manager.issue_certificate(
        domains=cert_request.domains,
        email=cert_request.email,
        staging=cert_request.staging,
        force_renewal=cert_request.force_renewal
    )
    
    if not result["success"]:
        log_system(
            f"Certificate issuance failed: {result['message']}",
            level="ERROR"
        )
        raise HTTPException(status_code=400, detail=result["message"])
    
    log_system(
        f"Certificate issuance successful for domains: {result.get('domains', [])}",
        level="INFO"
    )
    
    return result


@router.post("/renew")
async def renew_certificate(
    request: Request,
    force_renewal: bool = Body(False),
    auth_info: Dict = Depends(create_auth_dependency(AuthOptions.REQUIRE_BEARER))
):
    """
    Renew the current Let's Encrypt certificate
    
    Args:
        force_renewal: Whether to force renewal even if not needed
        
    Returns:
        Dict containing the result of the certificate renewal
    """
    client_ip = auth_info.get("client_ip", "unknown")
    
    log_access(
        "Certificate renewal request",
        client_ip=client_ip,
        level="INFO"
    )
    
    # Check if we should renew
    has_certs, days_remaining = certificate_manager.check_cert_status()
    
    if not has_certs:
        log_system(
            "Certificate renewal requested but no certificates found",
            level="WARNING"
        )
        raise HTTPException(
            status_code=404, 
            detail="No certificates found to renew. Please issue a new certificate first."
        )
    
    # If force renewal is requested or certificates are close to expiry
    if force_renewal or days_remaining <= certificate_manager._renew_before_days:
        log_system(
            f"Initiating certificate renewal (force={force_renewal}, days_remaining={days_remaining})",
            level="INFO"
        )
        
        result = await certificate_manager.renew_certificates()
        
        if not result["success"]:
            log_system(
                f"Certificate renewal failed: {result['message']}",
                level="ERROR"
            )
            raise HTTPException(status_code=400, detail=result["message"])
        
        log_system(
            "Certificate renewal successful",
            level="INFO"
        )
        
        return result
    else:
        log_system(
            f"Certificate renewal not needed (days_remaining={days_remaining})",
            level="INFO"
        )
        
        return {
            "success": True,
            "message": f"Certificate still valid for {days_remaining} days. Renewal not needed.",
            "days_remaining": days_remaining,
            "expiry": certificate_manager.get_cert_expiry_date()
        }


@router.get("/status")
async def check_certificate_status(
    request: Request,
    auth_info: Dict = Depends(create_auth_dependency(AuthOptions.REQUIRE_BEARER))
):
    """
    Check the status of the current SSL certificate
    
    Returns:
        Dict containing certificate status information
    """
    client_ip = auth_info.get("client_ip", "unknown")
    
    log_access(
        "Certificate status request",
        client_ip=client_ip,
        level="INFO"
    )
    
    has_certs, days_remaining = certificate_manager.check_cert_status()
    
    return {
        "has_certificate": has_certs,
        "days_remaining": days_remaining,
        "expiry_date": certificate_manager.get_cert_expiry_date(),
        "needs_renewal": days_remaining <= certificate_manager._renew_before_days if has_certs else False,
        "config": {
            "auto_renew": certificate_manager._auto_renew,
            "renew_before_days": certificate_manager._renew_before_days,
            "cert_dir": certificate_manager._cert_dir,
            "challenge_type": certificate_manager._challenge_type
        }
    }