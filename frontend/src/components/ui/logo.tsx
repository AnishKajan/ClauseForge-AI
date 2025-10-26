import Image from 'next/image'
import { Gavel } from 'lucide-react'

interface LogoProps {
  size?: number
  showText?: boolean
  className?: string
  useFavicon?: boolean
  iconOnly?: boolean
}

export function Logo({ 
  size = 32, 
  showText = true, 
  className = '', 
  useFavicon = false,
  iconOnly = false
}: LogoProps) {
  if (useFavicon) {
    return (
      <div className={`flex items-center space-x-3 ${className}`}>
        <Image
          src="/favicon-32x32.png"
          alt="ClauseForge"
          width={size}
          height={size}
          className="rounded"
        />
        {showText && !iconOnly && (
          <span className="text-2xl font-bold text-clauseforge-primary font-legal">ClauseForge</span>
        )}
      </div>
    )
  }

  if (iconOnly) {
    return (
      <div className={`flex items-center ${className}`}>
        <Gavel className="text-clauseforge-primary" style={{ width: size, height: size }} />
      </div>
    )
  }

  return (
    <div className={`flex items-center space-x-3 ${className}`}>
      <Gavel className="text-clauseforge-primary" style={{ width: size, height: size }} />
      {showText && (
        <span className="text-2xl font-bold text-clauseforge-primary font-legal">ClauseForge</span>
      )}
    </div>
  )
}