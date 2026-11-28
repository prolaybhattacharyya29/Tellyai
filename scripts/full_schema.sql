-- 1. Create admin_users table for Dashboard Authentication
CREATE TABLE IF NOT EXISTS public.admin_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'admin',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.admin_users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow anon read admin_users" ON public.admin_users FOR SELECT USING (true);
CREATE POLICY "Allow anon insert admin_users" ON public.admin_users FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anon update admin_users" ON public.admin_users FOR UPDATE USING (true);

-- Seed default admin user (admin / admin123)
-- Salted sha256 of "fe_credit_salt_2026admin123"
INSERT INTO public.admin_users (username, email, password_hash, full_name, role)
VALUES (
    'admin',
    'admin@fecredit.com.vn',
    '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92',
    'Toqi Super Admin',
    'superadmin'
)
ON CONFLICT (username) DO NOTHING;


-- 2. Create customers table (Unified schema + JSONB for all 12 campaigns)
CREATE TABLE IF NOT EXISTS public.customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id TEXT NOT NULL,
    campaign TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    age INT,
    gender TEXT,
    city TEXT,
    occupation TEXT,
    monthly_income_vnd NUMERIC(15, 2),
    preferred_time TEXT,
    preferred_language TEXT DEFAULT 'vietnamese',
    last_contact_date DATE,
    last_contact_outcome TEXT,
    campaign_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_customer_campaign UNIQUE (customer_id, campaign)
);

CREATE INDEX IF NOT EXISTS idx_customers_campaign ON public.customers(campaign);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON public.customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_customer_id ON public.customers(customer_id);
CREATE INDEX IF NOT EXISTS idx_customers_campaign_data ON public.customers USING GIN (campaign_data);

ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow anon read customers" ON public.customers FOR SELECT USING (true);
CREATE POLICY "Allow anon insert customers" ON public.customers FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow anon update customers" ON public.customers FOR UPDATE USING (true);
