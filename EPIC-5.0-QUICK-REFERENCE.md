# Epic 5.0 Quick Reference Guide

## 🎯 Complete E-commerce Platform - All Phases Done ✅

**What was built**: Full self-service subscription platform with Stripe integration, trial management, and invoice generation.

---

## 📍 Key URLs

### Public Pages (No Login Required)
- **Pricing**: `https://kubeworkz.io/pricing`
- **Signup with Trial**: `https://kubeworkz.io/signup`
- **Checkout**: `https://kubeworkz.io/checkout`

### Authenticated Pages
- **Billing Settings**: `https://kubeworkz.io/settings/billing`
  - Invoice History tab
  - Payment Methods tab (Stripe Portal)

---

## 🔑 API Endpoints

### Public APIs (Unauthenticated)
```bash
# Get all subscription tiers
GET /api/v1/public/tiers

# Get all features
GET /api/v1/public/features

# Sign up with auto trial assignment
POST /api/v1/public/signup/
Body: {"email": "user@example.com", "name": "John Doe"}

# Create Stripe checkout session
POST /api/v1/checkout/create-session
Body: {"email": "...", "tier_code": "starter", "billing_cycle": "monthly"}

# Stripe webhooks (configured in Stripe Dashboard)
POST /api/v1/checkout/webhook
```

### User APIs (Authenticated - Session Cookie Required)
```bash
# Get my subscription
GET /api/v1/my-subscription/

# Upgrade subscription
POST /api/v1/my-subscription/upgrade
Body: {"tier_code": "professional", "billing_cycle": "yearly"}

# Cancel subscription
POST /api/v1/my-subscription/cancel
Body: {"at_period_end": true, "reason": "Too expensive"}

# Get invoice history
GET /api/v1/invoices/

# Download invoice PDF
GET /api/v1/invoices/{id}/download

# Get Stripe Customer Portal URL
GET /api/v1/invoices/stripe/portal-session
```

### Admin APIs (Admin Only)
```bash
# Assign trial to user
POST /api/v1/admin/trials/assign
Body: {"email": "user@example.com", "trial_days": 14}

# Extend trial period
POST /api/v1/admin/trials/extend
Body: {"email": "user@example.com", "additional_days": 7, "reason": "Support request"}

# Get expiring trials
GET /api/v1/admin/trials/expiring?days=7

# Get trial statistics
GET /api/v1/admin/trials/stats
```

---

## 🗄️ Database Tables

### subscription_tiers
```sql
-- Seed data: trial, free, starter, professional, enterprise
SELECT id, code, name, price_monthly, price_yearly FROM subscription_tiers;
```

### user_subscriptions
```sql
-- Email-based subscriptions (no users table dependency)
SELECT email, tier_id, status, billing_cycle, current_period_end FROM user_subscriptions;
```

### invoices
```sql
-- Invoice records from Stripe
SELECT stripe_invoice_id, amount, status, issued_at FROM invoices;
```

---

## 🎬 User Flows

### 1. New User Signup with Trial
```
1. Visit /signup
2. Enter email → Submit
3. Backend assigns 14-day trial (status: trialing)
4. Redirect to dashboard
5. See TrialBanner with countdown
```

### 2. Trial to Paid Conversion
```
1. Click "Upgrade Now" in TrialBanner → /pricing
2. Select tier and billing cycle
3. Click "Get Started" → /checkout
4. Enter email → "Proceed to Payment"
5. Redirect to Stripe Checkout (hosted)
6. Complete payment on Stripe
7. Stripe redirects to /checkout/success
8. Webhook: checkout.session.completed
9. Backend creates subscription (status: active)
10. Trial converted ✅
```

### 3. View Invoices
```
1. Login → Navigate to /settings/billing
2. Click "Invoice History" tab
3. See list of invoices (date, plan, amount, status)
4. Click "Download" → Get PDF invoice
5. Or click "View" → Open Stripe-hosted invoice
```

### 4. Manage Payment Methods
```
1. Login → Navigate to /settings/billing
2. Click "Payment Methods" tab
3. Click "Open Payment Portal"
4. Redirect to Stripe Customer Portal
5. Add/remove cards, update billing address
6. Click "Return to..." → Back to /settings/billing
```

