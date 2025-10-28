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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <Navbar />
      
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header with gradient */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="text-4xl">🚀</div>
            <h1 className="text-4xl font-black bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              Live Streaming Query
            </h1>
          </div>
          <p className="text-gray-700 text-lg font-medium ml-14">
            Watch the AI agent work in real-time with cloud-powered search
          </p>
        </div>

        {/* Info Banner */}
        <div className="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl p-[2px] mb-8 shadow-lg">
          <div className="bg-white rounded-[10px] p-5">
            <div className="flex items-start gap-4">
              <div className="text-3xl">⚡</div>
              <div className="flex-1">
                <p className="font-bold text-gray-900 mb-2 text-lg">Real-Time Agent Workflow</p>
                <p className="text-gray-700 leading-relaxed">
                  Experience streaming updates as they happen! Watch each step: 
                  <span className="font-semibold text-indigo-600"> cache check</span> → 
                  <span className="font-semibold text-blue-600"> cloud embedding</span> → 
                  <span className="font-semibold text-purple-600"> vector search</span> → 
                  <span className="font-semibold text-green-600"> AI generation</span>
                </p>
                <div className="mt-3 flex gap-2 flex-wrap">
                  <span className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-bold">
                    No Model Loading
                  </span>
                  <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-bold">
                    Cloud Inference
                  </span>
                  <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold">
                    ~200ms Cache Hits
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <StreamingQuery />
      </div>
    </div>
  );
}

