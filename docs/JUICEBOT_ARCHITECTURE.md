# JuiceBot: AI-Powered Trading Assistant Platform

## Overview
JuiceBot is an autonomous/human-in-the-loop AI trading assistant that combines chat interface, real-time market data, and multiple trading strategies to help traders make better decisions and eventually trade autonomously.

## Core Capabilities
- **Multi-Strategy System**: Smart Money Concepts (SMC), Accumulation, Algo Scalp, Hit & Run
- **Real-time Market Analysis**: Access to live and historical bar data
- **Position Management**: Track trades, P&L, and performance
- **Paper Trading**: Realistic order simulation with slippage, stops, and fills
- **Conversational Memory**: Vector-based semantic search of past conversations
- **Self-Analysis**: AI benchmarks its own decisions and compares to trader actions
- **Xbox Controller Integration**: Left trigger = Buy, Right trigger = Sell

---

## Phase 1: Foundation & Basic Chat Intelligence (Week 1-2)

### 1.1 Backend AI Service (Python)
**Location**: Create new `ai-service/` directory
**Port**: 8002
**Framework**: FastAPI

**Dependencies**:
```bash
pip install anthropic langgraph langchain-anthropic supabase pgvector fastapi uvicorn websockets
```

**AI Model**: Claude Sonnet 4.5 (`claude-sonnet-4-20250514`)

**Core Tools** (for AI function calling):
- `get_current_price(symbol: str)` → Latest bar data from API
- `get_volume_stats(symbol: str, period: str)` → Average volume, relative volume
- `get_price_range(symbol: str, period: str)` → High/low over time period
- `get_historical_bars(symbol: str, limit: int)` → Raw OHLCV data
- `analyze_chart_pattern(bars: List, pattern_type: str)` → On-demand SMC indicator detection (FVG, BoS, CHoCH)

**API Endpoints**:
- `POST /chat` - Send message, get AI response
- `WS /chat/stream` - WebSocket for streaming responses
- `GET /conversation/{id}` - Retrieve conversation history
- `POST /conversation/new` - Start new conversation with strategy selection

### 1.2 Database Schema (Supabase)

#### New Tables

**conversations**
```sql
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT,
  symbol TEXT NOT NULL,
  strategy TEXT NOT NULL, -- 'smc', 'accumulation', 'algo_scalp', 'hit_run'
  paper_trading_enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**messages**
```sql
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL, -- 'user' or 'assistant'
  content TEXT NOT NULL,
  embedding VECTOR(1536), -- For semantic search
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_embedding ON messages USING ivfflat (embedding vector_cosine_ops);
```

**positions**
```sql
CREATE TABLE positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id),
  symbol TEXT NOT NULL,
  side TEXT NOT NULL, -- 'long' or 'short'
  entry_price DECIMAL NOT NULL,
  quantity INTEGER NOT NULL,
  entry_time TIMESTAMPTZ DEFAULT NOW(),
  exit_price DECIMAL,
  exit_time TIMESTAMPTZ,
  stop_loss DECIMAL,
  take_profit DECIMAL,
  pnl DECIMAL,
  pnl_pct DECIMAL,
  status TEXT DEFAULT 'open', -- 'open', 'closed', 'stopped_out'
  strategy TEXT NOT NULL,
  entry_reasoning TEXT
);

CREATE INDEX idx_positions_conversation ON positions(conversation_id);
CREATE INDEX idx_positions_status ON positions(status);
```

**trades** (individual fills for a position)
```sql
CREATE TABLE trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  position_id UUID REFERENCES positions(id) ON DELETE CASCADE,
  order_type TEXT NOT NULL, -- 'market', 'limit', 'stop'
  price DECIMAL NOT NULL,
  quantity INTEGER NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  filled BOOLEAN DEFAULT true,
  slippage DECIMAL DEFAULT 0
);
```

**ai_decisions**
```sql
CREATE TABLE ai_decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id),
  decision_type TEXT NOT NULL, -- 'entry', 'exit', 'hold', 'adjust_stop'
  reasoning TEXT NOT NULL,
  recommended_action JSONB, -- {action: 'buy', quantity: 100, stop: 50.00, ...}
  user_followed BOOLEAN,
  actual_outcome TEXT, -- Set after trade closes
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_decisions_conversation ON ai_decisions(conversation_id);
```

### 1.3 Frontend Updates

**ChatInterface.tsx** enhancements:
- Connect to AI service WebSocket (`ws://localhost:8002/chat/stream`)
- Add strategy selector dropdown at top of chat
- Display current position badge (e.g., "LONG AAPL +$45.23 (+2.1%)")
- Add `/` command menu:
  - `/position` - Show current position
  - `/volume` - Get volume stats
  - `/range` - Get price range
  - `/analyze [pattern]` - Run pattern detection
