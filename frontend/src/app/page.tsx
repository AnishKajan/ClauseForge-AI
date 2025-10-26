import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { FileText, Shield, Zap, Users } from 'lucide-react'
import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center space-x-2">
              <FileText className="h-8 w-8 text-blue-600" />
              <span className="text-2xl font-bold text-gray-900">ClauseForge</span>
            </Link>
            <div className="flex items-center space-x-4">
              <Button variant="ghost" asChild className="transition-colors hover:bg-gray-100">
                <Link href="/login">Sign In</Link>
              </Button>
              <Button asChild className="transition-all hover:opacity-90">
                <Link href="/signup">Get Started</Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            AI-Powered Contract Analysis
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Analyze contracts, identify risks, and ensure compliance with our advanced AI platform. 
            Upload documents and get instant insights powered by Claude AI.
          </p>
          <div className="flex justify-center space-x-4">
            <Button size="lg" className="px-8 transition-all hover:opacity-90 active:scale-95" asChild>
              <Link href="/signup">Start Free Trial</Link>
            </Button>
            <Button size="lg" variant="outline" className="px-8 transition-all hover:bg-gray-50 active:scale-95" asChild>
              <Link href="/demo">Watch Demo</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-white">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            Powerful Features for Legal Professionals
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            <Link href="/features/analysis" className="block">
              <Card className="h-full transition-all hover:shadow-lg hover:-translate-y-1 cursor-pointer">
                <CardHeader>
                  <FileText className="h-12 w-12 text-blue-600 mb-4" />
                  <CardTitle>Document Analysis</CardTitle>
                  <CardDescription>
                    Upload PDFs and DOCX files for instant AI-powered analysis
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
            
            <Link href="/features/risk" className="block">
              <Card className="h-full transition-all hover:shadow-lg hover:-translate-y-1 cursor-pointer">
                <CardHeader>
                  <Shield className="h-12 w-12 text-green-600 mb-4" />
                  <CardTitle>Risk Assessment</CardTitle>
                  <CardDescription>
                    Identify potential risks and compliance issues automatically
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
            
            <Link href="/features/chat" className="block">
              <Card className="h-full transition-all hover:shadow-lg hover:-translate-y-1 cursor-pointer">
                <CardHeader>
                  <Zap className="h-12 w-12 text-yellow-600 mb-4" />
                  <CardTitle>Smart Q&A</CardTitle>
                  <CardDescription>
                    Ask natural language questions about your contracts
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
            
            <Link href="/features/teams" className="block">
              <Card className="h-full transition-all hover:shadow-lg hover:-translate-y-1 cursor-pointer">
                <CardHeader>
                  <Users className="h-12 w-12 text-purple-600 mb-4" />
                  <CardTitle>Team Collaboration</CardTitle>
                  <CardDescription>
                    Share insights and collaborate with your legal team
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileText className="h-6 w-6" />
              <span className="text-xl font-bold">ClauseForge</span>
            </div>
            <p className="text-gray-400">
              © 2024 ClauseForge. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}