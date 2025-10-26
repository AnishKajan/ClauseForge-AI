import type { Metadata } from 'next'
import './globals.css'
import { Providers } from '@/components/providers'

export const metadata: Metadata = {
  title: 'ClauseForge - AI Contract Analyzer',
  description: 'AI-powered contract analysis and compliance platform',
  keywords: ['contract analysis', 'AI', 'legal tech', 'compliance', 'document review'],
  authors: [{ name: 'ClauseForge Team' }],
  creator: 'ClauseForge',
  publisher: 'ClauseForge',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  icons: {
    icon: [
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
    ],
    apple: [
      { url: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
    other: [
      {
        rel: 'mask-icon',
        url: '/safari-pinned-tab.svg',
        color: '#1E3A5F',
      },
    ],
  },
  manifest: '/site.webmanifest',
  themeColor: '#1E3A5F',
  colorScheme: 'light',
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://clauseforge.ai',
    siteName: 'ClauseForge',
    title: 'ClauseForge - AI Contract Analyzer',
    description: 'AI-powered contract analysis and compliance platform',
    images: [
      {
        url: '/android-chrome-512x512.png',
        width: 512,
        height: 512,
        alt: 'ClauseForge Logo',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'ClauseForge - AI Contract Analyzer',
    description: 'AI-powered contract analysis and compliance platform',
    images: ['/android-chrome-512x512.png'],
    creator: '@clauseforge',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="icon" href="/favicon-16x16.png" type="image/png" sizes="16x16" />
        <link rel="icon" href="/favicon-32x32.png" type="image/png" sizes="32x32" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="manifest" href="/site.webmanifest" />
        <meta name="theme-color" content="#1E3A5F" />
        <meta name="msapplication-TileColor" content="#1E3A5F" />
      </head>
      <body className="font-legal">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}