---

## 🔧 Installation & Setup

### 1. Install Dependencies (Optional - for PDF generation)
```bash
docker exec ops-center-direct pip install reportlab
```

### 2. Configure Environment Variables
```bash
# Required
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...  # Get from Stripe Dashboard

# Optional (for PDF invoices)
COMPANY_NAME=Ops Center
COMPANY_ADDRESS=123 Business St, City, State 12345
COMPANY_EMAIL=billing@opscenter.io
COMPANY_TAX_ID=XX-XXXXXXX

# Trial configuration
DEFAULT_TRIAL_DAYS=14
TRIAL_TIER_CODE=trial
FREE_TIER_CODE=free

# App URL (for Stripe redirects)
APP_URL=https://kubeworkz.io
```

### 3. Database Migrations (Already Applied)
```bash
# User subscriptions table
docker exec -i ops-center-postgresql psql -U unicorn -d unicorn_db \
  < scripts/create_user_subscriptions_table.sql

# Invoices table
docker exec -i ops-center-postgresql psql -U unicorn -d unicorn_db \
  < scripts/create_invoices_table.sql
```

### 4. Configure Stripe Webhooks
```
1. Go to: https://dashboard.stripe.com/webhooks
2. Add endpoint: https://kubeworkz.io/api/v1/checkout/webhook
3. Select events:
   - checkout.session.completed
   - customer.subscription.created
   - customer.subscription.updated
   - customer.subscription.deleted
   - invoice.paid
   - invoice.payment_failed
4. Copy webhook signing secret → STRIPE_WEBHOOK_SECRET
```

---

## 🧪 Testing Commands

### Test Public Signup
```bash
curl -X POST http://localhost:8084/api/v1/public/signup/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Expected: Trial assigned for 14 days
```

### Test Stripe Checkout (requires STRIPE_SECRET_KEY)
```bash
curl -X POST http://localhost:8084/api/v1/checkout/create-session \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "tier_code": "starter",
    "billing_cycle": "monthly"
  }'

# Expected: {session_id, checkout_url}
# Redirect user to checkout_url
```

### Check Trial Stats (Admin)
```bash
curl http://localhost:8084/api/v1/admin/trials/stats \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Returns: active_trials, expired_trials, conversions, etc.
```

### Test Invoice Download
```bash
# First, get invoices for logged-in user
curl http://localhost:8084/api/v1/invoices/ \
  -b "session_token=YOUR_SESSION_TOKEN"

# Then download specific invoice
curl http://localhost:8084/api/v1/invoices/1/download \
  -b "session_token=YOUR_SESSION_TOKEN"
```

---

## 📊 Subscription Status Values

| Status | Description |
|--------|-------------|
| `trialing` | Active trial period (14 days default) |
| `active` | Paid subscription, current |
| `expired` | Trial expired, downgraded to free |
| `canceled` | User canceled subscription |
| `past_due` | Payment failed, grace period |

---

## 🎨 Frontend Components

### Public Components
- `Pricing.jsx` - Tier comparison page
- `Signup.jsx` - Signup with auto-trial
- `Checkout.jsx` - Email collection before Stripe
- `CheckoutSuccess.jsx` - Payment success page
- `CheckoutCancelled.jsx` - Payment cancelled page

### Authenticated Components
- `TrialBanner.jsx` - Trial countdown (shown on all pages)
- `BillingSettings.jsx` - Billing management page
- `InvoiceHistory.jsx` - Invoice list table
- `PaymentMethods.jsx` - Stripe Portal button

---

## 🔄 Background Tasks

### Trial Scheduler
```
Runs every hour (3600 seconds)
Tasks:
1. Check for expired trials → Downgrade to free tier
2. Find trials expiring in 7 days → Send warning email
3. Find trials expiring in 3 days → Send warning email
4. Find trials expiring in 1 day → Send warning email
```

Started automatically on app startup in `server.py`:
```python
from trial_scheduler import trial_scheduler
await trial_scheduler.start()
```

---

## 🐛 Debugging

### Check if trial scheduler is running
```bash
docker logs ops-center-direct | grep "Trial"
# Should see: "Trial expiration scheduler started successfully"
```

