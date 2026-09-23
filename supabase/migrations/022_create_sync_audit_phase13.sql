-- Migration 022: Create sync_audit_log for Phase 13
-- Phase 13: Supabase Synchronization and Offline-First Behavior
--
-- Tracks mobile-to-cloud synchronization events, retry attempts,
-- idempotency enforcement, and conflict resolution ("server wins").

CREATE TABLE IF NOT EXISTS public.sync_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID REFERENCES public.participants(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    table_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'syncing', 'synced', 'conflict_resolved', 'failed')),
    conflict_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolution_strategy TEXT DEFAULT 'server_wins',
    retry_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    client_timestamp TIMESTAMPTZ NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_sync_audit_idempotency ON public.sync_audit_log(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_sync_audit_session ON public.sync_audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_sync_audit_participant ON public.sync_audit_log(participant_id);
CREATE INDEX IF NOT EXISTS idx_sync_audit_status ON public.sync_audit_log(status);

-- Enable Row Level Security
ALTER TABLE public.sync_audit_log ENABLE ROW LEVEL SECURITY;

-- Allow insert and select policies for research synchronization
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'sync_audit_log' AND policyname = 'sync_audit_insert_policy'
    ) THEN
        CREATE POLICY "sync_audit_insert_policy" ON public.sync_audit_log
            FOR INSERT WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'sync_audit_log' AND policyname = 'sync_audit_select_policy'
    ) THEN
        CREATE POLICY "sync_audit_select_policy" ON public.sync_audit_log
            FOR SELECT USING (true);
    END IF;
END $$;

COMMENT ON TABLE public.sync_audit_log IS 'Audit trail for mobile offline-first synchronization events and conflict resolutions (Phase 13).';
COMMENT ON COLUMN public.sync_audit_log.idempotency_key IS 'Unique deterministic key preventing duplicate uploads during retries.';
COMMENT ON COLUMN public.sync_audit_log.resolution_strategy IS 'Conflict resolution policy (default: server_wins).';
