# First Run Guide

Follow these steps **exactly** for your first time running the app.

## Step 1: Setup (2 minutes)

```bash
cd /Users/franckjones/Desktop/trade_app
npm run setup
```

This will:
- Create Python virtual environment
- Install all Python dependencies (~2 minutes)
- Install dashboard dependencies (~1 minute)

**Wait for it to complete!** You should see:
```
✓ Python setup complete
✓ Dashboard setup complete
```

## Step 2: Database Migration (1 minute)

You need to run this **once** to create all the database tables.

1. Open your browser and go to:
   **https://szuvtcbytepaflthqnal.supabase.co**

2. Click on "SQL Editor" in the left sidebar

3. Open the file: `sql/001_init_schema.sql` in your text editor

4. Copy the **entire contents** (all ~200 lines)

5. Paste into the Supabase SQL Editor

6. Click "Run" (or press Cmd+Enter)

7. You should see: **"Success. No rows returned"**

8. Click "Table Editor" in left sidebar - you should see 6 new tables:
   - ✅ screener_alerts
   - ✅ users
   - ✅ trades
   - ✅ sms_messages
   - ✅ market_data_cache
   - ✅ screener_performance

## Step 3: Create Dashboard Environment File (30 seconds)

```bash
cd dashboard
cp .env.local.example .env.local
```

Now edit `.env.local` with these values:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://szuvtcbytepaflthqnal.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN6dXZ0Y2J5dGVwYWZsdGhxbmFsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjExNTYzMDgsImV4cCI6MjA3NjczMjMwOH0.bmSCzvk3iyKQlixYp-r-AoNkXA8UGOI5fH6RfGLGXME
```

Save and close the file.

```bash
cd ..
```

## Step 4: Start Everything (10 seconds)

```bash
npm start
```

You should see:
```
🚀 Starting Trading SMS Assistant...

Starting api...
✓ api started (PID: 12345)

Starting screener...
✓ screener started (PID: 12346)

Starting dashboard...
✓ dashboard started (PID: 12347)

✅ All services started!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Dashboard:  http://localhost:3000
🔧 API:        http://localhost:8000
📖 API Docs:   http://localhost:8000/docs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The terminal will then show **live logs** from all services scrolling by.

## Step 5: Open Dashboard (5 seconds)

Open your browser and go to:
**http://localhost:3000**

You should see:
- ✅ "Trading Assistant Dashboard" header
- ✅ Three stats cards (may show 0s initially)
- ✅ "Recent Alerts" table (may be empty initially)

**Note:** If running outside market hours (before 4am ET or after 8pm ET), you may not see alerts immediately.

## Step 6: Test It's Working (30 seconds)

### Test 1: API Health
Open a new terminal and run:
```bash
curl http://localhost:8000/health
```

You should see:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-22T...",
  "database": "connected"
}
```

### Test 2: Check Alerts
```bash
curl http://localhost:8000/alerts
```

Should return a JSON array (may be empty `[]` if no alerts yet).

### Test 3: Check Status
In a new terminal:
```bash
npm run status
```

Should show:
```
API:            ✓ Running (PID: 12345)
Screener:       ✓ Running (PID: 12346)
Dashboard:      ✓ Running (PID: 12347)

✅ All services running!
```

## Step 7: See Alerts (During Market Hours)

If it's **between 4:00 AM - 8:00 PM ET on a weekday**, you should start seeing alerts within 1-2 minutes:

In your terminal (where npm start is running), you'll see:
```
[2025-01-22 09:31:23] AAPL moved by 3.2% (current: 150.25, previous: 145.00)
    ✓ Alert stored in database (ID: abc123...)
```

The dashboard will automatically update within 10 seconds!

### If Outside Market Hours

Run a test with replay mode:

```bash
# Stop current services
npm stop

# Run test mode
npm test
```

You should see historical alerts replaying.

## Step 8: Stop Everything

When you're done:

```bash
npm stop
```

You should see:
```
🛑 Stopping Trading SMS Assistant...

Stopping dashboard (PID: 12347)...
✓ dashboard stopped

Stopping api (PID: 12345)...
✓ api stopped

Stopping screener (PID: 12346)...
✓ screener stopped

✅ All services stopped!
```

## Troubleshooting

### "npm: command not found"
You need Node.js installed. Install from: https://nodejs.org

### "python3: command not found"
You need Python 3.9+. Install from: https://python.org

### "Database connection failed"
Check your `.env` file has the correct Supabase credentials.

### "Port 3000 already in use"
Something else is using port 3000. Stop it:
```bash
lsof -ti:3000 | xargs kill -9
npm start
```

### "Port 8000 already in use"
```bash
lsof -ti:8000 | xargs kill -9
npm start
```

### Dashboard shows "No alerts"
This is normal if:
- Running outside market hours (4am-8pm ET)
- No stocks have moved 3%+ yet
- Screener just started (give it 1-2 minutes)

### Services won't start
Try cleaning and re-setup:
```bash
npm run clean
npm run setup
npm start
```

## Next Steps

Once everything is working:

1. ✅ Let it run for 30 minutes during market hours
2. ✅ Watch alerts appear in dashboard
3. ✅ Check Supabase table editor to see alerts stored
4. ✅ Try different threshold: `./run.sh screener --threshold 0.02`
5. 📱 Ready for Phase 2: SMS integration!

## Daily Usage

After first-time setup, you only need:

```bash
# Morning
npm start

# Evening
npm stop
```

That's it!

---

**Need help?** See [COMMANDS.md](COMMANDS.md) for all available commands.
