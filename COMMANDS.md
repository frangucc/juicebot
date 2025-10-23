# Command Reference

Quick reference for all available commands.

## 🚀 Start/Stop Commands

### Start Everything
```bash
# Option 1: Using npm (recommended)
npm run dev
# or
npm start

# Option 2: Direct script
./start.sh
```

This will:
- ✅ Start API server (port 8000)
- ✅ Start screener service
- ✅ Start dashboard (port 3000)
- ✅ Show live logs from all services

**URLs:**
- Dashboard: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Stop Everything
```bash
# Option 1: Using npm
npm stop

# Option 2: Direct script
./stop.sh
```

This will:
- ✅ Gracefully stop all services
- ✅ Clean up PID files
- ✅ Kill processes on ports 3000 and 8000

### Check Status
```bash
# Option 1: Using npm
npm run status

# Option 2: Direct script
./status.sh
```

Shows:
- ✓ Which services are running
- ✓ PID numbers
- ✓ Port status
- ✓ Quick access URLs

### Restart Everything
```bash
npm run restart
```

Stops and starts all services with a 2-second delay.

## 📋 Logs

### View Logs (Real-time)

```bash
# All logs (shown by default when running npm start)
npm run logs:all

# Individual service logs
npm run logs:screener    # Screener output
npm run logs:api         # API output
npm run logs:dashboard   # Dashboard output
```

### View Historical Logs
```bash
# Screener
cat .pids/screener.log

# API
cat .pids/api.log

# Dashboard
cat .pids/dashboard.log
```

## 🔧 Development Commands

### Setup (First Time)
```bash
npm run setup
```

This will:
1. Create Python virtual environment
2. Install Python dependencies
3. Install dashboard dependencies

### Run Tests
```bash
npm test
```

Runs screener with replay mode (safe for testing outside market hours).

### Run Individual Services

```bash
# Just the screener
npm run screener

# Just the API
npm run api

# Just the dashboard
npm run dashboard
```

## 🧹 Cleanup

### Clean All Build Files
```bash
npm run clean
```

Removes:
- `.pids/` directory
- `venv/` directory
- `dashboard/node_modules/`
- `dashboard/.next/`

⚠️ **Warning:** You'll need to run `npm run setup` again after this.

## 🎛️ Advanced Commands

### Custom Screener Options

```bash
# Run screener with custom threshold (5%)
./run.sh screener --threshold 0.05

# Run screener with replay
./run.sh screener --replay --threshold 0.03

# Run screener for specific date
./run.sh screener --today 2025-01-22
```

### API Only (Development)
```bash
# With auto-reload
uvicorn api.main:app --reload --port 8000

# Different port
uvicorn api.main:app --port 8080
```

### Dashboard Only (Development)
```bash
cd dashboard
npm run dev         # Development mode
npm run build       # Production build
npm start           # Production server
```

## 🐛 Debugging Commands

### Check What's Running on Ports
```bash
# Check port 8000 (API)
lsof -i :8000

# Check port 3000 (Dashboard)
lsof -i :3000
```

### Kill Specific Port
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

### View Process Tree
```bash
# See all related processes
ps aux | grep -E "screener|uvicorn|next"
```

## 📊 Status Checks

### API Health
```bash
curl http://localhost:8000/health
```

### Get Recent Alerts
```bash
curl http://localhost:8000/alerts?limit=10
```

### Get Statistics
```bash
curl http://localhost:8000/alerts/stats
```

### Test Database Connection
```bash
# Check if Supabase is accessible
curl -H "apikey: YOUR_ANON_KEY" \
     "https://szuvtcbytepaflthqnal.supabase.co/rest/v1/screener_alerts?select=id&limit=1"
```

## 🔄 Common Workflows

### Daily Development Workflow
```bash
# Morning: Start everything
npm start

# ... work on code ...

# Evening: Stop everything
npm stop
```

### Testing Changes
```bash
# Stop services
npm stop

# Make code changes
# ... edit files ...

# Restart to see changes
npm start
```

### View Real-time Alerts
```bash
# In one terminal
npm start

# In another terminal (after a few seconds)
curl http://localhost:8000/alerts
```

### Debug Specific Service
```bash
# Stop everything
npm stop

# Run individual service to see output directly
./run.sh screener --threshold 0.03
```

## 🚨 Troubleshooting Commands

### "Port already in use"
```bash
npm stop
# If still issues:
lsof -ti:3000 | xargs kill -9
lsof -ti:8000 | xargs kill -9
```

### "Module not found"
```bash
# Reinstall Python dependencies
source venv/bin/activate
pip install -r requirements.txt
```

### "npm command not found"
```bash
# Dashboard dependencies
cd dashboard
npm install
cd ..
```

### Services won't start
```bash
# Clean everything and start fresh
npm run clean
npm run setup
npm start
```

### Check logs for errors
```bash
# Look for error messages
grep -i error .pids/*.log

# Show last 50 lines of each log
tail -50 .pids/*.log
```

## 📱 Quick Commands Summary

```bash
# Essential commands
npm start           # Start all services
npm stop            # Stop all services
npm run status      # Check status
npm run logs:all    # View logs

# Setup commands
npm run setup       # First-time setup
npm test            # Test screener

# Individual services
npm run screener    # Just screener
npm run api         # Just API
npm run dashboard   # Just dashboard

# Maintenance
npm run restart     # Restart all
npm run clean       # Clean builds
```

## 🎯 Most Common Commands

**90% of the time, you'll use these:**

```bash
npm start     # Start everything
npm stop      # Stop everything
npm run status # Check status
```

**That's it!** Everything else is for advanced use cases.

---

**Pro tip:** Keep a terminal open with `npm start` running during development. It shows live logs from all services!
