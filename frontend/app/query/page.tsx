'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import Navbar from '@/components/Navbar';
import AgentWorkflow from '@/components/AgentWorkflow';
import { apiClient, QueryResponse } from '@/lib/api';

export default function QueryPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'auto' | 'local' | 'internet' | 'hybrid'>('auto');
  const [searching, setSearching] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setSearching(true);
    setError('');
    setResult(null);

    try {
      const response = await apiClient.query({
        query: query.trim(),
        mode,
        top_k: 5,
      });
      setResult(response);
    } catch (err: any) {
      setError(err.message || 'Query failed');
    } finally {
      setSearching(false);
    }
  };

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
      
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Query System</h1>

        {/* Query Form */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-2">
                Your Question
              </label>
              <textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                rows={3}
                placeholder="Ask me anything..."
                required
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search Mode
              </label>
              <div className="flex flex-wrap gap-3">
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="auto"
                    checked={mode === 'auto'}
                    onChange={(e) => setMode(e.target.value as any)}
                    className="mr-2"
                  />
                  <span className="text-sm font-semibold">🤖 Auto (Agent Decides)</span>
                </label>
                
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="local"
                    checked={mode === 'local'}
                    onChange={(e) => setMode(e.target.value as any)}
                    className="mr-2"
                  />
                  <span className="text-sm">📚 Local (Knowledge Base)</span>
                </label>
                
                <label className={`flex items-center ${!permissions.can_search_internet ? 'opacity-50' : ''}`}>
                  <input
                    type="radio"
                    value="internet"
                    checked={mode === 'internet'}
                    onChange={(e) => setMode(e.target.value as any)}
                    disabled={!permissions.can_search_internet}
                    className="mr-2"
                  />
                  <span className="text-sm">🌐 Internet Search</span>
                </label>
                
                <label className={`flex items-center ${!permissions.can_search_internet ? 'opacity-50' : ''}`}>
                  <input
                    type="radio"
                    value="hybrid"
                    checked={mode === 'hybrid'}
                    onChange={(e) => setMode(e.target.value as any)}
                    disabled={!permissions.can_search_internet}
                    className="mr-2"
                  />
                  <span className="text-sm">🔀 Hybrid (Both)</span>
                </label>
              </div>
              {mode === 'auto' && (
                <p className="mt-2 text-xs text-blue-600">
                  Agent will automatically search locally first, then use internet if context is insufficient
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={searching}
              className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {searching ? 'Searching...' : 'Search'}
            </button>
          </form>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-md mb-6">
            {error}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Agent Metadata */}
            {(result.cached || result.context_quality || result.agent_decision) && (
              <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg shadow p-4">
                <div className="flex items-center justify-between flex-wrap gap-2 text-sm">
                  {result.cached && (
                    <div className="flex items-center gap-2">
                      <span className="text-green-600 font-semibold">⚡ CACHED</span>
                      <span className="text-gray-600">
                        (similarity: {result.cache_score?.toFixed(3)})
                      </span>
                    </div>
                  )}
                  
                  {result.context_quality && (
                    <div className="flex items-center gap-2">
                      <span className="text-gray-700 font-medium">Context Quality:</span>
                      <span className={`font-semibold ${
                        result.context_quality.overall_score > 0.7 ? 'text-green-600' :
                        result.context_quality.overall_score > 0.4 ? 'text-yellow-600' :
                        'text-red-600'
                      }`}>
                        {(result.context_quality.overall_score * 100).toFixed(0)}%
                      </span>
                      <span className="text-gray-500 text-xs">
                        ({result.context_quality.reason})
                      </span>
                    </div>
                  )}
                  
                  {result.agent_decision && (
                    <div className="flex items-center gap-2">
                      <span className="text-gray-700 font-medium">Agent Decision:</span>
                      <span className="text-indigo-600 font-mono text-xs">
                        {result.agent_decision}
                      </span>
                    </div>
                  )}
                  
                  {result.processing_time_ms && (
                    <div className="text-gray-500 text-xs">
                      {result.processing_time_ms}ms
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Answer */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold">Answer</h2>
                <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded">
                  {result.mode}
                </span>
              </div>
              <div className="prose max-w-none">
                <p className="text-gray-800 whitespace-pre-wrap">{result.answer}</p>
              </div>
            </div>

            {/* Agent Workflow */}
            {result.decision_log && result.decision_log.length > 0 && (
              <AgentWorkflow result={result} />
            )}

            {/* Sources */}
            {result.sources && result.sources.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold mb-4">📄 Sources</h2>
                <div className="space-y-4">
                  {result.sources.map((source, idx) => (
                    <div key={idx} className="border border-gray-200 rounded-md p-4">
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-medium text-gray-900">{source.doc_name}</h3>
                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                          Score: {source.score.toFixed(2)}
                        </span>
                      </div>
                      {source.page && (
                        <p className="text-xs text-gray-500 mb-2">Page {source.page}</p>
                      )}
                      <p className="text-sm text-gray-700">{source.chunk_text}</p>
                      {source.doc_id && source.doc_id.startsWith('http') && (
                        <a
                          href={source.doc_id}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-indigo-600 hover:text-indigo-800 mt-2 inline-block"
                        >
                          View Source →
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


