'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function GeekNav() {
  const pathname = usePathname();

  const links = [
    { href: '/', label: 'DASHBOARD', icon: '📊' },
    { href: '/live', label: 'ALERT FEED', icon: '⚡' },
    { href: '/raw-feed', label: 'RAW DATA', icon: '📡' },
  ];

  return (
    <nav className="border-b border-green-800 bg-gray-900 mb-6">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <span className="text-green-400 text-xl font-bold font-mono">
              TRADING.SYS <span className="animate-pulse">▊</span>
            </span>
          </div>

          {/* Navigation Links */}
          <div className="flex space-x-1">
            {links.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`
                    px-4 py-2 font-mono text-sm font-medium rounded
                    transition-all duration-200
                    ${
                      isActive
                        ? 'bg-green-900 text-green-300 border border-green-700 shadow-[0_0_10px_rgba(0,255,65,0.3)]'
                        : 'text-green-600 hover:bg-green-950 hover:text-green-400 border border-transparent'
                    }
                  `}
                >
                  <span className="mr-2">{link.icon}</span>
                  {link.label}
                </Link>
              );
            })}
          </div>

          {/* System Status */}
          <div className="flex items-center space-x-2 text-xs font-mono">
            <div className="flex items-center">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
              <span className="text-green-500">SYSTEM ONLINE</span>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
