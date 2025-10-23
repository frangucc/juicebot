# Next Steps to Get Running

## You're SO Close! Just 2 Quick Steps:

### Step 1: Run Database Migration (1 minute)

1. **Open Supabase:**
   ```
   https://szuvtcbytepaflthqnal.supabase.co
   ```

2. **Click "SQL Editor"** in the left sidebar

3. **Open the file:** `sql/001_init_schema.sql` on your computer

4. **Copy ALL contents** (~200 lines)

5. **Paste into SQL Editor** and click "Run" (or Cmd+Enter)

6. **Verify:** You should see "Success. No rows returned"

7. **Check:** Click "Table Editor" → Should see 6 new tables:
   - ✅ screener_alerts
   - ✅ users
   - ✅ trades
   - ✅ sms_messages
   - ✅ market_data_cache
   - ✅ screener_performance

**That's it for the database!**

---

### Step 2: Check Databento Connection

Your screener loaded 11,895 symbols successfully but hit a connection limit!

**Option 1: Check Your Portal**
1. Go to https://databento.com/portal
2. Look for "Active Connections" or "Session Management"
3. Close any old/unused connections
4. You may have an old browser tab or terminal still connected

**Option 2: Contact Databento** (if Option 1 doesn't work)
- Email: support@databento.com
- Tell them: "I'm getting 'User has reached their open connection limit' error"
- They can reset it quickly

**Option 3: Test Without Live Data** (works right now!)
- Just test the dashboard and API
- The screener loaded historical data successfully
- You can see the system working without live feed

---

### Step 3: Create Dashboard Config (30 seconds)

```bash
cd /Users/franckjones/Desktop/trade_app/dashboard

cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://szuvtcbytepaflthqnal.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN6dXZ0Y2J5dGVwYWZsdGhxbmFsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjExNTYzMDgsImV4cCI6MjA3NjczMjMwOH0.bmSCzvk3iyKQlixYp-r-AoNkXA8UGOI5fH6RfGLGXME
EOF

cd ..
```

---

### Step 4: Restart Everything

```bash
npm start
```

Then open: http://localhost:3000

---

## What You'll See:

### ✅ Working Now:
- API server running on port 8000
- Dashboard running on port 3000
- Screener loading 11,895 symbols
- Database tables created

### ⚠️ After Databento Fix:
- Live alerts streaming in
- Dashboard showing real-time data
- Everything working perfectly!

---

## Quick Test (Before Fixing Databento)

Even without live data, you can test:

```bash
# Test API
curl http://localhost:8000/health

# Should show: "status": "healthy", "database": "connected"
```

Open dashboard → Should show empty alerts (that's normal without live data)

---

## Timeline:

- **Step 1 (Database):** 1 minute ✅
- **Step 2 (Databento):** 5-10 minutes ⏳
- **Step 3 (Dashboard config):** 30 seconds ✅
- **Step 4 (Restart):** 10 seconds ✅

**Total time to fully working:** ~15 minutes max!

---

## After It's Working:

Read these for next steps:
- `WHAT_JUST_HAPPENED.md` - What worked, what needs fixing
- `API_KEYS_GUIDE.md` - Complete API key guide
- `COMMANDS.md` - All available commands

---

**Let's do this! Start with Step 1 (database migration).** 🚀

Once you run that SQL file in Supabase, come back and we'll tackle the Databento connection issue together.
