'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Card } from './ui/card'
import { Button } from './ui/button'

interface TeamMember {
  id: string
  email: string
  role: string
  provider: string
  is_active: boolean
  email_verified: boolean
  last_login: string | null
  created_at: string
}

interface Document {
  id: string
  title: string
  file_type: string
  file_size: number
  status: string
  uploaded_by: {
    id: string | null
    email: string | null
  }
  created_at: string
  updated_at: string
  processed_at: string | null
}

interface Activity {
  id: string
  action: string
  resource_type: string
  resource_id: string | null
  user: {
    id: string | null
    email: string | null
  }
  payload: any
  ip_address: string | null
  created_at: string
}

interface TeamWorkspaceProps {
  orgId: string
}

export default function TeamWorkspace({ orgId }: TeamWorkspaceProps) {
  const { user, accessToken } = useAuth()
  const [activeTab, setActiveTab] = useState<'members' | 'documents' | 'activity'>('members')
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([])
  const [documents, setDocuments] = useState<Document[]>([])
  const [activities, setActivities] = useState<Activity[]>([])
  const [loading, setLoading] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('viewer')
  const [inviting, setInviting] = useState(false)

  useEffect(() => {
    loadData()
  }, [activeTab, orgId])

  const loadData = async () => {
    setLoading(true)
    try {
      if (activeTab === 'members') {
        await loadTeamMembers()
      } else if (activeTab === 'documents') {
        await loadDocuments()
      } else if (activeTab === 'activity') {
        await loadActivity()
      }
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadTeamMembers = async () => {
    const response = await fetch('/api/organization/team', {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    })

    if (response.ok) {
      const data = await response.json()
      setTeamMembers(data.team_members)
    }
  }

  const loadDocuments = async () => {
    const response = await fetch('/api/organization/documents/shared', {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    })

    if (response.ok) {
      const data = await response.json()
      setDocuments(data.documents)
    }
  }

  const loadActivity = async () => {
    const response = await fetch('/api/organization/activity', {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    })

    if (response.ok) {
      const data = await response.json()
      setActivities(data.activities)
    }
  }

  const handleInviteMember = async () => {
    if (!inviteEmail || !inviteRole) return

    setInviting(true)
    try {
      const response = await fetch('/api/organization/team/invite', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          email: inviteEmail,
          role: inviteRole,
        }),
      })

      if (response.ok) {
        setInviteEmail('')
        setInviteRole('viewer')
        await loadTeamMembers()
        alert('Team member invited successfully!')
      } else {
        const error = await response.json()
        alert(`Failed to invite team member: ${error.detail}`)
      }
    } catch (error) {
      alert('Failed to invite team member')
    } finally {
      setInviting(false)
    }
  }

  const handleUpdateRole = async (userId: string, newRole: string) => {
    try {
      const response = await fetch(`/api/organization/team/${userId}/role`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ role: newRole }),
      })

      if (response.ok) {
        await loadTeamMembers()
        alert('Role updated successfully!')
      } else {
        const error = await response.json()
        alert(`Failed to update role: ${error.detail}`)
      }
    } catch (error) {
      alert('Failed to update role')
    }
  }

  const handleRemoveMember = async (userId: string, email: string) => {
    if (!confirm(`Are you sure you want to remove ${email} from the team?`)) {
      return
    }

    try {
      const response = await fetch(`/api/organization/team/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      })

      if (response.ok) {
        await loadTeamMembers()
        alert('Team member removed successfully!')
      } else {
        const error = await response.json()
        alert(`Failed to remove team member: ${error.detail}`)
      }
    } catch (error) {
      alert('Failed to remove team member')
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    if (bytes === 0) return '0 Bytes'
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-red-100 text-red-800'
      case 'reviewer':
        return 'bg-blue-100 text-blue-800'
      case 'viewer':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'processing':
        return 'bg-yellow-100 text-yellow-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const canManageTeam = user?.role === 'admin'

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {['members', 'documents', 'activity'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>
      </div>

      {/* Team Members Tab */}
      {activeTab === 'members' && (
        <div className="space-y-6">
          {/* Invite Member */}
          {canManageTeam && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Invite Team Member</h3>
              <div className="flex space-x-4">
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="Email address"
                  className="flex-1 p-2 border rounded-md"
                />
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="p-2 border rounded-md"
                >
                  <option value="viewer">Viewer</option>
                  <option value="reviewer">Reviewer</option>
                  <option value="admin">Admin</option>
                </select>
                <Button
                  onClick={handleInviteMember}
                  disabled={inviting || !inviteEmail}
                >
                  {inviting ? 'Inviting...' : 'Invite'}
                </Button>
              </div>
            </Card>
          )}

          {/* Team Members List */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Team Members</h3>
            {loading ? (
              <p>Loading team members...</p>
            ) : (
              <div className="space-y-4">
                {teamMembers.map((member) => (
                  <div key={member.id} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <div>
                          <p className="font-medium">{member.email}</p>
                          <p className="text-sm text-gray-500">
                            Joined {formatDate(member.created_at)}
                            {member.last_login && ` • Last login ${formatDate(member.last_login)}`}
                          </p>
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleBadgeColor(member.role)}`}>
                          {member.role}
                        </span>
                        {!member.is_active && (
                          <span className="px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                            Pending
                          </span>
                        )}
                      </div>
                    </div>
                    {canManageTeam && member.id !== user?.id && (
                      <div className="flex space-x-2">
                        <select
                          value={member.role}
                          onChange={(e) => handleUpdateRole(member.id, e.target.value)}
                          className="p-1 border rounded text-sm"
                        >
                          <option value="viewer">Viewer</option>
                          <option value="reviewer">Reviewer</option>
                          <option value="admin">Admin</option>
                        </select>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRemoveMember(member.id, member.email)}
                        >
                          Remove
                        </Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Shared Documents Tab */}
      {activeTab === 'documents' && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Shared Documents</h3>
          {loading ? (
            <p>Loading documents...</p>
          ) : (
            <div className="space-y-4">
              {documents.map((doc) => (
                <div key={doc.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <div>
                        <p className="font-medium">{doc.title}</p>
                        <p className="text-sm text-gray-500">
                          {formatFileSize(doc.file_size)} • {doc.file_type} • 
                          Uploaded by {doc.uploaded_by.email || 'Unknown'} on {formatDate(doc.created_at)}
                        </p>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadgeColor(doc.status)}`}>
                        {doc.status}
                      </span>
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    <Button variant="outline" size="sm">
                      View
                    </Button>
                    <Button variant="outline" size="sm">
                      Share
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Team Activity Tab */}
      {activeTab === 'activity' && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Team Activity</h3>
          {loading ? (
            <p>Loading activity...</p>
          ) : (
            <div className="space-y-4">
              {activities.map((activity) => (
                <div key={activity.id} className="flex items-start space-x-3 p-4 border rounded-lg">
                  <div className="flex-1">
                    <p className="font-medium">
                      {activity.user.email || 'System'} {activity.action.replace('_', ' ')}
                    </p>
                    <p className="text-sm text-gray-500">
                      {activity.resource_type && `${activity.resource_type} • `}
                      {formatDate(activity.created_at)}
                      {activity.ip_address && ` • ${activity.ip_address}`}
                    </p>
                    {activity.payload && Object.keys(activity.payload).length > 0 && (
                      <details className="mt-2">
                        <summary className="text-sm text-blue-600 cursor-pointer">Details</summary>
                        <pre className="mt-1 text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                          {JSON.stringify(activity.payload, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  )
}