# Voice Control System - Complete Documentation

## Overview

The Voice Control System enables hands-free trading through natural speech commands and authentic trader lingo voice feedback. This system uses a **wake word** ("Hey Juice") to activate commands and provides immediate execution with simultaneous multi-tasking support.

## Quick Start

### Basic Workflow
```
1. Click microphone button 🎤
2. Say: "Hey Juice, long one thousand at fifty-seven"
3. System executes: long 1000 @ 0.57
4. Voice responds: "Filled long one thousand at fifty-seven"
5. Purple line appears on chart
6. Continue trading (mic stays active for next command)
```

### Key Features
- ✅ **Wake word required**: All commands start with "Hey Juice"
- ✅ **Immediate execution**: No confirmation dialogs
- ✅ **Trader lingo responses**: Authentic trading floor voice
- ✅ **Simultaneous multi-tasking**: Speak while system responds
- ✅ **Always listening**: Mic stays active for continuous trading

## Technology Stack

### Speech-to-Text (STT)
**Web Speech API** (Browser Native)
- **Cost**: FREE
- **Latency**: Zero (local processing)
- **Accuracy**: Excellent for command recognition
- **Browser Support**: Chrome 25+, Edge, Safari 14.1+
- **Offline**: Yes (with language pack)
- **Why chosen**: Zero cost, lowest latency, sufficient accuracy

### Text-to-Speech (TTS)
**ElevenLabs Flash v2.5** (Cloud API)
- **Cost**: ~$5-10/month ($0.08 per minute)
- **Latency**: 75ms (ultra-low)
- **Quality**: Professional, natural trader voice
- **Languages**: 32 supported
- **Why chosen**: Best quality for trading confirmations, low latency
- **Fallback**: Web Speech API (browser native) if API fails

### Wake Word Detection
**Custom Pattern Matching** (Browser JavaScript)
- **Cost**: FREE
- **Method**: Continuous speech recognition with pattern matching
- **Wake phrase**: "Hey Juice"
- **Variants**: "hey juice", "hay juice", "a juice", "hey jews" (for robustness)
- **Processing**: Runs entirely in browser

## Voice Command Patterns

### Wake Word Requirement
All commands MUST start with "Hey Juice" (or variants).

**Wake word activates command mode for 5 seconds:**
```
"Hey Juice, [your command]"
```

**System flow:**
1. Mic active, listening for wake word
2. Wake word detected → Enter command mode
3. 5-second window to speak command
4. Command executed immediately
5. Return to listening for wake word

### Command Categories

#### Position Entry Commands

| You Say | Pattern | Executes | Voice Response |
|---------|---------|----------|----------------|
| "Hey Juice, long one thousand at fifty-seven" | `long 1000 @ 0.57` | Opens long position | "Filled long one thousand at fifty-seven" |
| "Hey Juice, short five hundred at sixty cents" | `short 500 @ 0.60` | Opens short position | "Filled short five hundred at sixty" |
| "Hey Juice, buy two thousand at point five three" | `long 2000 @ 0.53` | Opens long position | "Filled long two thousand at fifty-three cents" |
| "Hey Juice, sell one thousand at seventy-one cents" | `short 1000 @ 0.71` | Opens short position | "Filled short one thousand at seventy-one" |

**Natural Language Variants:**
- "at" = @ symbol
- "point five seven" = 0.57
- "fifty-seven cents" = 0.57
- "fifty-seven" = 0.57
- Numbers spelled out: "one thousand" = 1000

#### Position Management Commands

| You Say | Pattern | Executes | Voice Response |
|---------|---------|----------|----------------|
| "Hey Juice, what's my position" | `pos` | Show position | "Long one thousand at fifty-seven, up one hundred" |
| "Hey Juice, position" | `pos` | Show position | "Short five hundred at sixty, down twenty-five" |
| "Hey Juice, P and L" | `pos` | Show position | "Up one hundred on the day" |
| "Hey Juice, how am I doing" | `pos` | Show position | "Long one thousand, up fifty dollars" |
| "Hey Juice, close it" | `close` | Close position | "Out at sixty-two, up fifty" |
| "Hey Juice, get me out" | `close` | Close position | "Closed at sixty-one, plus one hundred" |
| "Hey Juice, exit" | `close` | Close position | "Out at fifty-nine, down twenty" |
| "Hey Juice, flatten" | `flat` | Close all positions | "All flat, plus one-fifty on the day" |
| "Hey Juice, flat" | `flat` | Close all positions | "Everything closed, up two hundred" |

