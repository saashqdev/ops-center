"""
Invoice Manager for Epic 5.0
Generates and manages PDF invoices for subscriptions
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from io import BytesIO
import os

logger = logging.getLogger(__name__)


class InvoiceManager:
    """Manages invoice generation and storage"""
    
    def __init__(self):
        self.company_name = os.getenv('COMPANY_NAME', 'Ops Center')
        self.company_address = os.getenv('COMPANY_ADDRESS', '123 Business St, City, State 12345')
        self.company_email = os.getenv('COMPANY_EMAIL', 'billing@opscenter.io')
        self.tax_id = os.getenv('COMPANY_TAX_ID', 'XX-XXXXXXX')
    
    async def create_invoice_record(
        self,
        subscription_id: int,
        stripe_invoice_id: str,
        amount: float,
        currency: str = 'usd',
        status: str = 'paid',
        invoice_url: Optional[str] = None,
        invoice_pdf: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an invoice record in the database
        
        Args:
            subscription_id: User subscription ID
            stripe_invoice_id: Stripe invoice ID
            amount: Invoice amount
            currency: Currency code
            status: Invoice status (paid, pending, failed)
            invoice_url: Stripe-hosted invoice URL
            invoice_pdf: Stripe PDF download URL
            
        Returns:
            Dict with invoice details
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchrow("""
                    INSERT INTO invoices (
                        subscription_id,
                        stripe_invoice_id,
                        amount,
                        currency,
                        status,
                        invoice_url,
                        invoice_pdf,
                        issued_at,
                        created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (stripe_invoice_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        invoice_url = EXCLUDED.invoice_url,
                        invoice_pdf = EXCLUDED.invoice_pdf,
                        updated_at = NOW()
                    RETURNING id
                """, subscription_id, stripe_invoice_id, amount, currency,
                    status, invoice_url, invoice_pdf, datetime.utcnow(), datetime.utcnow())
                
                logger.info(f"Created invoice record {result['id']} for subscription {subscription_id}")
                
                return {
                    "invoice_id": result['id'],
                    "stripe_invoice_id": stripe_invoice_id,
                    "amount": amount,
                    "currency": currency,
                    "status": status
                }
                
        except Exception as e:
            logger.error(f"Error creating invoice record: {e}", exc_info=True)
            raise
    
    async def get_invoices_by_email(
        self,
        email: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all invoices for a user
        
        Args:
            email: User email
            limit: Maximum number of invoices to return
            
        Returns:
            List of invoice records
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                invoices = await conn.fetch("""
                    SELECT 
                        i.*,
                        s.email,
                        t.name as tier_name,
                        t.code as tier_code
                    FROM invoices i
                    JOIN user_subscriptions s ON i.subscription_id = s.id
                    JOIN subscription_tiers t ON s.tier_id = t.id
                    WHERE s.email = $1
                    ORDER BY i.issued_at DESC
                    LIMIT $2
                """, email, limit)
                
                return [dict(inv) for inv in invoices]
                
        except Exception as e:
            logger.error(f"Error getting invoices: {e}", exc_info=True)
            return []
    
    async def get_invoice_by_id(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific invoice by ID"""
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                invoice = await conn.fetchrow("""
                    SELECT 
                        i.*,
                        s.email,
                        s.billing_cycle,
                        t.name as tier_name,
                        t.code as tier_code
                    FROM invoices i
                    JOIN user_subscriptions s ON i.subscription_id = s.id
                    JOIN subscription_tiers t ON s.tier_id = t.id
                    WHERE i.id = $1
                """, invoice_id)
                
                if invoice:
                    return dict(invoice)
                return None
                
        except Exception as e:
            logger.error(f"Error getting invoice: {e}", exc_info=True)
            return None
    
    def generate_invoice_pdf(
        self,
        invoice_data: Dict[str, Any]
    ) -> BytesIO:
        """
        Generate a PDF invoice
        
        Args:
            invoice_data: Invoice details including customer info, line items, etc.
            
        Returns:
            BytesIO containing PDF data
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib import colors
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Company header
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1e40af')
            )
            story.append(Paragraph(self.company_name, header_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Company details
            company_info = f"""
            <font size=10>
            {self.company_address}<br/>
            Email: {self.company_email}<br/>
            Tax ID: {self.tax_id}
            </font>
            """
            story.append(Paragraph(company_info, styles['Normal']))
            story.append(Spacer(1, 0.5*inch))
            
            # Invoice title
            invoice_title = f"<font size=18><b>INVOICE #{invoice_data.get('invoice_number', 'N/A')}</b></font>"
            story.append(Paragraph(invoice_title, styles['Heading2']))
            story.append(Spacer(1, 0.3*inch))
            
            # Customer and invoice details
            details_data = [
                ['Bill To:', 'Invoice Details:'],
                [invoice_data.get('customer_email', 'N/A'), f"Invoice Date: {invoice_data.get('issued_at', 'N/A')}"],
                ['', f"Status: {invoice_data.get('status', 'N/A').upper()}"],
                ['', f"Stripe Invoice: {invoice_data.get('stripe_invoice_id', 'N/A')}"]
            ]
            
            details_table = Table(details_data, colWidths=[3*inch, 3*inch])
            details_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(details_table)
            story.append(Spacer(1, 0.5*inch))
            
            # Line items
            line_items_data = [
                ['Description', 'Billing Cycle', 'Amount']
            ]
            
            tier_name = invoice_data.get('tier_name', 'Subscription')
            billing_cycle = invoice_data.get('billing_cycle', 'monthly')
            amount = invoice_data.get('amount', 0)
            currency = invoice_data.get('currency', 'usd').upper()
            
            line_items_data.append([
                f"{tier_name} Plan",
                billing_cycle.capitalize(),
                f"${amount:.2f} {currency}"
            ])
            
            items_table = Table(line_items_data, colWidths=[3*inch, 2*inch, 1.5*inch])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ]))
            story.append(items_table)
            story.append(Spacer(1, 0.5*inch))
            
            # Total
            total_data = [
                ['', 'Total:', f"${amount:.2f} {currency}"]
            ]
            total_table = Table(total_data, colWidths=[3*inch, 2*inch, 1.5*inch])
            total_table.setStyle(TableStyle([
                ('FONTNAME', (1, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (1, 0), (-1, 0), 14),
                ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
                ('LINEABOVE', (1, 0), (-1, 0), 2, colors.black),
            ]))
            story.append(total_table)
            story.append(Spacer(1, 1*inch))
            
            # Footer
            footer_text = """
            <font size=9>
            <b>Payment Method:</b> Credit Card (via Stripe)<br/>
            <b>Thank you for your business!</b><br/>
            For questions about this invoice, contact {email}
            </font>
            """.format(email=self.company_email)
            story.append(Paragraph(footer_text, styles['Normal']))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            
            logger.info(f"Generated PDF invoice for {invoice_data.get('customer_email')}")
            return buffer
            
        except ImportError:
            logger.error("reportlab not installed. Install with: pip install reportlab")
            raise Exception("PDF generation not available. Install reportlab package.")
        except Exception as e:
            logger.error(f"Error generating PDF: {e}", exc_info=True)
            raise
    
    async def process_stripe_invoice(
        self,
        stripe_invoice: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Process a Stripe invoice webhook event
        
        Args:
            stripe_invoice: Stripe invoice object
            
        Returns:
            Created invoice record or None
        """
        try:
            from database import get_db_pool
            
            stripe_invoice_id = stripe_invoice.get('id')
            stripe_subscription_id = stripe_invoice.get('subscription')
            amount = stripe_invoice.get('amount_paid', 0) / 100  # Convert cents to dollars
            currency = stripe_invoice.get('currency', 'usd')
            status = stripe_invoice.get('status', 'open')
            invoice_url = stripe_invoice.get('hosted_invoice_url')
            invoice_pdf = stripe_invoice.get('invoice_pdf')
            
            # Map Stripe status to our status
            status_map = {
                'paid': 'paid',
                'open': 'pending',
                'void': 'cancelled',
                'uncollectible': 'failed'
            }
            our_status = status_map.get(status, 'pending')
            
            # Get subscription ID from our database
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                subscription = await conn.fetchrow("""
                    SELECT id FROM user_subscriptions
                    WHERE stripe_subscription_id = $1
                """, stripe_subscription_id)
                
                if not subscription:
                    logger.warning(f"Subscription not found for Stripe invoice {stripe_invoice_id}")
                    return None
                
                # Create invoice record
                result = await self.create_invoice_record(
                    subscription_id=subscription['id'],
                    stripe_invoice_id=stripe_invoice_id,
                    amount=amount,
                    currency=currency,
                    status=our_status,
                    invoice_url=invoice_url,
                    invoice_pdf=invoice_pdf
                )
                
                # Send invoice email to customer
                if our_status == 'paid':
                    subscription_data = await conn.fetchrow("""
                        SELECT email FROM user_subscriptions WHERE id = $1
                    """, subscription['id'])
                    
                    if subscription_data:
                        await self._send_invoice_email(
                            email=subscription_data['email'],
                            invoice_id=result['id'],
                            amount=amount,
                            invoice_url=invoice_url
                        )
                
                return result
                
        except Exception as e:
            logger.error(f"Error processing Stripe invoice: {e}", exc_info=True)
            return None
    
    async def _send_invoice_email(
        self,
        email: str,
        invoice_id: int,
        amount: float,
        invoice_url: Optional[str] = None
    ):
        """Send invoice receipt email to customer"""
        try:
            from email_service import email_service
            
            await email_service.send_invoice(
                to=email,
                invoice_number=f"INV-{invoice_id:06d}",
                amount=amount,
                invoice_url=invoice_url
            )
            logger.info(f"Sent invoice email to {email} for invoice {invoice_id}")
        except Exception as e:
            logger.error(f"Error sending invoice email: {e}")


# Global singleton
invoice_manager = InvoiceManager()
