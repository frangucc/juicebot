# Architecture Overview

## System Design

This trading assistant uses a microservices architecture optimized for speed, reliability, and real-time processing.

## Core Components

### 1. Screener Service (`screener/`)
**Purpose:** Monitor all US stocks in real-time for trading opportunities

**Technology:**
- Python 3.9+ (async/await)
- Databento Live API (sub-millisecond latency)
- MBP-1 schema (top-of-book updates)

**Features:**
- Subscribes to ALL_SYMBOLS (~9,000 tickers)
- Detects gap-ups, volume spikes, price patterns
- Stores alerts in Supabase
- Extensible for custom indicators

**Data Flow:**
```
Databento → Scanner → Alert Handler → Supabase
                    ↓
               (Future: SMS Queue)
```

### 2. API Service (`api/`)
**Purpose:** REST API and WebSocket gateway

**Technology:**
- FastAPI (async, high performance)
- Uvicorn (ASGI server)
- WebSockets (planned)

**Endpoints:**
- `GET /health` - Health check
- `GET /alerts` - Recent alerts (with filters)
- `GET /alerts/today` - Today's alerts
- `GET /alerts/stats` - Statistics

**Future endpoints:**
- `POST /sms/webhook` - Twilio SMS receiver
- `WS /ws/alerts` - Real-time alert stream

### 3. Database (Supabase Postgres)
**Purpose:** Persistent storage with real-time capabilities

**Why Supabase:**
- ✅ PostgreSQL with JSONB (flexible schema)
- ✅ Real-time subscriptions (WebSocket)
- ✅ Row-level security (RLS)
- ✅ Built-in auth
- ✅ REST API auto-generated
- ✅ TimescaleDB extension available

**Key Tables:**
- `screener_alerts` - Real-time alerts
- `trades` - Position tracking
- `users` - User preferences
- `sms_messages` - Conversation history
- `market_data_cache` - OHLCV bars (JSONB)

### 4. Dashboard (`dashboard/`)
**Purpose:** Admin monitoring and control panel

**Technology:**
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Recharts (future)

**Features:**
- Real-time alert feed
- Statistics and charts
- Symbol search
- Mobile responsive

### 5. Workflows (Future: `workflows/`)
**Purpose:** Orchestrate trade lifecycle

**Technology:** Temporal.io

**Workflows:**
- Entry signal → Confirm → Monitor → Exit
- Stop-loss monitoring
- SMS follow-ups
- Retry logic

## Data Models

### Alert Model
```python
{
  "symbol": "AAPL",
  "alert_type": "gap_up",
  "trigger_price": 150.25,
  "trigger_time": "2025-01-22T09:31:00Z",
  "conditions": {
    "pct_move": 3.5,
    "previous_close": 145.00
  },
  "metadata": {
    "bid": 150.20,
    "ask": 150.30,
    "spread": 0.10
  }
}
```

### Trade Model
```python
{
  "user_id": "uuid",
  "symbol": "AAPL",
  "entry_price": 150.25,
  "stop_loss": 148.00,
  "take_profit": 155.00,
  "status": "monitoring",
  "bars_data": [...]  # JSONB array of OHLCV
}
```

## Design Principles

### 1. Speed & Performance
- Async Python throughout
- Sub-millisecond Databento feed
- Redis caching (planned)
- Efficient JSONB queries

### 2. Fault Tolerance
- Temporal workflows (durable execution)
- Retry logic on all external APIs
- Circuit breakers
- Graceful degradation

### 3. Scalability
- Stateless API (horizontal scaling)
- Postgres connection pooling
- Background job queues
- Microservices architecture

### 4. Functional Design
- Pure functions where possible
- Immutable data structures
- Side effects isolated to handlers
- Easy to test and reason about

## Technology Choices

### Why Databento?
- ✅ Fastest market data API
- ✅ ALL_SYMBOLS support
- ✅ Sub-ms latency
- ✅ Pre-market data
- ✅ Historical replay

### Why FastAPI?
- ✅ Async/await native
- ✅ Automatic OpenAPI docs
- ✅ Type safety (Pydantic)
- ✅ WebSocket support
- ✅ High performance

### Why Next.js?
- ✅ React with SSR
- ✅ App Router (modern)
- ✅ API routes
- ✅ PWA support
- ✅ Mobile-first

### Why Temporal? (Future)
- ✅ Durable workflows
- ✅ Built-in retries
- ✅ State management
- ✅ Observability
- ✅ Long-running processes

## Deployment Architecture (Future)

```
┌─────────────────────────────────────────┐
│           Databento Cloud               │
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│      Screener Service (Docker)          │
│      - Python async worker              │
│      - Autoscale based on load          │
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│         Redis (Managed)                 │
│      - Alert queue                      │
│      - Session cache                    │
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│      API Service (Docker)               │
│      - FastAPI                          │
│      - Multiple replicas                │
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│         Supabase (Managed)              │
│      - Postgres + Real-time             │
│      - Automatic backups                │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│      Dashboard (Vercel)                 │
│      - Next.js SSR                      │
│      - Edge deployment                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│      Temporal Cloud (Future)            │
│      - Workflow orchestration           │
└─────────────────────────────────────────┘
```

## Security Considerations

1. **API Keys**: Never commit to git (`.gitignore`)
2. **RLS**: Enabled on user-facing tables
3. **HTTPS**: Use in production
4. **Rate limiting**: Add to API endpoints
5. **Input validation**: Pydantic models

## Monitoring Strategy

### Metrics to Track:
- Screener latency (goal: <100ms per event)
- Alerts generated per hour
- Database query performance
- API response times
- SMS delivery rate (future)

### Tools:
- Supabase built-in monitoring
- FastAPI metrics endpoint
- Custom Postgres performance table
- Sentry for error tracking (future)
- Datadog/Grafana (production)

## Cost Optimization

### Current (Development):
- Databento: Free tier (delayed data) or starter plan
- Supabase: Free tier (500MB, 2GB bandwidth)
- Vercel: Free tier (Next.js)
- Total: ~$0-50/month

### Production (100 users):
- Databento: ~$200/month (real-time)
- Supabase: ~$25/month (Pro plan)
- Vercel: ~$20/month
- Twilio: ~$100/month (1K SMS)
- Total: ~$350/month

## Phase Roadmap

**Phase 1 (Current): Basic Screener ✅**
- Real-time gap scanner
- Database storage
- Admin dashboard

**Phase 2: SMS Integration**
- Twilio setup
- AI message parsing (Claude)
- User management

**Phase 3: Trade Management**
- Temporal workflows
- Position tracking
- Entry/exit logic

**Phase 4: Advanced Features**
- Custom indicators
- Pattern recognition
- News/sentiment APIs
- Backtesting

## Development Workflow

1. Make changes
2. Test locally (3 terminals)
3. Check Supabase for data
4. View dashboard
5. Commit to git
6. Deploy (future)

## Further Reading

- [Databento Docs](https://docs.databento.com)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Next.js App Router](https://nextjs.org/docs/app)
- [Temporal Docs](https://docs.temporal.io)
- [Supabase Docs](https://supabase.com/docs)
