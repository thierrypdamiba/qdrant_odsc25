'use client';

import { useState, useRef } from 'react';
import { useAuth } from '@/lib/auth-context';
import { apiClient } from '@/lib/api';

interface StreamEvent {
  type: 'status' | 'result' | 'error' | 'decision';
  step?: string;
  message?: string;
  time_ms?: number;
  timestamp?: number;
  quality?: any;
  mode?: string;
  num_sources?: number;
  quality_score?: number;
  quality_reason?: string;
  suggested_modes?: Array<{ mode: string; reason: string }>;
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
  const [useMmr, setUseMmr] = useState(false);
  const [diversity, setDiversity] = useState(0.5);
  const [userFeedback, setUserFeedback] = useState<string | null>(null);
  const [modeSuggestions, setModeSuggestions] = useState<any>(null);
  const abortController = useRef<AbortController | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setStreaming(true);
    setError('');
    setEvents([]);
    setResult(null);
    setLivePerf({});
    setUserFeedback(null);
    setModeSuggestions(null);

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
          use_mmr: useMmr,
          diversity: diversity,
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

            // Handle decision events with mode suggestions
            if (eventType === 'decision' && eventData.suggested_modes) {
              setModeSuggestions(eventData);
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

  const handleFeedback = async (feedback: 'thumbs_up' | 'thumbs_down') => {
    if (!result || !result.query_id) return;
    
    setUserFeedback(feedback);
    
    try {
      await apiClient.submitFeedback({
        query_id: result.query_id,
        feedback
      });
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
  };

  const permissions = user?.permissions;

  return (
    <div className="space-y-6">
      {/* Query Form */}
      <div className="bg-white rounded-lg shadow p-6">
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="query" className="block text-sm font-semibold text-gray-900 mb-2">
              Your Question
            </label>
            <textarea
              id="query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full px-3 py-2 text-gray-900 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              rows={3}
              placeholder="Ask me anything..."
              required
              disabled={streaming}
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-semibold text-gray-900 mb-2">
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
                <span className="text-sm font-semibold text-gray-900">🤖 Auto (Watch Agent Decide!)</span>
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
                <span className="text-sm text-gray-900 font-semibold">📚 Local</span>
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
                <span className="text-sm text-gray-900 font-semibold">🌐 Internet</span>
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
                <span className="text-sm text-gray-900 font-semibold">🔀 Hybrid</span>
              </label>
            </div>
          </div>

          {/* Diversity Toggle */}
          <div className="mb-4">
            <label className="flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={useMmr}
                onChange={(e) => setUseMmr(e.target.checked)}
                disabled={streaming}
                className="mr-2 h-5 w-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-sm font-semibold text-gray-900">
                🎨 Enable Diversity Search (MMR)
              </span>
            </label>
            {useMmr && (
              <div className="mt-3 ml-7">
                <label className="block text-sm font-semibold text-gray-900 mb-2">
                  Diversity Level: {diversity.toFixed(1)}
                  <span className="text-xs ml-2 text-gray-600">
                    ({diversity === 0 ? 'Relevance only' : diversity === 1 ? 'Maximum diversity' : `Balance: ${(diversity * 100).toFixed(0)}% diversity`})
                  </span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={diversity}
                  onChange={(e) => setDiversity(parseFloat(e.target.value))}
                  disabled={streaming}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-900 font-semibold mt-1">
                  <span>Relevance</span>
                  <span>Balanced</span>
                  <span>Diversity</span>
                </div>
                <p className="mt-2 text-xs text-gray-600">
                  MMR (Maximal Marginal Relevance) balances relevance with diversity. Lower values prioritize similarity to your query, while higher values find more varied results.
                </p>
              </div>
            )}
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
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <span className={streaming ? 'animate-pulse' : ''}>🔴</span>
            Agent Workflow {streaming && '(Live)'}
          </h3>
          
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {events.map((event, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm">
                <span className="text-gray-900 font-mono text-xs font-bold">{idx + 1}.</span>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-900 font-semibold">{event.message}</span>
                    {event.time_ms !== undefined && (
                      <span className="text-xs text-indigo-600 font-mono ml-2 font-bold">
                        +{event.time_ms}ms
                      </span>
                    )}
                  </div>
                  {event.quality && (
                    <div className="text-xs text-gray-900 mt-1 font-semibold">
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
          <h3 className="text-lg font-bold text-black mb-4 flex items-center gap-2">
            ⏱️ Live Performance Metrics
            {streaming && <span className="text-xs text-blue-600 animate-pulse">(Updating...)</span>}
          </h3>
          
          <div className="space-y-3">
            {livePerf.cache_hit_ms !== undefined && result?.cached && (
              <>
                <LivePerformanceBar label="⚡ Cache Hit (Total)" time={livePerf.cache_hit_ms} color="bg-green-600" highlighted />
                {result.qdrant_server_ms !== undefined && (
                  <>
                    <LivePerformanceBar 
                      label="  └─ Qdrant Server (total)" 
                      time={Math.round(result.qdrant_server_ms)} 
                      color="bg-blue-500" 
                    />
                    {result.embedding_est_ms !== undefined && result.embedding_est_ms > 0 && (
                      <LivePerformanceBar 
                        label="      ├─ Cloud Embedding (est)" 
                        time={Math.round(result.embedding_est_ms)} 
                        color="bg-cyan-400" 
                      />
                    )}
                    {result.search_est_ms !== undefined && result.search_est_ms > 0 && (
                      <LivePerformanceBar 
                        label="      └─ Vector Search (est)" 
                        time={Math.round(result.search_est_ms)} 
                        color="bg-indigo-400" 
                      />
                    )}
                    <LivePerformanceBar 
                      label="  └─ Network Round-Trip" 
                      time={Math.round(result.network_ms || 0)} 
                      color="bg-gray-500" 
                    />
                  </>
                )}
              </>
            )}
            {livePerf.cache_check_ms !== undefined && !result?.cached && (
              <LivePerformanceBar label="Cache Check (miss)" time={livePerf.cache_check_ms} color="bg-purple-500" />
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
                <span className="font-bold text-black">Total Time</span>
                <span className="font-bold text-indigo-600 text-lg">{result.processing_time_ms}ms</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border-2 border-red-300 text-red-800 p-4 rounded-md font-medium">
          {error}
        </div>
      )}

      {/* Mode Suggestions (when quality is low) */}
      {modeSuggestions && !streaming && (
        <div className="bg-yellow-50 border-2 border-yellow-400 rounded-lg p-4">
          <h3 className="text-lg font-bold mb-3 text-gray-900">🎯 Agent Suggested Search Mode</h3>
          <p className="text-sm text-gray-800 mb-3 font-medium">
            Quality Score: {(modeSuggestions.quality_score * 100).toFixed(1)}% - {modeSuggestions.quality_reason}
          </p>
          <p className="text-sm text-gray-800 mb-3 font-semibold">Agent selected: <span className="font-bold">{modeSuggestions.mode}</span></p>
          
          {modeSuggestions.suggested_modes && modeSuggestions.suggested_modes.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-semibold text-gray-900">Alternative modes:</p>
              {modeSuggestions.suggested_modes.map((suggestion: any, idx: number) => (
                <div key={idx} className="text-sm pl-4 border-l-2 border-yellow-400">
                  <span className="font-bold text-gray-900">{suggestion.mode}:</span> {suggestion.reason}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Final Result */}
      {result && !streaming && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">Answer</h2>
            {/* Feedback Buttons */}
            <div className="flex gap-2 items-center">
              <span className="text-sm text-gray-900 font-bold mr-2">Rate:</span>
              <button
                onClick={() => handleFeedback('thumbs_up')}
                className={`p-2 rounded-full transition-colors ${
                  userFeedback === 'thumbs_up' 
                    ? 'bg-green-500 text-white' 
                    : 'bg-gray-100 hover:bg-green-100 text-gray-600'
                }`}
                title="Thumbs up - Good answer"
              >
                👍
              </button>
              <button
                onClick={() => handleFeedback('thumbs_down')}
                className={`p-2 rounded-full transition-colors ${
                  userFeedback === 'thumbs_down' 
                    ? 'bg-red-500 text-white' 
                    : 'bg-gray-100 hover:bg-red-100 text-gray-600'
                }`}
                title="Thumbs down - Poor answer"
              >
                👎
              </button>
            </div>
          </div>
          <div className="prose max-w-none">
            <p className="text-gray-900 whitespace-pre-wrap font-medium">{result.answer}</p>
          </div>
          
          {result.sources && result.sources.length > 0 && (
            <div className="mt-6">
              <h3 className="font-bold mb-3 text-gray-900">Sources:</h3>
              <div className="space-y-2">
                {result.sources.map((source: any, idx: number) => (
                  <div key={idx} className="text-sm border-l-2 border-indigo-300 pl-3 py-1">
                    <div className="font-semibold text-gray-900">{source.doc_name}</div>
                    <div className="text-gray-900 text-xs font-medium">{source.chunk_text}</div>
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
      <span className={`text-sm w-48 ${highlighted ? 'font-bold' : 'font-semibold'} text-gray-900`}>
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
      <span className={`text-sm font-mono w-20 text-right ${highlighted ? 'font-bold text-gray-900' : 'font-medium text-gray-900'}`}>
        {time}ms
      </span>
    </div>
  );
}


