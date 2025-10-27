# System Flow Analysis: "What Do You See?"

## Complete Journey from User Question to AI Response

### Scenario: 1000 bars loaded, user asks "what do you see?"

---

## Phase 1: Data Collection (Historical Simulation)

### Step 1: Historical Bars Loaded
```
Database (historical_bars table)
  ↓
[5,352 bars for BYND stored]
  ↓
Historical WebSocket Server (historical_websocket_server.py)
  ↓
Fetches ALL bars via pagination:
  - Request 1: bars 0-999 (1000 bars)
  - Request 2: bars 1000-1999 (1000 bars)
  - Request 3: bars 2000-2999 (1000 bars)
  - Request 4: bars 3000-3999 (1000 bars)
  - Request 5: bars 4000-4999 (1000 bars)
  - Request 6: bars 5000-5351 (352 bars)
  ↓
Total: 5,352 bars loaded into memory
```

### Step 2: Chart Display
```
TradingView Chart (StockChart.tsx)
  ↓
Fetches from API: /bars/BYND/historical?limit=10000
  ↓
API returns all 5,352 bars (paginated internally)
  ↓
Chart displays all 5,352 bars visually
```

### Step 3: Live Replay Simulation
```
Historical WebSocket Server
  ↓
Begins replaying bars one-by-one at configured speed (60x, 300x, etc.)
  ↓
WebSocket connection to frontend/AI service
  ↓
Emits bar data: { timestamp, open, high, low, close, volume, meta: { bar_index, total_bars } }
  ↓
Current position: "Bar 1000 / 5352"
```

---

## Phase 2: AI Service Bar Storage

### Step 4: Classifier Receives Bars
```
AI Service (main.py)
  ↓
WebSocket endpoint: /bars/stream receives bar data
  ↓
Calls: classifiers[symbol].update_market_data(symbol, bar)
  ↓
TradingClassifier (fast_classifier_v2.py:40-50)
  ↓
Updates internal buffer:
  - self.bar_history.append(bar)
  - if len(self.bar_history) > 100: self.bar_history.pop(0)
  ↓
⚠️ ONLY KEEPS LAST 100 BARS IN MEMORY
```

**Current State After 1000 Bars Replayed:**
```python
classifier.bar_history = [
    # Bar 901, Bar 902, Bar 903, ... Bar 1000
    # Total: 100 bars (not 1000!)
]
```

---

## Phase 3: User Asks "What Do You See?"

### Step 5: Message Routing
```
User types: "what do you see?"
  ↓
Frontend (ChatInterface.tsx) sends to API
  ↓
POST /chat with { symbol: "BYND", message: "what do you see?", conversation_id: "..." }
  ↓
AI Service (main.py:280-349)
```

### Step 6: Fast Path Check (Skipped)
```python
# Check if message matches fast command pattern
classifier = classifiers.get("BYND")
fast_response = await classifier.classify(message, symbol)
# "what do you see?" doesn't match any fast patterns (like "buy", "sell", "pos")
# Returns: None
```

### Step 7: LLM Path (Main Flow)
```python
# Line 328-339: Slow path - use LLM
agent = SMCAgent()  # Or reuse existing conversation agent

# ⚠️ CRITICAL: Gets bar history from classifier
bar_history = classifier.bar_history  # ← ONLY 100 bars!

# Pass to agent
response, prompt = await agent.analyze(symbol, message, bar_history)
```

**What bar_history contains at this point:**
```python
bar_history = [
    {"timestamp": "...", "open": 0.5680, "high": 0.5720, "low": 0.5660, "close": 0.5690, "volume": 1200},
    {"timestamp": "...", "open": 0.5690, "high": 0.5710, "low": 0.5670, "close": 0.5700, "volume": 980},
    # ... 98 more bars ...
]
# Total: 100 bars (bars 901-1000 from the simulation)
```

---

## Phase 4: LLM Analysis

### Step 8: Agent Initialization
```python
SMCAgent.analyze(symbol="BYND", message="what do you see?", bar_history=[...100 bars...])
  ↓
# Store bar_history in agent for tool access
self.bar_history = bar_history  # 100 bars
  ↓
# Get system prompt (instructions/smc_strategy.md)
system_prompt = self.get_system_prompt(symbol)
```

### Step 9: LLM Receives Prompt
```
Claude 3.5 Sonnet receives:

SYSTEM PROMPT:
  - "You are an SMC trading expert"
  - "Available tools: detect_fvg, detect_bos, detect_choch, detect_pattern_confluence"
  - "ALWAYS show confidence scores and data quality"
  - "Response format: 📊 [SYMBOL] @ $X.XX | Data: [N] bars ([quality_score]/10)"

USER MESSAGE:
  "what do you see?"

AVAILABLE TOOLS:
  - detect_fvg(symbol, lookback=50)
  - detect_bos(symbol, lookback=50)
  - detect_choch(symbol, lookback=50)
  - detect_pattern_confluence(symbol, lookback=50)
```

