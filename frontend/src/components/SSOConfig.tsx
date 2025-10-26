'use client'

import React, { useState, useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { Card } from './ui/card'
import { Button } from './ui/button'

interface SSOConfig {
  type: 'oidc' | 'saml'
  name: string
  client_id?: string
  client_secret?: string
  discovery_url?: string
  issuer?: string
  entity_id?: string
  sso_url?: string
  sls_url?: string
  x509_cert?: string
  name_id_format?: string
  role_mapping: Record<string, string>
  default_role: string
  role_claim: string
  groups_claim: string
}

interface SSOConfigProps {
  orgId: string
}

export default function SSOConfig({ orgId }: SSOConfigProps) {
  const { data: session } = useSession()
  const [config, setConfig] = useState<SSOConfig>({
    type: 'oidc',
    name: '',
    role_mapping: {},
    default_role: 'viewer',
    role_claim: 'role',
    groups_claim: 'groups',
  })
  const [isConfigured, setIsConfigured] = useState(false)
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<any>(null)
  const [metadata, setMetadata] = useState<any>(null)

  useEffect(() => {
    loadSSOConfig()
  }, [orgId])

  const loadSSOConfig = async () => {
    try {
      const response = await fetch('/api/sso/config', {
        headers: {
          'Authorization': `Bearer ${session?.accessToken}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        if (data.configured) {
          setConfig(data.config)
          setIsConfigured(true)
        }
      }
    } catch (error) {
      console.error('Failed to load SSO config:', error)
    }
  }

  const handleSave = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/sso/configure', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.accessToken}`,
        },
        body: JSON.stringify(config),
      })

      if (response.ok) {
        const result = await response.json()
        setIsConfigured(true)
        setMetadata(result.metadata)
        alert('SSO configuration saved successfully!')
      } else {
        const error = await response.json()
        alert(`Failed to save SSO configuration: ${error.detail}`)
      }
    } catch (error) {
      alert('Failed to save SSO configuration')
    } finally {
      setLoading(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const response = await fetch(`/api/sso/test/${orgId}`, {
        headers: {
          'Authorization': `Bearer ${session?.accessToken}`,
        },
      })

      const result = await response.json()
      setTestResult(result)
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Failed to test SSO configuration',
      })
    } finally {
      setTesting(false)
    }
  }

  const handleDisable = async () => {
    if (!confirm('Are you sure you want to disable SSO? Users will no longer be able to sign in via SSO.')) {
      return
    }

    setLoading(true)
    try {
      const response = await fetch('/api/sso/config', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session?.accessToken}`,
        },
      })

      if (response.ok) {
        setIsConfigured(false)
        setConfig({
          type: 'oidc',
          name: '',
          role_mapping: {},
          default_role: 'viewer',
          role_claim: 'role',
          groups_claim: 'groups',
        })
        setMetadata(null)
        alert('SSO disabled successfully!')
      } else {
        const error = await response.json()
        alert(`Failed to disable SSO: ${error.detail}`)
      }
    } catch (error) {
      alert('Failed to disable SSO')
    } finally {
      setLoading(false)
    }
  }

  const addRoleMapping = () => {
    const ssoRole = prompt('Enter SSO role/group name:')
    const appRole = prompt('Enter application role (admin, reviewer, viewer):')
    
    if (ssoRole && appRole && ['admin', 'reviewer', 'viewer'].includes(appRole)) {
      setConfig(prev => ({
        ...prev,
        role_mapping: {
          ...prev.role_mapping,
          [ssoRole]: appRole,
        },
      }))
    }
  }

  const removeRoleMapping = (ssoRole: string) => {
    setConfig(prev => ({
      ...prev,
      role_mapping: Object.fromEntries(
        Object.entries(prev.role_mapping).filter(([key]) => key !== ssoRole)
      ),
    }))
  }

  if (session?.user?.role !== 'admin') {
    return (
      <Card className="p-6">
        <p className="text-gray-600">Only administrators can configure SSO.</p>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">
          Single Sign-On Configuration
        </h2>

        <div className="space-y-4">
          {/* Provider Type */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Provider Type
            </label>
            <select
              value={config.type}
              onChange={(e) => setConfig(prev => ({ ...prev, type: e.target.value as 'oidc' | 'saml' }))}
              className="w-full p-2 border rounded-md"
              disabled={isConfigured}
            >
              <option value="oidc">OpenID Connect (OIDC)</option>
              <option value="saml">SAML 2.0</option>
            </select>
          </div>

          {/* Provider Name */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Provider Name
            </label>
            <input
              type="text"
              value={config.name}
              onChange={(e) => setConfig(prev => ({ ...prev, name: e.target.value }))}
              className="w-full p-2 border rounded-md"
              placeholder="e.g., Azure AD, Okta"
            />
          </div>

          {/* OIDC Configuration */}
          {config.type === 'oidc' && (
            <>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Client ID
                </label>
                <input
                  type="text"
                  value={config.client_id || ''}
                  onChange={(e) => setConfig(prev => ({ ...prev, client_id: e.target.value }))}
                  className="w-full p-2 border rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Client Secret
                </label>
                <input
                  type="password"
                  value={config.client_secret || ''}
                  onChange={(e) => setConfig(prev => ({ ...prev, client_secret: e.target.value }))}
                  className="w-full p-2 border rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Discovery URL (optional)
                </label>
                <input
                  type="url"
                  value={config.discovery_url || ''}
                  onChange={(e) => setConfig(prev => ({ ...prev, discovery_url: e.target.value }))}
                  className="w-full p-2 border rounded-md"
                  placeholder="https://login.microsoftonline.com/{tenant}/.well-known/openid_configuration"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Issuer (if no discovery URL)
                </label>
                <input
                  type="url"
                  value={config.issuer || ''}
                  onChange={(e) => setConfig(prev => ({ ...prev, issuer: e.target.value }))}
                  className="w-full p-2 border rounded-md"
                />
              </div>
            </>
          )}

          {/* SAML Configuration */}
          {config.type === 'saml' && (
            <>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Entity ID
                </label>
                <input
                  type="text"
                  value={config.entity_id || ''}
                  onChange={(e) => setConfig(prev => ({ ...prev, entity_id: e.target.value }))}
                  className="w-full p-2 border rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  SSO URL
                </label>
                <input
                  type="url"
                  value={config.sso_url || ''}
                  onChange={(e) => setConfig(prev => ({ ...prev, sso_url: e.target.value }))}
                  className="w-full p-2 border rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Single Logout URL (optional)
                </label>
                <input
                  type="url"
                  value={config.sls_url || ''}
                  onChange={(e) => setConfig(prev => ({ ...prev, sls_url: e.target.value }))}
                  className="w-full p-2 border rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  X.509 Certificate
                </label>
                <textarea
                  value={config.x509_cert || ''}
                  onChange={(e) => setConfig(prev => ({ ...prev, x509_cert: e.target.value }))}
                  className="w-full p-2 border rounded-md h-32"
                  placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  NameID Format
                </label>
                <select
                  value={config.name_id_format || 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress'}
                  onChange={(e) => setConfig(prev => ({ ...prev, name_id_format: e.target.value }))}
                  className="w-full p-2 border rounded-md"
                >
                  <option value="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">Email Address</option>
                  <option value="urn:oasis:names:tc:SAML:2.0:nameid-format:persistent">Persistent</option>
                  <option value="urn:oasis:names:tc:SAML:2.0:nameid-format:transient">Transient</option>
                </select>
              </div>
            </>
          )}

          {/* Role Mapping */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Role Mapping
            </label>
            <div className="space-y-2">
              {Object.entries(config.role_mapping).map(([ssoRole, appRole]) => (
                <div key={ssoRole} className="flex items-center space-x-2">
                  <span className="flex-1 p-2 bg-gray-50 rounded">
                    {ssoRole} → {appRole}
                  </span>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => removeRoleMapping(ssoRole)}
                  >
                    Remove
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                onClick={addRoleMapping}
              >
                Add Role Mapping
              </Button>
            </div>
          </div>

          {/* Default Role */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Default Role
            </label>
            <select
              value={config.default_role}
              onChange={(e) => setConfig(prev => ({ ...prev, default_role: e.target.value }))}
              className="w-full p-2 border rounded-md"
            >
              <option value="viewer">Viewer</option>
              <option value="reviewer">Reviewer</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          {/* Role Claim */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Role Claim Name
            </label>
            <input
              type="text"
              value={config.role_claim}
              onChange={(e) => setConfig(prev => ({ ...prev, role_claim: e.target.value }))}
              className="w-full p-2 border rounded-md"
              placeholder="role"
            />
          </div>

          {/* Groups Claim */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Groups Claim Name
            </label>
            <input
              type="text"
              value={config.groups_claim}
              onChange={(e) => setConfig(prev => ({ ...prev, groups_claim: e.target.value }))}
              className="w-full p-2 border rounded-md"
              placeholder="groups"
            />
          </div>
        </div>

        <div className="flex space-x-4 mt-6">
          <Button
            onClick={handleSave}
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Save Configuration'}
          </Button>

          {isConfigured && (
            <>
              <Button
                variant="outline"
                onClick={handleTest}
                disabled={testing}
              >
                {testing ? 'Testing...' : 'Test Configuration'}
              </Button>

              <Button
                variant="outline"
                onClick={handleDisable}
                disabled={loading}
              >
                Disable SSO
              </Button>
            </>
          )}
        </div>
      </Card>

      {/* Test Results */}
      {testResult && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-2">Test Results</h3>
          <div className={`p-4 rounded-md ${testResult.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
            <p className="font-medium">
              {testResult.success ? '✓ Success' : '✗ Failed'}
            </p>
            <p>{testResult.message}</p>
            {testResult.endpoints && (
              <div className="mt-2">
                <p className="font-medium">Discovered Endpoints:</p>
                <ul className="list-disc list-inside">
                  <li>Issuer: {testResult.endpoints.issuer}</li>
                  <li>Authorization: {testResult.endpoints.authorization_endpoint}</li>
                  <li>Token: {testResult.endpoints.token_endpoint}</li>
                  <li>UserInfo: {testResult.endpoints.userinfo_endpoint}</li>
                </ul>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Metadata */}
      {metadata && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-2">Integration Information</h3>
          {metadata.type === 'saml' && (
            <div className="space-y-2">
              <p><strong>Entity ID:</strong> {metadata.entity_id}</p>
              <p><strong>ACS URL:</strong> {metadata.acs_url}</p>
              <div>
                <p><strong>Metadata XML:</strong></p>
                <a
                  href={`/api/sso/metadata/${orgId}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  Download Metadata
                </a>
              </div>
            </div>
          )}
          {metadata.type === 'oidc' && (
            <div className="space-y-2">
              <p><strong>Client ID:</strong> {metadata.client_id}</p>
              <p><strong>Redirect URI:</strong> {metadata.redirect_uri}</p>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}