'use client'

import { useEffect, useState } from 'react'
import { useSession, signOut } from 'next-auth/react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Logo } from '@/components/ui/logo'
import { FileText, Upload, MessageSquare, Users, Settings, LogOut } from 'lucide-react'

interface HealthStatus {
  status: 'healthy' | 'unhealthy' | 'loading'
  message?: string
}

export default function DashboardPage() {
  const { data: session } = useSession()
  const [healthStatus, setHealthStatus] = useState<HealthStatus>({ status: 'loading' })

  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/health`)
        if (response.ok) {
          const data = await response.json()
          setHealthStatus({ 
            status: 'healthy', 
            message: `Backend OK - ${data.message || 'Connected'}` 
          })
        } else {
          setHealthStatus({ 
            status: 'unhealthy', 
            message: `Backend Error - ${response.status}` 
          })
        }
      } catch (error) {
        setHealthStatus({ 
          status: 'unhealthy', 
          message: 'Backend Unreachable' 
        })
      }
    }

    checkBackendHealth()
  }, [])

  const handleSignOut = () => {
    signOut({ callbackUrl: '/' })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link href="/">
              <Logo useFavicon={true} />
            </Link>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                Welcome, {session?.user?.email}
              </span>
              <Button variant="ghost" size="sm" onClick={handleSignOut}>
                <LogOut className="h-4 w-4 mr-2" />
                Sign Out
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Status Card */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>System Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${
                healthStatus.status === 'healthy' ? 'bg-green-500' :
                healthStatus.status === 'unhealthy' ? 'bg-red-500' : 'bg-yellow-500'
              }`} />
              <span className="text-sm">
                {healthStatus.message || 'Checking backend status...'}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Welcome Section */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
          <p className="text-gray-600">
            Manage your contracts and analyze documents with AI-powered insights.
          </p>
        </div>

        {/* Quick Actions */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardHeader className="pb-3">
              <Upload className="h-8 w-8 text-blue-600 mb-2" />
              <CardTitle className="text-lg">Upload Document</CardTitle>
              <CardDescription>
                Upload a new contract for analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link href="/upload">Upload Now</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardHeader className="pb-3">
              <FileText className="h-8 w-8 text-green-600 mb-2" />
              <CardTitle className="text-lg">My Documents</CardTitle>
              <CardDescription>
                View and manage your documents
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" className="w-full">
                View Documents
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardHeader className="pb-3">
              <MessageSquare className="h-8 w-8 text-purple-600 mb-2" />
              <CardTitle className="text-lg">AI Chat</CardTitle>
              <CardDescription>
                Ask questions about your contracts
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" className="w-full">
                Start Chat
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow cursor-pointer">
            <CardHeader className="pb-3">
              <Settings className="h-8 w-8 text-gray-600 mb-2" />
              <CardTitle className="text-lg">Settings</CardTitle>
              <CardDescription>
                Manage your account settings
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" className="w-full">
                Settings
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Your latest document analyses and activities
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8 text-gray-500">
              <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No recent activity</p>
              <p className="text-sm">Upload your first document to get started</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}