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

export default function ChatInterface({ symbol }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isMounted, setIsMounted] = useState(false)

  useEffect(() => {
    setIsMounted(true)
    setMessages([{
      id: '1',
      role: 'assistant',
      content: `I'm here to help you analyze ${symbol}. Ask me anything about this stock!`
    }])
  }, [symbol])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    // Placeholder for AI response - you can integrate with your AI service later
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `I received your message about ${symbol}: "${userMessage.content}". AI integration coming soon!`
      }
      setMessages(prev => [...prev, assistantMessage])
      setIsLoading(false)
    }, 1000)
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
                color: '#55b685'
              }}
            >
              <p>{message.content}</p>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div style={{ fontFamily: 'SF Mono, Menlo, Monaco, Courier New, monospace', color: '#55b685' }}>
              <div className="flex gap-1 items-center">
                <div className="flex gap-1">
                  <div className="w-1.5 h-4 animate-bounce" style={{ backgroundColor: '#55b685', animationDelay: '0ms' }}></div>
                  <div className="w-1.5 h-4 animate-bounce" style={{ backgroundColor: '#55b685', animationDelay: '150ms' }}></div>
                  <div className="w-1.5 h-4 animate-bounce" style={{ backgroundColor: '#55b685', animationDelay: '300ms' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box - Docked at Bottom */}
      <div className="p-4 border-t border-[#55b68533]">
        <form onSubmit={handleSubmit} className="flex gap-3 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
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