### Step 10: LLM Decision
```
Claude thinks:
  "User wants pattern analysis. I should:
   1. Call detect_fvg() to find Fair Value Gaps
   2. Call detect_bos() to find Break of Structure
   3. Call detect_choch() to find Change of Character
   4. Call detect_pattern_confluence() if patterns exist
   5. Format response with confidence scores"

Claude decides to call tools (stop_reason: "tool_use"):
  - Tool 1: detect_fvg("BYND", lookback=50)
  - Tool 2: detect_bos("BYND", lookback=50)
  - Tool 3: detect_choch("BYND", lookback=50)
```

---

## Phase 5: Tool Execution (Pattern Detection)

### Step 11: Execute detect_fvg
```python
# smc_agent.py:363-367
tool_name = "detect_fvg"
tool_input = {"symbol": "BYND", "lookback": 50}

result = await detect_fvg(
    symbol="BYND",
    bar_history=[...100 bars...],  # ← From classifier
    lookback=50
)
```

### Step 12: FVG Detection Algorithm
```python
# tools/market_data.py:detect_fvg()

bars = bar_history[-50:]  # Take last 50 of the 100 bars
total_bars = len(bar_history)  # 100

# Loop through bars looking for 3-bar gaps
for i in range(len(bars) - 2):
    bar1, bar2, bar3 = bars[i], bars[i+1], bars[i+2]

    # Bullish FVG: bar1.high < bar3.low (gap up)
    if float(bar1["high"]) < float(bar3["low"]):
        gap_size = float(bar3["low"]) - float(bar1["high"])
        gap_pct = (gap_size / current_price) * 100

        # Calculate confidence score (1-10)
        confidence = 10.0

        # Deductions:
        if gap_pct < 0.2:
            confidence -= 3.0  # Too small
        if bars_ago > 40:
            confidence -= 2.0  # Too old
        if volume < avg_volume * 0.8:
            confidence -= 1.5  # Weak volume
        if distance_from_price > 5%:
            confidence -= 2.0  # Too far away

        fvg["confidence"] = max(1.0, confidence)

        if not fvg["filled"]:
            fvgs.append(fvg)

# Calculate data quality
quality_score = min(10.0, total_bars / 20)  # 100 / 20 = 5.0

return {
    "patterns": [
        {
            "type": "bullish",
            "top": 0.5720,
            "bottom": 0.5670,
            "confidence": 7.5,
            "gap_pct": 0.35,
            "bars_ago": 12
        },
        {
            "type": "bullish",
            "top": 0.5680,
            "bottom": 0.5640,
            "confidence": 5.2,
            "gap_pct": 0.28,
            "bars_ago": 35
        }
    ],
    "data_quality": {
        "bars_analyzed": 50,
        "total_bars_available": 100,
        "time_coverage_mins": 100,
        "quality_score": 5.0  # ← 100 bars = moderate quality
    },
    "confidence": 6.25  # Average of quality + best pattern
}
```

### Step 13: Execute detect_bos
```python
# Same process, analyzes 100 bars for Break of Structure

result = await detect_bos(
    symbol="BYND",
    bar_history=[...100 bars...],
    lookback=50
)

# Returns similar structure:
{
    "patterns": [
        {
            "type": "bullish",
            "break_level": 0.5750,
            "confidence": 6.8,
            "volume_ratio": 1.4,
            "bars_ago": 18
        }
    ],
    "data_quality": {"quality_score": 5.0},
    "confidence": 5.9
}
```

### Step 14: Execute detect_choch
```python
# Same process, analyzes for Change of Character

result = await detect_choch(
    symbol="BYND",
    bar_history=[...100 bars...],
    lookback=50
)

# Returns:
{
    "patterns": [],  # None found
    "data_quality": {"quality_score": 5.0},
    "confidence": 5.0
}
```

---

## Phase 6: LLM Synthesis

### Step 15: LLM Receives Tool Results
```
Claude receives:

FVG Result: {patterns: 2 found, quality_score: 5.0, confidence: 6.25}
BoS Result: {patterns: 1 found, quality_score: 5.0, confidence: 5.9}
CHoCH Result: {patterns: 0 found, quality_score: 5.0, confidence: 5.0}
```

### Step 16: LLM Formats Response
```
Claude synthesizes based on:
  - System prompt instructions (show scores, quality warnings)
  - Tool results (patterns with confidence scores)
  - Data quality metrics (5.0/10 = moderate)

Generates response:
```

