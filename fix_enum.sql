-- Fix PaymentRequestStatus enum type
-- This script fixes the enum type created with uppercase values

BEGIN;

-- Drop the existing table
DROP TABLE IF EXISTS payment_requests CASCADE;

-- Drop the existing enum type
DROP TYPE IF EXISTS paymentrequeststatus;

-- Create enum with correct lowercase values
CREATE TYPE paymentrequeststatus AS ENUM (
    'pending',
    'scheduled_today',
    'scheduled_date',
    'paid',
    'cancelled'
);

-- Recreate the payment_requests table
CREATE TABLE payment_requests (
    id SERIAL PRIMARY KEY,
    created_by_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR NOT NULL,
    amount VARCHAR NOT NULL,
    comment VARCHAR NOT NULL,
    invoice_file_id VARCHAR,
    status paymentrequeststatus NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    processing_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    paid_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    paid_at TIMESTAMP,
    scheduled_date DATE,
    payment_proof_file_id VARCHAR,
    worker_message_id BIGINT,
    billing_message_id BIGINT
);

-- Create indexes
CREATE INDEX ix_payment_requests_created_by_id ON payment_requests(created_by_id);
CREATE INDEX ix_payment_requests_status ON payment_requests(status);

COMMIT;
