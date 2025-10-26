'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { api } from '../lib/api'
import { 
  Citation, 
  RAGQueryRequest, 
  RAGQueryResponse, 
  ChatMessage 
} from '../types'

// Types are now imported from ../types

interface ChatPanelProps {
  selectedDocuments?: string[]
  onCitationClick?: (citation: Citation) => void
  className?: string
}

export function ChatPanel({ 
  selectedDocuments = [], 
  onCitationClick,
  className = ""
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingMessage, setStreamingMessage] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [modelSelection, setModelSelection] = useState('auto')
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingMessage])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!inputValue.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setError(null)
    setIsLoading(true)

    try {
      // Create abort controller for this request
      abortControllerRef.current = new AbortController()

      const requestData: RAGQueryRequest = {
        query: userMessage.content,
        document_ids: selectedDocuments.length > 0 ? selectedDocuments : undefined,
        max_results: 10,
        similarity_threshold: 0.7,
        stream: false // Start with non-streaming for simplicity
      }

      const response = await api.rag.query(requestData)
      const data: RAGQueryResponse = response.data

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        content: data.answer,
        citations: data.citations,
        timestamp: new Date(),
        confidence: data.confidence,
        model_used: data.model_used,
        processing_time: data.processing_time
      }

      setMessages(prev => [...prev, assistantMessage])

    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('Request was aborted')
        return
      }

      console.error('Chat error:', error)
      setError(error.message || 'Failed to get response')
      
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        type: 'assistant',
        content: `I encountered an error: ${error.message || 'Something went wrong'}. Please try again.`,
        timestamp: new Date()
      }
      
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }

  const handleStreamingQuery = async (query: string) => {
    setIsStreaming(true)
    setStreamingMessage('')
    
    try {
      abortControllerRef.current = new AbortController()

      const requestData: RAGQueryRequest = {
        query,
        document_ids: selectedDocuments.length > 0 ? selectedDocuments : undefined,
        stream: true
      }

      const response = await fetch('/api/rag/query/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
        signal: abortControllerRef.current.signal
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''
      let citations: Citation[] = []
      let metadata: any = {}

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.type === 'content') {
                setStreamingMessage(prev => prev + data.content)
              } else if (data.type === 'citation') {
                citations.push(data.citation)
              } else if (data.type === 'end') {
                metadata = data.metadata
              } else if (data.type === 'error') {
                throw new Error(data.content)
              }
            } catch (e) {
              console.error('Error parsing stream data:', e)
            }
          }
        }
      }

      // Create final message
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        content: streamingMessage,
        citations,
        timestamp: new Date(),
        confidence: metadata.confidence,
        model_used: metadata.model_used,
        processing_time: metadata.processing_time
      }

      setMessages(prev => [...prev, assistantMessage])
      setStreamingMessage('')

    } catch (error: any) {
      if (error.name === 'AbortError') return
      
      console.error('Streaming error:', error)
      setError(error.message)
    } finally {
      setIsStreaming(false)
      abortControllerRef.current = null
    }
  }

  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }

  const clearConversation = () => {
    setMessages([])
    setError(null)
    setStreamingMessage('')
  }

  const handleCitationClick = (citation: Citation) => {
    onCitationClick?.(citation)
  }

  const renderMessage = (message: ChatMessage) => (
    <div
      key={message.id}
      className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
    >
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          message.type === 'user'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-900 border'
        }`}
      >
        <div className="whitespace-pre-wrap">{message.content}</div>
        
        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <div className="text-xs font-medium text-gray-600 mb-2">
              Sources ({message.citations.length}):
            </div>
            <div className="space-y-2">
              {message.citations.map((citation, index) => (
                <div
                  key={`${citation.chunk_id}-${index}`}
                  className="text-xs bg-white border rounded p-2 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => handleCitationClick(citation)}
                >
                  <div className="font-medium text-blue-600 mb-1">
                    {citation.document_title}
                    {citation.page && ` (Page ${citation.page})`}
                  </div>
                  <div className="text-gray-600 line-clamp-2">
                    {citation.text}
                  </div>
                  <div className="text-gray-400 mt-1">
                    Relevance: {(citation.relevance_score * 100).toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Message metadata */}
        {message.type === 'assistant' && (message.confidence || message.processing_time) && (
          <div className="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-500">
            {message.confidence && (
              <span>Confidence: {(message.confidence * 100).toFixed(1)}%</span>
            )}
            {message.processing_time && (
              <span className="ml-3">
                Time: {message.processing_time.toFixed(2)}s
              </span>
            )}
            {message.model_used && (
              <span className="ml-3">Model: {message.model_used}</span>
            )}
          </div>
        )}
        
        <div className="text-xs text-gray-400 mt-1">
          {message.timestamp.toLocaleTimeString()}
        </div>
      </div>
    </div>
  )

  return (
    <Card className={`flex flex-col h-full ${className}`}>
      <CardHeader className="flex-shrink-0 pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">AI Assistant</CardTitle>
          <div className="flex items-center gap-2">
            {/* Model Selection */}
            <select
              value={modelSelection}
              onChange={(e) => setModelSelection(e.target.value)}
              className="text-sm border rounded px-2 py-1"
              disabled={isLoading || isStreaming}
            >
              <option value="auto">Auto</option>
              <option value="sonnet">Claude Sonnet</option>
              <option value="opus">Claude Opus</option>
            </select>
            
            {/* Clear button */}
            <Button
              variant="outline"
              size="sm"
              onClick={clearConversation}
              disabled={isLoading || isStreaming}
            >
              Clear
            </Button>
          </div>
        </div>
        
        {/* Document context indicator */}
        {selectedDocuments.length > 0 && (
          <div className="text-sm text-gray-600 bg-blue-50 rounded px-2 py-1">
            Searching in {selectedDocuments.length} selected document{selectedDocuments.length !== 1 ? 's' : ''}
          </div>
        )}
        
        {/* Error display */}
        {error && (
          <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
            {error}
          </div>
        )}
      </CardHeader>

      <CardContent className="flex-1 flex flex-col min-h-0">
        {/* Messages area */}
        <div className="flex-1 overflow-y-auto mb-4 space-y-2">
          {messages.length === 0 && !isStreaming && (
            <div className="text-center text-gray-500 py-8">
              <div className="text-lg mb-2">👋 Hello!</div>
              <div>Ask me anything about your uploaded documents.</div>
              <div className="text-sm mt-2">
                Try: "What are the key terms in this contract?" or "Are there any liability clauses?"
              </div>
            </div>
          )}
          
          {messages.map(renderMessage)}
          
          {/* Streaming message */}
          {isStreaming && streamingMessage && (
            <div className="flex justify-start mb-4">
              <div className="max-w-[80%] rounded-lg px-4 py-2 bg-gray-100 text-gray-900 border">
                <div className="whitespace-pre-wrap">{streamingMessage}</div>
                <div className="flex items-center mt-2 text-xs text-gray-500">
                  <div className="animate-pulse">●</div>
                  <span className="ml-1">Generating response...</span>
                </div>
              </div>
            </div>
          )}
          
          {/* Loading indicator */}
          {isLoading && !isStreaming && (
            <div className="flex justify-start mb-4">
              <div className="max-w-[80%] rounded-lg px-4 py-2 bg-gray-100 text-gray-900 border">
                <div className="flex items-center text-sm text-gray-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                  Thinking...
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <form onSubmit={handleSubmit} className="flex-shrink-0">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask a question about your documents..."
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading || isStreaming}
              maxLength={1000}
            />
            
            {(isLoading || isStreaming) ? (
              <Button
                type="button"
                onClick={stopGeneration}
                variant="outline"
                className="px-4 py-2"
              >
                Stop
              </Button>
            ) : (
              <Button
                type="submit"
                disabled={!inputValue.trim()}
                className="px-4 py-2"
              >
                Send
              </Button>
            )}
          </div>
          
          <div className="text-xs text-gray-500 mt-1">
            {inputValue.length}/1000 characters
          </div>
        </form>
      </CardContent>
    </Card>
  )
}