- Stream AI responses token-by-token
- Auto-scroll to latest message

**ChartAgentContent.tsx** updates:
- Add "Paper Trading Mode" toggle in header
- Pass current bar data to chat context
- Display position overlay on chart (entry line, stop line, take profit line)

---

## Phase 2: LangGraph Strategy System (Week 3-4)

### 2.1 Strategy State Machines

Each strategy is a LangGraph workflow with distinct states and transitions.

#### Smart Money Concepts (SMC)

**States**:
1. `observing` - Watching price action, no position
2. `identifying_structure` - Detected potential BoS/CHoCH
3. `waiting_for_entry` - Identified FVG or order block, waiting for retest
4. `in_position` - Trade active
5. `managing_trade` - Adjusting stops, watching for exit signals

**Detects**:
- Fair Value Gaps (FVG)
- Break of Structure (BoS)
- Change of Character (CHoCH)
- Order blocks
- Liquidity sweeps

**Entry Rules**:
- Wait for BoS confirming trend
- Enter on FVG retest in direction of BoS
- Stop loss below/above FVG opposite boundary

**Exit Rules**:
- CHoCH signals potential reversal
- Target: Previous swing high/low
- Trail stop after 1R profit

#### Accumulation Strategy

**States**:
1. `scanning_for_base` - Looking for consolidation
2. `confirming_accumulation` - Volume dry-up, tight range
3. `waiting_breakout` - Wyckoff spring/upthrust complete
4. `in_position` - Trade active post-breakout

**Detects**:
- Volume profile (decreasing volume in range)
- Price compression (ATR declining)
- Wyckoff patterns (spring, upthrust, backup)

**Entry Rules**:
- Enter on volume spike breakout from base
- Confirm with increased volume on breakout bar
- Stop below base low

**Exit Rules**:
- Target: Range height projected from breakout
- Exit 50% at 1R, trail remaining

#### Algo Scalp

**States**:
1. `scanning_volatility` - Looking for high volume + volatility
2. `waiting_setup` - Momentum spike detected
3. `rapid_entry` - Enter on pullback after spike
4. `quick_exit` - Fast 1-5min hold

**Detects**:
- Volume spikes (>3x average)
- Price momentum (rate of change)
- Quick reversals

**Entry Rules**:
- Enter on first pullback after volume spike
- Tight stop (0.5% to 1%)

**Exit Rules**:
- Take profit at 1-2% gain
- Exit after 5 minutes if no movement

#### Hit & Run

**States**:
1. `hunting_catalyst` - Scanning for news/volume anomalies
2. `entry_confirmation` - Catalyst confirmed, waiting for price confirmation
3. `in_trade` - Position active
4. `taking_profit` - Quick exit on target or reversal

**Detects**:
- Volume explosions (>5x average)
- Gap ups/downs
- Relative volume leaders

**Entry Rules**:
- Enter on continuation after initial spike
- Must have volume confirmation
- Stop loss: 2-3%

**Exit Rules**:
- Take profit: 5-10%
- Trail stop aggressively after initial move

### 2.2 AI Tools for Strategy Execution

```python
@tool
def enter_position(symbol: str, side: str, quantity: int, stop_loss: float, take_profit: float) -> dict:
    """Simulate entering a position with risk management"""
    # Creates position in database
    # Calculates realistic fill price with slippage
    # Returns position_id and fill details

@tool
def exit_position(position_id: str, reason: str) -> dict:
    """Close an open position"""
    # Simulates market order exit
    # Calculates final P&L
    # Updates position status to 'closed'

@tool
def update_stop_loss(position_id: str, new_stop: float) -> dict:
    """Update stop loss (for trailing stops)"""
    # Validates new stop is better than old
    # Updates position.stop_loss

@tool
def calculate_position_size(account_balance: float, risk_pct: float, stop_distance: float) -> int:
    """Calculate position size based on risk"""
    # Risk management: (account * risk%) / stop_distance

@tool
def benchmark_decision(decision_id: str, outcome: str) -> dict:
    """Record actual outcome of AI decision for self-analysis"""
    # Updates ai_decisions table with actual_outcome
    # Used for learning/improvement
```