#### Market Data Commands

| You Say | Pattern | Executes | Voice Response |
|---------|---------|----------|----------------|
| "Hey Juice, where's it trading" | `last` | Current price | "Sixty-one cents" |
| "Hey Juice, price" | `last` | Current price | "Fifty-seven" |
| "Hey Juice, last" | `last` | Current price | "Trading at sixty-two cents" |
| "Hey Juice, what's the range" | `high` | High/low | "High seventy, low fifty-five" |
| "Hey Juice, high and low" | `high` | High/low | "Range: seventy to fifty-five" |
| "Hey Juice, volume" | `volume` | Current volume | "Volume: fifty thousand shares" |

#### Adding to Position Commands

| You Say | Pattern | Executes | Voice Response |
|---------|---------|----------|----------------|
| "Hey Juice, add five hundred at fifty-five" | `long/short 500 @ 0.55` | Add to position | "Added five hundred, total fifteen hundred at fifty-six average" |
| "Hey Juice, more one thousand at sixty" | `long/short 1000 @ 0.60` | Add to position | "Bought one thousand more, two thousand at fifty-eight average" |

## Voice Response Scripts (Trader Lingo)

### Position Entry Confirmations

**Long Entry:**
```
Template: "Filled long [quantity] at [price]"

Examples:
- "Filled long one thousand at fifty-seven"
- "Filled long five hundred at sixty-two cents"
- "Bought one thousand at fifty-three"
```

**Short Entry:**
```
Template: "Filled short [quantity] at [price]"

Examples:
- "Filled short one thousand at seventy-one"
- "Filled short five hundred at sixty"
- "Sold one thousand at sixty-five"
```

### Position Status Responses

**Profitable Position:**
```
Template: "[side] [quantity] at [entry], up [pnl]"

Examples:
- "Long one thousand at fifty-seven, up one hundred"
- "Short five hundred at seventy, up fifty dollars"
- "Long two thousand at fifty-three, up two-fifty"
```

**Losing Position:**
```
Template: "[side] [quantity] at [entry], down [pnl]"

Examples:
- "Long one thousand at sixty, down twenty-five"
- "Short five hundred at fifty-five, down fifty"
- "Long two thousand at seventy, down one hundred"
```

**No Position:**
```
- "No position, flat"
- "You're flat"
- "Nothing on"
```

### Position Close Confirmations

**Profitable Close:**
```
Template: "Out at [exit_price], up [pnl]" OR "Closed at [exit_price], plus [pnl]"

Examples:
- "Out at sixty-two, up fifty"
- "Closed at fifty-five, plus one hundred"
- "Flat at sixty, up seventy-five"
```

**Losing Close:**
```
Template: "Out at [exit_price], down [pnl]" OR "Closed at [exit_price], minus [pnl]"

Examples:
- "Out at fifty-five, down twenty"
- "Closed at seventy, minus fifty"
- "Flat at sixty-five, down one hundred"
```

### Flatten Confirmations

```
Template: "All flat, [up/down] [total_pnl] on the day"

Examples:
- "All flat, plus one-fifty on the day"
- "Everything closed, up two hundred"
- "All positions flat, down fifty"
- "Flattened, plus three-twenty-five total"
```

### Market Data Responses

**Price:**
```
Template: "[price]" OR "Trading at [price]"

Examples:
- "Sixty-one cents"
- "Trading at fifty-seven"
- "Fifty-five"
```

**Range:**
```
Template: "High [high], low [low]"

Examples:
- "High seventy, low fifty-five"
- "Range: seventy-five to fifty"
- "High sixty-two, low fifty-seven"
```

**Volume:**
```
Template: "Volume: [volume] shares"

Examples:
- "Volume: fifty thousand shares"
- "Fifty-k on the tape"
- "One hundred thousand shares traded"
```

### Adding to Position Responses

**Same Side Addition:**
```
Template: "Added [quantity], total [new_total] at [avg_price] average"

Examples:
- "Added five hundred, total fifteen hundred at fifty-six average"
- "Bought five hundred more, one thousand at fifty-eight average"
- "Added one thousand, total three thousand at sixty average"
```

