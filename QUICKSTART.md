# Quick Start Guide

Get your trading assistant running in 5 minutes!

## Prerequisites Check

```bash
# Check Python version (need 3.9+)
python3 --version

# Check Node version (need 18+)
node --version

# Check npm
npm --version
```

## Step 1: Setup Database (2 minutes)

1. Open https://szuvtcbytepaflthqnal.supabase.co
2. Go to SQL Editor
3. Copy/paste contents of `sql/001_init_schema.sql`
4. Click "Run"
5. ✅ Check "Table Editor" - you should see 6 new tables

## Step 2: Install Python Dependencies (2 minutes)

```bash
cd /Users/franckjones/Desktop/trade_app

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Note:** If `ta-lib` fails:
```bash
# macOS only:
brew install ta-lib
pip install ta-lib
```

## Step 3: Test the Screener (1 minute)

```bash
# Still in venv
python -m screener.main --replay --threshold 0.03
```

You should see:
```
Loading previous day's closing prices...
Loaded 9247 symbols...
Starting live scanner...
[timestamp] TSLA moved by 5.43%
    ✓ Alert stored in database
```

Press **Ctrl+C** to stop when you see alerts.

## Step 4: Start Everything (Open 3 Terminals)

### Terminal 1: Screener
```bash
cd /Users/franckjones/Desktop/trade_app
source venv/bin/activate
python -m screener.main --threshold 0.03
```

### Terminal 2: API
```bash
cd /Users/franckjones/Desktop/trade_app
source venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

### Terminal 3: Dashboard
```bash
cd /Users/franckjones/Desktop/trade_app/dashboard
npm install  # first time only
cp .env.local.example .env.local  # first time only
# Edit .env.local with your Supabase URL and key
npm run dev
```

## Step 5: View Dashboard

Open http://localhost:3000

You should see:
- ✅ Stats cards (alerts, symbols, avg move)
- ✅ Recent alerts table
- ✅ Auto-refreshing data

## Testing API Directly

```bash
# Health check
curl http://localhost:8000/health

# Get alerts
curl http://localhost:8000/alerts

# Get stats
curl http://localhost:8000/alerts/stats

# Get today's alerts
curl http://localhost:8000/alerts/today
```

## What You Should See

### In Terminal 1 (Screener):
```
[2025-01-22 09:31:23] AAPL moved by 3.2%
    ✓ Alert stored in database (ID: abc123...)
[2025-01-22 09:31:45] TSLA moved by 4.5%
    ✓ Alert stored in database (ID: def456...)
```

### In Terminal 2 (API):
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started server process
```

### In Terminal 3 (Dashboard):
```
- ready started server on 0.0.0.0:3000
- Local:        http://localhost:3000
```

### In Browser (Dashboard):
- Real-time alerts appearing
- Stats updating every 30 seconds
- Mobile-friendly layout

## Common Issues

### "Module not found"
```bash
# Make sure you're in venv:
which python  # should show .../venv/bin/python
pip list  # should show databento, fastapi, etc.
```

### "Database connection failed"
```bash
# Check .env file:
cat .env | grep SUPABASE_URL
# Should show: https://szuvtcbytepaflthqnal.supabase.co
```

### "Databento API error"
```bash
# Check API key:
cat .env | grep DATABENTO
# Should show: DATABENTO_API_KEY=db-Uy7j8hhNfyxPadQFiHcpbKYUMCQDt
```

### Dashboard shows "No alerts"
1. Make sure screener (Terminal 1) is running
2. Make sure API (Terminal 2) is running
3. Wait 30 seconds for refresh
4. Check browser console for errors (F12)

### Port already in use
```bash
# API (port 8000):
lsof -ti:8000 | xargs kill -9

# Dashboard (port 3000):
lsof -ti:3000 | xargs kill -9
```

## Next Steps

Once everything works:

1. ✅ **Watch it run** - Let it scan for 30 minutes, watch alerts
2. ✅ **Check Supabase** - View `screener_alerts` table filling up
3. 📝 **Customize threshold** - Try `--threshold 0.05` (5%)
4. 📱 **Phase 2** - Add SMS integration (see SETUP.md)
5. 🤖 **Phase 3** - Add AI trade management
6. 📊 **Phase 4** - Custom indicators & patterns

## Stopping Everything

Press **Ctrl+C** in each terminal to stop services gracefully.

## Need Help?

- Full setup: See `SETUP.md`
- Architecture: See `ARCHITECTURE.md`
- Code docs: See `README.md`

## Tips

- **Run during pre-market** (4-9:30am ET) to see the most activity
- **Lower threshold** (1-2%) will generate more alerts
- **Check Supabase logs** for database insights
- **Use `--replay`** flag to test with historical data outside market hours

Enjoy your real-time stock screener! 🚀
