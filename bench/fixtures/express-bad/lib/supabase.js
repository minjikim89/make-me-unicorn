const { createClient } = require('@supabase/supabase-js'); module.exports = createClient('https://x.supabase.co', '{{SECRET:supabase_service_role}}');
