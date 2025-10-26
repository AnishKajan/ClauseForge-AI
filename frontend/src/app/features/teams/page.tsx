import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/ui/logo'
import { FileText, ArrowLeft, Users } from 'lucide-react'

export default function TeamsFeaturePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <header className="border-b bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link href="/">
              <Logo useFavicon={true} />
            </Link>
            <div className="flex items-center space-x-4">
              <Button variant="ghost" asChild>
                <Link href="/login">Sign In</Link>
              </Button>
              <Button asChild>
                <Link href="/signup">Get Started</Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          <Button variant="ghost" asChild className="mb-8">
            <Link href="/">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Home
            </Link>
          </Button>

          <div className="text-center mb-12">
            <Users className="h-16 w-16 text-purple-600 mx-auto mb-6" />
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              Team Collaboration
            </h1>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Share insights and collaborate with your legal team on contract analysis and review processes.
            </p>
          </div>

          <div className="text-center mt-12">
            <Button size="lg" asChild>
              <Link href="/signup">Try Team Collaboration</Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}