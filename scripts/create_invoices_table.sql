-- Epic 5.0 Phase 5: Invoices Table
-- Stores invoice records for subscriptions

CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER NOT NULL,
    stripe_invoice_id VARCHAR(255) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'usd',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    invoice_url TEXT,
    invoice_pdf TEXT,
    issued_at TIMESTAMP NOT NULL,
    due_date TIMESTAMP,
    paid_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP,
    
    CONSTRAINT fk_invoices_subscription_id FOREIGN KEY (subscription_id) 
        REFERENCES user_subscriptions(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_invoices_subscription_id ON invoices(subscription_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_invoices_stripe_invoice_id ON invoices(stripe_invoice_id);
CREATE INDEX IF NOT EXISTS ix_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS ix_invoices_issued_at ON invoices(issued_at DESC);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON invoices TO unicorn;
GRANT USAGE, SELECT ON SEQUENCE invoices_id_seq TO unicorn;

-- Verify table creation
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'invoices'
ORDER BY ordinal_position;
