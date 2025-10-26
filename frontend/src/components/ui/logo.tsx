import Image from 'next/image'
import { FileText } from 'lucide-react'

interface LogoProps {
  size?: number
  showText?: boolean
  className?: string
  useFavicon?: boolean
}

export function Logo({ 
  size = 32, 
  showText = true, 
  className = '', 
  useFavicon = false 
}: LogoProps) {
  if (useFavicon) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <Image
          src="/favicon-32x32.png"
          alt="ClauseForge"
          width={size}
          height={size}
          className="rounded"
        />
        {showText && (
          <span className="text-2xl font-bold text-gray-900">ClauseForge</span>
        )}
      </div>
    )
  }

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <FileText className={`text-blue-600`} style={{ width: size, height: size }} />
      {showText && (
        <span className="text-2xl font-bold text-gray-900">ClauseForge</span>
      )}
    </div>
  )
}