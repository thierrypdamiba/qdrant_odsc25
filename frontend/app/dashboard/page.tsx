'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import Navbar from '@/components/Navbar';
import Link from 'next/link';

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  const permissions = user.permissions;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Welcome, {user.username}!</h1>
          <p className="mt-2 text-gray-800 font-semibold">Role: {user.role}</p>
        </div>

        {/* Permissions Card */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-bold mb-4 text-gray-900">Your Permissions</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex items-center space-x-2">
              <span className={permissions.can_search_local ? 'text-green-700 text-xl font-bold' : 'text-red-700 text-xl font-bold'}>
                {permissions.can_search_local ? '✓' : '✗'}
              </span>
              <span className="text-sm font-semibold text-gray-800">Local Search</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className={permissions.can_search_internet ? 'text-green-700 text-xl font-bold' : 'text-red-700 text-xl font-bold'}>
                {permissions.can_search_internet ? '✓' : '✗'}
              </span>
              <span className="text-sm font-semibold text-gray-800">Internet Search</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className={permissions.can_access_classified ? 'text-green-700 text-xl font-bold' : 'text-red-700 text-xl font-bold'}>
                {permissions.can_access_classified ? '✓' : '✗'}
              </span>
              <span className="text-sm font-semibold text-gray-800">Classified Docs</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className={permissions.can_upload_documents ? 'text-green-700 text-xl font-bold' : 'text-red-700 text-xl font-bold'}>
                {permissions.can_upload_documents ? '✓' : '✗'}
              </span>
              <span className="text-sm font-semibold text-gray-800">Upload Docs</span>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid md:grid-cols-3 gap-6">
          <Link
            href="/query"
            className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
          >
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-lg font-bold mb-2 text-gray-900">Query System</h3>
            <p className="text-gray-900 text-sm font-medium">
              Search through your knowledge base or the internet
            </p>
          </Link>

          {permissions.can_upload_documents && (
            <Link
              href="/knowledge-base"
              className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
            >
              <div className="text-4xl mb-4">📚</div>
              <h3 className="text-lg font-bold mb-2 text-gray-900">Knowledge Base</h3>
              <p className="text-gray-900 text-sm font-medium">
                Manage documents and view processing status
              </p>
            </Link>
          )}

          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-4xl mb-4">📊</div>
            <h3 className="text-lg font-bold mb-2 text-gray-900">Statistics</h3>
            <p className="text-gray-900 text-sm mb-4 font-medium">System overview</p>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-800 font-semibold">Status:</span>
                <span className="text-green-700 font-bold">Active</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-800 font-semibold">Mode:</span>
                <span className="font-bold text-gray-900">Mock Services</span>
              </div>
            </div>
          </div>
        </div>

        {/* Info Cards */}
        <div className="mt-8 grid md:grid-cols-2 gap-6">
          <div className="bg-blue-50 rounded-lg p-6 border-2 border-blue-200">
            <h3 className="text-lg font-bold text-blue-900 mb-2">💡 Quick Tip</h3>
            <p className="text-blue-900 text-sm font-medium">
              Use the Query page to search through your documents. You can switch between local search, 
              internet search, and hybrid mode depending on your permissions.
            </p>
          </div>

          <div className="bg-purple-50 rounded-lg p-6 border-2 border-purple-200">
            <h3 className="text-lg font-bold text-purple-900 mb-2">🚀 Getting Started</h3>
            <p className="text-purple-900 text-sm font-medium">
              {permissions.can_upload_documents 
                ? 'Upload documents to your knowledge base to start building your searchable database.'
                : 'Contact your administrator to upload documents to the knowledge base.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}


