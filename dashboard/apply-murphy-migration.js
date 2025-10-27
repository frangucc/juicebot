#!/usr/bin/env node

/**
 * Apply Murphy Test Schema V2 Migration
 * =====================================
 * Executes SQL migration using Node.js and Supabase client
 */

const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

async function main() {
  console.log('='.repeat(60));
  console.log('Murphy Test Schema V2 Migration');
  console.log('='.repeat(60));
  console.log();

  // Get Supabase credentials
  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !supabaseKey) {
    console.error('❌ Error: SUPABASE_URL and SUPABASE_KEY required in .env');
    process.exit(1);
  }

  console.log('✓ Found Supabase credentials');
  console.log(`  URL: ${supabaseUrl.substring(0, 30)}...`);
  console.log();

  // Read SQL file
  const sqlPath = path.join(__dirname, '..', 'database', 'murphy_test_schema_v2.sql');

  if (!fs.existsSync(sqlPath)) {
    console.error(`❌ Error: SQL file not found: ${sqlPath}`);
    process.exit(1);
  }

  console.log('📖 Reading SQL migration file...');
  const sql = fs.readFileSync(sqlPath, 'utf8');
  console.log(`✓ Read ${sql.length} characters`);
  console.log();

  // Create Supabase client
  console.log('🔌 Connecting to Supabase...');
  const supabase = createClient(supabaseUrl, supabaseKey);
  console.log('✓ Connected');
  console.log();

  // Supabase JS client doesn't support raw SQL execution
  // We need to use RPC or direct PostgreSQL connection
  console.log('🚀 Executing SQL migration...');
  console.log();

  try {
    // Try using Supabase RPC to execute SQL
    // This requires a database function or direct connection

    // Split SQL into individual statements
    const statements = sql
      .split(';')
      .map(s => s.trim())
      .filter(s => s.length > 0 && !s.startsWith('--'));

    console.log(`📝 Found ${statements.length} SQL statements`);
    console.log();

    // Supabase JS doesn't support raw SQL, we need to use PostgreSQL client
    console.log('⚠️  Supabase JS client cannot execute raw SQL');
    console.log();
    console.log('Installing pg (PostgreSQL client)...');

    // Try to require pg, if not available, instruct user
    let pg;
    try {
      pg = require('pg');
    } catch (err) {
      console.log();
      console.log('📦 pg module not found. Installing...');
      const { execSync } = require('child_process');
      try {
        execSync('npm install --no-save pg', { cwd: path.join(__dirname, '..'), stdio: 'inherit' });
        pg = require('pg');
        console.log('✓ pg installed successfully');
      } catch (installErr) {
        console.error();
        console.error('❌ Failed to install pg module');
        console.error();
        console.error('Manual migration required:');
        console.error('1. Go to Supabase Dashboard → SQL Editor');
        console.error('2. Create new query');
        console.error('3. Copy contents of: database/murphy_test_schema_v2.sql');
        console.error('4. Run query');
        process.exit(1);
      }
    }

    // Get PostgreSQL connection string
    const dbUrl = process.env.DATABASE_URL;
    if (!dbUrl) {
      console.error('❌ DATABASE_URL not found in .env');
      console.error();
      console.error('Add this to your .env file:');
      console.error('DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres');
      console.error();
      console.error('Find it in: Supabase Dashboard → Project Settings → Database');
      console.error();
      console.error('OR run migration manually:');
      console.error('1. Go to Supabase Dashboard → SQL Editor');
      console.error('2. Copy contents of: database/murphy_test_schema_v2.sql');
      console.error('3. Run query');
      process.exit(1);
    }

    // Connect to PostgreSQL
    const { Client } = pg;
    const client = new Client({ connectionString: dbUrl });

    console.log('🔌 Connecting to PostgreSQL...');
    await client.connect();
    console.log('✓ Connected');
    console.log();

    console.log('📝 Executing SQL...');
    await client.query(sql);
    console.log('✓ Migration completed successfully!');
    console.log();

    await client.end();

    console.log('✅ Database tables created:');
    console.log('  ✓ murphy_test_sessions');
    console.log('  ✓ murphy_signal_records');
    console.log('  ✓ murphy_session_stats (view)');
    console.log();
    console.log('🎉 Murphy Test Lab is ready to use!');
    console.log();
    console.log('Next steps:');
    console.log('  1. Restart services: npm stop && npm start');
    console.log('  2. Type "murphy live" in chat');
    console.log('  3. Click flask icon to see Test Lab');
    console.log();

  } catch (error) {
    console.error('❌ Migration failed:', error.message);
    console.error();
    console.error('Manual migration fallback:');
    console.error('1. Go to Supabase Dashboard → SQL Editor');
    console.error('2. Create new query');
    console.error('3. Copy contents of: database/murphy_test_schema_v2.sql');
    console.error('4. Run query');
    process.exit(1);
  }
}

main().catch(err => {
  console.error('Unexpected error:', err);
  process.exit(1);
});
