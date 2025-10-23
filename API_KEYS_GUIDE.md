# API Keys Guide

Complete guide for obtaining all API keys needed for the trading assistant.

## 📋 Summary

| Service | Status | Phase | Required? | Cost |
|---------|--------|-------|-----------|------|
| Supabase | ✅ Already set | Phase 1 | ✅ Yes | Free |
| Databento | ✅ Already set | Phase 1 | ✅ Yes | Free tier available |
| Twilio | ❌ Not set | Phase 2 | Later | ~$1/month |
| Anthropic (Claude) | ❌ Not set | Phase 2 | Later | Pay per use |
| OpenAI | ❌ Not set | Phase 2 | Optional | Pay per use |

## ✅ Already Configured (Phase 1 - Current)

### 1. Supabase ✅
**Status:** Already in your `.env` file
**What it does:** Database, authentication, real-time subscriptions

```bash
SUPABASE_URL=https://szuvtcbytepaflthqnal.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres:vLy7fE1GOa070HkB@db...
```

**Action needed:** ✅ None - already set up!

---

### 2. Databento ✅
**Status:** Already in your `.env` file
**What it does:** Real-time stock market data (all 9,000+ US stocks)

```bash
DATABENTO_API_KEY=db-Uy7j8hhNfyxPadQFiHcpbKYUMCQDt
```

**Action needed:** ✅ None - already set up!

**Your account:** Check at https://databento.com/portal

---

## ❌ Not Yet Needed (Phase 2 - SMS Integration)

### 3. Twilio (SMS Service) - Phase 2
**Status:** Not set (not needed yet)
**What it does:** Send and receive SMS messages
**Cost:** ~$1/month + $0.0075 per SMS

#### How to Get:

1. **Sign up:** https://www.twilio.com/try-twilio
   - Free trial gives you $15 credit
   - Can send/receive SMS during trial

2. **Get a phone number:**
   - Go to Console → Phone Numbers → Buy a Number
   - Choose a US number (~$1/month)
   - Select one with SMS capabilities

3. **Get credentials:**
   - Go to Console → Account → API Keys & Tokens
   - Copy these three values:
     ```
     Account SID: ACxxxxxxxxxxxxxxxxxxxxx
     Auth Token: [hidden - click to reveal]
     Phone Number: +1234567890
     ```

4. **Add to `.env`:**
   ```bash
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_PHONE_NUMBER=+1234567890
   ```

**When to do this:** When starting Phase 2 (SMS integration)

---

### 4. Anthropic (Claude API) - Phase 2
**Status:** Not set (not needed yet)
**What it does:** AI parsing of SMS messages ("YES", "Entered at $150", etc.)
**Cost:** Pay per use (~$0.01 per message)

#### How to Get:

1. **Sign up:** https://console.anthropic.com/
   - Create account
   - Add payment method (required)

2. **Get API key:**
   - Go to Settings → API Keys
   - Click "Create Key"
   - Copy the key (starts with `sk-ant-`)

3. **Add to `.env`:**
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxx
   ```

**When to do this:** When starting Phase 2 (SMS integration)

**Pricing:**
- Claude 3.5 Sonnet: $3 per million input tokens
- ~$0.01 per SMS message parsed
- Example: 1,000 messages = ~$10

---

### 5. OpenAI (Optional Backup) - Phase 2
**Status:** Not set (optional)
**What it does:** Alternative to Claude for AI parsing
**Cost:** Pay per use (~$0.005 per message)

#### How to Get:

1. **Sign up:** https://platform.openai.com/signup
   - Create account
   - Add payment method

2. **Get API key:**
   - Go to API Keys
   - Click "Create new secret key"
   - Copy the key (starts with `sk-`)

3. **Add to `.env`:**
   ```bash
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
   ```

**When to do this:** Optional - only if you want backup to Anthropic

**Pricing:**
- GPT-4: $0.03 per 1K tokens
- GPT-3.5-turbo: $0.002 per 1K tokens
- ~$0.005 per message with GPT-3.5

---

## 🚫 NOT Needed (Maybe Later)

### Redis (Optional - Phase 3+)
**What it does:** Caching, pub/sub for real-time updates
**Cost:** Free (local) or ~$5/month (managed)

**Options:**
1. **Local (free):** `brew install redis`
2. **Upstash (managed):** https://upstash.com (free tier: 10K requests/day)

**Default in `.env`:**
```bash
REDIS_URL=redis://localhost:6379
```

**When to add:** Phase 3 or if you need better performance

---

### Temporal Cloud (Optional - Phase 3)
**What it does:** Workflow orchestration for trade lifecycle
**Cost:** Free (self-hosted) or ~$200/month (cloud)

**Options:**
1. **Self-hosted (free):** Docker container
2. **Temporal Cloud:** https://temporal.io/cloud

**When to add:** Phase 3 (trade management workflows)

---

## 📝 Complete `.env` File Structure

### Current (Phase 1) ✅
```bash
# Supabase (✅ already set)
SUPABASE_URL=https://szuvtcbytepaflthqnal.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres:vLy7fE1GOa070HkB@db...

