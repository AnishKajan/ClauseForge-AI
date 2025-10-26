// Type definitions for the application

export interface User {
  id: string
  email: string
  role: string
  org_id: string
}

export interface Document {
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

export interface DocumentUploadResponse {
  document_id: string
  s3_key: string
  upload_url: string
  status: string
  file_hash: string
  message: string
}

export interface DocumentListResponse {
  documents: Document[]
  total: number
  page: number
  per_page: number
}

export interface UploadStatusResponse {
  document_id: string
  status: string
  progress?: number
  message?: string
  error?: string
}

export interface Citation {
  document_id: string
  document_title: string
  page?: number
  chunk_id: string
  text: string
  relevance_score: number
}

export interface RAGQueryRequest {
  query: string
  document_ids?: string[]
  max_results?: number
  similarity_threshold?: number
  stream?: boolean
}

export interface RAGQueryResponse {
  answer: string
  citations: Citation[]
  confidence: number
  model_used: string
  processing_time: number
  query_id: string
  timestamp: string
}

export interface RAGStreamChunk {
  type: 'start' | 'content' | 'citation' | 'end' | 'error'
  content?: string
  citation?: Citation
  metadata?: Record<string, any>
}

export interface ChatMessage {
  id: string
  type: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  timestamp: Date
  confidence?: number
  model_used?: string
  processing_time?: number
}

// Analysis and Risk Assessment Types
export interface ClauseMatch {
  clause_type: string
  text: string
  confidence: number
  page: number
  risk_level: string
  matched_rule?: string
}

export interface ComplianceResult {
  rule_id: string
  rule_name: string
  status: string
  matched_clauses: ClauseMatch[]
  missing_clause: boolean
  risk_score: number
  recommendations: string[]
}

export interface RiskFactor {
  factor_id: string
  name: string
  description: string
  weight: number
  score: number
  category: string
  recommendations: string[]
}

export interface RiskScore {
  overall_score: number
  category: string
  confidence: number
  factors: RiskFactor[]
  trend?: string
}

export interface RecommendationDetail {
  id: string
  title: string
  description: string
  priority: string
  category: string
  impact: string
  effort: string
  clause_types: string[]
  suggested_language?: string
}

export interface AnalysisResult {
  id: string
  document_id: string
  playbook_id: string
  risk_score: RiskScore
  compliance_results: ComplianceResult[]
  recommendations: RecommendationDetail[]
  missing_clauses: string[]
  compliance_summary: {
    total_rules: number
    compliant: number
    non_compliant: number
    review_required: number
    missing_clauses: number
    overall_status: string
  }
  created_at: string
}

export interface AnalysisHistoryResponse {
  analyses: AnalysisResult[]
  total_count: number
}

export interface PlaybookInfo {
  id: string
  name: string
  description?: string
  is_default: boolean
  rules_count: number
  created_at: string
}

export interface TrendData {
  date: string
  risk_score: number
  compliance_percentage: number
}

// Legacy types for backward compatibility
export interface Recommendation {
  type: string
  description: string
  priority: string
  suggested_action: string
}

export interface Subscription {
  id: string
  plan: string
  status: string
  usage_limits: Record<string, number>
  current_usage: Record<string, number>
  created_at: string
}