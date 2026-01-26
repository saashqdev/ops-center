-- Epic 5.0: User Subscriptions Table
-- Run this manually if not using Alembic migrations

-- Note: Using email as primary identifier since we don't have users table yet
-- This table will track subscriptions and create organization/user as needed
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    tier_id INTEGER NOT NULL,
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    billing_cycle VARCHAR(20) NOT NULL DEFAULT 'monthly',
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at TIMESTAMP,
    canceled_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    
    CONSTRAINT uq_user_subscriptions_email UNIQUE (email),
    CONSTRAINT fk_user_subscriptions_tier_id FOREIGN KEY (tier_id) REFERENCES subscription_tiers(id) ON DELETE RESTRICT
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_user_subscriptions_email ON user_subscriptions(email);
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_subscriptions_stripe_subscription_id ON user_subscriptions(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS ix_user_subscriptions_stripe_customer_id ON user_subscriptions(stripe_customer_id);
CREATE INDEX IF NOT EXISTS ix_user_subscriptions_status ON user_subscriptions(status);

-- Add stripe_customer_id to organizations table (assuming this is where users are tracked)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'organizations' AND column_name = 'stripe_customer_id'
    ) THEN
        ALTER TABLE organizations ADD COLUMN stripe_customer_id VARCHAR(255);
        CREATE UNIQUE INDEX ix_organizations_stripe_customer_id ON organizations(stripe_customer_id);
    END IF;
END $$;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON user_subscriptions TO unicorn;
GRANT USAGE, SELECT ON SEQUENCE user_subscriptions_id_seq TO unicorn;

-- Verify table creation
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'user_subscriptions'
ORDER BY ordinal_position;