# Databento (✅ already set)
DATABENTO_API_KEY=db-Uy7j8hhNfyxPadQFiHcpbKYUMCQDt

# JWT (✅ already set)
JWT_KEY=60wOM+2IszlXYYU1lmTaie0Tq6g7jXhShTR8ziGcDQUkzIVu7nBl8XquOb1i9+e7U0/vIUGyy40JK2Qw4D+TfA==
```

### After Phase 2 Setup
```bash
# ... all the above ...

# Twilio (Phase 2 - add when ready for SMS)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890

# Anthropic (Phase 2 - add when ready for AI parsing)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxx

# OpenAI (Phase 2 - optional)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
```

### Future Phases
```bash
# ... all the above ...

# Redis (Phase 3 - optional)
REDIS_URL=redis://localhost:6379

# Temporal (Phase 3 - optional)
TEMPORAL_HOST=localhost:7233
```

---

## 💰 Cost Breakdown

### Phase 1 (Current - Running Now)
| Service | Cost | Status |
|---------|------|--------|
| Supabase | Free tier | ✅ Set |
| Databento | Free tier or $50/month | ✅ Set |
| **Total** | **$0-50/month** | **✅ Ready** |

### Phase 2 (SMS + AI)
| Service | Cost | Status |
|---------|------|--------|
| Twilio | $1/month + $0.0075/SMS | Not set |
| Anthropic | ~$0.01/message | Not set |
| **Total added** | **~$50-100/month for 1K messages** | Not needed yet |

### Phase 3+ (Advanced)
| Service | Cost | Status |
|---------|------|--------|
| Redis | Free (local) or $5/month | Not needed |
| Temporal | Free (self-host) or $200/month | Not needed |

---

## 🎯 What You Need RIGHT NOW

**For Phase 1 (current) to work:**

### ✅ You already have everything!

Your `.env` file is complete with:
- ✅ Supabase credentials
- ✅ Databento API key
- ✅ JWT secret

**You can run `npm start` right now!**

---

## 📅 When to Get Each Key

### Now (Phase 1)
- ✅ Supabase - **You have it**
- ✅ Databento - **You have it**

### Later (Phase 2 - ~2-3 weeks)
- ⏳ Twilio - Get when you want SMS alerts
- ⏳ Anthropic - Get when you want AI parsing

### Maybe (Phase 3+ - ~1-2 months)
- 🤔 Redis - Only if you need performance boost
- 🤔 Temporal - Only if you want workflow orchestration

---

## 🔐 Security Best Practices

### DO ✅
- Keep `.env` file private (already in `.gitignore`)
- Never commit API keys to git
- Rotate keys if exposed
- Use service role keys only in backend
- Use anon keys in frontend (dashboard)

### DON'T ❌
- Share API keys in screenshots
- Commit `.env` to version control
- Use production keys in development (if possible)
- Share Supabase service role key publicly
- Hardcode keys in source files

---

## 🆘 Troubleshooting

### "Databento authentication failed"
- Check your key at: https://databento.com/portal
- Verify it's copied correctly in `.env`
- No spaces or quotes around the key

### "Supabase connection error"
- Verify URL in `.env` matches your project
- Check service role key is correct
- Test connection in Supabase dashboard

### "Twilio error" (Phase 2)
- Verify Account SID starts with `AC`
- Check Auth Token is correct
- Ensure phone number includes country code (+1)

### "Anthropic API error" (Phase 2)
- Verify key starts with `sk-ant-`
- Check you have billing set up
- Confirm you're under rate limits

---

## 📊 Quick Reference

| Need it now? | Service | Where to get | Takes | Cost |
|--------------|---------|--------------|-------|------|
| ✅ Now | Supabase | You have it | - | Free |
| ✅ Now | Databento | You have it | - | $0-50/month |
| ⏳ Phase 2 | Twilio | twilio.com | 5 min | $1/month |
| ⏳ Phase 2 | Anthropic | console.anthropic.com | 2 min | Pay per use |
| 🤔 Optional | OpenAI | platform.openai.com | 2 min | Pay per use |
| 🤔 Later | Redis | upstash.com | 3 min | Free/month |

---

## ✅ Action Items

### Right Now (Phase 1)
- [x] Supabase keys - **Already in `.env`**
- [x] Databento key - **Already in `.env`**
- [ ] Nothing! You're ready to run `npm start`

### When Starting Phase 2 (SMS)
- [ ] Get Twilio account
- [ ] Buy phone number
- [ ] Add Twilio keys to `.env`
- [ ] Get Anthropic API key
- [ ] Add Anthropic key to `.env`

### Optional/Later
- [ ] Redis (if needed)
- [ ] Temporal (if needed)
- [ ] OpenAI (if wanted)

---

## 🎉 Summary

**You already have everything needed for Phase 1!**

Your `.env` file is complete with:
- ✅ Supabase (database)
- ✅ Databento (market data)
- ✅ JWT secret

**You can start the app right now:**
```bash
npm start
```

**When you're ready for Phase 2 (SMS):**
- Come back to this guide
- Get Twilio + Anthropic keys
- Add them to `.env`
- Continue building!

---

**Next step:** Read [FIRST_RUN.md](FIRST_RUN.md) and get the app running!