### Check subscription for specific email
```bash
docker exec ops-center-postgresql psql -U unicorn -d unicorn_db \
  -c "SELECT * FROM user_subscriptions WHERE email='test@example.com';"
```

### Check invoices for subscription
```bash
docker exec ops-center-postgresql psql -U unicorn -d unicorn_db \
  -c "SELECT * FROM invoices WHERE subscription_id=1;"
```

### View Stripe webhook logs
```bash
docker logs ops-center-direct | grep "webhook"
# Check for "Webhook received", "Processing...", errors
```

### Test PDF generation
```python
# In Python shell (docker exec -it ops-center-direct python)
from invoice_manager import invoice_manager

test_data = {
    'invoice_number': 'INV-000001',
    'customer_email': 'test@example.com',
    'tier_name': 'Starter',
    'billing_cycle': 'monthly',
    'amount': 29.00,
    'currency': 'usd',
    'status': 'paid',
    'issued_at': '2026-01-26',
    'stripe_invoice_id': 'in_test_123'
}

pdf = invoice_manager.generate_invoice_pdf(test_data)
# Should return BytesIO object without errors
```

---

## 🚀 Production Checklist

- [ ] Switch Stripe keys from test to live
- [ ] Configure webhook endpoint in Stripe Dashboard
- [ ] Enable webhook signature verification (STRIPE_WEBHOOK_SECRET)
- [ ] Install ReportLab: `pip install reportlab`
- [ ] Set company details (COMPANY_NAME, etc.)
- [ ] Configure email system (SMTP settings)
- [ ] Test complete checkout flow end-to-end
- [ ] Test trial expiration scheduler
- [ ] Test invoice generation and download
- [ ] Test payment portal redirect
- [ ] Set up monitoring for webhook failures
- [ ] Configure rate limiting on signup endpoint
- [ ] Add CAPTCHA to signup form
- [ ] Enable HTTPS for all endpoints

---

## 📈 Metrics to Monitor

1. **Trial Conversion Rate**: `recent_conversions_30d / (active_trials + expired_trials)`
2. **Active Trials**: Count of `status='trialing'`
3. **Expired Trials**: Count of `status='expired'`
4. **MRR (Monthly Recurring Revenue)**: Sum of monthly subscription amounts
5. **Churn Rate**: Canceled subscriptions / Total active subscriptions
6. **Failed Payments**: Count of `status='past_due'`
7. **Invoice Generation**: Success rate of PDF generation

---

## 🆘 Common Issues

### "No subscription found"
- User email mismatch between session and database
- Check: `SELECT * FROM user_subscriptions WHERE email='...'`

### "PDF generation failed"
- ReportLab not installed
- Solution: `docker exec ops-center-direct pip install reportlab`

### "Webhook signature verification failed"
- STRIPE_WEBHOOK_SECRET incorrect or missing
- Get correct secret from Stripe Dashboard → Webhooks

### "Trial not assigned on signup"
- No trial tier in database with `code='trial'`
- Check: `SELECT * FROM subscription_tiers WHERE code='trial'`

### "Payment portal not opening"
- No stripe_customer_id for user
- User must have completed at least one payment

---

## 📚 Documentation Files

- `EPIC-5.0-IMPLEMENTATION-SUMMARY.md` - Complete implementation details
- `EPIC-5.0-QUICK-REFERENCE.md` - This file
- `backend/invoice_manager.py` - Invoice generation code
- `backend/trial_manager.py` - Trial lifecycle code

---

## 🎉 Epic 5.0 Complete!

**5 Phases Implemented**:
1. ✅ Pricing Page & Public APIs
2. ✅ Stripe Checkout Integration
3. ✅ Subscription Management
4. ✅ Trial Management & Conversion
5. ✅ Invoice Generation & Payment Methods

**Stats**:
- ~3,000 lines of code
- 25+ API endpoints
- 6 database tables
- 10+ React components
- Full Stripe integration
- PDF invoice generation
- Trial management system
- Customer Portal integration

**Ready for Production** with:
- Stripe live keys
- ReportLab installation
- Email system configuration
- Webhook endpoint setup

---

Last Updated: January 26, 2026  
Version: Epic 5.0 Complete
