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
      <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6 hover:shadow-xl transition-shadow">
        <form onSubmit={handleSubmit}>
          <div className="mb-5">
            <label htmlFor="query" className="block text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
              <span className="text-lg">💬</span>
              Your Question
            </label>
            <textarea
              id="query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full px-4 py-3 text-gray-900 border-2 border-gray-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all placeholder:text-gray-400"
              rows={3}
              placeholder="Ask me anything... (e.g., 'What is anarchism?')"
              required
              disabled={streaming}
            />
          </div>

          <div className="mb-5">
            <label className="block text-sm font-bold text-gray-900 mb-3">
              Search Mode
            </label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <label className={`flex items-center justify-center gap-2 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                mode === 'auto' 
                  ? 'border-indigo-500 bg-indigo-50 shadow-md' 
                  : 'border-gray-200 bg-white hover:border-indigo-300 hover:bg-indigo-50'
              }`}>
                <input
                  type="radio"
                  value="auto"
                  checked={mode === 'auto'}
                  onChange={(e) => setMode(e.target.value as any)}
                  disabled={streaming}
                  className="sr-only"
                />
                <span className="text-2xl">🤖</span>
                <span className="text-sm font-bold text-gray-900">Auto</span>
              </label>
              
              <label className={`flex items-center justify-center gap-2 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                mode === 'local' 
                  ? 'border-blue-500 bg-blue-50 shadow-md' 
                  : 'border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50'
              }`}>
                <input
                  type="radio"
                  value="local"
                  checked={mode === 'local'}
                  onChange={(e) => setMode(e.target.value as any)}
                  disabled={streaming}
                  className="sr-only"
                />
                <span className="text-2xl">📚</span>
                <span className="text-sm font-bold text-gray-900">Local</span>
              </label>
              
              <label className={`flex items-center justify-center gap-2 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                !permissions?.can_search_internet ? 'opacity-40 cursor-not-allowed' : ''
              } ${
                mode === 'internet' 
                  ? 'border-green-500 bg-green-50 shadow-md' 
                  : 'border-gray-200 bg-white hover:border-green-300 hover:bg-green-50'
              }`}>
                <input
                  type="radio"
                  value="internet"
                  checked={mode === 'internet'}
                  onChange={(e) => setMode(e.target.value as any)}
                  disabled={!permissions?.can_search_internet || streaming}
                  className="sr-only"
                />
                <span className="text-2xl">🌐</span>
                <span className="text-sm font-bold text-gray-900">Internet</span>
              </label>
              
              <label className={`flex items-center justify-center gap-2 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                !permissions?.can_search_internet ? 'opacity-40 cursor-not-allowed' : ''
              } ${
                mode === 'hybrid' 
                  ? 'border-purple-500 bg-purple-50 shadow-md' 
                  : 'border-gray-200 bg-white hover:border-purple-300 hover:bg-purple-50'
              }`}>
                <input
                  type="radio"
                  value="hybrid"
                  checked={mode === 'hybrid'}
                  onChange={(e) => setMode(e.target.value as any)}
                  disabled={!permissions?.can_search_internet || streaming}
                  className="sr-only"
                />
                <span className="text-2xl">🔀</span>
                <span className="text-sm font-bold text-gray-900">Hybrid</span>
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

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={streaming}
              className="flex-1 py-3 px-6 border border-transparent rounded-lg shadow-lg text-base font-bold text-white bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-[1.02] active:scale-[0.98]"
            >
              {streaming ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                  </svg>
                  Processing...
                </span>
              ) : '🚀 Search (Live Stream)'}
            </button>
            
            {streaming && (
              <button
                type="button"
                onClick={handleCancel}
                className="py-3 px-6 border-2 border-red-400 rounded-lg shadow-md text-base font-bold text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-all"
              >
                ⛔ Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Live Event Stream */}
      {events.length > 0 && (
        <div className="bg-gradient-to-br from-slate-900 via-gray-900 to-slate-800 rounded-xl shadow-2xl p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-xl font-bold text-white flex items-center gap-3">
              <span className={`text-2xl ${streaming ? 'animate-pulse' : ''}`}>
                {streaming ? '🔴' : '✅'}
              </span>
              Agent Workflow
              {streaming && <span className="text-sm font-normal text-blue-300">(Live)</span>}
            </h3>
            {!streaming && events.length > 0 && (
              <span className="px-3 py-1 bg-green-500 text-white rounded-full text-xs font-bold">
                Complete
              </span>
            )}
          </div>
          
          <div className="space-y-2 max-h-[500px] overflow-y-auto custom-scrollbar">
            {events.map((event, idx) => (
              <div 
                key={idx} 
                className="flex items-start gap-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700/50 hover:bg-slate-700/50 transition-all"
              >
                <span className="text-indigo-400 font-mono text-sm font-bold min-w-[24px]">{idx + 1}.</span>
                <div className="flex-1">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-gray-100 font-medium leading-relaxed">{event.message}</span>
                    {event.time_ms !== undefined && (
                      <span className="text-xs text-green-400 font-mono font-bold bg-green-900/30 px-2 py-1 rounded whitespace-nowrap">
                        +{event.time_ms}ms
                      </span>
                    )}
                  </div>
                  {event.quality && (
                    <div className="text-xs text-gray-400 mt-2 font-medium bg-slate-900/50 p-2 rounded border border-slate-700">
                      Score: <span className="text-blue-400 font-bold">{(event.quality.overall_score * 100).toFixed(1)}%</span> 
                      <span className="mx-1">•</span>
                      Vector: <span className="text-cyan-400">{(event.quality.vector_score * 100).toFixed(0)}%</span>
                      <span className="mx-1">•</span>
                      Coverage: <span className="text-purple-400">{(event.quality.coverage * 100).toFixed(0)}%</span>
                      <span className="mx-1">•</span>
                      LLM: <span className="text-green-400">{(event.quality.llm_confidence * 100).toFixed(0)}%</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          
          {streaming && (
            <div className="mt-5 flex items-center justify-center gap-2 text-sm text-blue-300 font-medium">
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-ping"></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
              <span>Processing your query...</span>
            </div>
          )}
        </div>
      )}

      {/* Live Performance Breakdown */}
      {Object.keys(livePerf).length > 0 && (
        <div className="bg-gradient-to-br from-gray-50 to-white rounded-xl shadow-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-xl font-bold text-gray-900 flex items-center gap-3">
              ⏱️ Performance Metrics
              {streaming && <span className="text-xs font-normal text-blue-600 animate-pulse bg-blue-50 px-3 py-1 rounded-full">Live</span>}
            </h3>
            {result?.cached && (
              <div className="flex items-center gap-2 px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold">
                <span>⚡</span>
                Cached Response
              </div>
            )}
          </div>
          
          <div className="space-y-2">
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
            <div className="mt-6 pt-5 border-t-2 border-gray-200">
              <div className="flex items-center justify-between">
                <span className="font-black text-gray-900 text-lg">Total Time</span>
                <span className="font-black text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-blue-600 text-2xl">
                  {result.processing_time_ms}ms
                </span>
              </div>
              {result.cached && (
                <div className="mt-2 text-sm text-gray-600">
                  <span className="font-semibold">Cache Age:</span> {result.cache_age_minutes} minutes • <span className="font-semibold">Similarity:</span> {(result.cache_score * 100).toFixed(1)}%
                </div>
              )}
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
        <div className="bg-gradient-to-br from-white to-blue-50/30 rounded-xl shadow-xl border-2 border-indigo-200 p-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-black text-gray-900 flex items-center gap-3">
              <span className="text-3xl">✨</span>
              AI Answer
            </h2>
            {/* Feedback Buttons */}
            <div className="flex gap-3 items-center">
              <span className="text-sm text-gray-700 font-bold">Rate:</span>
              <button
                onClick={() => handleFeedback('thumbs_up')}
                className={`p-3 rounded-xl transition-all transform hover:scale-110 ${
                  userFeedback === 'thumbs_up' 
                    ? 'bg-green-500 text-white shadow-lg' 
                    : 'bg-gray-100 hover:bg-green-100 text-gray-700 hover:shadow-md'
                }`}
                title="Thumbs up - Good answer"
              >
                <span className="text-xl">👍</span>
              </button>
              <button
                onClick={() => handleFeedback('thumbs_down')}
                className={`p-3 rounded-xl transition-all transform hover:scale-110 ${
                  userFeedback === 'thumbs_down' 
                    ? 'bg-red-500 text-white shadow-lg' 
                    : 'bg-gray-100 hover:bg-red-100 text-gray-700 hover:shadow-md'
                }`}
                title="Thumbs down - Poor answer"
              >
                <span className="text-xl">👎</span>
              </button>
            </div>
          </div>
          <div className="prose max-w-none">
            <p className="text-gray-900 whitespace-pre-wrap font-medium text-base leading-relaxed bg-white/50 p-4 rounded-lg border border-gray-200">{result.answer}</p>
          </div>
          
          {result.sources && result.sources.length > 0 && (
            <div className="mt-8">
              <h3 className="font-black text-lg text-gray-900 mb-4 flex items-center gap-2">
                <span>📚</span>
                Sources
              </h3>
              <div className="grid grid-cols-1 gap-3">
                {result.sources.map((source: any, idx: number) => (
                  <div 
                    key={idx} 
                    className="bg-white/80 border-2 border-gray-200 rounded-xl p-4 hover:shadow-lg transition-all hover:border-blue-300"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-bold text-gray-900">{source.doc_name}</div>
                      <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-bold">
                        Score: {source.score.toFixed(2)}
                      </span>
                    </div>
                    <div className="text-sm text-gray-700 leading-relaxed">{source.chunk_text}</div>
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
  // Calculate width for the progress bar
  const maxWidth = 300; // Max visible width in pixels
  const widthPercent = Math.min(100, (time / maxWidth) * 100);
  
  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
      highlighted ? 'bg-blue-50 border-2 border-blue-200' : 'bg-gray-50 border border-gray-200'
    }`}>
      <span className={`text-sm flex-shrink-0 ${highlighted ? 'font-black text-gray-900' : 'font-bold text-gray-800'}`}>
        {label}
      </span>
      <div className="flex-1 bg-gray-200 rounded-full h-8 overflow-hidden shadow-inner">
        <div
          className={`${color} h-full flex items-center justify-end pr-4 transition-all duration-700 ease-out shadow-lg`}
          style={{ 
            width: `${widthPercent}%`,
            animation: 'slideIn 0.7s ease-out'
          }}
        >
          <span className="text-sm text-white font-black drop-shadow">
            {time}ms
          </span>
        </div>
      </div>
      <span className={`text-sm font-mono font-bold min-w-[70px] text-right ${
        highlighted ? 'text-gray-900' : 'text-gray-700'
      }`}>
        {time}ms
      </span>
    </div>
  );
}


