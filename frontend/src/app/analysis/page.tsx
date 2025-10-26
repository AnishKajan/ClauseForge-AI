'use client'

import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { RiskScore, ClauseTable, ComplianceDashboard } from '@/components'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { AnalysisResult, PlaybookInfo, TrendData } from '@/types'

export default function AnalysisPage() {
  const searchParams = useSearchParams()
  const documentId = searchParams.get('document_id')
  
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [playbooks, setPlaybooks] = useState<PlaybookInfo[]>([])
  const [selectedPlaybook, setSelectedPlaybook] = useState<string>('')
  const [trendData, setTrendData] = useState<TrendData[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Mock data for demonstration
  const mockAnalysisResult: AnalysisResult = {
    id: '123e4567-e89b-12d3-a456-426614174000',
    document_id: documentId || '123e4567-e89b-12d3-a456-426614174001',
    playbook_id: '123e4567-e89b-12d3-a456-426614174002',
    risk_score: {
      overall_score: 65,
      category: 'high',
      confidence: 0.85,
      factors: [
        {
          factor_id: 'indemnity_clause',
          name: 'Indemnity Clause',
          description: 'Compliance status: non_compliant',
          weight: 1.0,
          score: 85,
          category: 'Legal Protection',
          recommendations: ['Add mutual indemnity clause to protect both parties']
        },
        {
          factor_id: 'liability_cap',
          name: 'Liability Limitation',
          description: 'Compliance status: review_required',
          weight: 0.8,
          score: 45,
          category: 'Legal Protection',
          recommendations: ['Include reasonable liability caps to limit exposure']
        }
      ],
      trend: 'stable'
    },
    compliance_results: [
      {
        rule_id: 'indemnity_clause',
        rule_name: 'Indemnity Clause',
        status: 'non_compliant',
        matched_clauses: [],
        missing_clause: true,
        risk_score: 85,
        recommendations: ['Add mutual indemnity clause to protect both parties']
      },
      {
        rule_id: 'liability_cap',
        rule_name: 'Liability Limitation',
        status: 'review_required',
        matched_clauses: [
          {
            clause_type: 'liability',
            text: 'The Company\'s liability shall be limited to the amount paid under this agreement, except in cases of gross negligence or willful misconduct.',
            confidence: 0.75,
            page: 3,
            risk_level: 'medium'
          }
        ],
        missing_clause: false,
        risk_score: 45,
        recommendations: ['Consider adding specific liability caps with dollar amounts']
      },
      {
        rule_id: 'termination_clause',
        rule_name: 'Termination Rights',
        status: 'compliant',
        matched_clauses: [
          {
            clause_type: 'termination',
            text: 'Either party may terminate this Agreement with thirty (30) days written notice.',
            confidence: 0.92,
            page: 5,
            risk_level: 'low'
          }
        ],
        missing_clause: false,
        risk_score: 10,
        recommendations: []
      }
    ],
    recommendations: [
      {
        id: 'rec_1',
        title: 'Add Indemnity Clause',
        description: 'Include mutual indemnity provisions to protect both parties from third-party claims.',
        priority: 'urgent',
        category: 'Legal Protection',
        impact: 'high',
        effort: 'medium',
        clause_types: ['indemnity_clause'],
        suggested_language: 'Each party shall indemnify, defend, and hold harmless the other party from and against any and all claims, damages, losses, and expenses arising out of or resulting from the indemnifying party\'s breach of this Agreement or negligent or wrongful acts.'
      }
    ],
    missing_clauses: ['Indemnity Clause'],
    compliance_summary: {
      total_rules: 3,
      compliant: 1,
      non_compliant: 1,
      review_required: 1,
      missing_clauses: 1,
      overall_status: 'review_required'
    },
    created_at: new Date().toISOString()
  }

  const mockTrendData: TrendData[] = [
    { date: '2024-01-01', risk_score: 70, compliance_percentage: 60 },
    { date: '2024-01-08', risk_score: 68, compliance_percentage: 65 },
    { date: '2024-01-15', risk_score: 65, compliance_percentage: 67 },
    { date: '2024-01-22', risk_score: 65, compliance_percentage: 67 },
    { date: '2024-01-29', risk_score: 63, compliance_percentage: 70 }
  ]

  useEffect(() => {
    // In a real app, this would fetch data from the API
    setAnalysisResult(mockAnalysisResult)
    setTrendData(mockTrendData)
    setPlaybooks([
      {
        id: '1',
        name: 'Standard Contract Playbook',
        description: 'Comprehensive compliance rules for standard business contracts',
        is_default: true,
        rules_count: 8,
        created_at: '2024-01-01T00:00:00Z'
      }
    ])
  }, [documentId])

  const handleAnalyze = async () => {
    if (!documentId) return
    
    setLoading(true)
    setError(null)
    
    try {
      // In a real app, this would call the API
      // const response = await fetch(`/api/analysis/documents/${documentId}/analyze`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ playbook_id: selectedPlaybook || undefined })
      // })
      
      // Mock delay
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // For now, just update with mock data
      setAnalysisResult(mockAnalysisResult)
    } catch (err) {
      setError('Failed to analyze document')
    } finally {
      setLoading(false)
    }
  }

  const handleExport = () => {
    // In a real app, this would generate and download a report
    console.log('Exporting analysis results...')
  }

  if (!documentId) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="p-8 text-center">
          <h1 className="text-2xl font-bold mb-4">Document Analysis</h1>
          <p className="text-gray-600">Please select a document to analyze.</p>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Document Analysis</h1>
          <p className="text-gray-600 mt-1">
            Comprehensive compliance and risk assessment
          </p>
        </div>
        <div className="flex items-center space-x-4">
          {playbooks.length > 0 && (
            <select
              value={selectedPlaybook}
              onChange={(e) => setSelectedPlaybook(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Default Playbook</option>
              {playbooks.map((playbook) => (
                <option key={playbook.id} value={playbook.id}>
                  {playbook.name}
                </option>
              ))}
            </select>
          )}
          <Button
            onClick={handleAnalyze}
            disabled={loading}
            className="min-w-32"
          >
            {loading ? 'Analyzing...' : 'Analyze Document'}
          </Button>
        </div>
      </div>

      {error && (
        <Card className="p-4 bg-red-50 border-red-200">
          <p className="text-red-600">{error}</p>
        </Card>
      )}

      {analysisResult && (
        <>
          {/* Compliance Dashboard */}
          <ComplianceDashboard
            complianceSummary={analysisResult.compliance_summary}
            trendData={trendData}
            onRefresh={() => handleAnalyze()}
          />

          {/* Risk Score */}
          <RiskScore riskScore={analysisResult.risk_score} />

          {/* Compliance Results Table */}
          <ClauseTable
            complianceResults={analysisResult.compliance_results}
            onExport={handleExport}
          />

          {/* Recommendations */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Recommendations</h3>
            <div className="space-y-4">
              {analysisResult.recommendations.map((rec) => (
                <div key={rec.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">{rec.title}</h4>
                    <div className="flex items-center space-x-2">
                      <span className={`text-xs px-2 py-1 rounded ${
                        rec.priority === 'urgent' ? 'bg-red-100 text-red-800' :
                        rec.priority === 'high' ? 'bg-orange-100 text-orange-800' :
                        rec.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {rec.priority.toUpperCase()}
                      </span>
                      <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
                        {rec.category}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 mb-3">{rec.description}</p>
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>Impact: {rec.impact} | Effort: {rec.effort}</span>
                    {rec.clause_types.length > 0 && (
                      <span>Affects: {rec.clause_types.join(', ')}</span>
                    )}
                  </div>
                  {rec.suggested_language && (
                    <div className="mt-3 p-3 bg-blue-50 rounded border-l-4 border-blue-500">
                      <h5 className="text-sm font-medium text-blue-800 mb-1">Suggested Language:</h5>
                      <p className="text-sm text-blue-700 italic">"{rec.suggested_language}"</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </>
      )}

      {!analysisResult && !loading && (
        <Card className="p-8 text-center">
          <h2 className="text-xl font-semibold mb-4">Ready to Analyze</h2>
          <p className="text-gray-600 mb-6">
            Click "Analyze Document" to perform comprehensive compliance and risk assessment.
          </p>
          <Button onClick={handleAnalyze} size="lg">
            Start Analysis
          </Button>
        </Card>
      )}
    </div>
  )
}