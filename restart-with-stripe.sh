#!/bin/bash
# Restart Ops Center with Stripe environment variables
# This ensures Stripe keys are loaded from .env.auth

cd /home/ubuntu/Ops-Center-OSS

# Export Stripe keys from .env.auth
export STRIPE_SECRET_KEY=sk_test_51NVgMbHbRbwEK4CvvPQhOxXLXWthrQzZZaCKU6vQ3pvo7PKejJx8owS3m2srqr94cPXBcjTBiNOSDbRPsibamsz700vpTuzoZj
export STRIPE_PUBLISHABLE_KEY=pk_test_51NVgMbHbRbwEK4CvxTLkdblMg6gf2Wbl9HCyWGFJffvVa9LqplCZhlcVhdrplXOGLOTP2RKMjygIgIOcgE3oidtE00la53ujfL
export STRIPE_WEBHOOK_SECRET=whsec_test
export LAGO_API_KEY=d66b4d50-3a84-4e09-ac16-97b147d1d6ce

# Restart ops-center container
docker-compose -f docker-compose.traefik-integrated.yml up -d ops-center

echo "✅ Ops Center restarted with Stripe configuration"
echo "Stripe Secret Key: ${STRIPE_SECRET_KEY:0:20}..."
