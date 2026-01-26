-- Email Logs Table
-- Tracks all emails sent from the system

CREATE TABLE IF NOT EXISTS email_logs (
    id SERIAL PRIMARY KEY,
    to_email VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    html_body TEXT,
    text_body TEXT,
    success BOOLEAN NOT NULL DEFAULT false,
    error_message TEXT,
    metadata JSONB,
    sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_logs_to_email ON email_logs(to_email);
CREATE INDEX IF NOT EXISTS idx_email_logs_sent_at ON email_logs(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_logs_success ON email_logs(success);
CREATE INDEX IF NOT EXISTS idx_email_logs_metadata ON email_logs USING GIN(metadata);

-- Comments
COMMENT ON TABLE email_logs IS 'Audit log of all emails sent from the system';
COMMENT ON COLUMN email_logs.metadata IS 'Additional context: subscription_id, invoice_id, trial_id, etc.';