---

## Phase 3: Paper Trading Engine (Week 5)

### 3.1 Order Execution Simulator

**Realistic Fill Logic**:

**Market Orders**:
- Slippage = `spread * 0.5 + (volatility_factor * 0.1)`
- Fill immediately at current bid/ask + slippage
- Example: Buy 100 shares at $50.00 → filled at $50.05 (5¢ slippage)

**Limit Orders**:
- Only fill when `bar.low <= limit_price <= bar.high`
- Partial fills possible based on volume
- Queue position matters (use timestamp)

**Stop-Loss Orders**:
- Trigger when `bar.close` crosses stop level
- Fill at next bar open + slippage
- Realistic: stops can get worse fills during fast moves

**Trailing Stops**:
- Auto-adjust stop when price moves favorably
- Trail by fixed $ amount or %
- Update `position.stop_loss` on every bar

**Position Tracking**:
- Real-time P&L: `(current_price - entry_price) * quantity * direction`
- Update on every new bar
- Emit WebSocket event to frontend for live updates

### 3.2 Positions Dashboard (`/positions` route)

**New Next.js Page**: `dashboard/app/positions/page.tsx`

**Display Sections**:

1. **Active Positions Table**
   - Columns: Symbol, Side, Entry, Current, P&L ($), P&L (%), Duration, Stop, Target
   - Color-coded: Green for profitable, red for losing
   - Click row to open detail modal

2. **Closed Trades History**
   - Last 50 trades
   - Filter by: Strategy, Symbol, Date Range
   - Export to CSV

3. **Performance Stats**
   - Win rate, avg win, avg loss, profit factor
   - By strategy breakdown
   - Total P&L, ROI

4. **Equity Curve**
   - Line chart showing account balance over time
   - Mark entries/exits on chart
   - Use Recharts library

**WebSocket Updates**:
- Connect to `ws://localhost:8002/positions/stream`
- Real-time P&L updates
- Trade notifications

---

## Phase 4: Xbox Controller Integration (Week 6)

### 4.1 Gamepad API Implementation

**Frontend Integration** in `ChartAgentContent.tsx`:

```typescript
useEffect(() => {
  const gamepadHandler = (e: GamepadEvent) => {
    const gamepad = navigator.getGamepads()[e.gamepad.index]

    // Left Trigger (LT) = Buy
    if (gamepad.buttons[6].pressed && gamepad.buttons[6].value > 0.5) {
      handleTriggerBuy()
    }

    // Right Trigger (RT) = Sell
    if (gamepad.buttons[7].pressed && gamepad.buttons[7].value > 0.5) {
      handleTriggerSell()
    }
  }

  window.addEventListener('gamepadconnected', () => {
    console.log('Xbox controller connected')
  })

  window.addEventListener('gamepaddisconnected', () => {
    console.log('Xbox controller disconnected')
  })

  // Poll gamepad state at 60fps
  const interval = setInterval(() => {
    const gamepads = navigator.getGamepads()
    if (gamepads[0]) {
      gamepadHandler({ gamepad: gamepads[0] })
    }
  }, 16)

  return () => clearInterval(interval)
}, [])

const handleTriggerBuy = async () => {
  // Flash green animation
  setTriggerFlash('buy')

  // Ask AI to confirm position sizing
  const response = await fetch('http://localhost:8002/trigger/buy', {
    method: 'POST',
    body: JSON.stringify({ symbol, current_price: latestBar.close })
  })

  const { position_size, stop_loss, take_profit } = await response.json()

  // Execute trade
  // ...
}
```

**Visual Feedback**:
- Flash green overlay on left side of screen (LT press)
- Flash red overlay on right side (RT press)
- Haptic feedback if supported
- Audio "ding" on successful order

---

## Phase 5: Memory & Benchmarking (Week 7-8)

### 5.1 Conversational Memory System

**Hybrid Retrieval Strategy**:

1. **Short-term Memory** (Recent Context)
   - Keep last 20 messages in prompt context
   - Always included in every AI call
   - No embedding lookup needed

2. **Long-term Memory** (Semantic Search)
   - Embed user query using OpenAI/Anthropic embeddings
   - Vector search in `messages` table: `ORDER BY embedding <=> query_embedding LIMIT 5`
   - Include top 5 relevant past messages in context

