'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const navItems = [
    { href: '/dashboard', label: 'Dashboard', icon: '📊' },
    { href: '/query', label: 'Query', icon: '🔍' },
    { href: '/query-stream', label: 'Live Stream', icon: '📡' },
    { href: '/knowledge-base', label: 'Knowledge Base', icon: '📚', requiresUpload: true },
  ];

  return (
    <nav className="bg-white shadow-md border-b-2 border-gray-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Link href="/dashboard" className="text-xl font-bold text-indigo-700 hover:text-indigo-900">
                Agentic RAG
              </Link>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {navItems.map((item) => {
                if (item.requiresUpload && user && !user.permissions.can_upload_documents) {
                  return null;
                }
                
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-bold ${
                      isActive
                        ? 'border-indigo-700 text-gray-900'
                        : 'border-transparent text-gray-900 hover:border-gray-400 hover:text-gray-900'
                    }`}
                  >
                    <span className="mr-2">{item.icon}</span>
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="flex items-center space-x-4">
                <div className="text-sm">
                  <p className="font-bold text-gray-900">{user?.username}</p>
                  <p className="text-xs font-semibold text-gray-900">{user?.role}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="inline-flex items-center px-4 py-2 border-2 border-indigo-700 text-sm leading-4 font-bold rounded-md text-white bg-indigo-700 hover:bg-indigo-800 hover:border-indigo-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-600"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}


