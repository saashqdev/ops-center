"""
Email Service for UC-1 Pro Ops Center
Handles transactional emails for subscription events
"""

import os
import logging
from typing import Dict, Optional, Any
import httpx
from datetime import datetime
from database import get_db_pool

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending transactional emails"""

    def __init__(self):
        # Email configuration from environment
        self.enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
        self.provider = os.getenv("EMAIL_PROVIDER", "console")  # console, sendgrid, mailgun, smtp

        # Provider credentials
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.mailgun_api_key = os.getenv("MAILGUN_API_KEY")
        self.mailgun_domain = os.getenv("MAILGUN_DOMAIN")
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")

        # Email settings
        self.from_email = os.getenv("EMAIL_FROM", "noreply@your-domain.com")
        self.from_name = os.getenv("EMAIL_FROM_NAME", "Unicorn Commander")
        self.reply_to = os.getenv("EMAIL_REPLY_TO", "support@your-domain.com")

        logger.info(f"Email service initialized: provider={self.provider}, enabled={self.enabled}")

    async def send_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send email using configured provider

        Args:
            to: Recipient email address
            subject: Email subject line
            html_content: HTML email body
            text_content: Plain text email body (optional)
            metadata: Additional data to log (e.g., subscription_id, invoice_id)

        Returns:
            True if sent successfully, False otherwise
        """
        success = False
        error_message = None
        
        if not self.enabled:
            logger.info(f"[EMAIL DISABLED] Would send to {to}: {subject}")
            logger.debug(f"Email content: {html_content}")
            success = True
        else:
            try:
                # First, try to get active provider from database
                db_provider = await self._get_active_db_provider()
                
                if db_provider and db_provider['provider_type'] == 'postmark':
                    success = await self._send_via_postmark(
                        to, subject, html_content, text_content,
                        db_provider['api_key'], db_provider['smtp_from']
                    )
                elif self.provider == "console":
                    # Console logger for development
                    logger.info(f"[EMAIL] To: {to}")
                    logger.info(f"[EMAIL] Subject: {subject}")
                    logger.info(f"[EMAIL] Content:\n{html_content}")
                    success = True

                elif self.provider == "sendgrid":
                    success = await self._send_via_sendgrid(to, subject, html_content, text_content)

                elif self.provider == "mailgun":
                    success = await self._send_via_mailgun(to, subject, html_content, text_content)

                elif self.provider == "smtp":
                    success = await self._send_via_smtp(to, subject, html_content, text_content)

                else:
                    logger.error(f"Unknown email provider: {self.provider}")
                    error_message = f"Unknown email provider: {self.provider}"
                    success = False

            except Exception as e:
                logger.error(f"Failed to send email to {to}: {type(e).__name__}: {e}")
                error_message = f"{type(e).__name__}: {e}"
                success = False
        
        # Log email attempt
        await self._log_email(to, subject, html_content, text_content, success, error_message, metadata)
        
        return success
    
    async def _log_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str],
        success: bool,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log email send attempt to database"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Import json for metadata serialization
                import json
                metadata_json = json.dumps(metadata) if metadata else None
                
                await conn.execute("""
                    INSERT INTO email_logs (
                        to_email, subject, html_body, text_body,
                        success, error_message, metadata, sent_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
                """, to_email, subject, html_body, text_body, success, 
                error_message, metadata_json, datetime.utcnow())
                
                logger.debug(f"Logged email to {to_email}: success={success}")
        except Exception as e:
            logger.error(f"Error logging email: {e}")

    async def _get_active_db_provider(self) -> Optional[Dict[str, Any]]:
        """Get active email provider from database"""
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM email_providers 
                    WHERE enabled = true 
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error fetching active email provider: {e}")
            return None

    async def _send_via_postmark(
        self, to: str, subject: str, html_content: str, 
        text_content: Optional[str], api_key: str, from_email: str
    ) -> bool:
        """Send email via Postmark API"""
        if not api_key:
            logger.error("Postmark API key not configured")
            return False

        url = "https://api.postmarkapp.com/email"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": api_key
        }

        payload = {
            "From": from_email,
            "To": to,
            "Subject": subject,
            "HtmlBody": html_content,
            "MessageStream": "outbound"
        }

        if text_content:
            payload["TextBody"] = text_content

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                
                if response.status_code == 200:
                    result = response.json()
                    message_id = result.get("MessageID")
                    logger.info(f"Email sent successfully via Postmark to {to} (MessageID: {message_id})")
                    return True
                else:
                    logger.error(f"Postmark API error ({response.status_code}): {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Postmark send error: {type(e).__name__}: {e}")
            return False

    async def send_email_old(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send email using configured provider

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info(f"[EMAIL DISABLED] Would send to {to}: {subject}")
            logger.debug(f"Email content: {html_content}")
            return True

        try:
            if self.provider == "console":
                # Console logger for development
                logger.info(f"[EMAIL] To: {to}")
                logger.info(f"[EMAIL] Subject: {subject}")
                logger.info(f"[EMAIL] Content:\n{html_content}")
                return True

            elif self.provider == "sendgrid":
                return await self._send_via_sendgrid(to, subject, html_content, text_content)

            elif self.provider == "mailgun":
                return await self._send_via_mailgun(to, subject, html_content, text_content)

            elif self.provider == "smtp":
                return await self._send_via_smtp(to, subject, html_content, text_content)

            else:
                logger.error(f"Unknown email provider: {self.provider}")
                return False

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {type(e).__name__}: {e}")
            return False

    async def _send_via_sendgrid(
        self, to: str, subject: str, html_content: str, text_content: Optional[str]
    ) -> bool:
        """Send email via SendGrid API"""
        if not self.sendgrid_api_key:
            logger.error("SendGrid API key not configured")
            return False

        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {self.sendgrid_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": self.from_email, "name": self.from_name},
            "reply_to": {"email": self.reply_to},
            "subject": subject,
            "content": [
                {"type": "text/html", "value": html_content}
            ]
        }

        if text_content:
            payload["content"].insert(0, {"type": "text/plain", "value": text_content})

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)

            if response.status_code in [200, 202]:
                logger.info(f"Email sent successfully via SendGrid to {to}")
                return True
            else:
                logger.error(f"SendGrid API error: {response.status_code} - {response.text}")
                return False

    async def _send_via_mailgun(
        self, to: str, subject: str, html_content: str, text_content: Optional[str]
    ) -> bool:
        """Send email via Mailgun API"""
        if not self.mailgun_api_key or not self.mailgun_domain:
            logger.error("Mailgun API key or domain not configured")
            return False

        url = f"https://api.mailgun.net/v3/{self.mailgun_domain}/messages"
        auth = ("api", self.mailgun_api_key)

        data = {
            "from": f"{self.from_name} <{self.from_email}>",
            "to": to,
            "subject": subject,
            "html": html_content
        }

        if text_content:
            data["text"] = text_content

        async with httpx.AsyncClient() as client:
            response = await client.post(url, auth=auth, data=data, timeout=10.0)

            if response.status_code == 200:
                logger.info(f"Email sent successfully via Mailgun to {to}")
                return True
            else:
                logger.error(f"Mailgun API error: {response.status_code} - {response.text}")
                return False

    async def _send_via_smtp(
        self, to: str, subject: str, html_content: str, text_content: Optional[str]
    ) -> bool:
        """Send email via SMTP"""
        import aiosmtplib
        from email.message import EmailMessage

        if not all([self.smtp_host, self.smtp_username, self.smtp_password]):
            logger.error("SMTP credentials not configured")
            return False

        message = EmailMessage()
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to
        message["Subject"] = subject
        message["Reply-To"] = self.reply_to

        if text_content:
            message.set_content(text_content)
            message.add_alternative(html_content, subtype="html")
        else:
            message.set_content(html_content, subtype="html")

        try:
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_username,
                password=self.smtp_password,
                use_tls=True
            )
            logger.info(f"Email sent successfully via SMTP to {to}")
            return True
        except Exception as e:
            logger.error(f"SMTP send error: {type(e).__name__}: {e}")
            return False

    # ===== TEMPLATE METHODS =====

    async def send_subscription_confirmation(
        self,
        to: str,
        tier: str,
        amount: float,
        period_end: Optional[str] = None
    ) -> bool:
        """Send subscription confirmation email"""
        subject = f"Welcome to Unicorn Commander {tier.title()}!"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">🦄 Unicorn Commander</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Subscription Confirmed!</h2>

                <p style="color: #666; font-size: 16px;">
                    Thank you for subscribing to <strong>{tier.title()}</strong> tier!
                </p>

                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <table style="width: 100%;">
                        <tr>
                            <td style="padding: 10px;"><strong>Tier:</strong></td>
                            <td style="padding: 10px;">{tier.title()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px;"><strong>Amount:</strong></td>
                            <td style="padding: 10px;">${amount:.2f}/month</td>
                        </tr>
                        {f'<tr><td style="padding: 10px;"><strong>Next Billing:</strong></td><td style="padding: 10px;">{period_end}</td></tr>' if period_end else ''}
                    </table>
                </div>

                <p style="color: #666;">
                    You now have access to all {tier} features including:
                </p>
                <ul style="color: #666;">
                    <li>Open-WebUI Chat Interface</li>
                    <li>Center-Deep AI Search</li>
                    <li>50+ AI Models via OpenRouter</li>
                    <li>Bring Your Own Key (BYOK) Support</li>
                    <li>Priority Support</li>
                </ul>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://your-domain.com/dashboard"
                       style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Go to Dashboard
                    </a>
                </div>

                <p style="color: #999; font-size: 14px; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;">
                    Questions? Contact us at <a href="mailto:support@your-domain.com">support@your-domain.com</a>
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(to, subject, html_content)

    async def send_subscription_updated(
        self,
        to: str,
        old_tier: str,
        new_tier: str,
        amount: float
    ) -> bool:
        """Send subscription update email"""
        subject = f"Subscription Updated to {new_tier.title()}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">🦄 Unicorn Commander</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Subscription Updated</h2>

                <p style="color: #666; font-size: 16px;">
                    Your subscription has been updated from <strong>{old_tier.title()}</strong> to <strong>{new_tier.title()}</strong>.
                </p>

                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>New Plan:</strong> {new_tier.title()}</p>
                    <p><strong>New Price:</strong> ${amount:.2f}/month</p>
                </div>

                <p style="color: #666;">
                    Your new features and limits are now active.
                </p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://your-domain.com/dashboard"
                       style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View Dashboard
                    </a>
                </div>
            </div>
        </body>
        </html>
        """

        return await self.send_email(to, subject, html_content)

    async def send_subscription_canceled(
        self,
        to: str,
        tier: str,
        end_date: str
    ) -> bool:
        """Send subscription cancellation email"""
        subject = "Subscription Canceled"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">🦄 Unicorn Commander</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Subscription Canceled</h2>

                <p style="color: #666; font-size: 16px;">
                    We're sorry to see you go! Your <strong>{tier.title()}</strong> subscription has been canceled.
                </p>

                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>Access Until:</strong> {end_date}</p>
                    <p>You'll still have access to your subscription features until this date.</p>
                </div>

                <p style="color: #666;">
                    After this date, your account will be downgraded to the Trial tier with limited features.
                </p>

                <p style="color: #666;">
                    Changed your mind? You can reactivate your subscription anytime from your dashboard.
                </p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://your-domain.com/pricing"
                       style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Reactivate Subscription
                    </a>
                </div>

                <p style="color: #999; font-size: 14px; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;">
                    Need help? Contact us at <a href="mailto:support@your-domain.com">support@your-domain.com</a>
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(to, subject, html_content)

    async def send_payment_failed(
        self,
        to: str,
        amount: float,
        reason: Optional[str] = None
    ) -> bool:
        """Send payment failed email"""
        subject = "Payment Failed - Action Required"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">⚠️ Payment Failed</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Payment Could Not Be Processed</h2>

                <p style="color: #666; font-size: 16px;">
                    We were unable to process your payment of <strong>${amount:.2f}</strong>.
                </p>

                {f'<div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;"><p style="margin: 0; color: #856404;"><strong>Reason:</strong> {reason}</p></div>' if reason else ''}

                <p style="color: #666;">
                    To avoid interruption of your service, please update your payment method or retry the payment.
                </p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://your-domain.com/dashboard/billing"
                       style="background: #dc3545; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Update Payment Method
                    </a>
                </div>

                <p style="color: #999; font-size: 14px; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;">
                    Questions? Contact us at <a href="mailto:support@your-domain.com">support@your-domain.com</a>
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(to, subject, html_content)

    async def send_invoice(
        self,
        to: str,
        invoice_number: str,
        amount: float,
        invoice_url: Optional[str] = None
    ) -> bool:
        """Send invoice email"""
        subject = f"Invoice {invoice_number} - Unicorn Commander"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">🦄 Unicorn Commander</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Payment Receipt</h2>

                <p style="color: #666; font-size: 16px;">
                    Thank you for your payment!
                </p>

                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>Invoice Number:</strong> {invoice_number}</p>
                    <p><strong>Amount Paid:</strong> ${amount:.2f}</p>
                    <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                </div>

                {f'<div style="text-align: center; margin: 30px 0;"><a href="{invoice_url}" style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">View Invoice</a></div>' if invoice_url else ''}

                <p style="color: #999; font-size: 14px; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;">
                    Questions about this invoice? Contact us at <a href="mailto:billing@your-domain.com">billing@your-domain.com</a>
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(to, subject, html_content)

    # ===== TRIAL EMAIL TEMPLATES =====

    async def send_trial_welcome(
        self,
        to: str,
        trial_days: int = 14,
        trial_end_date: Optional[str] = None
    ) -> bool:
        """Send welcome email when trial starts"""
        subject = f"Welcome! Your {trial_days}-Day Trial Starts Now 🚀"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">🦄 Welcome to KubeWorkz!</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Your Free Trial Has Started!</h2>

                <p style="color: #666; font-size: 16px;">
                    Thank you for signing up! You now have <strong>{trial_days} days</strong> of full access to explore all features.
                </p>

                <div style="background: #e7f3ff; padding: 20px; border-left: 4px solid #2196f3; margin: 20px 0;">
                    <p style="margin: 0; color: #1976d2;">
                        <strong>Trial Period:</strong> {trial_days} days<br>
                        {f'<strong>Trial Ends:</strong> {trial_end_date}' if trial_end_date else ''}
                    </p>
                </div>

                <h3 style="color: #333; margin-top: 30px;">What's Included in Your Trial:</h3>
                <ul style="color: #666; line-height: 1.8;">
                    <li>🤖 Access to 50+ AI models via OpenRouter</li>
                    <li>💬 Open-WebUI chat interface</li>
                    <li>🔍 Center-Deep AI-powered search</li>
                    <li>🔑 Bring Your Own API Keys (BYOK)</li>
                    <li>📊 Full dashboard access</li>
                    <li>🎯 All Pro features unlocked</li>
                </ul>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://kubeworkz.io/dashboard"
                       style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Get Started →
                    </a>
                </div>

                <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0; color: #856404;">
                        <strong>💡 Pro Tip:</strong> Connect your own API keys to use your preferred AI models without consuming trial credits!
                    </p>
                </div>

                <p style="color: #666;">
                    Need help getting started? Check out our <a href="https://kubeworkz.io/docs" style="color: #667eea;">documentation</a> or reply to this email.
                </p>

                <p style="color: #999; font-size: 14px; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;">
                    Questions? We're here to help at <a href="mailto:support@kubeworkz.io">support@kubeworkz.io</a>
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to, subject, html_content,
            metadata={"type": "trial_welcome", "trial_days": trial_days}
        )

    async def send_trial_expiring_soon(
        self,
        to: str,
        days_remaining: int,
        trial_end_date: str
    ) -> bool:
        """Send reminder that trial is expiring soon"""
        subject = f"⏰ Your Trial Expires in {days_remaining} Day{'s' if days_remaining != 1 else ''}"

        urgency_color = "#ffc107" if days_remaining > 1 else "#dc3545"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, {urgency_color} 0%, {'#ff9800' if days_remaining > 1 else '#c82333'} 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">⏰ Trial Ending Soon</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Your Trial Expires in {days_remaining} Day{'s' if days_remaining != 1 else ''}!</h2>

                <p style="color: #666; font-size: 16px;">
                    We hope you've been enjoying KubeWorkz! Your free trial will end on <strong>{trial_end_date}</strong>.
                </p>

                <div style="background: #fff3cd; padding: 20px; border-left: 4px solid {urgency_color}; margin: 20px 0;">
                    <p style="margin: 0; color: #856404;">
                        <strong>Trial Ends:</strong> {trial_end_date}<br>
                        <strong>Time Remaining:</strong> {days_remaining} day{'s' if days_remaining != 1 else ''}
                    </p>
                </div>

                <h3 style="color: #333;">Don't Lose Access! Upgrade Now to:</h3>
                <ul style="color: #666; line-height: 1.8;">
                    <li>✅ Keep unlimited access to 50+ AI models</li>
                    <li>✅ Maintain your chat history and saved data</li>
                    <li>✅ Continue using BYOK features</li>
                    <li>✅ Get priority support</li>
                    <li>✅ Access future premium features first</li>
                </ul>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://kubeworkz.io/checkout"
                       style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold; font-size: 16px;">
                        Upgrade to Pro Now →
                    </a>
                </div>

                <div style="text-align: center; margin: 20px 0;">
                    <a href="https://kubeworkz.io/pricing" style="color: #667eea; text-decoration: none;">
                        View Pricing Plans
                    </a>
                </div>

                <p style="color: #999; font-size: 14px; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;">
                    Questions about upgrading? Contact us at <a href="mailto:sales@kubeworkz.io">sales@kubeworkz.io</a>
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to, subject, html_content,
            metadata={"type": "trial_expiring", "days_remaining": days_remaining}
        )

    async def send_trial_expired(
        self,
        to: str,
        trial_end_date: str
    ) -> bool:
        """Send notification that trial has expired"""
        subject = "Your Trial Has Ended - Upgrade to Continue"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Trial Period Ended</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Your Free Trial Has Expired</h2>

                <p style="color: #666; font-size: 16px;">
                    Your 14-day trial ended on <strong>{trial_end_date}</strong>. We hope you enjoyed exploring KubeWorkz!
                </p>

                <div style="background: #f8d7da; padding: 20px; border-left: 4px solid #dc3545; margin: 20px 0;">
                    <p style="margin: 0; color: #721c24;">
                        <strong>Status:</strong> Trial Expired<br>
                        <strong>Access:</strong> Limited to free tier features
                    </p>
                </div>

                <h3 style="color: #333;">Upgrade Now to Restore Full Access:</h3>
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <table style="width: 100%;">
                        <tr>
                            <td style="padding: 10px;">✅ Unlimited AI model access</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px;">✅ Full chat history</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px;">✅ BYOK features</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px;">✅ Priority support</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px;">✅ Advanced analytics</td>
                        </tr>
                    </table>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://kubeworkz.io/checkout"
                       style="background: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold; font-size: 16px;">
                        Upgrade to Pro →
                    </a>
                </div>

                <div style="background: #d1ecf1; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0; color: #0c5460;">
                        <strong>Special Offer:</strong> Upgrade within 7 days and get your first month at 20% off! Use code <strong>COMEBACK20</strong>
                    </p>
                </div>

                <div style="text-align: center; margin: 20px 0;">
                    <a href="https://kubeworkz.io/pricing" style="color: #667eea; text-decoration: none;">
                        View All Plans
                    </a>
                </div>

                <p style="color: #999; font-size: 14px; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;">
                    Have questions? We're here to help at <a href="mailto:sales@kubeworkz.io">sales@kubeworkz.io</a>
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to, subject, html_content,
            metadata={"type": "trial_expired", "expired_on": trial_end_date}
        )

    async def send_trial_extended(
        self,
        to: str,
        additional_days: int,
        new_end_date: str
    ) -> bool:
        """Send notification that trial was extended"""
        subject = f"🎉 Your Trial Has Been Extended by {additional_days} Days!"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">🎉 Trial Extended!</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Great News! Your Trial Has Been Extended</h2>

                <p style="color: #666; font-size: 16px;">
                    We've added <strong>{additional_days} extra days</strong> to your trial period!
                </p>

                <div style="background: #d4edda; padding: 20px; border-left: 4px solid #28a745; margin: 20px 0;">
                    <p style="margin: 0; color: #155724;">
                        <strong>Extension:</strong> +{additional_days} days<br>
                        <strong>New Trial End Date:</strong> {new_end_date}
                    </p>
                </div>

                <p style="color: #666;">
                    Continue exploring all the features KubeWorkz has to offer with your extended trial!
                </p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://kubeworkz.io/dashboard"
                       style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Return to Dashboard →
                    </a>
                </div>

                <p style="color: #999; font-size: 14px; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;">
                    Questions? Contact us at <a href="mailto:support@kubeworkz.io">support@kubeworkz.io</a>
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to, subject, html_content,
            metadata={"type": "trial_extended", "additional_days": additional_days}
        )

    # ===== DUNNING EMAIL TEMPLATES =====

    async def send_payment_retry_reminder(
        self,
        to: str,
        amount: float,
        attempt: int,
        days_until_suspension: int,
        failure_reason: Optional[str] = None
    ) -> bool:
        """Send first payment retry reminder (gentle)"""
        subject = "Payment Failed - Please Update Your Payment Method"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">⚠️ Payment Issue</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">We Couldn't Process Your Payment</h2>

                <p style="color: #666; font-size: 16px;">
                    We attempted to charge your payment method <strong>${amount:.2f}</strong> but the payment was declined.
                </p>

                {f'<div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;"><p style="margin: 0; color: #856404;"><strong>Reason:</strong> {failure_reason}</p></div>' if failure_reason else ''}

                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Amount Due:</strong> ${amount:.2f}</p>
                    <p style="margin: 10px 0 0 0;"><strong>Retry Attempt:</strong> {attempt} of 3</p>
                    <p style="margin: 10px 0 0 0;"><strong>Days Until Suspension:</strong> {days_until_suspension}</p>
                </div>

                <p style="color: #666;">
                    <strong>What happens next?</strong><br>
                    We'll automatically retry the payment in a few days. To avoid service interruption, please update your payment method now.
                </p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://kubeworkz.io/dashboard/billing"
                       style="background: #ffc107; color: #333; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Update Payment Method
                    </a>
                </div>

                <p style="color: #999; font-size: 14px; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;">
                    Questions? Contact us at <a href="mailto:billing@kubeworkz.io">billing@kubeworkz.io</a>
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to, subject, html_content,
            metadata={"type": "dunning_reminder", "attempt": attempt}
        )

    async def send_payment_retry_urgent(
        self,
        to: str,
        amount: float,
        attempt: int,
        days_until_suspension: int
    ) -> bool:
        """Send urgent payment retry notification (2nd attempt)"""
        subject = "⚠️ URGENT: Payment Required - Service at Risk"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">⚠️ URGENT: Action Required</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #e65100;">Your Service Will Be Suspended Soon</h2>

                <p style="color: #666; font-size: 16px;">
                    We've tried {attempt} times to process your payment of <strong>${amount:.2f}</strong> without success.
                </p>

                <div style="background: #ffebee; padding: 20px; border-left: 4px solid #f44336; margin: 20px 0;">
                    <p style="margin: 0; color: #c62828;">
                        <strong>⚠️ CRITICAL:</strong> Your subscription will be suspended in <strong>{days_until_suspension} days</strong> if payment is not received.
                    </p>
                </div>

                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Amount Due:</strong> ${amount:.2f}</p>
                    <p style="margin: 10px 0 0 0;"><strong>Retry Attempt:</strong> {attempt} of 3</p>
                    <p style="margin: 10px 0 0 0; color: #f44336;"><strong>⏰ Service Suspension:</strong> {days_until_suspension} days</p>
                </div>

                <h3 style="color: #333;">To Avoid Suspension:</h3>
                <ol style="color: #666; line-height: 1.8;">
                    <li>Update your payment method immediately</li>
                    <li>Ensure sufficient funds are available</li>
                    <li>Contact your bank if needed</li>
                </ol>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://kubeworkz.io/dashboard/billing"
                       style="background: #f44336; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold; font-size: 16px;">
                        Update Payment Now →
                    </a>
                </div>

                <p style="color: #999; font-size: 14px; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;">
                    Need help? Our billing team is standing by: <a href="mailto:billing@kubeworkz.io">billing@kubeworkz.io</a>
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to, subject, html_content,
            metadata={"type": "dunning_urgent", "attempt": attempt}
        )

    async def send_payment_retry_final(
        self,
        to: str,
        amount: float,
        days_until_suspension: int
    ) -> bool:
        """Send final payment retry notification (last chance)"""
        subject = "🚨 FINAL NOTICE: Payment Required to Avoid Suspension"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #d32f2f 0%, #b71c1c 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">🚨 FINAL NOTICE</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #b71c1c;">Last Chance to Avoid Suspension</h2>

                <p style="color: #666; font-size: 16px;">
                    This is our <strong>final attempt</strong> to collect payment of <strong>${amount:.2f}</strong>.
                </p>

                <div style="background: #ffcdd2; padding: 25px; border: 2px solid #d32f2f; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0; color: #b71c1c; font-size: 18px; font-weight: bold;">
                        🚨 YOUR SERVICE WILL BE SUSPENDED IN {days_until_suspension} DAY{'S' if days_until_suspension != 1 else ''}
                    </p>
                </div>

                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Outstanding Amount:</strong> ${amount:.2f}</p>
                    <p style="margin: 10px 0 0 0;"><strong>Failed Attempts:</strong> 3 of 3</p>
                    <p style="margin: 10px 0 0 0; color: #d32f2f; font-weight: bold;"><strong>⏰ Suspension Date:</strong> {days_until_suspension} days from now</p>
                </div>

                <h3 style="color: #333;">What Happens After Suspension:</h3>
                <ul style="color: #666; line-height: 1.8;">
                    <li>❌ Immediate loss of access to all features</li>
                    <li>❌ Your data will be retained for 30 days only</li>
                    <li>❌ Reactivation requires payment of all outstanding amounts</li>
                    <li>❌ Additional reactivation fees may apply</li>
                </ul>

                <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0; color: #856404;">
                        <strong>💡 Tip:</strong> If you're experiencing financial difficulties, contact us. We may be able to work out a payment plan.
                    </p>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://kubeworkz.io/dashboard/billing"
                       style="background: #d32f2f; color: white; padding: 20px 40px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold; font-size: 18px;">
                        Pay Now to Avoid Suspension →
                    </a>
                </div>

                <p style="color: #999; font-size: 14px; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;">
                    <strong>Urgent billing assistance:</strong> <a href="mailto:billing@kubeworkz.io">billing@kubeworkz.io</a> or call 1-800-XXX-XXXX
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to, subject, html_content,
            metadata={"type": "dunning_final", "attempt": 3}
        )

    async def send_subscription_suspended(
        self,
        to: str,
        amount_due: float
    ) -> bool:
        """Send notification that subscription has been suspended"""
        subject = "Subscription Suspended - Payment Required"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #424242 0%, #212121 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">🔒 Subscription Suspended</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Your Account Has Been Suspended</h2>

                <p style="color: #666; font-size: 16px;">
                    Your subscription has been suspended due to non-payment of <strong>${amount_due:.2f}</strong>.
                </p>

                <div style="background: #e0e0e0; padding: 20px; border-left: 4px solid #424242; margin: 20px 0;">
                    <p style="margin: 0; color: #424242;">
                        <strong>Status:</strong> Suspended<br>
                        <strong>Outstanding Balance:</strong> ${amount_due:.2f}<br>
                        <strong>Access:</strong> Restricted
                    </p>
                </div>

                <h3 style="color: #333;">To Reactivate Your Account:</h3>
                <ol style="color: #666; line-height: 1.8;">
                    <li>Update your payment method</li>
                    <li>Pay the outstanding balance of ${amount_due:.2f}</li>
                    <li>Your access will be restored immediately upon payment</li>
                </ol>

                <div style="background: #ffebee; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0; color: #c62828;">
                        <strong>⚠️ Important:</strong> Your data will be retained for 30 days. After that, it will be permanently deleted.
                    </p>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://kubeworkz.io/dashboard/billing"
                       style="background: #424242; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Reactivate Your Account →
                    </a>
                </div>

                <p style="color: #666;">
                    If you believe this is an error or need assistance, please contact our billing team immediately.
                </p>

                <p style="color: #999; font-size: 14px; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;">
                    Contact billing support: <a href="mailto:billing@kubeworkz.io">billing@kubeworkz.io</a>
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to, subject, html_content,
            metadata={"type": "subscription_suspended", "amount_due": amount_due}
        )

    async def send_organization_invitation(
        self,
        to: str,
        organization_name: str,
        inviter_name: str,
        role: str,
        is_new_user: bool = False,
        reset_password_url: Optional[str] = None
    ) -> bool:
        """
        Send organization invitation email

        Args:
            to: Recipient email address
            organization_name: Name of the organization they're invited to
            inviter_name: Name of person who sent the invitation
            role: Role in the organization (admin, member, etc.)
            is_new_user: Whether this is a new user account
            reset_password_url: URL for password reset (for new users)

        Returns:
            True if sent successfully
        """
        subject = f"You've been invited to join {organization_name}"

        # Determine login URL based on environment
        login_url = os.getenv("APP_URL", "https://kubeworkz.io") + "/auth/login"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">Team Invitation</h1>
            </div>

            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <p style="font-size: 16px;">Hello,</p>

                <p style="font-size: 16px;">
                    <strong>{inviter_name}</strong> has invited you to join <strong>{organization_name}</strong> on Ops Center.
                </p>

                <div style="background: white; border-left: 4px solid #667eea; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; color: #666;">
                        <strong>Your Role:</strong> {role.title()}
                    </p>
                </div>

                {"<p style='font-size: 16px;'>An account has been created for you. When you login for the first time, you'll be prompted to create your password.</p>" if is_new_user else "<p style='font-size: 16px;'>You can now access this organization using your existing account.</p>"}

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_password_url if is_new_user and reset_password_url else login_url}" 
                       style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; 
                              font-weight: bold; font-size: 16px;">
                        {"Get Started" if is_new_user else "Login to Ops Center"}
                    </a>
                </div>

                <p style="color: #666; font-size: 14px;">
                    If you have any questions or didn't expect this invitation, please contact {inviter_name} or our support team.
                </p>

                <p style="color: #999; font-size: 14px; border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;">
                    Need help? Contact us: <a href="mailto:support@kubeworkz.io">support@kubeworkz.io</a>
                </p>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to, subject, html_content,
            metadata={"type": "organization_invitation", "organization": organization_name, "role": role}
        )


# Singleton instance
email_service = EmailService()