3. **Context Injection**
   ```
   ## Recent Conversation
   [Last 20 messages]

   ## Relevant Past Context
   [Top 5 semantic matches from history]

   ## Current Question
   User: {current_message}
   ```

**Implementation**:
```python
async def get_conversation_context(conversation_id: str, current_message: str):
    # Get recent messages
    recent = await supabase.table('messages')\
        .select('*')\
        .eq('conversation_id', conversation_id)\
        .order('timestamp', desc=True)\
        .limit(20)\
        .execute()

    # Get semantic matches
    query_embedding = await get_embedding(current_message)
    relevant = await supabase.rpc('match_messages', {
        'query_embedding': query_embedding,
        'conversation_id': conversation_id,
        'match_count': 5
    }).execute()

    return {
        'recent': recent.data,
        'relevant': relevant.data
    }
```

**Supabase Function for Vector Search**:
```sql
CREATE FUNCTION match_messages (
  query_embedding VECTOR(1536),
  conversation_id UUID,
  match_count INT
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  role TEXT,
  timestamp TIMESTAMPTZ,
  similarity FLOAT
)
AS $$
BEGIN
  RETURN QUERY
  SELECT
    m.id,
    m.content,
    m.role,
    m.timestamp,
    1 - (m.embedding <=> query_embedding) AS similarity
  FROM messages m
  WHERE m.conversation_id = match_messages.conversation_id
  ORDER BY m.embedding <=> query_embedding
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
```

### 5.2 AI Self-Analysis System

**After Each Trade Closes**:

1. **Retrieve Decision Record**
   - Find `ai_decisions` entry for this trade
   - Get original reasoning and recommended action

2. **Compare Outcome**
   ```python
   decision = {
       'recommended': 'Buy 100 shares at $50.00, stop $49.00, target $52.00',
       'reasoning': 'FVG retest after bullish BoS, strong volume confirmation',
       'actual_outcome': 'Stopped out at $49.05, -$95 loss (-1.9%)',
       'user_followed': True
   }
   ```

3. **Generate Analysis**
   - Send to AI: "Review your decision. What went right/wrong?"
   - Store analysis in `ai_decisions.self_analysis` column
   - Update `actual_outcome` and `user_followed` fields

4. **Performance Dashboard**
   - Show AI win rate when user follows suggestions
   - Show user win rate when ignoring AI
   - Identify patterns: "AI performs better in trending markets"

**Benchmarking Query Example**:
```sql
-- AI Win Rate
SELECT
  COUNT(*) FILTER (WHERE pnl > 0) * 100.0 / COUNT(*) as win_rate
FROM positions p
JOIN ai_decisions ad ON ad.conversation_id = p.conversation_id
WHERE ad.user_followed = true
  AND ad.decision_type = 'entry'
  AND p.status = 'closed';

-- User vs AI Comparison
SELECT
  CASE WHEN ad.user_followed THEN 'Followed AI' ELSE 'Ignored AI' END as category,
  AVG(p.pnl) as avg_pnl,
  COUNT(*) as trade_count
FROM positions p
JOIN ai_decisions ad ON ad.conversation_id = p.conversation_id
WHERE p.status = 'closed'
GROUP BY ad.user_followed;
```

---

## Phase 6: Educational Center (Week 9-10)

### 6.1 Strategy Training Modules

**Interactive Lessons** (new route: `/learn`)

**Structure**:
- Module 1: Smart Money Concepts
  - Lesson 1.1: What is an FVG?
  - Lesson 1.2: Break of Structure vs Change of Character
  - Lesson 1.3: Order Blocks and Liquidity
  - Quiz: Identify FVGs on real charts

- Module 2: Accumulation Strategy
  - Lesson 2.1: Wyckoff Method
  - Lesson 2.2: Volume Analysis
  - Lesson 2.3: Identifying Bases
  - Quiz: Mark accumulation zones

- Module 3: Risk Management
  - Lesson 3.1: Position Sizing
  - Lesson 3.2: Stop Loss Placement
  - Lesson 3.3: R-Multiple Thinking

**Quiz System**:
- Users must score 80% to unlock autonomous trading for that strategy
- Store progress in `user_progress` table
- AI can quiz users during chat

**Backtesting Playground**:
- Select historical date range
- Run strategy on past data
- See hypothetical performance
- Compare to actual market results

### 6.2 AI Training Mode

**Prompt Optimization**:
- A/B test different system prompts
- Track which prompts lead to better trade outcomes
- Store successful patterns in knowledge base

