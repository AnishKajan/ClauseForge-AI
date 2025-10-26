'use client'

import React, { useState } from 'react'
import { FileUpload } from './FileUpload'
import { DocumentList } from './DocumentList'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'

interface Document {
  id: string
  title: string
  file_type: string
  file_size: number
  file_hash: string
  status: string
  uploaded_by: string
  uploader_email?: string
  created_at: string
  updated_at: string
  processed_at?: string
}

interface DocumentManagerProps {
  onDocumentSelect?: (document: Document) => void
}

export function DocumentManager({ onDocumentSelect }: DocumentManagerProps) {
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const handleUploadSuccess = (document: any) => {
    setUploadSuccess(`Document "${document.filename || 'file'}" uploaded successfully!`)
    setUploadError(null)
    // Refresh document list
    setRefreshTrigger(prev => prev + 1)
    
    // Clear success message after 5 seconds
    setTimeout(() => setUploadSuccess(null), 5000)
  }

  const handleUploadError = (error: string) => {
    setUploadError(error)
    setUploadSuccess(null)
    
    // Clear error message after 10 seconds
    setTimeout(() => setUploadError(null), 10000)
  }

  const handleDocumentSelect = (document: Document) => {
    setSelectedDocument(document)
    onDocumentSelect?.(document)
  }

  const handleDocumentDelete = (documentId: string) => {
    // If the deleted document was selected, clear selection
    if (selectedDocument?.id === documentId) {
      setSelectedDocument(null)
    }
    // Refresh document list
    setRefreshTrigger(prev => prev + 1)
  }

  return (
    <div className="space-y-6">
      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Documents</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Success/Error Messages */}
          {uploadSuccess && (
            <div className="mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded-md">
              <div className="flex items-center">
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                {uploadSuccess}
              </div>
            </div>
          )}
          
          {uploadError && (
            <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-md">
              <div className="flex items-center">
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
                {uploadError}
              </div>
            </div>
          )}
          
          <FileUpload
            onUploadSuccess={handleUploadSuccess}
            onUploadError={handleUploadError}
            multiple={true}
          />
        </CardContent>
      </Card>

      {/* Document List Section */}
      <DocumentList
        onDocumentSelect={handleDocumentSelect}
        onDocumentDelete={handleDocumentDelete}
        refreshTrigger={refreshTrigger}
      />

      {/* Selected Document Details */}
      {selectedDocument && (
        <Card>
          <CardHeader>
            <CardTitle>Document Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Basic Information</h4>
                <dl className="space-y-2 text-sm">
                  <div>
                    <dt className="font-medium text-gray-600">Title:</dt>
                    <dd className="text-gray-900">{selectedDocument.title}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-gray-600">File Type:</dt>
                    <dd className="text-gray-900">{selectedDocument.file_type}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-gray-600">File Size:</dt>
                    <dd className="text-gray-900">
                      {(selectedDocument.file_size / (1024 * 1024)).toFixed(2)} MB
                    </dd>
                  </div>
                  <div>
                    <dt className="font-medium text-gray-600">Status:</dt>
                    <dd className="text-gray-900">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        selectedDocument.status === 'completed' ? 'text-green-600 bg-green-100' :
                        selectedDocument.status === 'processing' ? 'text-blue-600 bg-blue-100' :
                        selectedDocument.status === 'failed' ? 'text-red-600 bg-red-100' :
                        'text-yellow-600 bg-yellow-100'
                      }`}>
                        {selectedDocument.status}
                      </span>
                    </dd>
                  </div>
                </dl>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Upload Information</h4>
                <dl className="space-y-2 text-sm">
                  <div>
                    <dt className="font-medium text-gray-600">Uploaded At:</dt>
                    <dd className="text-gray-900">
                      {new Date(selectedDocument.created_at).toLocaleString()}
                    </dd>
                  </div>
                  {selectedDocument.processed_at && (
                    <div>
                      <dt className="font-medium text-gray-600">Processed At:</dt>
                      <dd className="text-gray-900">
                        {new Date(selectedDocument.processed_at).toLocaleString()}
                      </dd>
                    </div>
                  )}
                  {selectedDocument.uploader_email && (
                    <div>
                      <dt className="font-medium text-gray-600">Uploaded By:</dt>
                      <dd className="text-gray-900">{selectedDocument.uploader_email}</dd>
                    </div>
                  )}
                  <div>
                    <dt className="font-medium text-gray-600">File Hash:</dt>
                    <dd className="text-gray-900 font-mono text-xs break-all">
                      {selectedDocument.file_hash}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
            
            {/* Actions */}
            <div className="mt-6 flex gap-2">
              {selectedDocument.status === 'uploaded' && (
                <button
                  onClick={async () => {
                    try {
                      // This would trigger document processing
                      console.log('Processing document:', selectedDocument.id)
                    } catch (error) {
                      console.error('Failed to process document:', error)
                    }
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  Process Document
                </button>
              )}
              
              {selectedDocument.status === 'completed' && (
                <button
                  onClick={() => {
                    // This would open the analysis view
                    console.log('Analyze document:', selectedDocument.id)
                  }}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                >
                  Analyze Document
                </button>
              )}
              
              <button
                onClick={() => setSelectedDocument(null)}
                className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
              >
                Close Details
              </button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}