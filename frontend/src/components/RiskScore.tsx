'use client'

import React from 'react'
import { Card } from './ui/card'

interface RiskFactor {
  factor_id: string
  name: string
  description: string
  weight: number
  score: number
  category: string
  recommendations: string[]
}

interface RiskScoreData {
  overall_score: number
  category: string
  confidence: number
  factors: RiskFactor[]
  trend?: string
}

interface RiskScoreProps {
  riskScore: RiskScoreData
  className?: string
}

const getRiskColor = (score: number): string => {
  if (score >= 80) return 'text-red-600 bg-red-50 border-red-200'
  if (score >= 60) return 'text-orange-600 bg-orange-50 border-orange-200'
  if (score >= 30) return 'text-yellow-600 bg-yellow-50 border-yellow-200'
  return 'text-green-600 bg-green-50 border-green-200'
}

const getRiskBadgeColor = (category: string): string => {
  switch (category.toLowerCase()) {
    case 'critical':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'high':
      return 'bg-orange-100 text-orange-800 border-orange-200'
    case 'medium':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    case 'low':
      return 'bg-green-100 text-green-800 border-green-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

const getTrendIcon = (trend?: string): string => {
  switch (trend) {
    case 'improving':
      return '↗️'
    case 'deteriorating':
      return '↘️'
    case 'stable':
      return '→'
    default:
      return ''
  }
}

const getTrendColor = (trend?: string): string => {
  switch (trend) {
    case 'improving':
      return 'text-green-600'
    case 'deteriorating':
      return 'text-red-600'
    case 'stable':
      return 'text-gray-600'
    default:
      return 'text-gray-400'
  }
}

export const RiskScore: React.FC<RiskScoreProps> = ({ riskScore, className = '' }) => {
  const { overall_score, category, confidence, factors, trend } = riskScore

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Overall Risk Score */}
      <Card className={`p-6 border-2 ${getRiskColor(overall_score)}`}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold mb-2">Overall Risk Score</h3>
            <div className="flex items-center space-x-4">
              <div className="text-4xl font-bold">
                {overall_score}
                <span className="text-lg font-normal">/100</span>
              </div>
              <div className="flex flex-col space-y-1">
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getRiskBadgeColor(category)}`}>
                  {category.toUpperCase()}
                </span>
                {trend && (
                  <div className={`flex items-center text-sm ${getTrendColor(trend)}`}>
                    <span className="mr-1">{getTrendIcon(trend)}</span>
                    <span className="capitalize">{trend}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-600 mb-1">Confidence</div>
            <div className="text-2xl font-semibold">
              {Math.round(confidence * 100)}%
            </div>
          </div>
        </div>
        
        {/* Risk Score Bar */}
        <div className="mt-4">
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all duration-500 ${
                overall_score >= 80 ? 'bg-red-500' :
                overall_score >= 60 ? 'bg-orange-500' :
                overall_score >= 30 ? 'bg-yellow-500' : 'bg-green-500'
              }`}
              style={{ width: `${overall_score}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>Low Risk</span>
            <span>Medium Risk</span>
            <span>High Risk</span>
            <span>Critical Risk</span>
          </div>
        </div>
      </Card>

      {/* Risk Factors Breakdown */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Risk Factors</h3>
        <div className="space-y-4">
          {factors.map((factor) => (
            <div key={factor.factor_id} className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-3">
                  <h4 className="font-medium">{factor.name}</h4>
                  <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
                    {factor.category}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">
                    Weight: {Math.round(factor.weight * 100)}%
                  </span>
                  <span className={`text-sm font-medium ${
                    factor.score >= 70 ? 'text-red-600' :
                    factor.score >= 40 ? 'text-orange-600' :
                    factor.score >= 20 ? 'text-yellow-600' : 'text-green-600'
                  }`}>
                    {Math.round(factor.score)}
                  </span>
                </div>
              </div>
              
              <p className="text-sm text-gray-600 mb-3">{factor.description}</p>
              
              {/* Factor Score Bar */}
              <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
                <div
                  className={`h-2 rounded-full ${
                    factor.score >= 70 ? 'bg-red-500' :
                    factor.score >= 40 ? 'bg-orange-500' :
                    factor.score >= 20 ? 'bg-yellow-500' : 'bg-green-500'
                  }`}
                  style={{ width: `${factor.score}%` }}
                />
              </div>
              
              {/* Recommendations */}
              {factor.recommendations.length > 0 && (
                <div className="mt-3">
                  <h5 className="text-sm font-medium text-gray-700 mb-2">Recommendations:</h5>
                  <ul className="text-sm text-gray-600 space-y-1">
                    {factor.recommendations.map((rec, index) => (
                      <li key={index} className="flex items-start">
                        <span className="text-blue-500 mr-2">•</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}