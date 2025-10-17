'use client';

import { useState, useRef } from 'react';
import { useAuth } from '@/lib/auth-context';

interface StreamEvent {
  type: 'status' | 'result' | 'error';
  step?: string;
  message?: string;
  time_ms?: number;
  timestamp?: number;
  quality?: any;
  mode?: string;
  num_sources?: number;
  [key: string]: any;
}

interface StreamingQueryProps {
  onComplete?: (result: any) => void;
}

export default function StreamingQuery({ onComplete }: StreamingQueryProps) {
  const { user } = useAuth();
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'auto' | 'local' | 'internet' | 'hybrid'>('auto');
  const [streaming, setStreaming] = useState(false);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [livePerf, setLivePerf] = useState<any>({});
  const abortController = useRef<AbortController | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setStreaming(true);
    setError('');
    setEvents([]);
    setResult(null);
    setLivePerf({});

    // Create abort controller for cancellation
    abortController.current = new AbortController();

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8000/query/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          query: query.trim(),
          mode,
          top_k: 5,
        }),
        signal: abortController.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete events
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;

          // Parse SSE format: "event: type\ndata: {...}"
          const eventMatch = line.match(/event: (\w+)\ndata: (.+)/);
          if (eventMatch) {
            const eventType = eventMatch[1];
            const eventData = JSON.parse(eventMatch[2]);

            const event: StreamEvent = {
              type: eventType as any,
              ...eventData,
            };

            setEvents((prev) => [...prev, event]);

            // Update live performance metrics
            if (event.time_ms !== undefined) {
              setLivePerf((prev: any) => ({
                ...prev,
                [event.step + '_ms']: event.time_ms,
                last_update: Date.now()
              }));
            }

            if (eventType === 'result') {
              setResult(eventData);
              if (onComplete) {
                onComplete(eventData);
              }
            } else if (eventType === 'error') {
              setError(eventData.message);
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Streaming failed');
      }
    } finally {
      setStreaming(false);
      abortController.current = null;
    }
  };

  const handleCancel = () => {
    if (abortController.current) {
      abortController.current.abort();
      setStreaming(false);
      setEvents((prev) => [
        ...prev,
        { type: 'status', step: 'cancelled', message: '🛑 Cancelled by user', timestamp: 0 },
      ]);
    }
  };

  const permissions = user?.permissions;

  return (
    <div className="space-y-6">
      {/* Query Form */}
      <div className="bg-white rounded-lg shadow p-6">
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
              disabled={streaming}
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
                  disabled={streaming}
                  className="mr-2"
                />
                <span className="text-sm font-semibold">🤖 Auto (Watch Agent Decide!)</span>
              </label>
              
              <label className="flex items-center">
                <input
                  type="radio"
                  value="local"
                  checked={mode === 'local'}
                  onChange={(e) => setMode(e.target.value as any)}
                  disabled={streaming}
                  className="mr-2"
                />
                <span className="text-sm">📚 Local</span>
              </label>
              
              <label className={`flex items-center ${!permissions?.can_search_internet ? 'opacity-50' : ''}`}>
                <input
                  type="radio"
                  value="internet"
                  checked={mode === 'internet'}
                  onChange={(e) => setMode(e.target.value as any)}
                  disabled={!permissions?.can_search_internet || streaming}
                  className="mr-2"
                />
                <span className="text-sm">🌐 Internet</span>
              </label>
              
              <label className={`flex items-center ${!permissions?.can_search_internet ? 'opacity-50' : ''}`}>
                <input
                  type="radio"
                  value="hybrid"
                  checked={mode === 'hybrid'}
                  onChange={(e) => setMode(e.target.value as any)}
                  disabled={!permissions?.can_search_internet || streaming}
                  className="mr-2"
                />
                <span className="text-sm">🔀 Hybrid</span>
              </label>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={streaming}
              className="flex-1 py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {streaming ? 'Processing...' : 'Search (Live Stream)'}
            </button>
            
            {streaming && (
              <button
                type="button"
                onClick={handleCancel}
                className="py-2 px-4 border border-red-300 rounded-md shadow-sm text-sm font-medium text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Live Event Stream */}
      {events.length > 0 && (
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className={streaming ? 'animate-pulse' : ''}>🔴</span>
            Agent Workflow {streaming && '(Live)'}
          </h3>
          
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {events.map((event, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm">
                <span className="text-gray-400 font-mono text-xs">{idx + 1}.</span>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-800">{event.message}</span>
                    {event.time_ms !== undefined && (
                      <span className="text-xs text-indigo-600 font-mono ml-2 font-semibold">
                        +{event.time_ms}ms
                      </span>
                    )}
                  </div>
                  {event.quality && (
                    <div className="text-xs text-gray-600 mt-1">
                      Score: {(event.quality.overall_score * 100).toFixed(1)}% 
                      (Vector: {(event.quality.vector_score * 100).toFixed(0)}%, 
                      Coverage: {(event.quality.coverage * 100).toFixed(0)}%, 
                      LLM: {(event.quality.llm_confidence * 100).toFixed(0)}%)
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          
          {streaming && (
            <div className="mt-4 flex items-center gap-2 text-sm text-blue-600">
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
              Processing...
            </div>
          )}
        </div>
      )}

      {/* Live Performance Breakdown */}
      {Object.keys(livePerf).length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            ⏱️ Live Performance Metrics
            {streaming && <span className="text-xs text-blue-600 animate-pulse">(Updating...)</span>}
          </h3>
          
          <div className="space-y-3">
            {livePerf.cache_check_ms !== undefined && (
              <LivePerformanceBar label="Cache Check" time={livePerf.cache_check_ms} color="bg-purple-500" />
            )}
            {livePerf.embedding_done_ms !== undefined && (
              <LivePerformanceBar label="Query Embedding" time={livePerf.embedding_done_ms} color="bg-cyan-500" />
            )}
            {livePerf.qdrant_done_ms !== undefined && (
              <LivePerformanceBar label="⚡ Qdrant Search" time={livePerf.qdrant_done_ms} color="bg-blue-600" highlighted />
            )}
            {livePerf.evaluation_done_ms !== undefined && (
              <LivePerformanceBar label="Context Evaluation" time={livePerf.evaluation_done_ms} color="bg-yellow-500" />
            )}
            {livePerf.llm_done_ms !== undefined && (
              <LivePerformanceBar label="Groq LLM Generation" time={livePerf.llm_done_ms} color="bg-red-500" />
            )}
            {livePerf.internet_done_ms !== undefined && (
              <LivePerformanceBar label="🌐 Internet Search" time={livePerf.internet_done_ms} color="bg-green-600" highlighted />
            )}
          </div>

          {result?.processing_time_ms && (
            <div className="mt-4 pt-4 border-t">
              <div className="flex items-center justify-between">
                <span className="font-semibold">Total Time</span>
                <span className="font-bold text-indigo-600 text-lg">{result.processing_time_ms}ms</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-md">
          {error}
        </div>
      )}

      {/* Final Result */}
      {result && !streaming && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Answer</h2>
          <div className="prose max-w-none">
            <p className="text-gray-800 whitespace-pre-wrap">{result.answer}</p>
          </div>
          
          {result.sources && result.sources.length > 0 && (
            <div className="mt-6">
              <h3 className="font-semibold mb-3">Sources:</h3>
              <div className="space-y-2">
                {result.sources.map((source: any, idx: number) => (
                  <div key={idx} className="text-sm border-l-2 border-indigo-300 pl-3 py-1">
                    <div className="font-medium">{source.doc_name}</div>
                    <div className="text-gray-600 text-xs">{source.chunk_text}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function LivePerformanceBar({ 
  label, 
  time, 
  color, 
  highlighted = false 
}: { 
  label: string; 
  time: number; 
  color: string; 
  highlighted?: boolean;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className={`text-sm w-48 ${highlighted ? 'font-bold' : 'font-medium'} text-gray-700`}>
        {label}
      </span>
      <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
        <div
          className={`${color} h-full flex items-center justify-end pr-3 transition-all duration-500 ease-out`}
          style={{ 
            width: time < 10 ? '10%' : time < 100 ? '25%' : time < 1000 ? '50%' : '100%',
            animation: 'slideIn 0.5s ease-out'
          }}
        >
          <span className="text-sm text-white font-bold">{time}ms</span>
        </div>
      </div>
      <span className={`text-sm font-mono w-20 text-right ${highlighted ? 'font-bold text-gray-900' : 'text-gray-600'}`}>
        {time}ms
      </span>
    </div>
  );
}


