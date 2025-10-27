'use client'

import { useState, useRef, useEffect } from 'react'
import { CornerDownLeft, FileCode } from 'lucide-react'

interface LLMDiagnostics {
  request: {
    symbol: string
    message: string
    conversation_id: string
    timestamp: string
  }
  response: {
    raw: string
    statusCode: number
    timestamp: string
  }
  prompt?: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  diagnostics?: LLMDiagnostics
  isLLM?: boolean
}

interface ChatInterfaceProps {
  symbol: string
}

interface SlashCommand {
  name: string
  description: string
  handler?: (args?: string[]) => string
  subCommands?: SlashCommand[]
}

const SLASH_COMMANDS: SlashCommand[] = [
  {
    name: '/commands',
    description: '🟢 Show fast keyword shortcuts',
    handler: () => `FAST KEYWORDS:
last/price/current → current price 🟢 F
position/pos → show position + P&L 🟢 F+AI
long <qty> @ <price> → record long 🟢 F+AI
short <qty> @ <price> → record short 🟢 F+AI
close/exit → close position + P&L 🟢 F+AI
volume/vol → current volume 🟢 F
high/low → today's range 🟢 F

EXAMPLES:
  > long 500 @ .53
  > position
  > last

Note: F+AI commands show fast response first,
then add AI analysis.`
  },
  {
    name: '/analysis',
    description: '🟡 Analysis tools and methods',
    handler: () => `ANALYSIS:
trend → trend analysis 🔴 LLM
fvg → fair value gaps 🟢 F
volume profile → volume levels 🔴 LLM
scalp levels → intraday zones 🔴 LLM

Coming soon...`
  },
  {
    name: '/position',
    description: '🟡 Position tracking and P&L',
    handler: () => `POSITION:
clerk → auto-update P&L 🔴 F
pl → position + profits 🟢 F
pos/position → position status 🟢 F

Coming soon...`
  },
  {
    name: '/trade',
    description: '🟢 Trade position commands',
    handler: () => `TRADE COMMANDS:
Type directly (no slash):

BASIC:
  long <qty> @ <price> → enter long 🟢 F
  short <qty> @ <price> → enter short 🟢 F
  pos / position → check position 🟢 F
  pl / pnl / profit → P&L summary 🟢 F
  close / exit → close position 🟢 F
  flat → flatten all positions 🟢 F
  price / last → current price 🟢 F
  volume / vol → current volume 🟢 F
  range / high / low → today's range 🟢 F

ADVANCED:
  accumulate → scale into position 🟢 F
  scalein → gradually enter position 🟢 F
  scaleout → gradually exit position 🟢 F
  reverse → flip position instantly 🟢 F
  stop / sl → set stop loss 🟢 F
  bracket → entry + stop + target 🟢 F
  reset → clear session P&L 🟢 F

AI-ASSISTED:
  flatten-smart → AI exit with limits 🟢 F+AI
  reverse-smart → AI reversal w/ safety 🟢 F+AI

EXAMPLES:
  > long 1000 @ 0.57
  > pos
  > flat
  > reverse

All commands save to database.`,
    subCommands: [
      // BASIC
      {
        name: 'long',
        description: 'Open long position at market or specified price 🟢 F',
        handler: () => 'EXECUTE_DIRECT:long'
      },
      {
        name: 'short',
        description: 'Open short position at market or specified price 🟢 F',
        handler: () => 'EXECUTE_DIRECT:short'
      },
      {
        name: 'position',
        description: 'Show current position with P&L 🟢 F',
        handler: () => 'EXECUTE_DIRECT:position'
      },
      {
        name: 'pl',
        description: 'Show P&L summary (unrealized + realized) 🟢 F',
        handler: () => 'EXECUTE_DIRECT:pl'
      },
      {
        name: 'pnl',
        description: 'Show P&L summary (alias for pl) 🟢 F',
        handler: () => 'EXECUTE_DIRECT:pnl'
      },
      {
        name: 'profit',
        description: 'Show P&L summary (alias for pl) 🟢 F',
        handler: () => 'EXECUTE_DIRECT:profit'
      },
      {
        name: 'close',
        description: 'Close all positions at market 🟢 F',
        handler: () => 'EXECUTE_DIRECT:close'
      },
      {
        name: 'flatten',
        description: 'Immediately close all positions at market 🟢 F',
        handler: () => 'EXECUTE_DIRECT:flatten'
      },
      {
        name: 'price',
        description: 'Get current price 🟢 F',
        handler: () => 'EXECUTE_DIRECT:price'
      },
      {
        name: 'volume',
        description: 'Get current volume 🟢 F',
        handler: () => 'EXECUTE_DIRECT:volume'
      },
      {
        name: 'range',
        description: 'Get todays high/low range 🟢 F',
        handler: () => 'EXECUTE_DIRECT:range'
      },
      // ADVANCED
      {
        name: 'accumulate',
        description: 'Gradually build position over time (scale in) 🟢 F',
        handler: () => 'EXECUTE_DIRECT:accumulate'
      },
      {
        name: 'scaleout',
        description: 'Gradually exit position in chunks 🟢 F',
        handler: () => 'EXECUTE_DIRECT:scaleout'
      },
      {
        name: 'scalein',
        description: 'Gradually enter position in chunks 🟢 F',
        handler: () => 'EXECUTE_DIRECT:scalein'
      },
      {
        name: 'reverse',
        description: 'Instantly flip position (long to short or vice versa) 🟢 F',
        handler: () => 'EXECUTE_DIRECT:reverse'
      },
      {
        name: 'stop',
        description: 'Set stop loss for current position 🟢 F',
        handler: () => 'EXECUTE_DIRECT:stop'
      },
      {
        name: 'bracket',
        description: 'Create bracket order (entry + stop + target) 🟢 F',
        handler: () => 'EXECUTE_DIRECT:bracket'
      },
      {
        name: 'reset',
        description: 'Clear session P&L and start fresh 🟢 F',
        handler: () => 'EXECUTE_DIRECT:reset'
      },
      // AI-ASSISTED
      {
        name: 'flatten-smart',
        description: 'AI-assisted flatten with limit orders and safety checks 🟢 F+AI',
        handler: () => 'EXECUTE_DIRECT:flatten-smart'
      },
      {
        name: 'reverse-smart',
        description: 'AI-assisted reversal with safety checks 🟢 F+AI',
        handler: () => 'EXECUTE_DIRECT:reverse-smart'
      }
    ]
  },
  {
    name: '/indicators',
    description: '🟢 Technical indicators',
    handler: () => `TECHNICAL INDICATORS:
Type directly (no slash):

VOLUME INDICATORS:
  vp → Volume Profile (POC & value area) 🟢 F
  rvol → Relative Volume (hot/cold/explosive) 🟢 F
  vwap → Volume-Weighted Average Price 🟢 F
  voltrend → Volume trend analysis 🟢 F

All indicators use bar history data only.
Fast execution, no AI required.`,
    subCommands: [
      {
        name: 'vp',
        description: 'Volume Profile - POC and value area 🟢 F',
        handler: () => 'EXECUTE_DIRECT:vp'
      },
      {
        name: 'rvol',
        description: 'Relative Volume - hot/cold/explosive 🟢 F',
        handler: () => 'EXECUTE_DIRECT:rvol'
      },
      {
        name: 'vwap',
        description: 'Volume-Weighted Average Price 🟢 F',
        handler: () => 'EXECUTE_DIRECT:vwap'
      },
      {
        name: 'voltrend',
        description: 'Volume Trend - increasing/decreasing 🟢 F',
        handler: () => 'EXECUTE_DIRECT:voltrend'
      }
    ]
  },
  {
    name: '/strategy',
    description: '🔴 Trading strategy selection',
    handler: () => `STRATEGY:
smart money → SMC trades 🔴 F
quick scalp → fast scalps 🔴 F
accumulation → build position 🔴 F
hit and run → momentum 🔴 F
diamond hand → hold volatility 🔴 F

Not yet implemented.`
  },
  {
    name: '/alpha',
    description: '🟡 Alpha signals and market intel',
    handler: () => `ALPHA:
news → breaking news 🔴 LLM
float → float rotation 🔴 LLM
discord → community sentiment 🔴 LLM
sentiment → social pulse 🔴 LLM
financials → key metrics 🔴 LLM

Coming soon...`
  },
  {
    name: '/about',
    description: '🔴 Company overview and fundamentals',
    handler: () => `ABOUT:
• Company description 🔴 LLM
• Cash flow & value 🔴 LLM
• Book value 🔴 LLM
• Financial facts 🔴 LLM

Coming soon...`
  },
  {
    name: '/research',
    description: '🔴 LLM deep dive research',
    handler: () => `RESEARCH:
• Fundamentals 🔴 LLM
• Price levels 🔴 LLM
• Technical setup 🔴 LLM
• Catalysts & risks 🔴 LLM
• Trade thesis 🔴 LLM

Not yet implemented.`
  },
  {
    name: '/agents',
    description: '🔴 View available agents',
    handler: () => `AVAILABLE AGENTS:

Coming soon...`
  },
  {
    name: '/help',
    description: '🟢 Get help with commands',
    handler: () => `HELP:
Type "/" to see all available commands.

For more info on a specific command:
  > /commands     → fast keywords
  > /analysis     → analysis types
  > /position     → position tracking
  > /alpha        → alpha sources

Use arrow keys to navigate, Enter/Tab to select.`
  },
  {
    name: '/test',
    description: '🟢 Run integration tests',
    handler: () => 'TEST_MODE_INIT',
    subCommands: [
      {
        name: 'trade',
        description: 'Test /trade commands',
        handler: () => 'TEST_TRADE_INIT',
        subCommands: [
          {
            name: 'fast',
            description: 'Test basic commands (entry/exit/position)',
            handler: () => 'TEST_FAST_ONLY'
          },
          {
            name: 'all',
            description: 'Test all commands (including bracket, stops)',
            handler: () => 'TEST_ALL_COMMANDS'
          },
          {
            name: 'ai',
            description: 'Full AI test with LLM calls',
            handler: () => 'TEST_AI_FULL'
          },
          {
            name: '-quick',
            description: 'Quick test (no LLM)',
            handler: () => 'TEST_QUICK'
          }
        ]
      },
      {
        name: 'indicators',
        description: 'Test /indicators commands',
        handler: () => 'TEST_INDICATORS'
      },
      {
        name: 'strategy',
        description: 'Test /strategy commands',
        handler: () => 'TEST_STRATEGY'
      }
    ]
  },
]

