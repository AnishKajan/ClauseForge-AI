'use client'

import React, { useState, useEffect } from 'react'
import { Card } from './ui/card'
import { Button } from './ui/button'

interface ComplianceSummary {
  total_rules: number
  compliant: number
  non_compliant: number
  review_required: number
  missing_clauses: number
  overall_status: string
}

interface TrendData {
  date: string
  risk_score: number
  compliance_percentage: number
}

interface ComplianceDashboardProps {
  complianceSummary: ComplianceSummary
  trendData?: TrendData[]
  className?: string
  onRefresh?: () => void
}

const getStatusColor = (status: string): string => {
  switch (status.toLowerCase()) {
    case 'compliant':
      return 'text-green-600 bg-green-50 border-green-200'
    case 'non_compliant':
      return 'text-red-600 bg-red-50 border-red-200'
    case 'review_required':
      return 'text-yellow-600 bg-yellow-50 border-yellow-200'
    default:
      return 'text-gray-600 bg-gray-50 border-gray-200'
  }
}

const formatStatus = (status: string): string => {
  return status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
}

export const ComplianceDashboard: React.FC<ComplianceDashboardProps> = ({
  complianceSummary,
  trendData = [],
  className = '',
  onRefresh
}) => {
  const [selectedTimeframe, setSelectedTimeframe] = useState<'7d' | '30d' | '90d'>('30d')

  const compliancePercentage = complianceSummary.total_rules > 0 
    ? Math.round((complianceSummary.compliant / complianceSummary.total_rules) * 100)
    : 0

  const riskPercentage = complianceSummary.total_rules > 0
    ? Math.round(((complianceSummary.non_compliant + complianceSummary.review_required) / complianceSummary.total_rules) * 100)
    : 0

  // Simple trend calculation
  const getTrendDirection = (): 'up' | 'down' | 'stable' => {
    if (trendData.length < 2) return 'stable'
    
    const recent = trendData.slice(-3)
    const older = trendData.slice(-6, -3)
    
    if (recent.length === 0 || older.length === 0) return 'stable'
    
    const recentAvg = recent.reduce((sum, d) => sum + d.compliance_percentage, 0) / recent.length
    const olderAvg = older.reduce((sum, d) => sum + d.compliance_percentage, 0) / older.length
    
    const diff = recentAvg - olderAvg
    
    if (diff > 5) return 'up'
    if (diff < -5) return 'down'
    return 'stable'
  }

  const trendDirection = getTrendDirection()

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Compliance Dashboard</h2>
        {onRefresh && (
          <Button onClick={onRefresh} variant="outline" size="sm">
            Refresh Data
          </Button>
        )}
      </div>

      {/* Overall Status Card */}
      <Card className={`p-6 border-2 ${getStatusColor(complianceSummary.overall_status)}`}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold mb-2">Overall Compliance Status</h3>
            <div className="flex items-center space-x-4">
              <div className="text-4xl font-bold">
                {compliancePercentage}%
              </div>
              <div className="flex flex-col space-y-1">
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getStatusColor(complianceSummary.overall_status)}`}>
                  {formatStatus(complianceSummary.overall_status)}
                </span>
                <div className="flex items-center text-sm text-gray-600">
                  <span className="mr-1">
                    {trendDirection === 'up' ? '📈' : trendDirection === 'down' ? '📉' : '➡️'}
                  </span>
                  <span className="capitalize">
                    {trendDirection === 'up' ? 'Improving' : trendDirection === 'down' ? 'Declining' : 'Stable'}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-600 mb-1">Rules Evaluated</div>
            <div className="text-2xl font-semibold">
              {complianceSummary.total_rules}
            </div>
          </div>
        </div>
        
        {/* Compliance Progress Bar */}
        <div className="mt-4">
          <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
            <div className="h-full flex">
              <div
                className="bg-green-500 transition-all duration-500"
                style={{ width: `${(complianceSummary.compliant / complianceSummary.total_rules) * 100}%` }}
              />
              <div
                className="bg-yellow-500 transition-all duration-500"
                style={{ width: `${(complianceSummary.review_required / complianceSummary.total_rules) * 100}%` }}
              />
              <div
                className="bg-red-500 transition-all duration-500"
                style={{ width: `${(complianceSummary.non_compliant / complianceSummary.total_rules) * 100}%` }}
              />
            </div>
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-2">
            <span>Compliant: {complianceSummary.compliant}</span>
            <span>Review Required: {complianceSummary.review_required}</span>
            <span>Non-Compliant: {complianceSummary.non_compliant}</span>
          </div>
        </div>
      </Card>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 bg-green-50 border-green-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-700">Compliant Rules</p>
              <p className="text-2xl font-bold text-green-600">{complianceSummary.compliant}</p>
            </div>
            <div className="text-green-500 text-2xl">✅</div>
          </div>
          <div className="mt-2">
            <div className="text-xs text-green-600">
              {compliancePercentage}% of total rules
            </div>
          </div>
        </Card>

        <Card className="p-4 bg-red-50 border-red-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-red-700">Non-Compliant</p>
              <p className="text-2xl font-bold text-red-600">{complianceSummary.non_compliant}</p>
            </div>
            <div className="text-red-500 text-2xl">❌</div>
          </div>
          <div className="mt-2">
            <div className="text-xs text-red-600">
              {Math.round((complianceSummary.non_compliant / complianceSummary.total_rules) * 100)}% of total rules
            </div>
          </div>
        </Card>

        <Card className="p-4 bg-yellow-50 border-yellow-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-yellow-700">Review Required</p>
              <p className="text-2xl font-bold text-yellow-600">{complianceSummary.review_required}</p>
            </div>
            <div className="text-yellow-500 text-2xl">⚠️</div>
          </div>
          <div className="mt-2">
            <div className="text-xs text-yellow-600">
              {Math.round((complianceSummary.review_required / complianceSummary.total_rules) * 100)}% of total rules
            </div>
          </div>
        </Card>

        <Card className="p-4 bg-orange-50 border-orange-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-orange-700">Missing Clauses</p>
              <p className="text-2xl font-bold text-orange-600">{complianceSummary.missing_clauses}</p>
            </div>
            <div className="text-orange-500 text-2xl">📋</div>
          </div>
          <div className="mt-2">
            <div className="text-xs text-orange-600">
              Critical gaps identified
            </div>
          </div>
        </Card>
      </div>

      {/* Trend Analysis */}
      {trendData.length > 0 && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Compliance Trend</h3>
            <div className="flex space-x-2">
              {(['7d', '30d', '90d'] as const).map((timeframe) => (
                <button
                  key={timeframe}
                  onClick={() => setSelectedTimeframe(timeframe)}
                  className={`px-3 py-1 text-sm rounded ${
                    selectedTimeframe === timeframe
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {timeframe}
                </button>
              ))}
            </div>
          </div>
          
          {/* Simple trend visualization */}
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm text-gray-600">
              <span>Compliance Percentage Over Time</span>
              <span>Risk Score Trend</span>
            </div>
            
            {/* Simplified trend display */}
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-2">
                {trendData.slice(-5).map((data, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">
                      {new Date(data.date).toLocaleDateString()}
                    </span>
                    <div className="flex items-center space-x-2">
                      <div className="w-20 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${data.compliance_percentage}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium w-8">
                        {data.compliance_percentage}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="space-y-2">
                {trendData.slice(-5).map((data, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">
                      {new Date(data.date).toLocaleDateString()}
                    </span>
                    <div className="flex items-center space-x-2">
                      <div className="w-20 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all duration-300 ${
                            data.risk_score >= 70 ? 'bg-red-500' :
                            data.risk_score >= 40 ? 'bg-orange-500' :
                            data.risk_score >= 20 ? 'bg-yellow-500' : 'bg-green-500'
                          }`}
                          style={{ width: `${data.risk_score}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium w-8">
                        {data.risk_score}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Quick Actions */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Button variant="outline" className="justify-start">
            📊 Generate Compliance Report
          </Button>
          <Button variant="outline" className="justify-start">
            📋 Review Missing Clauses
          </Button>
          <Button variant="outline" className="justify-start">
            ⚙️ Update Compliance Rules
          </Button>
        </div>
      </Card>
    </div>
  )
}