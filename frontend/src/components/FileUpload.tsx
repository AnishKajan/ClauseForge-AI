'use client'

import React, { useState, useCallback, useRef } from 'react'
import { Button } from './ui/button'
import { Card, CardContent } from './ui/card'
import { apiClient as api } from '@/lib/api'

interface FileUploadProps {
  onUploadSuccess?: (document: any) => void
  onUploadError?: (error: string) => void
  maxFileSize?: number // in MB
  allowedTypes?: string[]
  multiple?: boolean
}

interface UploadProgress {
  file: File
  progress: number
  status: 'uploading' | 'success' | 'error'
  error?: string
  documentId?: string
}

export function FileUpload({
  onUploadSuccess,
  onUploadError,
  maxFileSize = 50,
  allowedTypes = ['.pdf', '.docx', '.doc'],
  multiple = false
}: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const [uploads, setUploads] = useState<UploadProgress[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = (file: File): string | null => {
    // Check file size
    const maxSizeBytes = maxFileSize * 1024 * 1024
    if (file.size > maxSizeBytes) {
      return `File size exceeds ${maxFileSize}MB limit`
    }

    // Check file type
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!allowedTypes.includes(fileExtension)) {
      return `File type not allowed. Allowed types: ${allowedTypes.join(', ')}`
    }

    return null
  }

  const uploadFile = async (file: File) => {
    const uploadId = Date.now() + Math.random()
    
    // Add to uploads list
    setUploads(prev => [...prev, {
      file,
      progress: 0,
      status: 'uploading'
    }])

    try {
      const response = await api.documents.upload(file)
      
      // Update progress to success
      setUploads(prev => prev.map(upload => 
        upload.file === file 
          ? { ...upload, progress: 100, status: 'success', documentId: response.data.document_id }
          : upload
      ))

      onUploadSuccess?.(response.data)
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Upload failed'
      
      // Update progress to error
      setUploads(prev => prev.map(upload => 
        upload.file === file 
          ? { ...upload, status: 'error', error: errorMessage }
          : upload
      ))

      onUploadError?.(errorMessage)
    }
  }

  const handleFiles = useCallback(async (files: FileList) => {
    const fileArray = Array.from(files)
    
    if (!multiple && fileArray.length > 1) {
      onUploadError?.('Multiple files not allowed')
      return
    }

    for (const file of fileArray) {
      const validationError = validateFile(file)
      if (validationError) {
        onUploadError?.(validationError)
        continue
      }

      await uploadFile(file)
    }
  }, [multiple, maxFileSize, allowedTypes, onUploadSuccess, onUploadError])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    
    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFiles(files)
    }
  }, [handleFiles])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFiles(files)
    }
    // Reset input value to allow selecting the same file again
    e.target.value = ''
  }, [handleFiles])

  const handleClick = () => {
    fileInputRef.current?.click()
  }

  const clearUploads = () => {
    setUploads([])
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className="w-full">
      {/* Upload Area */}
      <Card 
        className={`border-2 border-dashed transition-colors cursor-pointer ${
          isDragOver 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <CardContent className="flex flex-col items-center justify-center py-12 px-6 text-center">
          <div className="mb-4">
            <svg
              className="w-12 h-12 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>
          
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Upload Documents
          </h3>
          
          <p className="text-sm text-gray-600 mb-4">
            Drag and drop your files here, or click to browse
          </p>
          
          <div className="text-xs text-gray-500">
            <p>Supported formats: {allowedTypes.join(', ')}</p>
            <p>Maximum file size: {maxFileSize}MB</p>
            {multiple && <p>Multiple files allowed</p>}
          </div>
          
          <Button className="mt-4" variant="outline">
            Choose Files
          </Button>
        </CardContent>
      </Card>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept={allowedTypes.join(',')}
        multiple={multiple}
        onChange={handleFileSelect}
      />

      {/* Upload Progress */}
      {uploads.length > 0 && (
        <Card className="mt-4">
          <CardContent className="p-4">
            <div className="flex justify-between items-center mb-4">
              <h4 className="font-medium">Upload Progress</h4>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={clearUploads}
              >
                Clear
              </Button>
            </div>
            
            <div className="space-y-3">
              {uploads.map((upload, index) => (
                <div key={index} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {upload.file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatFileSize(upload.file.size)}
                      </p>
                    </div>
                    
                    <div className="ml-4 flex-shrink-0">
                      {upload.status === 'uploading' && (
                        <div className="flex items-center">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                          <span className="ml-2 text-sm text-blue-600">Uploading...</span>
                        </div>
                      )}
                      
                      {upload.status === 'success' && (
                        <div className="flex items-center text-green-600">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                          <span className="ml-2 text-sm">Success</span>
                        </div>
                      )}
                      
                      {upload.status === 'error' && (
                        <div className="flex items-center text-red-600">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                          </svg>
                          <span className="ml-2 text-sm">Error</span>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {upload.status === 'uploading' && (
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${upload.progress}%` }}
                      ></div>
                    </div>
                  )}
                  
                  {upload.error && (
                    <p className="text-xs text-red-600 mt-1">{upload.error}</p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}