**Reversal (Opposite Side):**
```
Template: "Out at [exit_price], [up/down] [pnl]. Filled [new_side] [quantity] at [entry]"

Examples:
- "Out at fifty-seven, up one hundred. Filled long five hundred at fifty-seven"
- "Closed short at sixty, plus fifty. Filled long one thousand at sixty"
- "Out at sixty-five, down twenty-five. Filled short five hundred at sixty-five"
```

## Wake Word Implementation

### Detection Strategy

**Continuous Listening Mode:**
```
1. Mic button clicked → Start listening
2. Continuously process speech in chunks
3. Check each chunk for wake word pattern
4. Wake word detected → Enter command mode
5. Process next 5 seconds as command
6. Execute command immediately
7. Return to wake word listening
```

**Wake Word Patterns:**
```javascript
const WAKE_PATTERNS = [
  /\bhey\s+juice\b/i,
  /\bhay\s+juice\b/i,  // Common mishear
  /\ba\s+juice\b/i,     // Common mishear
  /\bhey\s+jews\b/i,    // Common mishear
  /\bjuice\b/i          // Fallback if "hey" missed
]
```

### Wake Word Robustness

**Handle common variations:**
- "hey juice" ✅
- "hay juice" ✅ (mishear)
- "a juice" ✅ (mishear)
- "hey jews" ✅ (mishear)
- "hey, juice" ✅ (with pause)
- "HEY JUICE" ✅ (loud)

**False positive prevention:**
- Require at least 2 words
- Minimum confidence threshold: 70%
- Cancel command mode if no command in 5 seconds

### Visual Feedback for Wake Word

**Mic Button States:**
1. **Idle** (gray 🎤): Not active
2. **Listening for wake word** (yellow 🟡): Active, waiting for "Hey trading"
3. **Command mode** (red 🔴): Wake word heard, recording command
4. **Processing** (spinner ⏳): Command recognized, executing
5. **Speaking** (speaker 🔊): Voice feedback playing

**Text Feedback:**
```
State: Listening for wake word
Display: "Say 'Hey Juice' to start..."

State: Command mode
Display: "Listening..." + realtime transcript

State: Command recognized
Display: "Executing: long 1000 @ 0.57"

State: Speaking response
Display: "Filled long one thousand at fifty-seven" (as it speaks)
```

## Simultaneous Multi-Tasking

### Non-Blocking Audio

**Allow speech during TTS playback:**
- Wake word detection runs continuously
- TTS plays in background
- User can speak new command while previous response plays
- New command interrupts current TTS (stops immediately)
- New command executes without waiting

**Implementation:**
```typescript
class VoiceControl {
  private isSpeaking = false
  private currentAudio: AudioPlayer | null = null

  async speak(text: string) {
    // Start TTS playback (non-blocking)
    this.currentAudio = await this.tts.speak(text)
    this.isSpeaking = true

    // Continue listening for wake word
    this.continuousListen()
  }

  onWakeWordDetected() {
    // Stop any playing TTS immediately
    if (this.currentAudio) {
      this.currentAudio.stop()
      this.isSpeaking = false
    }

    // Enter command mode
    this.enterCommandMode()
  }
}
```

### User Experience Flow

**Rapid-fire trading:**
```
[You click mic 🎤]
System: Listening for wake word...

[You] "Hey Juice, long one thousand at fifty-seven"
System: [Executes immediately] "Filled long one thousand—"

[You interrupt] "Hey Juice, add five hundred at fifty-five"
System: [Stops previous TTS, executes new command]
        "Added five hundred, total fifteen hundred—"

[You interrupt again] "Hey Juice, close it"
System: [Stops TTS, closes position]
        "Out at sixty, up seventy-five"
```

**No delay between commands** - immediate execution allows high-frequency trading.

## UI/UX Specifications

### Microphone Button

**Placement:**
```
┌─────────────────────────────────────┐
│   Chat Messages                     │
│   [User messages]                   │
│   [AI responses]                    │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ [📝 Type message...          ] [🎤] │ ← Mic button (32×32px)
│                                [↵]  │
└─────────────────────────────────────┘
```

