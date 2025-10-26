// API Response Types

export interface HealthResponse {
  status: string
  message: string
  timestamp: string
  version?: string
}

export interface User {
  id: string
  email: string
  role: string
  org_id: string
  is_active: boolean
  email_verified: boolean
  provider: string
  created_at: string
  last_login?: string
}

export interface Document {
  id: string
  filename: string
  file_size: number
  file_type: string
  upload_date: string
  status: 'processing' | 'completed' | 'failed'
  analysis_id?: string
}

export interface Analysis {
  id: string
  document_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  summary?: string
  key_clauses?: string[]
  risks?: Risk[]
  compliance_issues?: ComplianceIssue[]
  created_at: string
  completed_at?: string
}

export interface Risk {
  id: string
  type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  recommendation?: string
  clause_reference?: string
}

export interface ComplianceIssue {
  id: string
  regulation: string
  issue_type: string
  description: string
  severity: 'low' | 'medium' | 'high'
  recommendation?: string
}

export interface UploadResponse {
  document_id: string
  filename: string
  status: string
  message: string
}

export interface ApiError {
  detail: string
  error_code?: string
  timestamp?: string
}