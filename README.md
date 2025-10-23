# Trading SMS Assistant

Real-time stock screener with SMS alerts for pre-market movers and gap-ups.

**Built with:** Python, FastAPI, Databento, Supabase, Next.js

---

## 👋 New Here?

**👉 Start with [START_HERE.md](START_HERE.md)** - Your complete getting started guide!

---

## 🚀 Quick Start

```bash
# 1. First-time setup
npm run setup

# 2. Run the database migration in Supabase
#    (Copy/paste sql/001_init_schema.sql in SQL Editor)

# 3. Start everything
npm start
```

**Then open:** http://localhost:3000

**To stop:** `npm stop`

📖 **First time?** Read [QUICKSTART.md](QUICKSTART.md) for detailed 5-minute setup.
📋 **All commands:** See [COMMANDS.md](COMMANDS.md) for complete reference.

## ✨ Features

### Phase 1 (MVP - Complete ✅)
- [x] Real-time scanner for all 9,000+ US stocks
- [x] Pre-market gap detection (4am-9:30am ET)
- [x] Configurable threshold (default 3%)
- [x] Supabase database storage
- [x] REST API with health checks
- [x] Next.js admin dashboard
- [x] Real-time alert feed

### Phase 2 (Next)
- [ ] SMS alerts via Twilio
- [ ] AI-powered response parsing (Anthropic Claude)
- [ ] User management
- [ ] Trade confirmation workflow

### Phase 3 (Future)
- [ ] Position tracking
- [ ] Stop-loss monitoring
- [ ] Exit signal detection
- [ ] P&L calculation
- [ ] Temporal.io workflows

### Phase 4 (Future)
- [ ] Custom indicators (RSI, VWAP, volume)
- [ ] Pattern recognition
- [ ] News/sentiment integration
- [ ] Backtesting framework

## 🏗️ Architecture

```
Databento → Screener → Supabase → API → Dashboard
                ↓
            Alerts (Future: SMS)
```

**Tech Stack:**
- **Backend**: Python 3.9+, FastAPI (async)
- **Real-time Data**: Databento Live API
- **Database**: Supabase Postgres + JSONB
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Future**: Temporal.io (workflows), Twilio (SMS), Anthropic (AI)

**Why these choices?** See [ARCHITECTURE.md](ARCHITECTURE.md)

## 📁 Project Structure

```
trade_app/
├── screener/              # Real-time market scanner
│   ├── scanner.py         # Core scanning logic
│   ├── alert_handler.py   # Alert storage
│   └── main.py           # CLI entry point
│
├── api/                   # FastAPI REST API
│   └── main.py           # Endpoints for alerts, health
│
├── dashboard/             # Next.js admin UI
│   ├── app/              # Pages (App Router)
│   ├── components/       # React components
│   └── package.json      # Dependencies
│
├── shared/                # Shared utilities
│   ├── config.py         # Settings management
│   └── database.py       # Supabase client
│
├── sql/                   # Database migrations
│   └── 001_init_schema.sql
│
└── workflows/             # Temporal (Phase 3)
```

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide (start here!)
- **[SETUP.md](SETUP.md)** - Detailed installation and configuration
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical deep-dive
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Complete overview
- **[sql/README.md](sql/README.md)** - Database schema docs

## 🔧 Usage

### Essential Commands

```bash
npm start              # Start all services (API + Screener + Dashboard)
npm stop               # Stop all services
npm run status         # Check what's running
npm run logs:all       # View live logs
npm run restart        # Restart everything
```

### Running the Screener

```bash
# With all services (recommended)
npm start

# Standalone screener with custom options
./run.sh screener --threshold 0.05    # 5% threshold
./run.sh screener --replay            # Replay mode (testing)
./run.sh screener --today 2025-01-22  # Specific date
```

📋 **More commands:** See [COMMANDS.md](COMMANDS.md)

### API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Get recent alerts
curl http://localhost:8000/alerts?limit=10

# Get today's alerts
curl http://localhost:8000/alerts/today

# Get statistics
curl http://localhost:8000/alerts/stats

# API docs (auto-generated)
open http://localhost:8000/docs
```

### Dashboard

Open http://localhost:3000 to see:
- Real-time alert feed
- Statistics (total alerts, unique symbols, avg move)
- Auto-refresh every 10-30 seconds
- Mobile-responsive design

## 🗄️ Database Schema

Key tables:
- `screener_alerts` - Real-time alerts from scanner
- `trades` - Position tracking (Phase 3)
- `users` - User accounts and preferences
- `sms_messages` - Conversation history (Phase 2)
- `market_data_cache` - OHLCV bars (JSONB)

**Run migration:** Copy `sql/001_init_schema.sql` into Supabase SQL Editor

## ⚙️ Configuration

All configuration is in `.env` (already set up):

```bash
# Supabase (configured ✅)
SUPABASE_URL=https://szuvtcbytepaflthqnal.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...

# Databento (configured ✅)
DATABENTO_API_KEY=db-Uy7j8hhNfyxPadQFiHcpbKYUMCQDt

# Future Phase 2:
TWILIO_ACCOUNT_SID=...
ANTHROPIC_API_KEY=...
```

## 🧪 Testing

```bash
# Test with replay (works outside market hours)
./run.sh test

# Run unit tests (future)
pytest tests/

# Manual test during pre-market
# Run between 4:00am - 9:30am ET for best results
./run.sh screener --threshold 0.02
```

## 📊 Performance

- **Screener**: ~5s to load previous day's prices, <100ms per alert
- **API**: ~10-50ms response time
- **Database**: Sub-100ms queries
- **Feed latency**: Sub-millisecond from Databento

## 💰 Cost

**Development**: $0-50/month
- Databento: Free tier or $50/month
- Supabase: Free tier
- Everything else: Free

**Production (100 users)**: ~$350/month
- Databento: $200/month
- Supabase: $25/month
- Twilio: $100/month
- Vercel: $20/month

## 🚢 Deployment (Future)

- **Screener**: Docker → Cloud Run/ECS
- **API**: Docker → Cloud Run/ECS with load balancer
- **Dashboard**: Vercel (automatic from git)
- **Database**: Supabase (managed)

## 🤝 Contributing

This is a personal project, but improvements welcome:
1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

Private project - All rights reserved

## 🆘 Troubleshooting

### "Module not found"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Database connection failed"
Check `.env` has correct Supabase credentials

### "Databento API error"
Verify `DATABENTO_API_KEY` in `.env`

### Dashboard not loading
1. Ensure API is running on port 8000
2. Check `dashboard/.env.local` exists
3. Clear browser cache

More help: See [QUICKSTART.md](QUICKSTART.md#common-issues)

## 📧 Support

- Databento docs: https://docs.databento.com
- Supabase docs: https://supabase.com/docs
- FastAPI docs: https://fastapi.tiangolo.com
- Next.js docs: https://nextjs.org/docs

---

**Status**: Phase 1 Complete ✅ | Ready for Phase 2 (SMS Integration)
