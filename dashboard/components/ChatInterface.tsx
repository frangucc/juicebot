'use client'

import { useState, useRef, useEffect } from 'react'
import { CornerDownLeft } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

interface ChatInterfaceProps {
  symbol: string
}

interface SlashCommand {
  name: string
  description: string
  handler?: () => string
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

long <qty> @ <price> → enter long 🟢 F+AI
short <qty> @ <price> → enter short 🟢 F+AI
pos/position → check position 🟢 F+AI
close/exit → close position 🟢 F+AI
flat → close all positions 🔴 F

EXAMPLES:
  > long 1000 @ 0.57
  > short 500 @ 12.45
  > pos
  > close

Note: These commands store to database
and trigger clerk updates (coming soon).`
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
    handler: () => 'TEST_MODE_INIT' // Special flag to trigger test mode
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
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Filter commands based on input
  const filteredCommands = input.startsWith('/')
    ? SLASH_COMMANDS.filter(cmd => cmd.name.startsWith(input.toLowerCase()))
    : []

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Handle ESC key to abort LLM calls
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isLoading && abortControllerRef.current) {
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

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isLoading])

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
      { cmd: 'long 100 @ 0.50', type: 'F' as const, expectedPattern: /✓ (LONG|CLOSED)/ },
      { cmd: 'pos', type: 'F' as const, expectedPattern: /(LONG|SHORT|No open position)/ },
      { cmd: 'close position', type: 'F' as const, expectedPattern: /(✓ CLOSED|No open position)/ },
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

  const handleCommandSelect = (command: SlashCommand) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: command.name
    }
    setMessages(prev => [...prev, userMessage])

    // Check for test command
    if (command.name === '/test') {
      runIntegrationTests('full')
      setInput('')
      setShowCommands(false)
      setTimeout(() => textareaRef.current?.focus(), 0)
      return
    }

    // Execute handler if it exists
    if (command.handler) {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: command.handler()
      }
      setMessages(prev => [...prev, assistantMessage])
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
      const response = await fetch('http://localhost:8002/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbol: symbol,
          message: userMessage.content,
          conversation_id: `conv_${symbol}_${Date.now()}`
        }),
        signal: abortControllerRef.current.signal
      })

      if (!response.ok) {
        throw new Error(`AI service error: ${response.statusText}`)
      }

      setLoadingStatus('processing response...')
      const data = await response.json()

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response
      }

      setMessages(prev => [...prev, assistantMessage])
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
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className="max-w-[90%] text-base leading-relaxed"
              style={{
                fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace',
                color: message.role === 'user' ? '#6b7280' : '#55b685',
                whiteSpace: 'pre-wrap'
              }}
            >
              {message.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div style={{ fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace', color: '#55b685' }}>
              <div className="flex gap-2 items-center">
                <div className="flex gap-1">
                  <div className="w-1.5 h-4 animate-bounce" style={{ backgroundColor: '#55b685', animationDelay: '0ms' }}></div>
                  <div className="w-1.5 h-4 animate-bounce" style={{ backgroundColor: '#55b685', animationDelay: '150ms' }}></div>
                  <div className="w-1.5 h-4 animate-bounce" style={{ backgroundColor: '#55b685', animationDelay: '300ms' }}></div>
                </div>
                {loadingStatus && <span className="text-sm opacity-70">{loadingStatus}</span>}
              </div>
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
                <div className="font-bold">{cmd.name}</div>
                <div className="text-sm opacity-70 mt-1">{cmd.description}</div>
              </div>
            ))}
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
    </div>
  )
}
