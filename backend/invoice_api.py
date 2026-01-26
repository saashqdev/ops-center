"""
Invoice API for Epic 5.0
User-facing endpoints for invoice history and downloads
"""

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
from datetime import datetime

from invoice_manager import invoice_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


class InvoiceResponse(BaseModel):
    id: int
    stripe_invoice_id: str
    amount: float
    currency: str
    status: str
    tier_name: str
    billing_cycle: Optional[str] = None
    issued_at: datetime
    invoice_url: Optional[str] = None
    invoice_pdf: Optional[str] = None


async def get_current_user_email(request: Request) -> str:
    """Get current user email from session"""
    from redis_session import redis_session_manager
    
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_data = redis_session_manager.get(session_token)
    if not session_data:
        raise HTTPException(status_code=401, detail="Session expired")
    
    user = session_data.get("user", {})
    email = user.get("email")
    
    if not email:
        raise HTTPException(status_code=401, detail="User email not found in session")
    
    return email


@router.get("/", response_model=List[InvoiceResponse])
async def get_my_invoices(
    request: Request,
    limit: int = 50
):
    """
    Get invoice history for current user
    """
    try:
        user_email = await get_current_user_email(request)
        invoices = await invoice_manager.get_invoices_by_email(user_email, limit=limit)
        
        return invoices
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invoices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve invoices")


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: int,
    request: Request
):
    """
    Get a specific invoice by ID
    """
    try:
        user_email = await get_current_user_email(request)
        invoice = await invoice_manager.get_invoice_by_id(invoice_id)
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Verify invoice belongs to current user
        if invoice.get('email') != user_email:
            raise HTTPException(status_code=403, detail="Not authorized to view this invoice")
        
        return invoice
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invoice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve invoice")


@router.get("/{invoice_id}/download")
async def download_invoice_pdf(
    invoice_id: int,
    request: Request
):
    """
    Download invoice as PDF
    """
    try:
        user_email = await get_current_user_email(request)
        invoice = await invoice_manager.get_invoice_by_id(invoice_id)
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Verify invoice belongs to current user
        if invoice.get('email') != user_email:
            raise HTTPException(status_code=403, detail="Not authorized to download this invoice")
        
        # If Stripe PDF URL exists, redirect to it
        if invoice.get('invoice_pdf'):
            return {
                "pdf_url": invoice['invoice_pdf'],
                "message": "Use the pdf_url to download the invoice"
            }
        
        # Generate PDF on the fly
        invoice_data = {
            'invoice_number': f"INV-{invoice['id']:06d}",
            'customer_email': invoice['email'],
            'tier_name': invoice['tier_name'],
            'billing_cycle': invoice.get('billing_cycle', 'monthly'),
            'amount': float(invoice['amount']),
            'currency': invoice['currency'],
            'status': invoice['status'],
            'issued_at': invoice['issued_at'].strftime('%Y-%m-%d'),
            'stripe_invoice_id': invoice['stripe_invoice_id']
        }
        
        pdf_buffer = invoice_manager.generate_invoice_pdf(invoice_data)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=invoice-{invoice['id']}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading invoice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate invoice PDF")


@router.get("/stripe/portal-session")
async def create_customer_portal_session(request: Request):
    """
    Create a Stripe Customer Portal session for payment method management
    """
    try:
        import stripe
        import os
        
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        user_email = await get_current_user_email(request)
        
        # Get user's Stripe customer ID
        from database import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            subscription = await conn.fetchrow("""
                SELECT stripe_customer_id
                FROM user_subscriptions
                WHERE email = $1 AND stripe_customer_id IS NOT NULL
                LIMIT 1
            """, user_email)
            
            if not subscription or not subscription['stripe_customer_id']:
                raise HTTPException(
                    status_code=404,
                    detail="No active subscription with payment method found"
                )
            
            # Create portal session
            session = stripe.billing_portal.Session.create(
                customer=subscription['stripe_customer_id'],
                return_url=os.getenv('APP_URL', 'http://localhost:5173') + '/settings/billing'
            )
            
            return {
                "url": session.url,
                "message": "Redirect user to this URL to manage payment methods"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating portal session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create customer portal session")