**Performance Tracking**:
```python
system_prompts = {
    'v1': "You are a conservative SMC trader...",
    'v2': "You are an aggressive SMC trader...",
    'v3': "You combine SMC with volume analysis..."
}

# Rotate prompts and track performance
async def evaluate_prompt_performance(prompt_version: str):
    trades = await get_trades_with_prompt_version(prompt_version)
    return {
        'win_rate': calculate_win_rate(trades),
        'avg_pnl': calculate_avg_pnl(trades),
        'sharpe_ratio': calculate_sharpe(trades)
    }
```

**Knowledge Base**:
- Store successful trade setups
- AI references past wins when seeing similar patterns
- Continuously update based on new data

---

## Technology Stack Summary

### Backend Services

**API Service** (existing, port 8000):
- FastAPI
- Supabase client
- Market data endpoints
- Bar aggregation

**AI Service** (new, port 8002):
- FastAPI
- LangGraph for state machines
- LangChain for tool orchestration
- Anthropic Claude Sonnet 4.5
- WebSocket for streaming
- pgvector for embeddings

### Frontend

**Framework**: Next.js 14 + TypeScript + TailwindCSS

**Key Libraries**:
- `lightweight-charts` - Chart visualization
- `lucide-react` - Icons
- `recharts` - Analytics charts
- Native Gamepad API - Xbox controller

**New Routes**:
- `/chart-agent` - Existing, enhance with AI
- `/positions` - New, position tracking dashboard
- `/learn` - New, educational modules

### Database

**Supabase** (Postgres with pgvector):
- Existing tables: `price_bars`, `symbol_state`, `screener_alerts`
- New tables: `conversations`, `messages`, `positions`, `trades`, `ai_decisions`

### Infrastructure

**npm Scripts** (update `package.json`):
```json
{
  "scripts": {
    "start": "concurrently \"npm run start:api\" \"npm run start:ai\" \"npm run start:dashboard\"",
    "start:api": "cd api && uvicorn main:app --port 8000",
    "start:ai": "cd ai-service && uvicorn main:app --port 8002",
    "start:dashboard": "cd dashboard && next dev",
    "stop": "lsof -ti:8000,8002,3000 | xargs kill -9"
  }
}
```

**Environment Variables** (`.env`):
```
# Existing
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...

# New
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=... # For embeddings if not using Anthropic
```

---

## First Milestone: Basic Chat Intelligence

### Goal
Get simple queries working before building complex strategy logic.

### Test Cases
1. User: "What's the current price?"
   - AI calls `get_current_price('AAPL')`
   - Responds: "AAPL is currently trading at $175.42"

2. User: "What's been the average volume today?"
   - AI calls `get_volume_stats('AAPL', 'today')`
   - Responds: "Average volume today is 52.3M shares, which is 1.2x the 20-day average"

3. User: "What's the high and low?"
   - AI calls `get_price_range('AAPL', 'today')`
   - Responds: "Today's range: High $176.50, Low $174.20"

4. User: "Show me my position"
   - AI queries `positions` table
   - Responds: "You're currently LONG 100 shares of AAPL at $175.00. Current P&L: +$42 (+0.24%)"

### Implementation Steps
1. Set up AI service with Claude API
2. Implement 4 basic tools
3. Connect frontend WebSocket to AI service
4. Test end-to-end flow
5. Add conversation persistence
6. Deploy and iterate

---

## What's Not Missing ✅

✅ **Real-time indicator detection** - AI computes on-demand using bar data tools
✅ **Position tracking window** - Separate `/positions` route with live updates
✅ **Xbox controller integration** - Gamepad API + trigger event handlers
✅ **AI self-analysis** - `ai_decisions` table + benchmarking system
✅ **Strategy switching** - LangGraph state machines with strategy-specific behavior
✅ **Conversation memory** - Hybrid system (recent + semantic pgvector search)
✅ **Paper trading realism** - Slippage, partial fills, stop logic
✅ **Educational system** - Learn modules, quizzes, backtesting playground
✅ **Autonomous mode** - Full state machine workflows for each strategy

---

## Next Steps

1. **Set up AI service repo structure**
2. **Install dependencies and configure Anthropic API**
3. **Create Supabase tables and vector search function**
4. **Implement first 4 basic tools**
5. **Connect frontend chat to AI WebSocket**
6. **Test first milestone queries**
7. **Iterate and expand to strategy system**

Let's build JuiceBot! 🤖📈