**Button Design:**
- Size: 32×32px
- Position: Between input and Enter button
- Border-radius: 50% (circular)
- Background: Transparent when idle
- Hover: Subtle green glow (#55b68533)
- Active: Solid background with animation

**Button States:**

| State | Icon | Color | Animation | Description |
|-------|------|-------|-----------|-------------|
| Idle | 🎤 | #6b7280 (gray) | None | Not active |
| Listening for wake word | 🟡 | #fbbf24 (yellow) | Gentle pulse | Active, waiting |
| Command mode | 🔴 | #ff0000 (red) | Strong pulse | Recording command |
| Processing | ⏳ | #55b685 (green) | Spinner | Executing |
| Speaking | 🔊 | #55b685 (green) | Sound wave | TTS playing |
| Error | ⚠️ | #fbbf24 (yellow) | None | Error state |

### Visual Feedback Elements

**1. Wake Word Status Bar**
```
┌─────────────────────────────────────┐
│ 🟡 Listening for wake word...      │
└─────────────────────────────────────┘
```
- Position: Above chat input
- Height: 32px
- Background: Semi-transparent yellow
- Shows: Current listening state

**2. Realtime Transcript Display**
```
┌─────────────────────────────────────┐
│ 🔴 "long one thousand at fifty..."  │
└─────────────────────────────────────┘
```
- Position: Above chat input
- Height: Auto (multiline if needed)
- Background: Semi-transparent red (command mode)
- Shows: What's being heard in real-time
- Updates: Every 100ms

**3. Command Confirmation**
```
┌─────────────────────────────────────┐
│ ⏳ Executing: long 1000 @ 0.57     │
└─────────────────────────────────────┘
```
- Position: Above chat input
- Height: 32px
- Background: Semi-transparent green
- Shows: Parsed command before execution
- Duration: 500ms

**4. Voice Response Display**
```
┌─────────────────────────────────────┐
│ 🔊 "Filled long one thousand..."    │
└─────────────────────────────────────┘
```
- Position: Above chat input
- Height: Auto (multiline if needed)
- Background: Semi-transparent green
- Shows: TTS text as it speaks
- Synced: Text highlights as words are spoken

**5. Waveform Visualizer**
```
┌─────────────────────────────────────┐
│ 🔴 ▁▂▃▅▇▅▃▂▁▂▃▅▇▅▃▂▁              │
└─────────────────────────────────────┘
```
- Position: Inside status bar
- Height: 20px
- Style: Green bars (#55b685)
- Shows: Audio input levels
- Updates: Real-time (60fps)

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+M` or `Cmd+M` | Toggle mic on/off |
| `Space` (hold) | Push-to-talk (optional mode) |
| `Esc` | Cancel recording, stop TTS |

### Mobile Considerations

**Touch Behavior:**
- Tap to toggle mic on/off
- Long press for push-to-talk mode
- Visual feedback larger on mobile (48×48px)
- Haptic feedback on state changes

## Pattern Matching Logic

### Command Parser

```typescript
interface VoicePattern {
  wake: RegExp[]           // Wake word patterns
  command: RegExp          // Command pattern
  extractor: Function      // Extract parameters
  executor: Function       // Execute command
  response: Function       // Generate TTS response
}

const VOICE_PATTERNS: VoicePattern[] = [
  // Long Position
  {
    wake: [/\bhey\s+juice\b/i, /\bhay\s+juice\b/i, /\bhey\s+jews\b/i],
    command: /\b(long|buy)\s+(one\s+thousand|two\s+thousand|\d+)\s+(?:at\s+)?(?:point\s+)?(\d+)\s*(?:cents)?/i,
    extractor: (match) => ({
      side: 'long',
      quantity: parseQuantity(match[2]),
      price: parsePrice(match[3])
    }),
    executor: async (params) => {
      return await executePosition('long', params.quantity, params.price)
    },
    response: (params, result) => {
      return `Filled long ${spellQuantity(params.quantity)} at ${spellPrice(params.price)}`
    }
  },

  // Short Position
  {
    wake: [/\bhey\s+juice\b/i, /\bhay\s+juice\b/i, /\bhey\s+jews\b/i],
    command: /\b(short|sell)\s+(\d+|one\s+thousand|two\s+thousand)\s+(?:at\s+)?(?:point\s+)?(\d+)\s*(?:cents)?/i,
    extractor: (match) => ({
      side: 'short',
      quantity: parseQuantity(match[2]),
      price: parsePrice(match[3])
    }),
    executor: async (params) => {
      return await executePosition('short', params.quantity, params.price)
    },
    response: (params, result) => {
      return `Filled short ${spellQuantity(params.quantity)} at ${spellPrice(params.price)}`
    }
  },

  // Position Check
  {
    wake: [/\bhey\s+juice\b/i, /\bhay\s+juice\b/i, /\bhey\s+jews\b/i],
    command: /\b(position|pos|what'?s?\s+my\s+position|p\s*and\s*l|how\s+am\s+i)\b/i,
    extractor: () => ({}),
    executor: async () => {
      return await getPosition()
    },
    response: (params, result) => {
      if (!result.position) return "No position, flat"
      const side = result.position.side
      const qty = spellQuantity(result.position.quantity)
      const entry = spellPrice(result.position.entry_price)
      const pnl = spellPrice(Math.abs(result.pnl))
      const direction = result.pnl >= 0 ? 'up' : 'down'
      return `${side} ${qty} at ${entry}, ${direction} ${pnl}`
    }
  },

  // Close Position
  {
    wake: [/\bhey\s+juice\b/i, /\bhay\s+juice\b/i, /\bhey\s+jews\b/i],
    command: /\b(close|exit|get\s+me\s+out|out)\b/i,
    extractor: () => ({}),
    executor: async () => {
      return await closePosition()
    },
    response: (params, result) => {
      const exit = spellPrice(result.exit_price)
      const pnl = spellPrice(Math.abs(result.pnl))
      const direction = result.pnl >= 0 ? 'up' : 'down'
      return `Out at ${exit}, ${direction} ${pnl}`
    }
  },

  // Flatten
  {
    wake: [/\bhey\s+juice\b/i, /\bhay\s+juice\b/i, /\bhey\s+jews\b/i],
    command: /\b(flat|flatten)\b/i,
    extractor: () => ({}),
    executor: async () => {
      return await flattenAll()
    },
    response: (params, result) => {
      const pnl = spellPrice(Math.abs(result.total_pnl))
      const direction = result.total_pnl >= 0 ? 'plus' : 'minus'
      return `All flat, ${direction} ${pnl} on the day`
    }
  },

  // Price Check
  {
    wake: [/\bhey\s+juice\b/i, /\bhay\s+juice\b/i, /\bhey\s+jews\b/i],
    command: /\b(price|last|where'?s?\s+it\s+trading|trading\s+at)\b/i,
    extractor: () => ({}),
    executor: async () => {
      return await getCurrentPrice()
    },
    response: (params, result) => {
      return spellPrice(result.price)
    }
  }
]
```

### Number Parsing Functions

```typescript
function parseQuantity(text: string): number {
  // Handle spelled out numbers
  const spelledNumbers: Record<string, number> = {
    'one hundred': 100,
    'two hundred': 200,
    'five hundred': 500,
    'one thousand': 1000,
    'two thousand': 2000,
    'five thousand': 5000,
    'ten thousand': 10000
  }

  const lower = text.toLowerCase().trim()
  if (spelledNumbers[lower]) return spelledNumbers[lower]

  // Handle numeric
  return parseInt(text.replace(/[,\s]/g, ''))
}

function parsePrice(text: string): number {
  // Handle "point five seven" → 0.57
  // Handle "fifty-seven cents" → 0.57
  // Handle "57" → 0.57
  // Handle "0.57" → 0.57

  const lower = text.toLowerCase().trim()

  // Remove "cents"
  const cleaned = lower.replace(/\s*cents?/i, '')

  // Parse as float
  const num = parseFloat(cleaned)

  // If less than 10, assume decimal (57 → 0.57)
  if (num < 10 && num >= 1) {
    return num / 100
  }

  return num
}

function spellQuantity(qty: number): string {
  if (qty === 100) return "one hundred"
  if (qty === 500) return "five hundred"
  if (qty === 1000) return "one thousand"
  if (qty === 2000) return "two thousand"
  if (qty === 5000) return "five thousand"
  if (qty === 10000) return "ten thousand"

  // For other numbers, just say the number
  return qty.toString()
}

function spellPrice(price: number): string {
  // Always use decimal format for TTS
  // 0.57 → "fifty-seven cents"
  // 1.23 → "one twenty-three"
  // 12.45 → "twelve forty-five"

  if (price < 1) {
    const cents = Math.round(price * 100)
    return `${spellNumber(cents)} cents`
  }

  const dollars = Math.floor(price)
  const cents = Math.round((price - dollars) * 100)

  if (cents === 0) {
    return `${spellNumber(dollars)} dollars`
  }

  return `${spellNumber(dollars)} ${spellNumber(cents)}`
}

function spellNumber(n: number): string {
  // Convert numbers to words for natural speech
  const ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
  const teens = ['ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
  const tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']

  if (n < 10) return ones[n]
  if (n < 20) return teens[n - 10]
  if (n < 100) {
    const tensDigit = Math.floor(n / 10)
    const onesDigit = n % 10
    return tens[tensDigit] + (onesDigit ? '-' + ones[onesDigit] : '')
  }

  return n.toString()
}
```

## Implementation Architecture

### Component Structure

```
dashboard/
├── components/
│   ├── ChatInterface.tsx (modified)
│   │   └── Integrates VoiceControlButton
│   ├── VoiceControlButton.tsx (new)
│   │   ├── Mic button with state management
│   │   ├── Visual feedback components
│   │   └── Wake word status display
│   └── VoiceVisualizer.tsx (new)
│       └── Waveform animation
│
├── services/
│   ├── VoiceRecognitionService.ts (new)
│   │   ├── Web Speech API integration
│   │   ├── Wake word detection
│   │   ├── Continuous listening logic
│   │   └── Transcript processing
│   ├── TextToSpeechService.ts (new)
│   │   ├── ElevenLabs API integration
│   │   ├── Web Speech API fallback
│   │   ├── Non-blocking audio playback
│   │   └── Interrupt handling
│   ├── VoiceCommandParser.ts (new)
│   │   ├── Pattern matching
│   │   ├── Parameter extraction
│   │   ├── Number/price parsing
│   │   └── Response generation
│   └── TraderLingoGenerator.ts (new)
│       ├── TTS script templates
│       ├── Number-to-words conversion
│       └── Response formatting
```

### Service Implementations

#### VoiceRecognitionService.ts

```typescript
export class VoiceRecognitionService {
  private recognition: SpeechRecognition
  private isListening = false
  private inCommandMode = false
  private commandModeTimeout: NodeJS.Timeout | null = null

  constructor(
    private onWakeWord: () => void,
    private onCommand: (transcript: string) => void,
    private onTranscript: (text: string, isFinal: boolean) => void
  ) {
    this.recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)()
    this.setupRecognition()
  }

  private setupRecognition() {
    this.recognition.continuous = true
    this.recognition.interimResults = true
    this.recognition.lang = 'en-US'
    this.recognition.maxAlternatives = 3

    this.recognition.onresult = (event) => {
      const result = event.results[event.results.length - 1]
      const transcript = result[0].transcript.toLowerCase().trim()
      const isFinal = result.isFinal

      // Show realtime transcript
      this.onTranscript(transcript, isFinal)

      if (this.inCommandMode) {
        // In command mode, process as command
        if (isFinal) {
          this.processCommand(transcript)
        }
      } else {
        // Listening for wake word
        if (this.detectWakeWord(transcript)) {
          this.enterCommandMode()
        }
      }
    }

    this.recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error)
    }

    this.recognition.onend = () => {
      if (this.isListening) {
        // Restart if we're supposed to be listening
        this.recognition.start()
      }
    }
  }

  private detectWakeWord(transcript: string): boolean {
    const wakePatterns = [
      /\bhey\s+trading\b/i,
      /\bhay\s+trading\b/i,
      /\ba\s+trading\b/i,
      /\btrading\b/i
    ]

    return wakePatterns.some(pattern => pattern.test(transcript))
  }

  private enterCommandMode() {
    this.inCommandMode = true
    this.onWakeWord()

    // Exit command mode after 5 seconds if no command
    this.commandModeTimeout = setTimeout(() => {
      this.exitCommandMode()
    }, 5000)
  }

  private exitCommandMode() {
    this.inCommandMode = false
    if (this.commandModeTimeout) {
      clearTimeout(this.commandModeTimeout)
      this.commandModeTimeout = null
    }
  }

  private processCommand(transcript: string) {
    this.exitCommandMode()
    this.onCommand(transcript)
  }

  public start() {
    this.isListening = true
    this.recognition.start()
  }

  public stop() {
    this.isListening = false
    this.exitCommandMode()
    this.recognition.stop()
  }

  public forceCommandMode() {
    // For testing/debugging
    this.enterCommandMode()
  }
}
```

#### TextToSpeechService.ts

```typescript
export class TextToSpeechService {
  private elevenlabsApiKey: string
  private currentAudio: HTMLAudioElement | null = null
  private isSpeaking = false

  constructor(apiKey: string) {
    this.elevenlabsApiKey = apiKey
  }

  async speak(text: string, priority: 'high' | 'low' = 'high'): Promise<void> {
    // Stop any currently playing audio
    this.stop()

    try {
      if (priority === 'high' && this.elevenlabsApiKey) {
        await this.speakElevenLabs(text)
      } else {
        await this.speakNative(text)
      }
    } catch (error) {
      console.error('TTS error:', error)
      // Fallback to native
      await this.speakNative(text)
    }
  }

  private async speakElevenLabs(text: string): Promise<void> {
    const response = await fetch('https://api.elevenlabs.io/v1/text-to-speech/VOICE_ID/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'xi-api-key': this.elevenlabsApiKey
      },
      body: JSON.stringify({
        text,
        model_id: 'eleven_flash_v2_5',
        voice_settings: {
          stability: 0.5,
          similarity_boost: 0.75,
          style: 0.5,
          use_speaker_boost: true
        }
      })
    })

    if (!response.ok) throw new Error('ElevenLabs API failed')

    const audioBlob = await response.blob()
    const audioUrl = URL.createObjectURL(audioBlob)

    return new Promise((resolve, reject) => {
      this.currentAudio = new Audio(audioUrl)
      this.isSpeaking = true

      this.currentAudio.onended = () => {
        this.isSpeaking = false
        URL.revokeObjectURL(audioUrl)
        resolve()
      }

      this.currentAudio.onerror = reject
      this.currentAudio.play()
    })
  }

  private async speakNative(text: string): Promise<void> {
    return new Promise((resolve) => {
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.rate = 1.1  // Slightly faster for trading
      utterance.pitch = 1.0
      utterance.volume = 1.0

      utterance.onend = () => {
        this.isSpeaking = false
        resolve()
      }

      this.isSpeaking = true
      window.speechSynthesis.speak(utterance)
    })
  }

  public stop() {
    if (this.currentAudio) {
      this.currentAudio.pause()
      this.currentAudio = null
    }

    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel()
    }

    this.isSpeaking = false
  }

  public get speaking(): boolean {
    return this.isSpeaking
  }
}
```

## Cost Estimates

### Monthly Costs (Active Trading)

#### Hybrid Approach (Recommended)
**Assumptions:**
- 4 hours active trading per day
- 20 trading days per month
- ~50 voice commands per day
- ~30 TTS responses per day

**Costs:**
- Web Speech API (STT): $0/month (FREE)
- ElevenLabs (TTS): ~$5-10/month
  - 30 responses/day × 20 days = 600 responses
  - Avg 3 seconds per response = 1,800 seconds = 30 minutes
  - 30 minutes × $0.08/minute = $2.40/month
  - Add buffer for errors/retries: $5-10/month

**Total: $5-10/month**

#### Full Cloud Approach
**Costs:**
- AssemblyAI (STT): $10-20/month
  - 4 hours × 20 days = 80 hours
  - 80 hours × $0.15/hour = $12/month
- ElevenLabs (TTS): $5-10/month

**Total: $15-30/month**

#### Open Source Approach
**Costs:**
- Everything: $0/month
- One-time setup: 4-6 hours
- Ongoing maintenance: ~1 hour/month

**Total: $0/month + time investment**

## Testing Procedures

### Unit Testing Voice Commands

```typescript
describe('VoiceCommandParser', () => {
  it('should parse long position command', () => {
    const transcript = "hey juice, long one thousand at fifty-seven"
    const result = parser.parse(transcript)
    expect(result).toEqual({
      command: 'long',
      quantity: 1000,
      price: 0.57
    })
  })

  it('should parse short position command', () => {
    const transcript = "hey juice, short five hundred at sixty cents"
    const result = parser.parse(transcript)
    expect(result).toEqual({
      command: 'short',
      quantity: 500,
      price: 0.60
    })
  })

  it('should parse position check', () => {
    const transcript = "hey juice, what's my position"
    const result = parser.parse(transcript)
    expect(result.command).toBe('pos')
  })
})
```

### Integration Testing

**Test Wake Word Detection:**
```
1. Click mic button
2. Say: "Hey Juice"
3. Verify: Button turns red, "Command mode" displayed
4. Wait 5 seconds
5. Verify: Returns to yellow, "Listening for wake word"
```

**Test Immediate Execution:**
```
1. Click mic button
2. Say: "Hey Juice, long one thousand at fifty-seven"
3. Verify: Command executes within 500ms
4. Verify: Voice response plays
5. Verify: Purple line appears on chart
```

**Test Simultaneous Multi-tasking:**
```
1. Click mic button
2. Say: "Hey Juice, long one thousand at fifty-seven"
3. While TTS is playing, say: "Hey Juice, position"
4. Verify: First TTS stops immediately
5. Verify: Second command executes
6. Verify: Second TTS plays
```

**Test Interrupt Handling:**
```
1. Click mic button
2. Say: "Hey Juice, long one thousand at fifty-seven"
3. While TTS is playing, click Esc
4. Verify: TTS stops immediately
5. Verify: System returns to wake word listening
```

## Troubleshooting

### Common Issues

#### Wake Word Not Detected
**Symptoms**: Mic is active but commands not recognized

**Checks**:
1. Verify mic permissions granted in browser
2. Check console for speech recognition errors
3. Test with simple phrase: "Hey Juice, price"
4. Ensure speaking clearly and at normal volume

**Solution**: Lower wake word confidence threshold

#### Commands Misheard
**Symptoms**: Wrong command executed

**Checks**:
1. Check realtime transcript for accuracy
2. Verify pattern matching logic
3. Test with simpler phrases

**Solution**: Add more pattern variations, improve noise cancellation

#### TTS Not Playing
**Symptoms**: Commands execute but no voice response

**Checks**:
1. Verify ElevenLabs API key configured
2. Check browser console for API errors
3. Test with native TTS fallback

**Solution**: Use Web Speech API as fallback

#### High Latency
**Symptoms**: Delay between command and response

**Checks**:
1. Check network latency to ElevenLabs
2. Verify using Flash v2.5 model (not Multilingual)
3. Check browser performance

**Solution**: Switch to native TTS for lower latency

## Privacy & Security

### Data Handling

**Speech-to-Text (Web Speech API):**
- Audio sent to Google servers for processing
- No local storage of audio
- Transcripts not stored by browser

**Text-to-Speech (ElevenLabs):**
- Text sent to ElevenLabs API
- No audio storage on client
- API calls over HTTPS

**Local Storage:**
- No voice data stored locally
- Only stores: API keys (encrypted), user preferences

### Compliance

**GDPR Considerations:**
- Voice data processed by third parties (Google, ElevenLabs)
- Users should be informed via privacy policy
- Option to use fully local (Vosk) for compliance

**Best Practices:**
- Don't store audio recordings
- Use HTTPS for all API calls
- Encrypt API keys in local storage
- Provide opt-out mechanism

## Future Enhancements

### Planned Features

1. **Custom Voice Training**
   - Train on user's voice for better accuracy
   - Personalized wake word

2. **Multi-Language Support**
   - Spanish, Chinese, etc.
   - Trader lingo in each language

3. **Voice Macros**
   - "Hey trading, strategy one" → Executes predefined strategy
   - Custom voice shortcuts

4. **Voice Alerts**
   - System speaks alerts: "Stop loss hit at fifty-five"
   - Configurable alert phrases

5. **Offline Mode**
   - Download Vosk models for full offline
   - Local TTS with Kokoro

6. **Voice Biometrics**
   - Voice authentication
   - Prevent unauthorized trading

7. **Multi-Speaker Support**
   - Recognize different traders
   - Separate accounts per voice

## Summary

The Voice Control System provides:
- ✅ Wake word activation ("Hey Juice")
- ✅ Immediate command execution
- ✅ Authentic trader lingo responses
- ✅ Simultaneous multi-tasking
- ✅ Low latency (75ms TTS)
- ✅ Hands-free trading workflow
- ✅ Cost-effective (~$5-10/month)
- ✅ Browser-based (no backend changes)

Ready to implement with your exact specifications!
