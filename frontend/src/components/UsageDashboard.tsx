'use client';

import React, { useState, useEffect } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';

interface UsageAlert {
  type: string;
  usage_type: string;
  message: string;
  severity: 'critical' | 'warning' | 'info';
}

interface UsageHistory {
  month: string;
  usage: {
    pages?: number;
    tokens?: number;
    documents?: number;
  };
}

interface UsageAnalytics {
  period: {
    start: string;
    end: string;
    days: number;
  };
  subscription: {
    plan: string;
    status: string;
  };
  usage: {
    pages: number;
    tokens: number;
    documents: number;
  };
  limits: {
    pages_per_month: number;
    tokens_per_month: number;
    documents_per_month: number;
  };
  remaining: {
    pages_per_month: number;
    tokens_per_month: number;
    documents_per_month: number;
  };
  percentage_used: {
    pages_per_month: number;
    tokens_per_month: number;
    documents_per_month: number;
  };
  insights: string[];
  recommendations: string[];
}

export default function UsageDashboard() {
  const [analytics, setAnalytics] = useState<UsageAnalytics | null>(null);
  const [alerts, setAlerts] = useState<UsageAlert[]>([]);
  const [history, setHistory] = useState<UsageHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState(30);

  useEffect(() => {
    fetchUsageData();
  }, [selectedPeriod]);

  const fetchUsageData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      
      // Fetch usage analytics
      const analyticsResponse = await fetch(`/api/usage/analytics?days=${selectedPeriod}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const analyticsData = await analyticsResponse.json();
      
      if (analyticsData.success) {
        setAnalytics(analyticsData.data);
      }

      // Fetch usage alerts
      const alertsResponse = await fetch('/api/usage/alerts', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const alertsData = await alertsResponse.json();
      
      if (alertsData.success) {
        setAlerts([...alertsData.data.alerts, ...alertsData.data.warnings]);
      }

      // Fetch usage history
      const historyResponse = await fetch('/api/usage/history?months=6', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const historyData = await historyResponse.json();
      
      if (historyData.success) {
        setHistory(historyData.data.history);
      }

    } catch (err) {
      setError('Failed to load usage data');
      console.error('Error fetching usage data:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'warning': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'info': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'text-red-600';
    if (percentage >= 75) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getProgressBarColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 75) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-32 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
        <Button 
          onClick={fetchUsageData} 
          className="mt-2"
          variant="outline"
        >
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Usage Dashboard</h2>
        <div className="flex space-x-2">
          {[7, 30, 90].map((days) => (
            <Button
              key={days}
              variant={selectedPeriod === days ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedPeriod(days)}
            >
              {days} days
            </Button>
          ))}
        </div>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-lg font-semibold">Usage Alerts</h3>
          {alerts.map((alert, index) => (
            <div
              key={index}
              className={`p-3 rounded-lg border ${getSeverityColor(alert.severity)}`}
            >
              <p className="font-medium">{alert.message}</p>
            </div>
          ))}
        </div>
      )}

      {/* Current Usage Overview */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Pages</h3>
              <span className={`text-2xl font-bold ${getUsageColor(analytics.percentage_used.pages_per_month)}`}>
                {analytics.percentage_used.pages_per_month.toFixed(1)}%
              </span>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Used</span>
                <span>{formatNumber(analytics.usage.pages)}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${getProgressBarColor(analytics.percentage_used.pages_per_month)}`}
                  style={{ width: `${Math.min(analytics.percentage_used.pages_per_month, 100)}%` }}
                ></div>
              </div>
              <div className="flex justify-between text-sm text-gray-600">
                <span>Remaining: {formatNumber(analytics.remaining.pages_per_month)}</span>
                <span>Limit: {formatNumber(analytics.limits.pages_per_month)}</span>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Tokens</h3>
              <span className={`text-2xl font-bold ${getUsageColor(analytics.percentage_used.tokens_per_month)}`}>
                {analytics.percentage_used.tokens_per_month.toFixed(1)}%
              </span>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Used</span>
                <span>{formatNumber(analytics.usage.tokens)}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${getProgressBarColor(analytics.percentage_used.tokens_per_month)}`}
                  style={{ width: `${Math.min(analytics.percentage_used.tokens_per_month, 100)}%` }}
                ></div>
              </div>
              <div className="flex justify-between text-sm text-gray-600">
                <span>Remaining: {formatNumber(analytics.remaining.tokens_per_month)}</span>
                <span>Limit: {formatNumber(analytics.limits.tokens_per_month)}</span>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Documents</h3>
              <span className={`text-2xl font-bold ${getUsageColor(analytics.percentage_used.documents_per_month)}`}>
                {analytics.percentage_used.documents_per_month.toFixed(1)}%
              </span>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Used</span>
                <span>{formatNumber(analytics.usage.documents)}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${getProgressBarColor(analytics.percentage_used.documents_per_month)}`}
                  style={{ width: `${Math.min(analytics.percentage_used.documents_per_month, 100)}%` }}
                ></div>
              </div>
              <div className="flex justify-between text-sm text-gray-600">
                <span>Remaining: {formatNumber(analytics.remaining.documents_per_month)}</span>
                <span>Limit: {formatNumber(analytics.limits.documents_per_month)}</span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Usage History Chart */}
      {history.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Usage History (Last 6 Months)</h3>
          <div className="space-y-4">
            {history.map((month, index) => (
              <div key={index} className="flex items-center space-x-4">
                <div className="w-20 text-sm font-medium">
                  {new Date(month.month + '-01').toLocaleDateString('en-US', { 
                    month: 'short', 
                    year: 'numeric' 
                  })}
                </div>
                <div className="flex-1 grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Pages: </span>
                    <span className="font-medium">{formatNumber(month.usage.pages || 0)}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Tokens: </span>
                    <span className="font-medium">{formatNumber(month.usage.tokens || 0)}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Docs: </span>
                    <span className="font-medium">{formatNumber(month.usage.documents || 0)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Insights and Recommendations */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {analytics.insights.length > 0 && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Usage Insights</h3>
              <ul className="space-y-2">
                {analytics.insights.map((insight, index) => (
                  <li key={index} className="flex items-start space-x-2">
                    <svg className="w-4 h-4 text-blue-500 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm">{insight}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {analytics.recommendations.length > 0 && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Recommendations</h3>
              <ul className="space-y-2">
                {analytics.recommendations.map((recommendation, index) => (
                  <li key={index} className="flex items-start space-x-2">
                    <svg className="w-4 h-4 text-green-500 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm">{recommendation}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}

      {/* Subscription Info */}
      {analytics && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Subscription Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-gray-600">Current Plan</p>
              <p className="font-semibold capitalize">{analytics.subscription.plan}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Status</p>
              <p className={`font-semibold capitalize ${
                analytics.subscription.status === 'active' ? 'text-green-600' : 'text-red-600'
              }`}>
                {analytics.subscription.status}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Analysis Period</p>
              <p className="font-semibold">{analytics.period.days} days</p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}