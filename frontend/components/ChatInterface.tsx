'use client'

import { useState, useEffect, useRef } from 'react'

interface Message {
  id: string
  type: 'user' | 'ai'
  text: string
  timestamp?: number
  segment_text?: string
}

interface ChatInterfaceProps {
  videoId: string | null
  onSegmentReady: (segmentUrl: string) => void
}

export default function ChatInterface({ videoId, onSegmentReady }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [connected, setConnected] = useState(false)
  const [sending, setSending] = useState(false)
  const [connectionAttempts, setConnectionAttempts] = useState(0)
  const socketRef = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const connectWebSocket = (attempts = 0) => {
    // Validate videoId before attempting connection
    if (!videoId || videoId.length === 0) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        type: 'ai',
        text: 'No video selected. Please upload and select a video to start chatting.',
      }])
      return
    }

    // Clear any existing "No video selected" error messages when videoId becomes available
    setMessages(prev => prev.filter(msg =>
      !msg.text.includes('No video selected. Please upload and select a video to start chatting.')
    ))

    // Use dynamic host detection for development/production
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = process.env.NODE_ENV === 'development' ? 'localhost:8000' : window.location.host
    const wsUrl = `${protocol}//${wsHost}/ws/chat/${videoId}/`

    if (process.env.NODE_ENV === 'development') {
      console.log('Attempting WebSocket connection to:', wsUrl, 'Attempt:', attempts + 1)
    }

    const socket = new WebSocket(wsUrl)
    socketRef.current = socket

    socket.onopen = () => {
      setConnected(true)
      setConnectionAttempts(0)
      if (process.env.NODE_ENV === 'development') {
        console.log('WebSocket connected successfully to:', wsUrl)
      }
    }

    socket.onclose = (event) => {
      setConnected(false)
      if (process.env.NODE_ENV === 'development') {
        console.log('WebSocket disconnected. Code:', event.code, 'Reason:', event.reason)
      }

      // Only retry if it wasn't a clean closure and we haven't exceeded retry attempts
      if (event.code !== 1000 && attempts < 3) {
        const nextAttempts = attempts + 1
        setConnectionAttempts(nextAttempts)

        // Exponential backoff: 1s, 2s, 4s
        const delay = Math.pow(2, attempts) * 1000

        if (process.env.NODE_ENV === 'development') {
          console.log(`Retrying connection in ${delay}ms (attempt ${nextAttempts}/3)`)
        }

        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket(nextAttempts)
        }, delay)
      } else if (attempts >= 3) {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          type: 'ai',
          text: `Connection failed after 3 attempts. Please check that the backend server is running and refresh to try again.`,
        }])
      }
    }

    socket.onerror = (error) => {
      if (process.env.NODE_ENV === 'development') {
        console.log('WebSocket error occurred:', error)
        console.log('Connection URL was:', wsUrl)
        console.log('Ready State:', socket.readyState)
      }
      setConnected(false)
    }

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('WebSocket message received:', data)

        if (data.type === 'user_message') {
          setMessages(prev => [...prev, {
            id: data.id,
            type: 'user',
            text: data.message
          }])
        } else if (data.type === 'ai_message') {
          setMessages(prev => [...prev, {
            id: data.id,
            type: 'ai',
            text: data.message,
            timestamp: data.timestamp,
            segment_text: data.segment_text
          }])
          setSending(false)

          // If we have a segment URL, automatically play it
          if (data.segment_url) {
            console.log('Playing video segment:', data.segment_url)
            onSegmentReady(data.segment_url)
          } else {
            console.log('No segment URL in AI response. Data:', data)
          }
        } else if (data.type === 'connection') {
          console.log('Connection established:', data.message)
        } else if (data.type === 'error') {
          if (process.env.NODE_ENV === 'development') {
            console.log('WebSocket error message:', data.message)
          }
          setSending(false)
        }
      } catch (error) {
        if (process.env.NODE_ENV === 'development') {
          console.log('Error parsing WebSocket message:', error)
        }
      }
    }

    return () => {
      socket.close()
    }
  }

  useEffect(() => {
    connectWebSocket(0)

    return () => {
      if (socketRef.current) {
        socketRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [videoId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || !connected || sending) return

    setSending(true)
    const message = { message: input }
    socketRef.current?.send(JSON.stringify(message))
    setInput('')
  }

  const formatTimestamp = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div
      className="bg-white rounded-lg shadow-lg border-2 border-gray-200 flex flex-col overflow-hidden"
      style={{
        width: '512px',
        height: '512px',
        minWidth: '512px',
        maxWidth: '512px',
        minHeight: '512px',
        maxHeight: '512px',
        flexShrink: 0,
        flexGrow: 0
      }}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-800">
            Chat
          </h3>
          <div className="flex items-center">
            <div className={`w-2 h-2 rounded-full mr-2 ${connected ? 'bg-green-500' : connectionAttempts > 0 ? 'bg-yellow-500' : 'bg-red-500'}`} />
            <span className="text-xs text-gray-500">
              {connected ? 'Connected' : connectionAttempts > 0 ? 'Reconnecting...' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-16">
            {!videoId ? (
              <p className="text-sm">Upload a video to start chatting</p>
            ) : (
              <p className="text-sm">Ask questions about your video!</p>
            )}
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] px-3 py-2 rounded-lg text-sm ${
                  message.type === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                <p className="whitespace-pre-wrap">{message.text}</p>
                {message.timestamp !== undefined && (
                  <p className="mt-1 text-xs opacity-60">
                    {formatTimestamp(message.timestamp)}
                  </p>
                )}
                {message.segment_text && (
                  <div className="mt-2 p-2 bg-gray-50 rounded text-xs italic border-l-2 border-gray-300">
                    "{message.segment_text}"
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <form onSubmit={sendMessage} className="border-t border-gray-200 p-4">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={videoId ? "Ask about the video..." : "Upload a video first"}
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={!videoId || !connected || sending}
          />
          <button
            type="submit"
            disabled={!videoId || !connected || sending || !input.trim()}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {sending ? 'Sending...' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  )
}