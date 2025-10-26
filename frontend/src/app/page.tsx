import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Logo } from '@/components/ui/logo'
import { FileText, Shield, Zap, Users } from 'lucide-react'
import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link href="/">
              <Logo size={36} showText={true} />
            </Link>
            <div className="flex items-center space-x-4">
              <Button variant="ghost" asChild className="text-clauseforge-primary hover:bg-clauseforge-primary/5 font-legal transition-colors">
                <Link href="/login">Sign In</Link>
              </Button>
              <Button asChild className="bg-clauseforge-primary hover:bg-clauseforge-primary-hover text-white font-legal transition-all rounded-lg">
                <Link href="/signup">Get Started</Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-5xl font-bold text-clauseforge-primary mb-6 font-legal">
            AI-Powered Contract Analysis
          </h1>
          <p className="text-xl text-clauseforge-primary/80 mb-8 max-w-3xl mx-auto font-legal">
            Analyze contracts, identify risks, and ensure compliance with our advanced AI platform. 
            Upload documents and get instant insights powered by Claude AI.
          </p>
          <div className="flex justify-center space-x-4">
            <Button size="lg" className="px-8 bg-clauseforge-primary hover:bg-clauseforge-primary-hover text-white font-legal transition-all rounded-lg" asChild>
              <Link href="/signup">Start Free Trial</Link>
            </Button>
            <Button size="lg" variant="outline" className="px-8 border-clauseforge-primary text-clauseforge-primary hover:bg-clauseforge-primary hover:text-white font-legal transition-all rounded-lg" asChild>
              <Link href="/demo">Watch Demo</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-white">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center text-clauseforge-primary mb-12 font-legal">
            Powerful Features for Legal Professionals
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            <Link href="/features/analysis" className="block">
              <Card className="h-full transition-all hover:shadow-lg hover:-translate-y-1 cursor-pointer border-gray-200 bg-white">
                <CardHeader>
                  <FileText className="h-12 w-12 text-clauseforge-primary mb-4" />
                  <CardTitle className="text-clauseforge-primary font-legal">Document Analysis</CardTitle>
                  <CardDescription className="text-clauseforge-primary/70 font-legal">
                    Upload PDFs and DOCX files for instant AI-powered analysis
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
            
            <Link href="/features/risk" className="block">
              <Card className="h-full transition-all hover:shadow-lg hover:-translate-y-1 cursor-pointer border-gray-200 bg-white">
                <CardHeader>
                  <Shield className="h-12 w-12 text-clauseforge-primary mb-4" />
                  <CardTitle className="text-clauseforge-primary font-legal">Risk Assessment</CardTitle>
                  <CardDescription className="text-clauseforge-primary/70 font-legal">
                    Identify potential risks and compliance issues automatically
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
            
            <Link href="/features/chat" className="block">
              <Card className="h-full transition-all hover:shadow-lg hover:-translate-y-1 cursor-pointer border-gray-200 bg-white">
                <CardHeader>
                  <Zap className="h-12 w-12 text-clauseforge-primary mb-4" />
                  <CardTitle className="text-clauseforge-primary font-legal">Smart Q&A</CardTitle>
                  <CardDescription className="text-clauseforge-primary/70 font-legal">
                    Ask natural language questions about your contracts
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
            
            <Link href="/features/teams" className="block">
              <Card className="h-full transition-all hover:shadow-lg hover:-translate-y-1 cursor-pointer border-gray-200 bg-white">
                <CardHeader>
                  <Users className="h-12 w-12 text-clauseforge-primary mb-4" />
                  <CardTitle className="text-clauseforge-primary font-legal">Team Collaboration</CardTitle>
                  <CardDescription className="text-clauseforge-primary/70 font-legal">
                    Share insights and collaborate with your legal team
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-clauseforge-primary text-white py-12">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Logo iconOnly={true} size={24} className="text-white" />
              <span className="text-xl font-bold font-legal">ClauseForge</span>
            </div>
            <p className="text-white/70 font-legal">
              © 2024 ClauseForge. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}