**LLM Output:**
```
📊 BYND @ $0.5690 | Data: 100 bars (5.0/10 quality)

🎯 Bullish FVG at $0.5670-$0.5720 (12 bars ago)
   Confidence: 7.5/10 | Gap: 0.35% | Volume: ✓

📈 Bullish BoS at $0.5750 (18 bars ago)
   Confidence: 6.8/10 | Volume: Strong (1.4x)

⚠️ Moderate data quality - patterns visible but limited history

💡 Possible entry: $0.5670 (FVG retest) | Stop: $0.5640 | Target: $0.5800
   Win Probability: 60-65%
```

---

## Phase 7: Response Delivery

### Step 17: Return to User
```
AI Service (main.py)
  ↓
Returns ChatResponse with formatted text
  ↓
Frontend (ChatInterface.tsx)
  ↓
Displays in chat interface
  ↓
User sees response with confidence scores!
```

---

## Key Observations

### ⚠️ The Bottleneck: Only 100 Bars Available

Even though:
- ✅ Database has 5,352 bars
- ✅ Chart displays all 5,352 bars
- ✅ Simulation is at bar 1000/5352
- ❌ **AI only has the last 100 bars in memory**

**Why?**
```python
# fast_classifier_v2.py:44-47
self.bar_history.append(bar)
if len(self.bar_history) > 100:
    self.bar_history.pop(0)  # ← Discards old bars!
```

### Impact on Pattern Detection

With only 100 bars:
- **FVG detection**: Analyzes last 50 bars (of 100 available)
- **BoS detection**: Analyzes last 50 bars (of 100 available)
- **CHoCH detection**: Analyzes last 50 bars (of 100 available)
- **Data quality score**: 5.0/10 (100 bars / 20 = 5.0)

Patterns that occurred **more than 100 bars ago** are **invisible** to the AI, even though:
- They're visible on the chart
- They're in the database
- The simulation has replayed them

### Confidence Score Impact

```python
# With 100 bars:
quality_score = 100 / 20 = 5.0/10  # "Moderate data"

# If AI had all 1000 bars:
quality_score = 1000 / 20 = 10/10  # "Excellent data" (capped at 10)

# Pattern confidence would be SAME (based on pattern characteristics)
# Overall confidence = (quality_score + pattern_confidence) / 2
# So better data quality = higher overall confidence!
```

---

## Performance Characteristics

### Time Complexity
- **Pattern detection**: O(n) where n = lookback (typically 50)
- **Per tool call**: ~0.01-0.05 seconds
- **Total LLM call**: ~2-5 seconds (includes tool execution + LLM thinking)

### Memory Usage
- **Classifier buffer**: 100 bars × ~100 bytes = ~10 KB per symbol
- **LLM context**: System prompt + conversation history (typically < 10K tokens)
- **Tool results**: JSON objects (~1-5 KB each)

### Scalability
- **Current**: Can handle dozens of concurrent symbols
- **Bottleneck**: LLM API calls (rate limited by Anthropic)
- **Not a bottleneck**: Pattern detection (very fast Python computations)

---

## Potential Improvements

### 1. Increase Classifier Buffer
```python
# Instead of 100 bars, store more:
if len(self.bar_history) > 500:  # or 1000
    self.bar_history.pop(0)
```

**Trade-off**: More memory usage, but better pattern detection

### 2. Smart Bar Storage
```python
# Keep all bars, but summarize old ones:
- Last 100 bars: Full resolution (1-min)
- Bars 100-500: 5-min aggregated
- Bars 500+: 15-min aggregated
```

**Trade-off**: Complexity, but better long-term pattern visibility

### 3. On-Demand Historical Fetch
```python
# When LLM needs more history, fetch from database
if lookback > len(bar_history):
    additional_bars = await fetch_from_database(symbol, lookback)
    bar_history = additional_bars + bar_history
```

**Trade-off**: Slower (database query), but accurate

---

## Summary

**What Actually Happens:**
1. User has 1000 bars replayed (visible on chart)
2. AI only has last **100 bars** in memory
3. LLM calls pattern detection tools with those 100 bars
4. Tools analyze last **50 bars** (lookback parameter)
5. Patterns are detected with confidence scores
6. Data quality score: **5.0/10** (moderate, due to only 100 bars)
7. LLM formats response with scores and warnings
8. User sees analysis with realistic confidence levels

**The System Is Working As Designed:**
- ✅ Fast (no database queries during analysis)
- ✅ Memory efficient (only 100 bars per symbol)
- ✅ Confidence scores reflect limited data
- ✅ Warns user about data quality
- ⚠️ Can't see patterns > 100 bars ago (design trade-off)
