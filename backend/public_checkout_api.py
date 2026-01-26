"""
Public Checkout API for Self-Service Subscription Purchase
Epic 5.0 - E-commerce & Self-Service Checkout

Provides unauthenticated endpoints for new users to purchase subscriptions
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import logging
import os
import stripe
from datetime import datetime
from subscription_manager_simple import subscription_manager
from invoice_manager import invoice_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/checkout", tags=["checkout"])

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3000/checkout/success")
STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", "http://localhost:3000/checkout/cancelled")


class CreateCheckoutRequest(BaseModel):
    tier_code: str
    billing_cycle: str  # 'monthly' or 'yearly'
    email: EmailStr
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str
    publishable_key: str


class GetConfigResponse(BaseModel):
    publishable_key: str
    currency: str
    country: str


@router.get("/config", response_model=GetConfigResponse)
async def get_checkout_config():
    """
    Get Stripe publishable key and configuration for frontend
    No authentication required
    """
    if not STRIPE_PUBLISHABLE_KEY:
        raise HTTPException(
            status_code=500, 
            detail="Stripe is not configured. Please contact support."
        )
    
    return GetConfigResponse(
        publishable_key=STRIPE_PUBLISHABLE_KEY,
        currency="usd",
        country="US"
    )


@router.post("/create-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(request: CreateCheckoutRequest):
    """
    Create a Stripe Checkout session for new subscription purchase
    No authentication required - for public self-service checkout
    
    Flow:
    1. Validate tier and get price
    2. Create/get Stripe customer
    3. Create checkout session
    4. Return session ID and URL for redirect
    """
    try:
        if not stripe.api_key:
            raise HTTPException(
                status_code=500,
                detail="Stripe is not configured"
            )
        
        # Validate tier code
        from database import get_db_pool
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            tier = await conn.fetchrow("""
                SELECT 
                    id,
                    tier_code,
                    tier_name,
                    price_monthly,
                    price_yearly,
                    stripe_price_monthly,
                    stripe_price_yearly
                FROM subscription_tiers
                WHERE tier_code = $1 AND is_active = true
            """, request.tier_code)
            
            if not tier:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tier '{request.tier_code}' not found"
                )
            
            # Get price ID based on billing cycle
            if request.billing_cycle == 'yearly':
                price_id = tier['stripe_price_yearly']
                if not price_id:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Yearly billing not available for {tier['tier_name']}"
                    )
            elif request.billing_cycle == 'monthly':
                price_id = tier['stripe_price_monthly']
                if not price_id:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Monthly billing not available for {tier['tier_name']}"
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="billing_cycle must be 'monthly' or 'yearly'"
                )
        
        # Create or retrieve Stripe customer
        customers = stripe.Customer.list(email=request.email, limit=1)
        
        if customers.data:
            customer = customers.data[0]
            logger.info(f"Using existing Stripe customer: {customer.id}")
        else:
            customer = stripe.Customer.create(
                email=request.email,
                metadata={
                    'tier_code': request.tier_code,
                    'billing_cycle': request.billing_cycle,
                    'source': 'public_checkout'
                }
            )
            logger.info(f"Created new Stripe customer: {customer.id}")
        
        # Determine success/cancel URLs
        success_url = request.success_url or f"{STRIPE_SUCCESS_URL}?tier={request.tier_code}&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = request.cancel_url or STRIPE_CANCEL_URL
        
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            mode='subscription',
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'tier_code': request.tier_code,
                'tier_name': tier['tier_name'],
                'billing_cycle': request.billing_cycle,
                'customer_email': request.email
            },
            allow_promotion_codes=True,
            billing_address_collection='required',
            customer_update={
                'address': 'auto',
                'name': 'auto'
            }
        )
        
        logger.info(f"Created checkout session {checkout_session.id} for {request.email}")
        
        return CheckoutSessionResponse(
            session_id=checkout_session.id,
            checkout_url=checkout_session.url,
            publishable_key=STRIPE_PUBLISHABLE_KEY
        )
        
    except HTTPException:
        raise
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Stripe error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create checkout session"
        )


@router.get("/session/{session_id}")
async def get_checkout_session(session_id: str):
    """
    Retrieve checkout session details
    Used to verify payment status after redirect
    """
    try:
        if not stripe.api_key:
            raise HTTPException(status_code=500, detail="Stripe not configured")
        
        session = stripe.checkout.Session.retrieve(session_id)
        
        return {
            "id": session.id,
            "payment_status": session.payment_status,
            "status": session.status,
            "customer_email": session.customer_details.email if session.customer_details else None,
            "amount_total": session.amount_total,
            "currency": session.currency,
            "metadata": session.metadata
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error retrieving session: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving session: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.post("/webhook")
async def handle_checkout_webhook(request: Request):
    """
    Handle Stripe webhook events for checkout completion
    This endpoint is called by Stripe when events occur (payment success, etc.)
    """
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        if not webhook_secret:
            logger.warning("Stripe webhook secret not configured")
            # For development, process without verification
            event = stripe.Event.construct_from(
                await request.json(),
                stripe.api_key
            )
        else:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            except stripe.error.SignatureVerificationError as e:
                logger.error(f"Webhook signature verification failed: {e}")
                raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle the event
        if event.type == 'checkout.session.completed':
            session = event.data.object
            await handle_checkout_completed(session)
            
        elif event.type == 'customer.subscription.created':
            subscription = event.data.object
            await handle_subscription_created(subscription)
            
        elif event.type == 'customer.subscription.updated':
            subscription = event.data.object
            await handle_subscription_updated(subscription)
            
        elif event.type == 'customer.subscription.deleted':
            subscription = event.data.object
            await handle_subscription_deleted(subscription)
        
        elif event.type == 'invoice.paid':
            invoice = event.data.object
            await handle_invoice_paid(invoice)
        
        elif event.type == 'invoice.payment_failed':
            invoice = event.data.object
            await handle_invoice_payment_failed(invoice)
        
        else:
            logger.info(f"Unhandled webhook event type: {event.type}")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_checkout_completed(session: Dict[str, Any]):
    """
    Process completed checkout session
    - Create user account if new
    - Activate subscription
    - Send welcome email
    """
    try:
        customer_email = session.get('customer_details', {}).get('email')
        tier_code = session.get('metadata', {}).get('tier_code')
        billing_cycle = session.get('metadata', {}).get('billing_cycle', 'monthly')
        
        stripe_customer_id = session.get('customer')
        stripe_subscription_id = session.get('subscription')
        
        if not all([customer_email, tier_code, stripe_customer_id, stripe_subscription_id]):
            logger.error(f"Missing required data in checkout session: {session.get('id')}")
            return
        
        logger.info(f"Processing checkout completion for {customer_email}, tier: {tier_code}")
        
        # Create/update subscription
        result = await subscription_manager.create_subscription_from_checkout(
            email=customer_email,
            tier_code=tier_code,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            billing_cycle=billing_cycle
        )
        
        logger.info(f"Subscription created: {result}")
        
        # TODO: Send welcome email
        # TODO: Trigger onboarding flow
        
    except Exception as e:
        logger.error(f"Error handling checkout completion: {e}")
        raise


async def handle_subscription_created(subscription: Dict[str, Any]):
    """
    Process new subscription creation
    - Update user tier in database
    - Grant feature access
    """
    try:
        subscription_id = subscription.get('id')
        customer_id = subscription.get('customer')
        status = subscription.get('status')
        
        current_period_start = datetime.fromtimestamp(subscription.get('current_period_start', 0))
        current_period_end = datetime.fromtimestamp(subscription.get('current_period_end', 0))
        
        logger.info(f"Processing subscription created: {subscription_id}, status: {status}")
        
        # Update subscription status
        await subscription_manager.update_subscription_status(
            stripe_subscription_id=subscription_id,
            status=status,
            current_period_start=current_period_start,
            current_period_end=current_period_end
        )
        
        logger.info(f"Subscription status updated: {subscription_id}")
        
    except Exception as e:
        logger.error(f"Error handling subscription creation: {e}")
        raise


async def handle_subscription_updated(subscription: Dict[str, Any]):
    """
    Process subscription update
    - Handle plan changes
    - Update billing cycle
    """
    try:
        subscription_id = subscription.get('id')
        status = subscription.get('status')
        
        current_period_start = datetime.fromtimestamp(subscription.get('current_period_start', 0))
        current_period_end = datetime.fromtimestamp(subscription.get('current_period_end', 0))
        
        logger.info(f"Processing subscription update: {subscription_id}, status: {status}")
        
        # Update subscription status
        await subscription_manager.update_subscription_status(
            stripe_subscription_id=subscription_id,
            status=status,
            current_period_start=current_period_start,
            current_period_end=current_period_end
        )
        
        logger.info(f"Subscription updated: {subscription_id}")
        
    except Exception as e:
        logger.error(f"Error handling subscription update: {e}")
        raise


async def handle_subscription_deleted(subscription: Dict[str, Any]):
    """
    Process subscription cancellation
    - Downgrade user to free tier
    - Send cancellation email
    """
    try:
        subscription_id = subscription.get('id')
        
        logger.info(f"Processing subscription deletion: {subscription_id}")
        
        # Update subscription status to canceled
        await subscription_manager.update_subscription_status(
            stripe_subscription_id=subscription_id,
            status='canceled'
        )
        
        logger.info(f"Subscription canceled: {subscription_id}")
        
        # TODO: Send cancellation confirmation email
        # TODO: Downgrade to trial tier if needed
        
    except Exception as e:
        logger.error(f"Error handling subscription deletion: {e}")
        raise


async def handle_invoice_paid(invoice: Dict[str, Any]):
    """
    Process successful invoice payment
    - Create invoice record
    - Send invoice email
    """
    try:
        from invoice_manager import invoice_manager
        
        invoice_id = invoice.get('id')
        logger.info(f"Processing paid invoice: {invoice_id}")
        
        # Create invoice record
        await invoice_manager.process_stripe_invoice(invoice)
        
        # TODO: Send invoice email to customer
        
    except Exception as e:
        logger.error(f"Error handling invoice payment: {e}")
        raise


async def handle_invoice_payment_failed(invoice: Dict[str, Any]):
    """
    Process failed invoice payment
    - Update subscription status
    - Send payment failed email
    """
    try:
        from invoice_manager import invoice_manager
        
        invoice_id = invoice.get('id')
        stripe_subscription_id = invoice.get('subscription')
        
        logger.warning(f"Payment failed for invoice {invoice_id}, subscription {stripe_subscription_id}")
        
        # Update subscription status to past_due
        await subscription_manager.update_subscription_status(
            stripe_subscription_id=stripe_subscription_id,
            status='past_due'
        )
        
        # Create failed invoice record
        await invoice_manager.process_stripe_invoice(invoice)
        
        # TODO: Send payment failed email
        # TODO: Implement retry logic
        
    except Exception as e:
        logger.error(f"Error handling failed payment: {e}")
        raise

async def handle_invoice_paid(invoice: Dict[str, Any]):
    """
    Process successful invoice payment
    - Create invoice record
    - Send invoice email
    """
    try:
        invoice_id = invoice.get('id')
        logger.info(f"Processing paid invoice: {invoice_id}")
        
        # Create invoice record
        await invoice_manager.process_stripe_invoice(invoice)
        
        # TODO: Send invoice email to customer
        
    except Exception as e:
        logger.error(f"Error handling invoice payment: {e}")
        raise


async def handle_invoice_payment_failed(invoice: Dict[str, Any]):
    """
    Process failed invoice payment
    - Update subscription status
    - Send payment failed email
    """
    try:
        invoice_id = invoice.get('id')
        stripe_subscription_id = invoice.get('subscription')
        
        logger.warning(f"Payment failed for invoice {invoice_id}, subscription {stripe_subscription_id}")
        
        # Update subscription status to past_due
        await subscription_manager.update_subscription_status(
            stripe_subscription_id=stripe_subscription_id,
            status='past_due'
        )
        
        # Create failed invoice record
        await invoice_manager.process_stripe_invoice(invoice)
        
        # Send payment failed email
        from database import get_db_pool
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            subscription = await conn.fetchrow("""
                SELECT email FROM user_subscriptions
                WHERE stripe_subscription_id = $1
            """, stripe_subscription_id)
            
            if subscription:
                from email_service import email_service
                amount = invoice.get('amount_due', 0) / 100
                failure_reason = invoice.get('last_payment_error', {}).get('message')
                
                await email_service.send_payment_failed(
                    to=subscription['email'],
                    amount=amount,
                    reason=failure_reason
                )
                logger.info(f"Sent payment failed email to {subscription['email']}")
        
        # TODO: Implement retry logic with dunning
        
    except Exception as e:
        logger.error(f"Error handling failed payment: {e}")
        raise
