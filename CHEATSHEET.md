# Command Cheat Sheet

Quick reference card - print this out!

## 🎯 Most Common Commands

```bash
npm start              # Start everything
npm stop               # Stop everything
npm run status         # Check what's running
```

**That's 90% of what you need!**

## 🚀 First Time Setup

```bash
npm run setup          # Install dependencies
# Then: Run SQL migration in Supabase
# Then: Create dashboard/.env.local
npm start              # Start!
```

## 📊 Monitoring

```bash
npm run status         # Service status
npm run logs:all       # View all logs
npm run logs:screener  # Just screener
npm run logs:api       # Just API
npm run logs:dashboard # Just dashboard
```

## 🔧 Individual Services

```bash
npm run screener       # Just screener
npm run api           # Just API
npm run dashboard     # Just dashboard
```

## 🧪 Testing

```bash
npm test              # Test mode (replay)
curl localhost:8000/health  # API health
curl localhost:8000/alerts  # Get alerts
```

## 🐛 Troubleshooting

```bash
npm stop              # Stop all
npm run clean         # Clean everything
npm run setup         # Reinstall
npm start             # Start fresh

# Port issues
lsof -ti:3000 | xargs kill -9  # Kill dashboard port
lsof -ti:8000 | xargs kill -9  # Kill API port
```

## 📍 URLs

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

## 📁 Important Files

| File | Purpose |
|------|---------|
| `.env` | API keys (already set) |
| `dashboard/.env.local` | Dashboard config (create this) |
| `sql/001_init_schema.sql` | Database (run once) |

## 🔄 Typical Workflow

```bash
# Morning
cd /Users/franckjones/Desktop/trade_app
npm start

# ... work/monitor ...

# Evening
npm stop
```

## 📝 Log Files Location

```
.pids/screener.log    # Screener output
.pids/api.log         # API output
.pids/dashboard.log   # Dashboard output
```

## ⚡ Advanced

```bash
# Custom threshold (5%)
./run.sh screener --threshold 0.05

# Replay mode
./run.sh screener --replay

# Specific date
./run.sh screener --today 2025-01-22

# Restart all
npm run restart
```

## 🆘 Emergency

```bash
# Kill everything
npm stop
lsof -ti:3000 | xargs kill -9
lsof -ti:8000 | xargs kill -9
ps aux | grep -E "screener|uvicorn|next" | awk '{print $2}' | xargs kill -9

# Nuclear option (clean slate)
npm run clean
npm run setup
npm start
```

## 📚 Full Documentation

- `FIRST_RUN.md` - First time setup guide
- `COMMANDS.md` - Complete command reference
- `README.md` - Project overview
- `QUICKSTART.md` - 5-minute guide
- `ARCHITECTURE.md` - Technical details

---

**Print this page and keep it handy!**
