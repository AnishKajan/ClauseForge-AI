'use client'

import { useState, useCallback } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useDropzone } from 'react-dropzone'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Logo } from '@/components/ui/logo'
import { FileText, Upload, X, CheckCircle, AlertCircle } from 'lucide-react'

interface UploadStatus {
  status: 'idle' | 'uploading' | 'success' | 'error'
  progress: number
  message?: string
}

export default function UploadPage() {
  const { accessToken } = useAuth()
  const router = useRouter()
  const [files, setFiles] = useState<File[]>([])
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({ 
    status: 'idle', 
    progress: 0 
  })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prev => [...prev, ...acceptedFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc']
    },
    maxSize: 50 * 1024 * 1024, // 50MB
  })

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (files.length === 0) return

    setUploadStatus({ status: 'uploading', progress: 0 })

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        const formData = new FormData()
        formData.append('file', file)

        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/documents/upload`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
          body: formData,
        })

        if (!response.ok) {
          throw new Error(`Failed to upload ${file.name}`)
        }

        const progress = ((i + 1) / files.length) * 100
        setUploadStatus({ status: 'uploading', progress })
      }

      setUploadStatus({ 
        status: 'success', 
        progress: 100, 
        message: `Successfully uploaded ${files.length} file(s)` 
      })
      
      // Clear files after successful upload
      setTimeout(() => {
        setFiles([])
        setUploadStatus({ status: 'idle', progress: 0 })
      }, 3000)

    } catch (error: any) {
      setUploadStatus({ 
        status: 'error', 
        progress: 0, 
        message: error.message || 'Upload failed' 
      })
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link href="/">
              <Logo useFavicon={true} />
            </Link>
            <div className="flex items-center space-x-4">
              <Button variant="ghost" asChild>
                <Link href="/dashboard">Dashboard</Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload Documents</h1>
            <p className="text-gray-600">
              Upload your contracts and legal documents for AI-powered analysis.
            </p>
          </div>

          {/* Upload Area */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Select Files</CardTitle>
              <CardDescription>
                Drag and drop files here, or click to select. Supports PDF, DOCX, and DOC files up to 50MB.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  isDragActive 
                    ? 'border-blue-500 bg-blue-50' 
                    : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                {isDragActive ? (
                  <p className="text-blue-600">Drop the files here...</p>
                ) : (
                  <div>
                    <p className="text-gray-600 mb-2">
                      Drag and drop files here, or click to select
                    </p>
                    <p className="text-sm text-gray-500">
                      PDF, DOCX, DOC files up to 50MB
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* File List */}
          {files.length > 0 && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>Selected Files ({files.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {files.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <FileText className="h-5 w-5 text-blue-600" />
                        <div>
                          <p className="font-medium">{file.name}</p>
                          <p className="text-sm text-gray-500">
                            {(file.size / 1024 / 1024).toFixed(2)} MB
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(index)}
                        disabled={uploadStatus.status === 'uploading'}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Upload Progress */}
          {uploadStatus.status !== 'idle' && (
            <Card className="mb-6">
              <CardContent className="pt-6">
                <div className="flex items-center space-x-3 mb-3">
                  {uploadStatus.status === 'uploading' && (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600" />
                  )}
                  {uploadStatus.status === 'success' && (
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  )}
                  {uploadStatus.status === 'error' && (
                    <AlertCircle className="h-5 w-5 text-red-600" />
                  )}
                  <span className="font-medium">
                    {uploadStatus.status === 'uploading' && 'Uploading...'}
                    {uploadStatus.status === 'success' && 'Upload Complete'}
                    {uploadStatus.status === 'error' && 'Upload Failed'}
                  </span>
                </div>
                
                {uploadStatus.status === 'uploading' && (
                  <Progress value={uploadStatus.progress} className="mb-2" />
                )}
                
                {uploadStatus.message && (
                  <p className={`text-sm ${
                    uploadStatus.status === 'success' ? 'text-green-600' : 
                    uploadStatus.status === 'error' ? 'text-red-600' : 'text-gray-600'
                  }`}>
                    {uploadStatus.message}
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Upload Button */}
          <div className="flex justify-center">
            <Button
              onClick={handleUpload}
              disabled={files.length === 0 || uploadStatus.status === 'uploading'}
              size="lg"
              className="px-8"
            >
              {uploadStatus.status === 'uploading' ? 'Uploading...' : `Upload ${files.length} File(s)`}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}