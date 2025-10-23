# Setup Guide - Trading SMS Assistant

Complete setup instructions for your trading assistant application.

## Prerequisites

- Python 3.9+
- Node.js 18+
- Supabase account
- Databento account

## Step 1: Database Setup

1. Go to your Supabase project dashboard at https://szuvtcbytepaflthqnal.supabase.co

2. Navigate to the SQL Editor

3. Run the migration file:
   - Copy contents of `sql/001_init_schema.sql`
   - Paste and execute in SQL Editor
   - Verify tables were created under "Table Editor"

You should see these tables:
- users
- screener_alerts
- trades
- sms_messages
- market_data_cache
- screener_performance

## Step 2: Python Environment

1. Create virtual environment:
```bash
cd /Users/franckjones/Desktop/trade_app
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Note: If `ta-lib` fails to install, you may need to install TA-Lib C library first:
```bash
# macOS
brew install ta-lib

# Linux
sudo apt-get install ta-lib

# Then retry: pip install ta-lib
```

## Step 3: Environment Variables

Your `.env` file is already configured with:
- ✅ Supabase credentials
- ✅ Databento API key

Optional: Add these for future phases:
```bash
# Add to .env for Phase 2 (SMS)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=your_number

# Add for AI parsing
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key

# Add for Redis (optional)
REDIS_URL=redis://localhost:6379
```

## Step 4: Test the Screener

Run the screener in replay mode (replays pre-market data):

```bash
python -m screener.main --replay --threshold 0.03
```

You should see output like:
```
[2025-01-22 09:15:23] Loading previous day's closing prices...
[2025-01-22 09:15:28] Loaded 9247 symbols with previous closing prices
[2025-01-22 09:15:28] Starting live scanner...
[2025-01-22 09:15:28] Threshold: 3.0%
[2025-01-22 09:15:28] Watching 9247 symbols
[2025-04-24T04:00:00.007704938-04:00] TSLA moved by 5.43% (current: 245.4300, previous: 259.5100)
    ✓ Alert stored in database (ID: abc123de..., total: 1)
```

Press Ctrl+C to stop.

## Step 5: Start the API Server

In a new terminal:

```bash
source venv/bin/activate
python -m api.main
```

Test it:
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

## Step 6: Start the Dashboard

In a new terminal:

```bash
cd dashboard
npm install
```

Create `.env.local`:
```bash
cp .env.local.example .env.local
```

Edit `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://szuvtcbytepaflthqnal.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Start the dashboard:
```bash
npm run dev
```

Open http://localhost:3000

## Running Everything Together

Use 3 terminal windows:

**Terminal 1 - Screener:**
```bash
cd /Users/franckjones/Desktop/trade_app
source venv/bin/activate
python -m screener.main --threshold 0.03
```

**Terminal 2 - API:**
```bash
cd /Users/franckjones/Desktop/trade_app
source venv/bin/activate
uvicorn api.main:app --reload
```

**Terminal 3 - Dashboard:**
```bash
cd /Users/franckjones/Desktop/trade_app/dashboard
npm run dev
```

## Troubleshooting

### "Module not found" error
Make sure you're in the virtual environment:
```bash
source venv/bin/activate
which python  # Should show path to venv
```

### Database connection error
Check your `.env` file has correct Supabase credentials.

### Databento API error
Verify your API key in `.env`:
```bash
DATABENTO_API_KEY=db-Uy7j8hhNfyxPadQFiHcpbKYUMCQDt
```

### Dashboard not loading
1. Make sure API is running on port 8000
2. Check `.env.local` has correct URLs
3. Clear browser cache

## Next Steps

Once everything is running:

1. ✅ Watch alerts appear in real-time on the dashboard
2. ✅ Check Supabase "screener_alerts" table filling up
3. 📱 Phase 2: Add SMS integration (Twilio)
4. 🤖 Phase 3: Add AI-powered trade management
5. 📊 Phase 4: Advanced patterns and indicators

## Support

- Databento docs: https://docs.databento.com
- Supabase docs: https://supabase.com/docs
- Next.js docs: https://nextjs.org/docs
