-- ==============================================================================
-- Schema: Admin Users Table for FE Credit AI Calling Platform
-- Paste and run this script in your Supabase SQL Editor:
-- https://supabase.com/dashboard/project/lagejwzhelvqlyqhsvig/sql
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.admin_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) DEFAULT 'FE Credit Staff',
    role VARCHAR(50) DEFAULT 'admin',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for lightning fast login lookup
CREATE INDEX IF NOT EXISTS idx_admin_users_username ON public.admin_users(username);
CREATE INDEX IF NOT EXISTS idx_admin_users_email ON public.admin_users(email);

-- Enable Row Level Security (RLS)
ALTER TABLE public.admin_users ENABLE ROW LEVEL SECURITY;

-- Policy: Allow service role full access and authenticated/anon read for login verification
CREATE POLICY "Allow service role full access" 
ON public.admin_users 
FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);

CREATE POLICY "Allow public read for authentication" 
ON public.admin_users 
FOR SELECT 
TO anon, authenticated 
USING (is_active = true);

-- Insert initial default admin accounts (passwords can be plain or hashed)
INSERT INTO public.admin_users (username, email, password_hash, name, role)
VALUES 
    ('admin', 'admin@fecredit.com', 'admin123', 'Platform Administrator', 'superadmin'),
    ('demo', 'demo@fecredit.com', 'demo123', 'Demo Presenter', 'admin')
ON CONFLICT (username) DO NOTHING;
