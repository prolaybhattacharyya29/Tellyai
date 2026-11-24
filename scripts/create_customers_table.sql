-- Create customers table for FE Credit Demo
-- Unified schema storing common customer identity attributes alongside campaign-specific JSONB data.

CREATE TABLE IF NOT EXISTS public.customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id TEXT NOT NULL,                         -- e.g. XS-10000, EC-10000, WB-10000
    campaign TEXT NOT NULL,                            -- e.g. cross_sell, early_collections, winback
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    age INT,
    gender TEXT,                                       -- 'M', 'F', etc.
    city TEXT,
    occupation TEXT,
    monthly_income_vnd NUMERIC(15, 2),
    preferred_time TEXT,                               -- 'morning', 'afternoon', 'evening'
    preferred_language TEXT DEFAULT 'vietnamese',
    last_contact_date DATE,
    last_contact_outcome TEXT,
    
    -- Campaign-specific financial metrics, product offers & behavioral signals
    campaign_data JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_customer_campaign UNIQUE (customer_id, campaign)
);

-- Fast lookup indexes
CREATE INDEX IF NOT EXISTS idx_customers_campaign ON public.customers(campaign);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON public.customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_customer_id ON public.customers(customer_id);
CREATE INDEX IF NOT EXISTS idx_customers_campaign_data ON public.customers USING GIN (campaign_data);

-- Enable RLS and allow read/write with service role & anon for demo
ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anon read customers"
    ON public.customers FOR SELECT
    USING (true);

CREATE POLICY "Allow anon insert customers"
    ON public.customers FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Allow anon update customers"
    ON public.customers FOR UPDATE
    USING (true);
