'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import { Button } from './ui/button'

interface BackNavigationProps {
  label?: string
  href?: string
  className?: string
}

export function BackNavigation({ 
  label = 'Back', 
  href, 
  className = '' 
}: BackNavigationProps) {
  const router = useRouter()

  const handleBack = () => {
    if (href) {
      router.push(href)
    } else {
      router.back()
    }
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleBack}
      className={`mb-4 text-clauseforge-primary hover:bg-clauseforge-primary/10 ${className}`}
    >
      <ArrowLeft className="w-4 h-4 mr-2" />
      {label}
    </Button>
  )
}

export default BackNavigation