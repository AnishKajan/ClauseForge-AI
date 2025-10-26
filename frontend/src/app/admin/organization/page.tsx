'use client'

import React, { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import SSOConfig from '@/components/SSOConfig'
import TeamWorkspace from '@/components/TeamWorkspace'

interface OrganizationDetails {
  id: string
  name: string
  created_at: string
  updated_at: string
  sso_configured: boolean
  team_members: any[]
  document_stats: any
  subscription: any
}

export default function OrganizationPage() {
  const { data: session } = useSession()
  const [activeTab, setActiveTab] = useState<'overview' | 'team' | 'sso' | 'settings'>('overview')
  const [orgDetails, setOrgDetails] = useState<OrganizationDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [orgName, setOrgName] = useState('')
  const [updating, setUpdating] = useState(false)

  useEffect(() => {
    loadOrganizationDetails()
  }, [])

  const loadOrganizationDetails = async () => {
    try {
      const response = await fetch('/api/organization/details', {
        headers: {
          'Authorization': `Bearer ${session?.accessToken}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setOrgDetails(data)
        setOrgName(data.name)
      }
    } catch (error) {
      console.error('Failed to load organization details:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateOrganization = async () => {
    if (!orgName.trim()) return

    setUpdating(true)
    try {
      const response = await fetch('/api/organization/settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.accessToken}`,
        },
        body: JSON.stringify({ name: orgName }),
      })

      if (response.ok) {
        await loadOrganizationDetails()
        alert('Organization updated successfully!')
      } else {
        const error = await response.json()
        alert(`Failed to update organization: ${error.detail}`)
      }
    } catch (error) {
      alert('Failed to update organization')
    } finally {
      setUpdating(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!orgDetails) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-600">Failed to load organization details.</p>
      </div>
    )
  }

  if (session?.user?.role !== 'admin') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="p-8">
          <h2 className="text-xl font-semibold mb-4">Access Denied</h2>
          <p className="text-gray-600">Only administrators can access organization settings.</p>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Organization Management</h1>
          <p className="mt-2 text-gray-600">
            Manage your organization settings, team members, and SSO configuration.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-8">
          <nav className="-mb-px flex space-x-8">
            {[
              { key: 'overview', label: 'Overview' },
              { key: 'team', label: 'Team Workspace' },
              { key: 'sso', label: 'Single Sign-On' },
              { key: 'settings', label: 'Settings' },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Organization Info */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Organization</h3>
              <div className="space-y-2">
                <p><strong>Name:</strong> {orgDetails.name}</p>
                <p><strong>Created:</strong> {formatDate(orgDetails.created_at)}</p>
                <p><strong>Team Size:</strong> {orgDetails.team_members.length} members</p>
                <p><strong>SSO:</strong> {orgDetails.sso_configured ? 'Configured' : 'Not configured'}</p>
              </div>
            </Card>

            {/* Document Stats */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Documents</h3>
              <div className="space-y-2">
                <p><strong>Total:</strong> {orgDetails.document_stats?.total_documents || 0}</p>
                <p><strong>Storage:</strong> {orgDetails.document_stats?.total_size_mb || 0} MB</p>
                <div className="mt-4">
                  <p className="text-sm font-medium mb-2">By Status:</p>
                  {orgDetails.document_stats?.status_breakdown && Object.entries(orgDetails.document_stats.status_breakdown).map(([status, count]) => (
                    <p key={status} className="text-sm">
                      {status}: {count as number}
                    </p>
                  ))}
                </div>
              </div>
            </Card>

            {/* Subscription */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Subscription</h3>
              {orgDetails.subscription ? (
                <div className="space-y-2">
                  <p><strong>Plan:</strong> {orgDetails.subscription.plan}</p>
                  <p><strong>Status:</strong> {orgDetails.subscription.status}</p>
                  <p><strong>Since:</strong> {formatDate(orgDetails.subscription.created_at)}</p>
                </div>
              ) : (
                <p className="text-gray-600">No active subscription</p>
              )}
            </Card>

            {/* Recent Team Members */}
            <Card className="p-6 md:col-span-2 lg:col-span-3">
              <h3 className="text-lg font-semibold mb-4">Recent Team Members</h3>
              <div className="space-y-3">
                {orgDetails.team_members.slice(0, 5).map((member) => (
                  <div key={member.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium">{member.email}</p>
                      <p className="text-sm text-gray-500">
                        {member.role} • Joined {formatDate(member.created_at)}
                      </p>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      member.is_active ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {member.is_active ? 'Active' : 'Pending'}
                    </span>
                  </div>
                ))}
                {orgDetails.team_members.length > 5 && (
                  <Button
                    variant="outline"
                    onClick={() => setActiveTab('team')}
                    className="w-full"
                  >
                    View All Team Members ({orgDetails.team_members.length})
                  </Button>
                )}
              </div>
            </Card>
          </div>
        )}

        {/* Team Workspace Tab */}
        {activeTab === 'team' && (
          <TeamWorkspace orgId={orgDetails.id} />
        )}

        {/* SSO Tab */}
        {activeTab === 'sso' && (
          <SSOConfig orgId={orgDetails.id} />
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Organization Settings</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Organization Name
                  </label>
                  <input
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    className="w-full p-2 border rounded-md"
                  />
                </div>
                <Button
                  onClick={handleUpdateOrganization}
                  disabled={updating || orgName === orgDetails.name}
                >
                  {updating ? 'Updating...' : 'Update Organization'}
                </Button>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4 text-red-600">Danger Zone</h3>
              <div className="space-y-4">
                <div className="p-4 border border-red-200 rounded-lg bg-red-50">
                  <h4 className="font-medium text-red-800 mb-2">Delete Organization</h4>
                  <p className="text-sm text-red-700 mb-4">
                    This action cannot be undone. This will permanently delete your organization,
                    all team members, documents, and associated data.
                  </p>
                  <Button variant="outline" className="text-red-600 border-red-300 hover:bg-red-50">
                    Delete Organization
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}