# Stripe Integration Setup Guide
**Epic 5.0 - E-commerce & Self-Service Checkout**

## Overview
This guide explains how to set up Stripe payment processing for the self-service subscription checkout flow.

## Prerequisites
1. Stripe account (sign up at https://stripe.com)
2. Access to Stripe Dashboard
3. Ops Center backend running

## Step 1: Get Stripe API Keys

### Test Mode (Development)
1. Log in to [Stripe Dashboard](https://dashboard.stripe.com)
2. Ensure you're in **Test mode** (toggle in top-right)
3. Navigate to **Developers → API keys**
4. Copy the following keys:
   - **Publishable key** (starts with `pk_test_`)
   - **Secret key** (starts with `sk_test_`)

### Live Mode (Production)
1. Complete Stripe account activation
2. Switch to **Live mode** in Stripe Dashboard
3. Navigate to **Developers → API keys**
4. Copy the following keys:
   - **Publishable key** (starts with `pk_live_`)
   - **Secret key** (starts with `sk_live_`)

## Step 2: Create Stripe Products & Prices

For each subscription tier (trial, starter, byok, managed, vip_founder, enterprise):

1. Go to **Products → Add product** in Stripe Dashboard
2. Create product:
   - **Name**: Tier name (e.g., "Starter Plan")
   - **Description**: Tier description
   - **Pricing model**: Recurring
   - **Billing period**: Monthly
   - **Price**: Set monthly price (e.g., $29.00)
   - Click **Save product**
3. Note the **Price ID** (starts with `price_`)
4. Click **Add another price** to create yearly pricing:
   - **Billing period**: Yearly
   - **Price**: Set annual price (e.g., $278.40 for 20% discount)
   - Click **Save**
5. Note the **Yearly Price ID**

### Example Product Structure

```
Trial Tier:
- Product ID: prod_xxx
- Monthly Price ID: price_trial_monthly (Price: $0.00)
- Yearly Price ID: price_trial_yearly (Price: $0.00)

Starter Tier:
- Product ID: prod_yyy
- Monthly Price ID: price_starter_monthly (Price: $29.00)
- Yearly Price ID: price_starter_yearly (Price: $278.40)

... repeat for all tiers
```

## Step 3: Update Database with Stripe Price IDs

Connect to PostgreSQL and update the `subscription_tiers` table:

```sql
-- Update Trial tier
UPDATE subscription_tiers
SET 
    stripe_price_monthly = 'price_trial_monthly_id_here',
    stripe_price_yearly = 'price_trial_yearly_id_here'
WHERE tier_code = 'trial';

-- Update Starter tier
UPDATE subscription_tiers
SET 
    stripe_price_monthly = 'price_starter_monthly_id_here',
    stripe_price_yearly = 'price_starter_yearly_id_here'
WHERE tier_code = 'starter';

-- Repeat for all tiers: byok, managed, vip_founder, enterprise
```

### Quick Database Update Script

```bash
# SSH into server
ssh ubuntu@kubeworkz.io

# Connect to PostgreSQL
docker exec -it ops-center-postgresql psql -U unicorn -d unicorn_db

# Run updates
UPDATE subscription_tiers SET stripe_price_monthly = 'price_xxx', stripe_price_yearly = 'price_yyy' WHERE tier_code = 'trial';
UPDATE subscription_tiers SET stripe_price_monthly = 'price_xxx', stripe_price_yearly = 'price_yyy' WHERE tier_code = 'starter';
UPDATE subscription_tiers SET stripe_price_monthly = 'price_xxx', stripe_price_yearly = 'price_yyy' WHERE tier_code = 'byok';
UPDATE subscription_tiers SET stripe_price_monthly = 'price_xxx', stripe_price_yearly = 'price_yyy' WHERE tier_code = 'managed';
UPDATE subscription_tiers SET stripe_price_monthly = 'price_xxx', stripe_price_yearly = 'price_yyy' WHERE tier_code = 'vip_founder';
UPDATE subscription_tiers SET stripe_price_monthly = 'price_xxx', stripe_price_yearly = 'price_yyy' WHERE tier_code = 'enterprise';
```

## Step 4: Configure Environment Variables

Add Stripe keys to your environment:

### Option A: Using .env file

Create or update `.env` file in project root:

```bash
# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

### Option B: Export to shell (temporary)

```bash
export STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
export STRIPE_SECRET_KEY=sk_test_your_secret_key_here
export STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

### Option C: Update docker-compose.direct.yml directly

Edit the environment section (lines 93-96) with actual values:

```yaml
- STRIPE_PUBLISHABLE_KEY=pk_test_actual_key_here
- STRIPE_SECRET_KEY=sk_test_actual_key_here
- STRIPE_WEBHOOK_SECRET=whsec_actual_secret_here
```

## Step 5: Restart Backend

Apply the new environment variables:

```bash
cd /home/ubuntu/Ops-Center-OSS
docker-compose -f docker-compose.direct.yml restart ops-center-direct
```

## Step 6: Configure Stripe Webhook

To receive real-time payment events:

### For Production (Live Webhook)

1. Go to **Developers → Webhooks** in Stripe Dashboard
2. Click **Add endpoint**
3. **Endpoint URL**: `https://kubeworkz.io/api/v1/checkout/webhook`
4. **Events to send**:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. Click **Add endpoint**
6. Copy the **Signing secret** (starts with `whsec_`)
7. Update `STRIPE_WEBHOOK_SECRET` environment variable
8. Restart backend

### For Development (Stripe CLI)

Install Stripe CLI: https://stripe.com/docs/stripe-cli

```bash
# Login to Stripe
stripe login

# Forward webhooks to local server
stripe listen --forward-to http://localhost:8084/api/v1/checkout/webhook

# Copy the webhook signing secret and set it:
export STRIPE_WEBHOOK_SECRET=whsec_from_cli_output
```

## Step 7: Test the Integration

### Test Checkout Flow

1. Navigate to: `https://kubeworkz.io/pricing`
2. Select a tier and billing cycle
3. Click "Get Started"
4. Enter test email on checkout page
5. Click "Continue to Payment"
6. You should be redirected to Stripe Checkout

### Test with Stripe Test Cards

Use these test card numbers in Stripe Checkout:

**Successful Payment**:
- Card: `4242 4242 4242 4242`
- Expiry: Any future date (e.g., `12/34`)
- CVC: Any 3 digits (e.g., `123`)
- ZIP: Any 5 digits (e.g., `12345`)

**Payment Requires Authentication (3D Secure)**:
- Card: `4000 0025 0000 3155`

**Payment Declined**:
- Card: `4000 0000 0000 0002`

**Insufficient Funds**:
- Card: `4000 0000 0000 9995`

Full list: https://stripe.com/docs/testing#cards

### Verify Webhook Events

Check backend logs for webhook processing:

```bash
docker logs ops-center-direct -f | grep "Checkout completed"
```

## Step 8: Verify Database Integration

After a successful test payment, verify the subscription was created:

```sql
-- Check if customer was created
SELECT * FROM stripe_customers WHERE email = 'test@example.com';

-- Check if subscription was created
SELECT * FROM subscriptions WHERE customer_email = 'test@example.com';
```

## API Endpoints

### Public Checkout API (No Auth Required)

```bash
# Get Stripe config
curl https://kubeworkz.io/api/v1/checkout/config

# Create checkout session
curl -X POST https://kubeworkz.io/api/v1/checkout/create-session \
  -H "Content-Type: application/json" \
  -d '{
    "tier_code": "starter",
    "billing_cycle": "monthly",
    "email": "customer@example.com"
  }'

# Get session status
curl https://kubeworkz.io/api/v1/checkout/session/cs_test_xxx
```

### Public Tiers API

```bash
# Get all tiers
curl https://kubeworkz.io/api/v1/public/tiers

# Get tier features
curl https://kubeworkz.io/api/v1/public/tiers/starter/features
```

## Troubleshooting

### Issue: "Stripe is not configured"
**Solution**: Ensure `STRIPE_SECRET_KEY` and `STRIPE_PUBLISHABLE_KEY` are set and restart backend

### Issue: "Yearly billing not available for [tier]"
**Solution**: Update `stripe_price_yearly` in database for that tier

### Issue: Webhook signature verification failed
**Solution**: 
1. Verify `STRIPE_WEBHOOK_SECRET` matches the secret from Stripe Dashboard
2. Check webhook endpoint URL is correct
3. Ensure webhook is receiving events (check Stripe Dashboard → Webhooks → View logs)

### Issue: Customer sees "Price does not exist"
**Solution**:
1. Verify Price ID exists in Stripe Dashboard
2. Ensure Price ID in database matches exactly
3. Check Price is active (not archived)

## Security Best Practices

1. **Never commit API keys** to Git
2. Use **test mode** for development
3. Use **environment variables** for sensitive data
4. Verify **webhook signatures** in production
5. Use **HTTPS** for webhook endpoints
6. Rotate keys periodically
7. Monitor Stripe Dashboard for suspicious activity
8. Enable **Stripe Radar** for fraud detection

## Going Live Checklist

- [ ] Switch from test keys to live keys
- [ ] Update all Stripe Price IDs in database to live prices
- [ ] Configure production webhook endpoint
- [ ] Test end-to-end flow with live cards (small amount)
- [ ] Enable Stripe Radar fraud protection
- [ ] Set up email notifications for failed payments
- [ ] Configure tax calculation (if applicable)
- [ ] Enable customer portal for subscription management
- [ ] Document refund process
- [ ] Train support team on Stripe Dashboard

## Next Steps

After Stripe integration is complete:

1. **Subscription Management**: Implement upgrade/downgrade flows
2. **Trial Management**: Automate trial expiry and conversion
3. **Invoice Generation**: Email receipts and invoices
4. **Payment Methods**: Allow customers to update cards
5. **Cancellation Flow**: Handle subscription cancellations
6. **Webhook Testing**: Comprehensive webhook event handling
7. **Analytics**: Track conversion rates and revenue

## Support Resources

- [Stripe Documentation](https://stripe.com/docs)
- [Stripe API Reference](https://stripe.com/docs/api)
- [Stripe Testing Guide](https://stripe.com/docs/testing)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks)
- [Stripe Security](https://stripe.com/docs/security)

## Contact

For issues with this integration:
- Check logs: `docker logs ops-center-direct -f`
- Review Stripe Dashboard for errors
- Contact support team
