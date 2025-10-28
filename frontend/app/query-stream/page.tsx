'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import Navbar from '@/components/Navbar';
import StreamingQuery from '@/components/StreamingQuery';

export default function StreamingQueryPage() {
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

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Live Streaming Query</h1>
          <p className="text-gray-900 font-semibold mt-2">
            Watch the agent work in real-time as it processes your query
          </p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-start gap-3">
            <div className="text-2xl">💡</div>
            <div className="flex-1 text-sm">
              <p className="font-semibold text-blue-900 mb-1">Real-Time Agent Workflow</p>
              <p className="text-blue-800">
                This page streams updates as they happen! You'll see each step: cache check → 
                Qdrant search → quality evaluation → agent decision → LLM generation → caching.
                No more waiting blindly for 30 seconds!
              </p>
            </div>
          </div>
        </div>

        <StreamingQuery />
      </div>
    </div>
  );
}

