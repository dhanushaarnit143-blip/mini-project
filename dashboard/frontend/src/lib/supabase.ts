import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://trtvdmgswouirfaqyrdk.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRydHZkbWdzd291aXJmYXF5cmRrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxNjM3OTAsImV4cCI6MjEwNTczOTc5MH0.wxyGhyELZJy_-R2X4xqDaIsgofDbdQJtwZWjboCOKrM';

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
