'use client'

import React, { useState, useMemo } from 'react'
import { Card } from './ui/card'
import { Button } from './ui/button'

interface ClauseMatch {
  clause_type: string
  text: string
  confidence: number
  page: number
  risk_level: string
  matched_rule?: string
}

interface ComplianceResult {
  rule_id: string
  rule_name: string
  status: string
  matched_clauses: ClauseMatch[]
  missing_clause: boolean
  risk_score: number
  recommendations: string[]
}

interface ClauseTableProps {
  complianceResults: ComplianceResult[]
  className?: string
  onExport?: () => void
}

type SortField = 'rule_name' | 'status' | 'risk_score' | 'clause_count'
type SortDirection = 'asc' | 'desc'
type FilterStatus = 'all' | 'compliant' | 'non_compliant' | 'review_required'
type FilterRiskLevel = 'all' | 'low' | 'medium' | 'high' | 'critical'

const getStatusColor = (status: string): string => {
  switch (status) {
    case 'compliant':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'non_compliant':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'review_required':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

const getRiskLevelColor = (riskLevel: string): string => {
  switch (riskLevel.toLowerCase()) {
    case 'critical':
      return 'bg-red-100 text-red-800'
    case 'high':
      return 'bg-orange-100 text-orange-800'
    case 'medium':
      return 'bg-yellow-100 text-yellow-800'
    case 'low':
      return 'bg-green-100 text-green-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const formatStatus = (status: string): string => {
  return status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
}

export const ClauseTable: React.FC<ClauseTableProps> = ({ 
  complianceResults, 
  className = '',
  onExport 
}) => {
  const [sortField, setSortField] = useState<SortField>('risk_score')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all')
  const [filterRiskLevel, setFilterRiskLevel] = useState<FilterRiskLevel>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  // Filter and sort data
  const filteredAndSortedResults = useMemo(() => {
    let filtered = complianceResults.filter(result => {
      // Status filter
      if (filterStatus !== 'all' && result.status !== filterStatus) {
        return false
      }

      // Risk level filter (based on highest risk clause)
      if (filterRiskLevel !== 'all') {
        const hasRiskLevel = result.matched_clauses.some(
          clause => clause.risk_level.toLowerCase() === filterRiskLevel
        )
        if (!hasRiskLevel) return false
      }

      // Search filter
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase()
        return (
          result.rule_name.toLowerCase().includes(searchLower) ||
          result.matched_clauses.some(clause => 
            clause.text.toLowerCase().includes(searchLower) ||
            clause.clause_type.toLowerCase().includes(searchLower)
          )
        )
      }

      return true
    })

    // Sort
    filtered.sort((a, b) => {
      let aValue: any, bValue: any

      switch (sortField) {
        case 'rule_name':
          aValue = a.rule_name
          bValue = b.rule_name
          break
        case 'status':
          aValue = a.status
          bValue = b.status
          break
        case 'risk_score':
          aValue = a.risk_score
          bValue = b.risk_score
          break
        case 'clause_count':
          aValue = a.matched_clauses.length
          bValue = b.matched_clauses.length
          break
        default:
          return 0
      }

      if (typeof aValue === 'string') {
        aValue = aValue.toLowerCase()
        bValue = bValue.toLowerCase()
      }

      if (sortDirection === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0
      }
    })

    return filtered
  }, [complianceResults, sortField, sortDirection, filterStatus, filterRiskLevel, searchTerm])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const toggleRowExpansion = (ruleId: string) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(ruleId)) {
      newExpanded.delete(ruleId)
    } else {
      newExpanded.add(ruleId)
    }
    setExpandedRows(newExpanded)
  }

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return '↕️'
    return sortDirection === 'asc' ? '↑' : '↓'
  }

  return (
    <Card className={`p-6 ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold">Compliance Analysis Results</h3>
        {onExport && (
          <Button onClick={onExport} variant="outline" size="sm">
            Export Results
          </Button>
        )}
      </div>

      {/* Filters and Search */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex-1 min-w-64">
          <input
            type="text"
            placeholder="Search rules or clauses..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as FilterStatus)}
          className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Statuses</option>
          <option value="compliant">Compliant</option>
          <option value="non_compliant">Non-Compliant</option>
          <option value="review_required">Review Required</option>
        </select>

        <select
          value={filterRiskLevel}
          onChange={(e) => setFilterRiskLevel(e.target.value as FilterRiskLevel)}
          className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Risk Levels</option>
          <option value="low">Low Risk</option>
          <option value="medium">Medium Risk</option>
          <option value="high">High Risk</option>
          <option value="critical">Critical Risk</option>
        </select>
      </div>

      {/* Results Summary */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="text-center p-3 bg-green-50 rounded-lg">
          <div className="text-2xl font-bold text-green-600">
            {complianceResults.filter(r => r.status === 'compliant').length}
          </div>
          <div className="text-sm text-green-700">Compliant</div>
        </div>
        <div className="text-center p-3 bg-red-50 rounded-lg">
          <div className="text-2xl font-bold text-red-600">
            {complianceResults.filter(r => r.status === 'non_compliant').length}
          </div>
          <div className="text-sm text-red-700">Non-Compliant</div>
        </div>
        <div className="text-center p-3 bg-yellow-50 rounded-lg">
          <div className="text-2xl font-bold text-yellow-600">
            {complianceResults.filter(r => r.status === 'review_required').length}
          </div>
          <div className="text-sm text-yellow-700">Review Required</div>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="text-2xl font-bold text-gray-600">
            {complianceResults.filter(r => r.missing_clause).length}
          </div>
          <div className="text-sm text-gray-700">Missing Clauses</div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left p-3 font-medium">
                <button
                  onClick={() => handleSort('rule_name')}
                  className="flex items-center space-x-1 hover:text-blue-600"
                >
                  <span>Rule</span>
                  <span>{getSortIcon('rule_name')}</span>
                </button>
              </th>
              <th className="text-left p-3 font-medium">
                <button
                  onClick={() => handleSort('status')}
                  className="flex items-center space-x-1 hover:text-blue-600"
                >
                  <span>Status</span>
                  <span>{getSortIcon('status')}</span>
                </button>
              </th>
              <th className="text-left p-3 font-medium">
                <button
                  onClick={() => handleSort('clause_count')}
                  className="flex items-center space-x-1 hover:text-blue-600"
                >
                  <span>Clauses Found</span>
                  <span>{getSortIcon('clause_count')}</span>
                </button>
              </th>
              <th className="text-left p-3 font-medium">
                <button
                  onClick={() => handleSort('risk_score')}
                  className="flex items-center space-x-1 hover:text-blue-600"
                >
                  <span>Risk Score</span>
                  <span>{getSortIcon('risk_score')}</span>
                </button>
              </th>
              <th className="text-left p-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedResults.map((result) => (
              <React.Fragment key={result.rule_id}>
                <tr className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="p-3">
                    <div className="font-medium">{result.rule_name}</div>
                    {result.missing_clause && (
                      <div className="text-sm text-red-600 mt-1">
                        ⚠️ Missing required clause
                      </div>
                    )}
                  </td>
                  <td className="p-3">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(result.status)}`}>
                      {formatStatus(result.status)}
                    </span>
                  </td>
                  <td className="p-3">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium">{result.matched_clauses.length}</span>
                      {result.matched_clauses.length > 0 && (
                        <div className="flex space-x-1">
                          {Array.from(new Set(result.matched_clauses.map(c => c.risk_level))).map(level => (
                            <span
                              key={level}
                              className={`inline-block w-2 h-2 rounded-full ${getRiskLevelColor(level).split(' ')[0].replace('bg-', 'bg-')}`}
                              title={`${level} risk`}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="p-3">
                    <div className={`font-medium ${
                      result.risk_score >= 70 ? 'text-red-600' :
                      result.risk_score >= 40 ? 'text-orange-600' :
                      result.risk_score >= 20 ? 'text-yellow-600' : 'text-green-600'
                    }`}>
                      {Math.round(result.risk_score)}
                    </div>
                  </td>
                  <td className="p-3">
                    <Button
                      onClick={() => toggleRowExpansion(result.rule_id)}
                      variant="outline"
                      size="sm"
                    >
                      {expandedRows.has(result.rule_id) ? 'Hide Details' : 'Show Details'}
                    </Button>
                  </td>
                </tr>
                
                {/* Expanded Row Details */}
                {expandedRows.has(result.rule_id) && (
                  <tr>
                    <td colSpan={5} className="p-0">
                      <div className="bg-gray-50 p-4 border-l-4 border-blue-500">
                        {/* Matched Clauses */}
                        {result.matched_clauses.length > 0 && (
                          <div className="mb-4">
                            <h4 className="font-medium mb-2">Matched Clauses:</h4>
                            <div className="space-y-3">
                              {result.matched_clauses.map((clause, index) => (
                                <div key={index} className="bg-white p-3 rounded border">
                                  <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center space-x-2">
                                      <span className="text-sm font-medium text-gray-600">
                                        Page {clause.page}
                                      </span>
                                      <span className={`text-xs px-2 py-1 rounded ${getRiskLevelColor(clause.risk_level)}`}>
                                        {clause.risk_level.toUpperCase()}
                                      </span>
                                    </div>
                                    <div className="text-sm text-gray-600">
                                      Confidence: {Math.round(clause.confidence * 100)}%
                                    </div>
                                  </div>
                                  <p className="text-sm text-gray-700 italic">
                                    "{clause.text.length > 200 ? clause.text.substring(0, 200) + '...' : clause.text}"
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {/* Recommendations */}
                        {result.recommendations.length > 0 && (
                          <div>
                            <h4 className="font-medium mb-2">Recommendations:</h4>
                            <ul className="space-y-1">
                              {result.recommendations.map((rec, index) => (
                                <li key={index} className="flex items-start text-sm">
                                  <span className="text-blue-500 mr-2 mt-1">•</span>
                                  <span>{rec}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
        
        {filteredAndSortedResults.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No compliance results match your current filters.
          </div>
        )}
      </div>
    </Card>
  )
}