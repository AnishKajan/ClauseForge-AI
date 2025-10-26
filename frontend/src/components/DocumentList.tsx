'use client'

import React, { useState, useEffect } from 'react'
import { Button } from './ui/button'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { apiClient as api } from '@/lib/api'

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

interface DocumentListProps {
  onDocumentSelect?: (document: Document) => void
  onDocumentDelete?: (documentId: string) => void
  refreshTrigger?: number
}

export function DocumentList({ 
  onDocumentSelect, 
  onDocumentDelete,
  refreshTrigger 
}: DocumentListProps) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'created_at' | 'title' | 'status'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const fetchDocuments = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const params: any = { limit: 100 }
      if (searchTerm) {
        params.search = searchTerm
      }
      if (statusFilter !== 'all') {
        params.status_filter = statusFilter
      }
      
      const response = await api.documents.list(params)
      setDocuments(response.data.documents || [])
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDocuments()
  }, [searchTerm, statusFilter, refreshTrigger])

  const handleDelete = async (documentId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) {
      return
    }

    try {
      await api.documents.delete(documentId)
      setDocuments(prev => prev.filter(doc => doc.id !== documentId))
      onDocumentDelete?.(documentId)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete document')
    }
  }

  const handleDownload = async (document: Document) => {
    try {
      const response = await api.documents.get(`${document.id}/download`)
      window.open(response.data.download_url, '_blank')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to generate download link')
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100'
      case 'processing':
        return 'text-blue-600 bg-blue-100'
      case 'failed':
        return 'text-red-600 bg-red-100'
      case 'uploaded':
        return 'text-yellow-600 bg-yellow-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const sortedDocuments = [...documents].sort((a, b) => {
    let aValue: any = a[sortBy]
    let bValue: any = b[sortBy]
    
    if (sortBy === 'created_at') {
      aValue = new Date(aValue).getTime()
      bValue = new Date(bValue).getTime()
    }
    
    if (sortOrder === 'asc') {
      return aValue > bValue ? 1 : -1
    } else {
      return aValue < bValue ? 1 : -1
    }
  })

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-2">Loading documents...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-red-600">
            <p>{error}</p>
            <Button onClick={fetchDocuments} className="mt-2">
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Documents</CardTitle>
        
        {/* Filters and Search */}
        <div className="flex flex-col sm:flex-row gap-4 mt-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div className="flex gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Status</option>
              <option value="uploaded">Uploaded</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
            
            <select
              value={`${sortBy}-${sortOrder}`}
              onChange={(e) => {
                const [field, order] = e.target.value.split('-')
                setSortBy(field as any)
                setSortOrder(order as any)
              }}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="created_at-desc">Newest First</option>
              <option value="created_at-asc">Oldest First</option>
              <option value="title-asc">Title A-Z</option>
              <option value="title-desc">Title Z-A</option>
              <option value="status-asc">Status A-Z</option>
            </select>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {sortedDocuments.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>No documents found</p>
            {searchTerm && (
              <Button 
                variant="outline" 
                onClick={() => setSearchTerm('')}
                className="mt-2"
              >
                Clear Search
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {sortedDocuments.map((document) => (
              <div
                key={document.id}
                className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 
                        className="text-lg font-medium text-gray-900 truncate cursor-pointer hover:text-blue-600"
                        onClick={() => onDocumentSelect?.(document)}
                      >
                        {document.title}
                      </h3>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(document.status)}`}>
                        {document.status}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm text-gray-600">
                      <div>
                        <span className="font-medium">Size:</span> {formatFileSize(document.file_size)}
                      </div>
                      <div>
                        <span className="font-medium">Type:</span> {document.file_type}
                      </div>
                      <div>
                        <span className="font-medium">Uploaded:</span> {formatDate(document.created_at)}
                      </div>
                      {document.processed_at && (
                        <div>
                          <span className="font-medium">Processed:</span> {formatDate(document.processed_at)}
                        </div>
                      )}
                    </div>
                    
                    {document.uploader_email && (
                      <p className="text-sm text-gray-500 mt-1">
                        Uploaded by: {document.uploader_email}
                      </p>
                    )}
                  </div>
                  
                  <div className="ml-4 flex flex-col sm:flex-row gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onDocumentSelect?.(document)}
                    >
                      View
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDownload(document)}
                    >
                      Download
                    </Button>
                    
                    {document.status === 'uploaded' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={async () => {
                          try {
                            await api.documents.process(document.id)
                            fetchDocuments() // Refresh to show updated status
                          } catch (err: any) {
                            alert(err.response?.data?.detail || 'Failed to process document')
                          }
                        }}
                      >
                        Process
                      </Button>
                    )}
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(document.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}