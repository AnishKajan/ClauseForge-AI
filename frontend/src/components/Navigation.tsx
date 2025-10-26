'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FileText, BarChart3, CreditCard, MessageSquare, Settings, LogOut } from 'lucide-react';
import { Button } from './ui/button';
import { Logo } from './ui/logo';

const navigationItems = [
  { name: 'Documents', href: '/', icon: FileText },
  { name: 'Analysis', href: '/analysis', icon: BarChart3 },
  { name: 'Chat', href: '/chat', icon: MessageSquare },
  { name: 'Billing', href: '/billing', icon: CreditCard },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            {/* Logo */}
            <div className="flex-shrink-0 flex items-center">
              <Link href="/" className="flex items-center">
                <Logo size={32} showText={true} />
              </Link>
            </div>

            {/* Navigation Links */}
            <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
              {navigationItems.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;
                
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium font-legal transition-colors ${
                      isActive
                        ? 'border-clauseforge-primary text-clauseforge-primary'
                        : 'border-transparent text-clauseforge-primary/70 hover:border-clauseforge-primary/30 hover:text-clauseforge-primary'
                    }`}
                  >
                    <Icon className="w-4 h-4 mr-2" />
                    {item.name}
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Right side */}
          <div className="hidden sm:ml-6 sm:flex sm:items-center space-x-4">
            <div className="text-sm text-clauseforge-primary/70 font-legal">
              Free Plan • 45/50 pages used
            </div>
            <Button variant="outline" size="sm" className="border-clauseforge-primary text-clauseforge-primary hover:bg-clauseforge-primary hover:text-white font-legal">
              <LogOut className="w-4 h-4 mr-2" />
              Sign Out
            </Button>
          </div>

          {/* Mobile menu button */}
          <div className="sm:hidden flex items-center">
            <Button variant="ghost" size="sm" className="text-clauseforge-primary">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      <div className="sm:hidden">
        <div className="pt-2 pb-3 space-y-1">
          {navigationItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`block pl-3 pr-4 py-2 border-l-4 text-base font-medium font-legal transition-colors ${
                  isActive
                    ? 'bg-clauseforge-primary/5 border-clauseforge-primary text-clauseforge-primary'
                    : 'border-transparent text-clauseforge-primary/70 hover:bg-clauseforge-primary/5 hover:border-clauseforge-primary/30 hover:text-clauseforge-primary'
                }`}
              >
                <div className="flex items-center">
                  <Icon className="w-4 h-4 mr-3" />
                  {item.name}
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}