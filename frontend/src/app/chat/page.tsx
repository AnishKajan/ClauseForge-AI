'use client'

import React, { useState } from 'react'
import { ChatPanel } from '@/components/ChatPanel'
import { DocumentManager } from '@/components/DocumentManager'
import { Citation } from '@/types'

export default function ChatPage() {
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([])
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null)

  const handleDocumentSelect = (document: any) => {
    // Toggle document selection
    setSelectedDocuments(prev => {
      if (prev.includes(document.id)) {
        return prev.filter(id => id !== document.id)
      } else {
        return [...prev, document.id]
      }
    })
  }

  const handleCitationClick = (citation: Citation) => {
    setSelectedCitation(citation)
    // In a real app, this would navigate to the document viewer
    // and highlight the relevant section
    console.log('Citation clicked:', citation)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            AI Document Chat
          </h1>
          <p className="text-gray-600">
            Upload documents and ask questions about their content using AI-powered analysis.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-[calc(100vh-200px)]">
          {/* Left side: Document management */}
          <div className="space-y-6">
            <DocumentManager onDocumentSelect={handleDocumentSelect} />
            
            {/* Selected documents indicator */}
            {selectedDocuments.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="font-medium text-blue-900 mb-2">
                  Selected for Chat ({selectedDocuments.length})
                </h3>
                <div className="text-sm text-blue-700">
                  Your questions will search within the selected documents.
                </div>
                <button
                  onClick={() => setSelectedDocuments([])}
                  className="mt-2 text-sm text-blue-600 hover:text-blue-800 underline"
                >
                  Clear selection
                </button>
              </div>
            )}

            {/* Citation details */}
            {selectedCitation && (
              <div className="bg-white border rounded-lg p-4">
                <h3 className="font-medium text-gray-900 mb-2">
                  Citation Details
                </h3>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium">Document:</span>{' '}
                    {selectedCitation.document_title}
                  </div>
                  {selectedCitation.page && (
                    <div>
                      <span className="font-medium">Page:</span>{' '}
                      {selectedCitation.page}
                    </div>
                  )}
                  <div>
                    <span className="font-medium">Relevance:</span>{' '}
                    {(selectedCitation.relevance_score * 100).toFixed(1)}%
                  </div>
                  <div>
                    <span className="font-medium">Text:</span>
                    <div className="mt-1 p-2 bg-gray-50 rounded text-gray-700">
                      {selectedCitation.text}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedCitation(null)}
                  className="mt-3 text-sm text-gray-600 hover:text-gray-800 underline"
                >
                  Close
                </button>
              </div>
            )}
          </div>

          {/* Right side: Chat interface */}
          <div className="h-full">
            <ChatPanel
              selectedDocuments={selectedDocuments}
              onCitationClick={handleCitationClick}
              className="h-full"
            />
          </div>
        </div>
      </div>
    </div>
  )
}