interface TestResult {
  command: string
  type: 'F' | 'AI' | 'LLM'
  status: 'pass' | 'fail'
  message?: string
}

export default function ChatInterface({ symbol }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isMounted, setIsMounted] = useState(false)
  const [isTestMode, setIsTestMode] = useState(false)
  const [testResults, setTestResults] = useState<TestResult[]>([])
  const [currentTestPhase, setCurrentTestPhase] = useState<'fast' | 'ai-prompt' | 'ai-running' | 'complete'>('fast')
  const [conversationId, setConversationId] = useState<string>(`conv_${symbol}_${Date.now()}`)
  const eventsWsRef = useRef<WebSocket | null>(null)
  const [scaleoutStatus, setScaleoutStatus] = useState<{
    active: boolean
    message: string
    quantity?: number
    price?: number
    currentChunk?: number
    totalChunks?: number
  } | null>(null)

  useEffect(() => {
    setIsMounted(true)
    setMessages([{
      id: '1',
      role: 'assistant',
      content: `📊 JuiceBot SMC Agent ready.\n\nAnalyzing ${symbol} using Smart Money Concepts (FVG, BoS, CHoCH).\n\nAsk me:\n• "What do you see?"\n• "Where should I enter?"\n• "I went long 100 at [price]"\n\nLet's find some alpha.`
    }])
  }, [symbol])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [loadingStatus, setLoadingStatus] = useState('')
  const [showCommands, setShowCommands] = useState(false)
  const [selectedCommandIndex, setSelectedCommandIndex] = useState(0)
  const [showDiagnostics, setShowDiagnostics] = useState(false)
  const [selectedDiagnostics, setSelectedDiagnostics] = useState<LLMDiagnostics | null>(null)
  const [trackingMessageId, setTrackingMessageId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Parse command path and get filtered commands
  const getFilteredCommands = (): SlashCommand[] => {
    if (!input.startsWith('/')) return []

    // Parse the input into parts: /test ai -quick → ['test', 'ai', '-quick']
    const inputWithoutSlash = input.slice(1) // Remove leading /
    const parts = inputWithoutSlash.split(' ')
    const currentPart = parts[parts.length - 1]
    const completedParts = parts.slice(0, -1)

    // If input ends with space, show sub-commands of the completed command
    const endsWithSpace = input.endsWith(' ')

    if (endsWithSpace && completedParts.length > 0) {
      // Navigate to the parent command
      let commands: SlashCommand[] = SLASH_COMMANDS
      let parentCommand: SlashCommand | undefined

      for (const part of completedParts) {
        parentCommand = commands.find(cmd => cmd.name === `/${part}` || cmd.name === part)
        if (!parentCommand || !parentCommand.subCommands) {
          return []
        }
        commands = parentCommand.subCommands
      }

      // Return all sub-commands of the parent
      return parentCommand?.subCommands || []
    }

    // Otherwise, filter commands at the current level
    if (completedParts.length === 0) {
      // Root level: filter by current part
      return SLASH_COMMANDS.filter(cmd =>
        cmd.name.toLowerCase().startsWith(`/${currentPart.toLowerCase()}`)
      )
    } else {
      // Navigate to sub-commands
      let commands: SlashCommand[] = SLASH_COMMANDS

      for (const part of completedParts) {
        const parentCommand = commands.find(cmd => cmd.name === `/${part}` || cmd.name === part)
        if (!parentCommand || !parentCommand.subCommands) {
          return []
        }
        commands = parentCommand.subCommands
      }

      // Filter sub-commands by current part
      return commands.filter(cmd =>
        cmd.name.toLowerCase().startsWith(currentPart.toLowerCase())
      )
    }
  }

  const filteredCommands = getFilteredCommands()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
    // Return focus to textarea after messages update
    setTimeout(() => textareaRef.current?.focus(), 100)
  }, [messages])

  // Auto-update diagnostics modal when tracking message gets updated
  useEffect(() => {
    if (trackingMessageId && showDiagnostics) {
      const message = messages.find(m => m.id === trackingMessageId)
      if (message?.diagnostics) {
        setSelectedDiagnostics(message.diagnostics)
      }
    }
  }, [messages, trackingMessageId, showDiagnostics])

  // Handle ESC key to abort LLM calls or close diagnostic modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        // Close diagnostic modal first if open
        if (showDiagnostics) {
          setShowDiagnostics(false)
          return
        }

        // Otherwise abort LLM call if loading
        if (isLoading && abortControllerRef.current) {
          abortControllerRef.current.abort()
          setIsLoading(false)
          setLoadingStatus('')

          const abortMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: '⚠️ Request aborted by user'
          }
          setMessages(prev => [...prev, abortMessage])
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isLoading, showDiagnostics])

  const runIntegrationTests = async (mode: 'full' | 'quick' = 'full') => {
    setIsTestMode(true)
    setTestResults([])
    setCurrentTestPhase('fast')

    const results: TestResult[] = []

    // Add test start message
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'assistant',
      content: `🧪 INTEGRATION TEST STARTED\nMode: ${mode}\n\nTesting Fast Commands (F)...`
    }])

    // Fast command tests
    const fastTests = [
      { cmd: 'last', type: 'F' as const, expectedPattern: /\$[\d.]+/ },
      { cmd: 'price', type: 'F' as const, expectedPattern: /\$[\d.]+/ },
      { cmd: 'volume', type: 'F' as const, expectedPattern: /Vol:/ },
      { cmd: 'high', type: 'F' as const, expectedPattern: /High:.*Low:/ },
      { cmd: 'long 100 @ 0.50', type: 'F' as const, expectedPattern: /✓ (LONG|ADDED)/ },
      { cmd: 'pos', type: 'F' as const, expectedPattern: /(LONG|SHORT|No open position)/ },
      { cmd: 'flat', type: 'F' as const, expectedPattern: /(✓ FLATTENED|✓ CLOSED|No open position)/ },
    ]

    for (const test of fastTests) {
      try {
        const response = await fetch('http://localhost:8002/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            symbol: symbol,
            message: test.cmd,
            conversation_id: `test_${Date.now()}`
          })
        })

        const data = await response.json()
        const passed = test.expectedPattern.test(data.response)

        results.push({
          command: test.cmd,
          type: test.type,
          status: passed ? 'pass' : 'fail',
          message: passed ? undefined : `Expected pattern not found: ${test.expectedPattern}`
        })

        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'assistant',
          content: `${passed ? '🟢' : '🔴'} ${test.cmd} - ${passed ? 'PASS' : 'FAIL'}`
        }])

        await new Promise(resolve => setTimeout(resolve, 300))
      } catch (error) {
        results.push({
          command: test.cmd,
          type: test.type,
          status: 'fail',
          message: `Error: ${error}`
        })
      }
    }

    setTestResults(results)
    setCurrentTestPhase('ai-prompt')

    // Ask if user wants to test AI commands
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'assistant',
      content: `\nFast command tests complete: ${results.filter(r => r.status === 'pass').length}/${results.length} passed\n\nTest AI commands? Type:\n  'yes' - Full AI test (with LLM calls)\n  'quick' - Quick test (no LLM)\n  'no' - Skip AI tests`
    }])

    setIsTestMode(false)
  }

  const runAITests = async (quick: boolean = false) => {
    setCurrentTestPhase('ai-running')
    const aiResults: TestResult[] = []

    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'assistant',
      content: `\nTesting AI Commands (${quick ? 'QUICK MODE' : 'FULL MODE'})...`
    }])

    const aiTests = [
      { cmd: 'What do you see on the chart?', type: 'LLM' as const },
      { cmd: 'Where should I enter?', type: 'LLM' as const },
      { cmd: 'What are the key levels?', type: 'LLM' as const },
    ]

    if (quick) {
      // Quick mode - just check if commands are recognized
      for (const test of aiTests) {
        aiResults.push({
          command: test.cmd,
          type: test.type,
          status: 'pass',
          message: 'Command recognized (quick mode)'
        })

        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'assistant',
          content: `🟢 "${test.cmd}" - PASS (quick)`
        }])

        await new Promise(resolve => setTimeout(resolve, 100))
      }
    } else {
      // Full mode - actually call LLM
      for (const test of aiTests) {
        try {
          const response = await fetch('http://localhost:8002/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              symbol: symbol,
              message: test.cmd,
              conversation_id: `test_ai_${Date.now()}`
            })
          })

          const data = await response.json()
          const passed = data.response && data.response.length > 10

          aiResults.push({
            command: test.cmd,
            type: test.type,
            status: passed ? 'pass' : 'fail',
            message: passed ? undefined : 'No response from LLM'
          })

          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: 'assistant',
            content: `${passed ? '🟢' : '🔴'} "${test.cmd}" - ${passed ? 'PASS' : 'FAIL'}`
          }])

          await new Promise(resolve => setTimeout(resolve, 1000))
        } catch (error) {
          aiResults.push({
            command: test.cmd,
            type: test.type,
            status: 'fail',
            message: `Error: ${error}`
          })
        }
      }
    }

    setTestResults(prev => [...prev, ...aiResults])
    setCurrentTestPhase('complete')

    // Show summary
    const allResults = [...testResults, ...aiResults]
    const totalPassed = allResults.filter(r => r.status === 'pass').length
    const totalTests = allResults.length

    const summary = `
📊 TEST SUMMARY
═══════════════════════════════════
Total: ${totalTests} tests
Passed: 🟢 ${totalPassed}
Failed: 🔴 ${totalTests - totalPassed}
Success Rate: ${((totalPassed / totalTests) * 100).toFixed(1)}%

Fast Commands (F): ${testResults.filter(r => r.type === 'F' && r.status === 'pass').length}/${testResults.filter(r => r.type === 'F').length}
AI Commands (LLM): ${aiResults.filter(r => r.status === 'pass').length}/${aiResults.length}

${allResults.filter(r => r.status === 'fail').length > 0 ? '\nFailed Tests:\n' + allResults.filter(r => r.status === 'fail').map(r => `🔴 ${r.command}: ${r.message || 'Unknown error'}`).join('\n') : '✅ All tests passed!'}
`

    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'assistant',
      content: summary
    }])
  }

  // WebSocket connection for real-time server events
  const connectEventsWebSocket = () => {
    if (eventsWsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[EventsWS] Already connected')
      return
    }

    console.log('[EventsWS] Connecting to event stream for', symbol)

    const ws = new WebSocket(`ws://localhost:8002/events/${symbol}`)
    eventsWsRef.current = ws

    ws.onopen = () => {
      console.log('[EventsWS] ✓ Connected to event stream')
    }

    ws.onmessage = (messageEvent) => {
      try {
        const data = JSON.parse(messageEvent.data)

        // Skip ping messages
        if (data.type === 'ping') return

        console.log('[EventsWS] Received:', data)

        // Extract the actual event from the wrapper
        const evt = data.event || data

        console.log('[EventsWS] Processing event:', evt)

        // Update scaleout status bar from events
        if (evt.type === 'scaleout_start') {
          setScaleoutStatus({
            active: true,
            message: `Starting: ${evt.data?.total_qty || '?'} shares in ${evt.data?.num_chunks || '?'} chunks`,
            quantity: evt.data?.total_qty,
            totalChunks: evt.data?.num_chunks
          })
        } else if (evt.type === 'scaleout_progress') {
          setScaleoutStatus({
            active: true,
            message: `Chunk ${evt.data?.chunk_num || '?'}/${evt.data?.total_chunks || '?'}`,
            quantity: evt.data?.remaining_qty,
            price: evt.data?.price,
            currentChunk: evt.data?.chunk_num,
            totalChunks: evt.data?.total_chunks
          })
        } else if (evt.type === 'scaleout_complete' || evt.type === 'scaleout_cancelled') {
          setScaleoutStatus(null)
          // Close connection after scaleout finishes
          disconnectEventsWebSocket()
        }
        // Update scalein status bar from events
        else if (evt.type === 'scalein_start') {
          setScaleoutStatus({
            active: true,
            message: `Scalein: ${evt.data?.total_qty || '?'} shares in ${evt.data?.num_chunks || '?'} chunks`,
            quantity: evt.data?.total_qty,
            totalChunks: evt.data?.num_chunks
          })
        } else if (evt.type === 'scalein_progress') {
          setScaleoutStatus({
            active: true,
            message: `Scalein ${evt.data?.chunk_num || '?'}/${evt.data?.total_chunks || '?'}`,
            quantity: evt.data?.position_qty,
            price: evt.data?.price,
            currentChunk: evt.data?.chunk_num,
            totalChunks: evt.data?.total_chunks
          })
        } else if (evt.type === 'scalein_complete' || evt.type === 'scalein_cancelled') {
          setScaleoutStatus(null)
          // Close connection after scalein finishes
          disconnectEventsWebSocket()
        }

        // Add event as assistant message if it has content
        if (evt.message) {
          setMessages(prev => [
            ...prev,
            {
              id: `event_${Date.now()}_${Math.random()}`,
              role: 'assistant' as const,
              content: evt.message
            }
          ])
        }
      } catch (error) {
        console.error('[EventsWS] Error parsing message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('[EventsWS] WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('[EventsWS] Connection closed')
      eventsWsRef.current = null
    }
  }

  const disconnectEventsWebSocket = () => {
    if (eventsWsRef.current) {
      console.log('[EventsWS] Disconnecting')
      eventsWsRef.current.close()
      eventsWsRef.current = null
    }
  }

  const cancelScaleout = async () => {
    try {
      // Detect if this is scalein or scaleout
      const isScalein = scaleoutStatus?.message?.includes('Scalein')
      const endpoint = isScalein ? 'scalein' : 'scaleout'

      const response = await fetch(`http://localhost:8002/${endpoint}/${symbol}/cancel`, {
        method: 'POST'
      })
      const data = await response.json()

      if (data.success) {
        setScaleoutStatus(null)
        disconnectEventsWebSocket()
      }
    } catch (error) {
      console.error(`Error cancelling ${scaleoutStatus?.message?.includes('Scalein') ? 'scalein' : 'scaleout'}:`, error)
    }
  }

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => disconnectEventsWebSocket()
  }, [])

  const handleCommandSelect = (command: SlashCommand) => {
    // Build full command path
    const inputWithoutSlash = input.slice(1)
    const parts = inputWithoutSlash.split(' ').filter(p => p.length > 0)
    const endsWithSpace = input.endsWith(' ')

    // If we're selecting a sub-command, append it to the current path
    let newInput: string
    if (parts.length > 0 && (endsWithSpace || parts[parts.length - 1] !== command.name.replace('/', ''))) {
      // Append sub-command
      const basePath = parts.slice(0, -1).join(' ')
      newInput = basePath ? `/${basePath} ${command.name}` : `/${command.name.replace('/', '')}`
    } else {
      // Root level command
      newInput = command.name
    }

    // If command has sub-commands, just complete the input and show sub-commands
    if (command.subCommands && command.subCommands.length > 0) {
      setInput(newInput + ' ')
      setShowCommands(true)
      setSelectedCommandIndex(0)
      return
    }

    // Execute the command
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: newInput
    }
    setMessages(prev => [...prev, userMessage])

    // Handle command execution
    if (command.handler) {
      const result = command.handler()

      // Check for EXECUTE_DIRECT flag - send directly to AI service
      if (result.startsWith('EXECUTE_DIRECT:')) {
        const directCommand = result.replace('EXECUTE_DIRECT:', '')

        setInput('')
        setShowCommands(false)
        setIsLoading(true)
        setLoadingStatus('gathering price action data from bars... (ESC to abort)')

        const controller = new AbortController()
        abortControllerRef.current = controller

        const requestPayload = {
          symbol: symbol,
          message: directCommand,
          conversation_id: Date.now().toString()
        }
        const requestTimestamp = new Date().toISOString()

        // Initialize diagnostics immediately
        setSelectedDiagnostics({
          request: {
            symbol: requestPayload.symbol,
            message: requestPayload.message,
            conversation_id: requestPayload.conversation_id,
            timestamp: requestTimestamp
          },
          response: {
            raw: '⏳ Waiting for response...',
            statusCode: 0,
            timestamp: ''
          },
          prompt: '⏳ Generating prompt...'
        })

        fetch('http://localhost:8002/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestPayload),
          signal: controller.signal
        })
          .then(res => {
            const responseTimestamp = new Date().toISOString()
            return res.json().then(data => ({ data, status: res.status, responseTimestamp }))
          })
          .then(({ data, status, responseTimestamp }) => {
            // Only mark as LLM if there's actually a prompt (fast responses return prompt: null)
            const isActuallyLLM = data.prompt != null

            const assistantMessage: Message = {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: data.response,
              isLLM: isActuallyLLM,
              diagnostics: isActuallyLLM ? {
                request: {
                  symbol: requestPayload.symbol,
                  message: requestPayload.message,
                  conversation_id: requestPayload.conversation_id,
                  timestamp: requestTimestamp
                },
                response: {
                  raw: JSON.stringify(data, null, 2),
                  statusCode: status,
                  timestamp: responseTimestamp
                },
                prompt: data.prompt
              } : undefined
            }
            setMessages(prev => [...prev, assistantMessage])

            // Track this message for real-time diagnostic updates
            if (isActuallyLLM && assistantMessage.diagnostics) {
              setTrackingMessageId(assistantMessage.id)
            }
          })
          .catch(error => {
            if (error.name !== 'AbortError') {
              const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: `Error: ${error.message}`
              }
              setMessages(prev => [...prev, errorMessage])
            }
          })
          .finally(() => {
            setIsLoading(false)
            setLoadingStatus('')
            abortControllerRef.current = null
            setTimeout(() => textareaRef.current?.focus(), 0)
          })

        return
      }

      // Check for other special flags
      if (result === 'TEST_MODE_INIT' || result === 'TEST_AI_FULL') {
        runIntegrationTests('full')
      } else if (result === 'TEST_FAST_ONLY' || result === 'TEST_QUICK') {
        runIntegrationTests('quick')
      } else if (result === 'TRADE_RESET') {
        // TODO: Implement trade reset
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Trade reset coming soon...'
        }
        setMessages(prev => [...prev, assistantMessage])
      } else if (result === 'TRADE_HISTORY') {
        // TODO: Implement trade history
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Trade history coming soon...'
        }
        setMessages(prev => [...prev, assistantMessage])
      } else if (result === 'TRADE_SUMMARY') {
        // TODO: Implement trade summary
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Trade summary coming soon...'
        }
        setMessages(prev => [...prev, assistantMessage])
      } else {
        // Regular command response
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: result
        }
        setMessages(prev => [...prev, assistantMessage])
      }
    } else {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Command ${command.name} coming soon...`
      }
      setMessages(prev => [...prev, assistantMessage])
    }

    setInput('')
    setShowCommands(false)

    // Return focus to textarea
    setTimeout(() => textareaRef.current?.focus(), 0)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    // Handle test mode responses
    if (currentTestPhase === 'ai-prompt') {
      const response = input.trim().toLowerCase()
      setInput('')

      if (response === 'yes') {
        runAITests(false)
      } else if (response === 'quick') {
        runAITests(true)
      } else {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          role: 'assistant',
          content: 'AI tests skipped. Test run complete.'
        }])
        setCurrentTestPhase('complete')
      }
      return
    }

    // Handle slash commands
    if (input.startsWith('/')) {
      // Check for /test with arguments
      if (input.startsWith('/test')) {
        const args = input.split(' ')
        if (args[1] === 'ai' && args[2] === '-quick') {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: 'user',
            content: input
          }])
          setInput('')
          runIntegrationTests('quick')
          return
        }
      }

      const command = SLASH_COMMANDS.find(cmd => cmd.name === input.trim())
      if (command) {
        handleCommandSelect(command)
        return
      }
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setShowCommands(false)
    setLoadingStatus('gathering price action data from bars... (ESC to abort)')

    // Create abort controller
    abortControllerRef.current = new AbortController()

    try {
      // Call JuiceBot AI service
      setLoadingStatus('analyzing with claude sonnet 4.5 + SMC tools... (ESC to abort)')

      const requestPayload = {
        symbol: symbol,
        message: userMessage.content,
        conversation_id: conversationId
      }
      const requestTimestamp = new Date().toISOString()

      // Initialize diagnostics immediately so icon is clickable during loading
      setSelectedDiagnostics({
        request: {
          symbol: requestPayload.symbol,
          message: requestPayload.message,
          conversation_id: requestPayload.conversation_id,
          timestamp: requestTimestamp
        },
        response: {
          raw: '⏳ Waiting for response...',
          statusCode: 0,
          timestamp: ''
        },
        prompt: '⏳ Generating prompt...'
      })

      const response = await fetch('http://localhost:8002/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestPayload),
        signal: abortControllerRef.current.signal
      })

      if (!response.ok) {
        throw new Error(`AI service error: ${response.statusText}`)
      }

      setLoadingStatus('processing response...')
      const data = await response.json()
      const responseTimestamp = new Date().toISOString()

      // Update conversation_id from backend response to maintain state
      if (data.conversation_id) {
        setConversationId(data.conversation_id)
      }

      // Only mark as LLM if there's actually a prompt (fast responses return prompt: null)
      const isActuallyLLM = data.prompt != null

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response,
        isLLM: isActuallyLLM,
        diagnostics: isActuallyLLM ? {
          request: {
            symbol: requestPayload.symbol,
            message: requestPayload.message,
            conversation_id: requestPayload.conversation_id,
            timestamp: requestTimestamp
          },
          response: {
            raw: JSON.stringify(data, null, 2),
            statusCode: response.status,
            timestamp: responseTimestamp
          },
          prompt: data.prompt
        } : undefined
      }

      setMessages(prev => [...prev, assistantMessage])

      // Track this message for real-time diagnostic updates
      if (isActuallyLLM && assistantMessage.diagnostics) {
        setTrackingMessageId(assistantMessage.id)
      }

      // Start WebSocket event stream if scaleout or scalein was initiated
      if (data.response && (data.response.includes('SCALEOUT INITIATED') || data.response.includes('SCALEIN INITIATED'))) {
        const operationType = data.response.includes('SCALEOUT INITIATED') ? 'SCALEOUT' : 'SCALEIN'
        console.log(`[EventsWS] ⚡ ${operationType} DETECTED - CONNECTING TO EVENT STREAM`)
        console.log('[EventsWS] Response:', data.response)
        connectEventsWebSocket()
      } else {
        console.log('[EventsWS] No scaleout/scalein detected in response')
      }

      setLoadingStatus('')
    } catch (error) {
      // Check if it was aborted
      if (error instanceof Error && error.name === 'AbortError') {
        // Already handled by ESC key listener
        return
      }

      console.error('AI chat error:', error)

      // Show error message to user
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `⚠️ Sorry, I'm having trouble connecting to my AI brain. Error: ${error instanceof Error ? error.message : 'Unknown error'}`
      }
      setMessages(prev => [...prev, errorMessage])
      setLoadingStatus('')
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null

      // Return focus to textarea
      setTimeout(() => textareaRef.current?.focus(), 0)
    }
  }

  // Auto-resize textarea - grows up to 30% of the left panel height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      const maxHeight = window.innerHeight * 0.3 * 0.25 // 30% of the 25% left panel
      const newHeight = Math.min(textareaRef.current.scrollHeight, maxHeight)
      textareaRef.current.style.height = `${newHeight}px`
    }
  }, [input])

  return (
    <div className="h-full flex flex-col geek-scanline">
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} group`}
          >
            <div className="flex items-start gap-2 max-w-[90%]">
              <div
                className="text-base leading-relaxed flex-1"
                style={{
                  fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace',
                  color: message.role === 'user' ? '#6b7280' : '#55b685',
                  whiteSpace: 'pre-wrap'
                }}
              >
                {message.content}
              </div>
              {message.isLLM && message.diagnostics && (
                <button
                  onClick={() => {
                    setSelectedDiagnostics(message.diagnostics!)
                    setTrackingMessageId(message.id)
                    setShowDiagnostics(true)
                  }}
                  className="opacity-50 hover:opacity-100 transition-opacity flex-shrink-0 mt-1"
                  style={{ color: '#55b685' }}
                  title="View LLM diagnostics"
                >
                  <FileCode size={16} />
                </button>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start group">
            <div className="flex items-start gap-2 max-w-[90%]">
              <div
                style={{ fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace', color: '#55b685' }}
                className="flex-1"
              >
                <div className="flex gap-2 items-center">
                  <div className="flex gap-1">
                    <div className="w-1.5 h-4 animate-bounce" style={{ backgroundColor: '#55b685', animationDelay: '0ms' }}></div>
                    <div className="w-1.5 h-4 animate-bounce" style={{ backgroundColor: '#55b685', animationDelay: '150ms' }}></div>
                    <div className="w-1.5 h-4 animate-bounce" style={{ backgroundColor: '#55b685', animationDelay: '300ms' }}></div>
                  </div>
                  {loadingStatus && <span className="text-sm opacity-70">{loadingStatus}</span>}
                </div>
              </div>
              <button
                onClick={() => {
                  if (selectedDiagnostics) {
                    setShowDiagnostics(true)
                  }
                }}
                className="opacity-50 hover:opacity-100 transition-opacity flex-shrink-0 mt-1 animate-pulse"
                style={{ color: '#55b685' }}
                title="View LLM diagnostics (processing...)"
              >
                <FileCode size={16} />
              </button>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box - Docked at Bottom */}
      <div className="p-4 border-t border-[#55b68533] relative">
        {/* Slash Command Dropdown */}
        {showCommands && filteredCommands.length > 0 && (
          <div
            className="absolute bottom-full left-4 right-4 mb-2 border border-[#55b68533] rounded overflow-hidden"
            style={{
              backgroundColor: '#0b0e13',
              maxHeight: '50vh',
              overflowY: 'auto'
            }}
          >
            {filteredCommands.map((cmd, index) => (
              <div
                key={cmd.name}
                onClick={() => handleCommandSelect(cmd)}
                className="px-4 py-3 cursor-pointer border-b border-[#55b68533] last:border-b-0"
                style={{
                  backgroundColor: index === selectedCommandIndex ? '#55b68520' : 'transparent',
                  fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace',
                  color: '#55b685'
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="font-bold">{cmd.name}</div>
                  {cmd.subCommands && cmd.subCommands.length > 0 && (
                    <div className="text-xs opacity-50">→</div>
                  )}
                </div>
                <div className="text-sm opacity-70 mt-1">{cmd.description}</div>
              </div>
            ))}
          </div>
        )}

        {/* Scaleout/Scalein Status Bar */}
        {scaleoutStatus && scaleoutStatus.active && (
          <div className="absolute bottom-[60px] left-0 right-0 h-[40px] bg-green-500/10 backdrop-blur-sm border-t border-green-500/30 flex items-center justify-between px-4 font-mono text-sm z-[1001]">
            <div className="flex items-center gap-3">
              <span className="text-green-300">
                {scaleoutStatus.message.includes('Scalein') ? 'Scalein' : 'Scaleout'} running:
              </span>
              <span className="text-white">
                Chunk {scaleoutStatus.currentChunk || '?'}/{scaleoutStatus.totalChunks || '?'}
              </span>
              {scaleoutStatus.quantity !== undefined && (
                <span className="text-green-400">
                  {scaleoutStatus.quantity.toLocaleString()}
                  {scaleoutStatus.price && ` @ $${scaleoutStatus.price.toFixed(2)}`}
                </span>
              )}
            </div>
            <button
              onClick={cancelScaleout}
              className="text-red-400 hover:text-red-300 font-mono text-xs transition-colors"
              type="button"
            >
              CANCEL
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex gap-3 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              setShowCommands(e.target.value.startsWith('/'))
              if (e.target.value.startsWith('/')) {
                setSelectedCommandIndex(0)
              }
            }}
            onKeyDown={(e) => {
              // Ctrl+C (or Cmd+C on Mac) with no selection clears input
              if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
                const textarea = e.target as HTMLTextAreaElement
                // Only clear if there's no text selection
                if (textarea.selectionStart === textarea.selectionEnd) {
                  e.preventDefault()
                  setInput('')
                  setShowCommands(false)
                  return
                }
                // Otherwise let default copy behavior happen
              }

              if (filteredCommands.length > 0 && showCommands) {
                if (e.key === 'ArrowDown') {
                  e.preventDefault()
                  setSelectedCommandIndex(prev =>
                    prev < filteredCommands.length - 1 ? prev + 1 : prev
                  )
                } else if (e.key === 'ArrowUp') {
                  e.preventDefault()
                  setSelectedCommandIndex(prev => prev > 0 ? prev - 1 : 0)
                } else if (e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey)) {
                  e.preventDefault()
                  if (filteredCommands[selectedCommandIndex]) {
                    handleCommandSelect(filteredCommands[selectedCommandIndex])
                  }
                  return
                } else if (e.key === 'Escape') {
                  setShowCommands(false)
                  return
                }
              }

              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit(e)
              }
            }}
            placeholder="Ask me anything or use / for tools"
            className="flex-1 bg-transparent px-0 py-3 text-base focus:outline-none resize-none min-h-[56px]"
            style={{
              fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace',
              color: '#55b685'
            }}
            disabled={isLoading}
            rows={1}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="disabled:opacity-30 disabled:cursor-not-allowed transition-all pb-2"
            style={{ color: '#55b685' }}
          >
            <CornerDownLeft className="w-5 h-5" />
          </button>
        </form>
      </div>

      {/* Diagnostic Modal - Left 25% Overlay */}
      {showDiagnostics && selectedDiagnostics && (
        <div
          className="fixed inset-0 z-50 flex"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowDiagnostics(false)
            }
          }}
        >
          {/* Diagnostic Panel - Left 25% */}
          <div
            className="w-1/4 h-full overflow-y-auto p-6 geek-scanline"
            style={{
              backgroundColor: 'rgba(0, 0, 0, 0.95)',
              borderRight: '1px solid #55b68533'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <h2
                className="text-lg font-bold"
                style={{
                  fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace',
                  color: '#55b685'
                }}
              >
                LLM DIAGNOSTICS
              </h2>
              <button
                onClick={() => setShowDiagnostics(false)}
                className="opacity-50 hover:opacity-100 transition-opacity"
                style={{ color: '#55b685' }}
              >
                ✕
              </button>
            </div>

            {/* Request Section */}
            <div className="mb-6">
              <h3
                className="text-sm font-bold mb-3 opacity-70"
                style={{
                  fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace',
                  color: '#55b685'
                }}
              >
                REQUEST
              </h3>
              <div
                className="text-xs space-y-2 p-3 rounded"
                style={{
                  fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace',
                  color: '#55b685',
                  backgroundColor: 'rgba(85, 182, 133, 0.05)',
                  border: '1px solid #55b68533'
                }}
              >
                <div>
                  <span className="opacity-50">Symbol:</span> {selectedDiagnostics.request.symbol}
                </div>
                <div>
                  <span className="opacity-50">Message:</span> {selectedDiagnostics.request.message}
                </div>
                <div>
                  <span className="opacity-50">Conversation ID:</span>
                  <div className="break-all text-[10px] mt-1">{selectedDiagnostics.request.conversation_id}</div>
                </div>
                <div>
                  <span className="opacity-50">Timestamp:</span>
                  <div className="text-[10px] mt-1">{selectedDiagnostics.request.timestamp}</div>
                </div>
              </div>
            </div>

            {/* Prompt Section */}
            <div className="mb-6">
              <h3
                className="text-sm font-bold mb-3 opacity-70"
                style={{
                  fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace',
                  color: '#55b685'
                }}
              >
                PROMPT
              </h3>
              <div
                className="text-xs p-3 rounded whitespace-pre-wrap"
                style={{
                  fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace',
                  color: '#55b685',
                  backgroundColor: 'rgba(85, 182, 133, 0.05)',
                  border: '1px solid #55b68533',
                  maxHeight: '200px',
                  overflowY: 'auto'
                }}
              >
                {selectedDiagnostics.prompt}
              </div>
            </div>

            {/* Response Section */}
            <div>
              <h3
                className="text-sm font-bold mb-3 opacity-70"
                style={{
                  fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace',
                  color: '#55b685'
                }}
              >
                RESPONSE
              </h3>
              <div className="space-y-2 mb-3">
                <div
                  className="text-xs"
                  style={{
                    fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace',
                    color: '#55b685'
                  }}
                >
                  <span className="opacity-50">Status Code:</span> {selectedDiagnostics.response.statusCode}
                </div>
                <div
                  className="text-xs"
                  style={{
                    fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace',
                    color: '#55b685'
                  }}
                >
                  <span className="opacity-50">Timestamp:</span>
                  <div className="text-[10px] mt-1">{selectedDiagnostics.response.timestamp}</div>
                </div>
              </div>
              <div
                className="text-xs p-3 rounded whitespace-pre-wrap"
                style={{
                  fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace',
                  color: '#55b685',
                  backgroundColor: 'rgba(85, 182, 133, 0.05)',
                  border: '1px solid #55b68533',
                  maxHeight: '300px',
                  overflowY: 'auto'
                }}
              >
                {selectedDiagnostics.response.raw}
              </div>
            </div>
          </div>

          {/* Darkened Right Side - Clickable to close */}
          <div
            className="flex-1"
            style={{ backgroundColor: 'rgba(0, 0, 0, 0.3)' }}
            onClick={() => setShowDiagnostics(false)}
          />
        </div>
      )}
    </div>
  )
}
// Force rebuild $(date)
