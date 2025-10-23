# 👋 START HERE!

**Welcome to your Trading SMS Assistant!**

This is your **starting point**. Read this first, then follow the steps below.

---

## 🎉 Just Ran `npm start`?

**👉 Read [WHAT_JUST_HAPPENED.md](WHAT_JUST_HAPPENED.md) first!**

It explains what worked, what needs fixing, and how to get everything running.

---

## What Is This?

A **real-time stock screener** that watches all 9,000+ US stocks and alerts you when they move significantly (default: 3%+). Built to eventually send SMS alerts and help manage trades.

**Phase 1 Status:** ✅ Complete! Working screener with dashboard.

## Quick Facts

- ⚡ **Sub-millisecond** market data latency
- 📊 **9,000+ stocks** monitored simultaneously
- 🔥 **Pre-market coverage** (4am ET onwards)
- 💾 **Supabase** database with flexible schema
- 📱 **Mobile-ready** dashboard

## 🎯 Your First 3 Commands

```bash
# 1. Setup (first time only - takes 3 minutes)
npm run setup

# 2. Start everything
npm start

# 3. Stop everything (when done)
npm stop
```

**That's it!** Those three commands are 90% of what you need.

## 📖 Which Guide Should I Read?

Choose based on your situation:

### 🆕 **First Time User?**
👉 Read: **[FIRST_RUN.md](FIRST_RUN.md)**
- Step-by-step first-time setup
- Includes database migration
- Troubleshooting for common issues

### ⚡ **Want to Start Fast?**
👉 Read: **[QUICKSTART.md](QUICKSTART.md)**
- 5-minute setup guide
- Get running ASAP
- Minimal explanation

### 🔧 **Need All Commands?**
👉 Read: **[COMMANDS.md](COMMANDS.md)**
- Complete command reference
- Every npm script explained
- Debugging commands

### 📋 **Want a Cheat Sheet?**
👉 Read: **[CHEATSHEET.md](CHEATSHEET.md)**
- Quick reference card
- Print it out!
- Most common commands

### 🏗️ **Want Technical Details?**
👉 Read: **[ARCHITECTURE.md](ARCHITECTURE.md)**
- System design decisions
- Technology choices explained
- Scaling considerations

### 📊 **Want Complete Overview?**
👉 Read: **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)**
- Everything in one place
- All features explained
- Roadmap for future phases

## 🚦 Status Check

**Before you start**, make sure you have:

- [x] `.env` file with API keys (✅ already configured)
- [ ] Database migration run in Supabase (you need to do this once)
- [ ] `dashboard/.env.local` created (you need to do this once)
- [ ] Dependencies installed (`npm run setup`)

## 📁 Project Structure

```
trade_app/
├── START_HERE.md          ← You are here!
├── FIRST_RUN.md          ← Read this next
├── CHEATSHEET.md         ← Print this
├── COMMANDS.md           ← Reference guide
├── README.md             ← Project overview
│
├── screener/             ← Real-time scanner
├── api/                  ← REST API
├── dashboard/            ← Web UI
├── sql/                  ← Database schema
└── .env                  ← Config (set ✅)
```

## 🎬 Typical Session

```bash
# Open terminal
cd /Users/franckjones/Desktop/trade_app

# Start everything (one command!)
npm start

# See logs streaming...
# [2025-01-22 09:31:23] AAPL moved by 3.2%
# [2025-01-22 09:31:45] TSLA moved by 4.5%

# Open dashboard in browser:
# http://localhost:3000

# When done (press Ctrl+C or in another terminal):
npm stop
```

## 🌟 Key Features

### Currently Working ✅
- [x] Real-time screener (all US stocks)
- [x] Pre-market gap detection
- [x] Database storage (Supabase)
- [x] REST API (FastAPI)
- [x] Web dashboard (Next.js)
- [x] One-command start/stop

### Coming Soon (Phase 2)
- [ ] SMS alerts via Twilio
- [ ] AI response parsing
- [ ] User management
- [ ] Trade tracking

### Future (Phase 3+)
- [ ] Position monitoring
- [ ] Stop-loss automation
- [ ] Custom indicators
- [ ] Pattern recognition

## 📊 What You'll See

### In Terminal
```
Starting api...
✓ api started (PID: 12345)

Starting screener...
✓ screener started (PID: 12346)

Starting dashboard...
✓ dashboard started (PID: 12347)

[2025-01-22 09:31:23] AAPL moved by 3.2%
    ✓ Alert stored in database
```

### In Dashboard (http://localhost:3000)
- **Stats cards:** Total alerts, unique symbols, avg move %
- **Alert feed:** Real-time table of all alerts
- **Auto-refresh:** Updates every 10-30 seconds

### In Supabase
- **screener_alerts table:** All alerts stored here
- Can query, export, analyze
- Real-time subscriptions available

## ⏱️ Time Estimates

| Task | Time |
|------|------|
| First-time setup | 3-5 minutes |
| Database migration | 1 minute |
| Starting services | 10 seconds |
| Stopping services | 2 seconds |

## 🆘 Help!

### Something's not working?

1. **First step:** Read [FIRST_RUN.md](FIRST_RUN.md) - covers most issues
2. **Check status:** Run `npm run status`
3. **View logs:** Run `npm run logs:all`
4. **Nuclear option:**
   ```bash
   npm run clean
   npm run setup
   npm start
   ```

### Common Issues

| Problem | Solution |
|---------|----------|
| Port in use | `npm stop` then `npm start` |
| Module not found | `npm run setup` |
| Database error | Check `.env` has correct credentials |
| No alerts showing | Normal outside market hours (4am-8pm ET) |

## 🎯 Your Action Plan

**Right now, do this:**

1. ✅ Read this page (you're doing it!)
2. 📖 Open and read [FIRST_RUN.md](FIRST_RUN.md)
3. ⚙️ Follow the setup steps
4. 🚀 Run `npm start`
5. 🌐 Open http://localhost:3000
6. 🎉 Watch alerts roll in!

## 📞 Resources

- **Databento Docs:** https://docs.databento.com
- **Supabase Docs:** https://supabase.com/docs
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Next.js Docs:** https://nextjs.org/docs

## 💡 Pro Tips

1. **Run during pre-market** (4-9:30am ET) for maximum action
2. **Keep terminal visible** to see alerts in real-time
3. **Use `npm run status`** to check if everything's running
4. **Lower threshold** (1-2%) = more alerts
5. **Test mode** (`npm test`) works outside market hours

## 🎓 Learning Path

**Week 1:** Get it running, watch alerts, understand flow
**Week 2:** Customize threshold, explore dashboard
**Week 3:** Ready for Phase 2 (SMS integration)

## ✅ Success Checklist

After first run, you should have:

- [ ] All services running (`npm run status` shows ✓✓✓)
- [ ] Dashboard accessible at http://localhost:3000
- [ ] API responding at http://localhost:8000/health
- [ ] Alerts appearing in dashboard
- [ ] Data in Supabase screener_alerts table

## 🚀 Ready?

**Let's go!** Open [FIRST_RUN.md](FIRST_RUN.md) and follow the steps.

---

**Remember:** Just three commands:
1. `npm run setup` (first time)
2. `npm start` (every time)
3. `npm stop` (when done)

You've got this! 💪
