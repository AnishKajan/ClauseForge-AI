import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { FileText, Shield, Zap, Users } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileText className="h-8 w-8 text-blue-600" />
              <span className="text-2xl font-bold text-gray-900">LexiScan</span>
            </div>
            <div className="flex items-center space-x-4">
              <Button variant="ghost">Sign In</Button>
              <Button>Get Started</Button>
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
            <Button size="lg" className="px-8">
              Start Free Trial
            </Button>
            <Button size="lg" variant="outline" className="px-8">
              Watch Demo
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
            <Card>
              <CardHeader>
                <FileText className="h-12 w-12 text-blue-600 mb-4" />
                <CardTitle>Document Analysis</CardTitle>
                <CardDescription>
                  Upload PDFs and DOCX files for instant AI-powered analysis
                </CardDescription>
              </CardHeader>
            </Card>
            
            <Card>
              <CardHeader>
                <Shield className="h-12 w-12 text-green-600 mb-4" />
                <CardTitle>Risk Assessment</CardTitle>
                <CardDescription>
                  Identify potential risks and compliance issues automatically
                </CardDescription>
              </CardHeader>
            </Card>
            
            <Card>
              <CardHeader>
                <Zap className="h-12 w-12 text-yellow-600 mb-4" />
                <CardTitle>Smart Q&A</CardTitle>
                <CardDescription>
                  Ask natural language questions about your contracts
                </CardDescription>
              </CardHeader>
            </Card>
            
            <Card>
              <CardHeader>
                <Users className="h-12 w-12 text-purple-600 mb-4" />
                <CardTitle>Team Collaboration</CardTitle>
                <CardDescription>
                  Share insights and collaborate with your legal team
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileText className="h-6 w-6" />
              <span className="text-xl font-bold">LexiScan</span>
            </div>
            <p className="text-gray-400">
              © 2024 LexiScan. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}