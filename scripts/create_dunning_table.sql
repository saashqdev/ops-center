-- Payment Dunning Table
-- Tracks payment retry attempts and dunning campaigns

CREATE TABLE IF NOT EXISTS payment_dunning (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER NOT NULL REFERENCES user_subscriptions(id) ON DELETE CASCADE,
    stripe_invoice_id VARCHAR(255),
    
    -- Dunning state
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, resolved, failed, cancelled
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    
    -- Important dates
    first_failure_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_retry_at TIMESTAMP,
    next_retry_at TIMESTAMP,
    grace_period_ends_at TIMESTAMP,
    resolved_at TIMESTAMP,
    
    -- Payment details
    amount_due DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'usd',
    failure_reason TEXT,
    
    -- Metadata
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_dunning_subscription ON payment_dunning(subscription_id);
CREATE INDEX IF NOT EXISTS idx_dunning_status ON payment_dunning(status);
CREATE INDEX IF NOT EXISTS idx_dunning_next_retry ON payment_dunning(next_retry_at) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_dunning_stripe_invoice ON payment_dunning(stripe_invoice_id);
CREATE INDEX IF NOT EXISTS idx_dunning_grace_period ON payment_dunning(grace_period_ends_at) WHERE status = 'active';

-- Comments
COMMENT ON TABLE payment_dunning IS 'Tracks payment retry attempts and dunning campaigns for failed payments';
COMMENT ON COLUMN payment_dunning.status IS 'active: retrying, resolved: payment succeeded, failed: max retries exhausted, cancelled: user cancelled subscription';
COMMENT ON COLUMN payment_dunning.retry_count IS 'Number of retry attempts made';
COMMENT ON COLUMN payment_dunning.grace_period_ends_at IS 'When to suspend subscription if payment still failed';
COMMENT ON COLUMN payment_dunning.metadata IS 'Additional context: email_sent_count, last_email_type, etc.';
