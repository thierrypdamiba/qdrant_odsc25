'use client';

import { QueryResponse } from '@/lib/api';

interface AgentWorkflowProps {
  result: QueryResponse;
}

export default function AgentWorkflow({ result }: AgentWorkflowProps) {
  if (!result.decision_log || result.decision_log.length === 0) {
    return null;
  }

  const perf = result.performance_breakdown;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">🤖 Agent Workflow</h3>
      
      {/* Decision Log */}
      <div className="space-y-2 mb-6">
        {result.decision_log.map((step, idx) => (
          <div key={idx} className="flex items-start gap-2 text-sm">
            <span className="text-gray-400 font-mono">{idx + 1}.</span>
            <span className="text-gray-700">{step}</span>
          </div>
        ))}
      </div>

      {/* Performance Breakdown */}
      {perf && (
        <div className="border-t pt-4">
          <h4 className="text-sm font-semibold mb-3 text-gray-700">⏱️ Performance Breakdown</h4>
          
          <div className="space-y-2">
            {/* Total Time */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-900">Total Time</span>
              <span className="text-sm font-bold text-indigo-600">{perf.total_ms}ms</span>
            </div>

            {/* Individual Components */}
            {perf.cache_check_ms !== undefined && (
              <PerformanceBar
                label="Cache Check"
                time={perf.cache_check_ms}
                total={perf.total_ms}
                color="bg-purple-500"
              />
            )}
            
            {perf.embedding_ms !== undefined && (
              <PerformanceBar
                label="Query Embedding"
                time={perf.embedding_ms}
                total={perf.total_ms}
                color="bg-cyan-500"
              />
            )}
            
            {perf.qdrant_search_ms !== undefined && (
              <PerformanceBar
                label="Qdrant Vector Search"
                time={perf.qdrant_search_ms}
                total={perf.total_ms}
                color="bg-blue-500"
              />
            )}
            
            {perf.context_eval_ms !== undefined && (
              <PerformanceBar
                label="Context Evaluation"
                time={perf.context_eval_ms}
                total={perf.total_ms}
                color="bg-yellow-500"
              />
            )}
            
            {perf.internet_search_ms !== undefined && (
              <PerformanceBar
                label="Internet Search"
                time={perf.internet_search_ms}
                total={perf.total_ms}
                color="bg-green-500"
              />
            )}
            
            {perf.llm_generation_ms !== undefined && perf.llm_generation_ms > 0 && (
              <PerformanceBar
                label="Groq LLM Generation"
                time={perf.llm_generation_ms}
                total={perf.total_ms}
                color="bg-red-500"
              />
            )}
            
            {perf.cache_store_ms !== undefined && (
              <PerformanceBar
                label="Cache Storage"
                time={perf.cache_store_ms}
                total={perf.total_ms}
                color="bg-gray-500"
              />
            )}
          </div>

          {/* Visual Timeline */}
          <div className="mt-4">
            <div className="h-10 flex rounded overflow-hidden shadow-sm">
              {perf.cache_check_ms && (
                <div
                  className="bg-purple-500 flex items-center justify-center text-xs text-white font-medium relative group"
                  style={{ width: `${Math.max((perf.cache_check_ms / perf.total_ms) * 100, 1)}%` }}
                  title={`Cache Check: ${perf.cache_check_ms}ms`}
                >
                  <span className="absolute inset-0 flex items-center justify-center">Cache</span>
                </div>
              )}
              {perf.embedding_ms && (
                <div
                  className="bg-cyan-500 flex items-center justify-center text-xs text-white font-medium"
                  style={{ width: `${Math.max((perf.embedding_ms / perf.total_ms) * 100, 1)}%` }}
                  title={`Embedding: ${perf.embedding_ms}ms (${((perf.embedding_ms/perf.total_ms)*100).toFixed(3)}%)`}
                >
                  <span className="px-1">Emb</span>
                </div>
              )}
              {perf.qdrant_search_ms && (
                <div
                  className="bg-blue-600 flex items-center justify-center text-xs text-white font-bold border-l border-white"
                  style={{ width: `${Math.max((perf.qdrant_search_ms / perf.total_ms) * 100, 2)}%` }}
                  title={`Qdrant Vector Search: ${perf.qdrant_search_ms}ms (${((perf.qdrant_search_ms/perf.total_ms)*100).toFixed(3)}%)`}
                >
                  <span className="px-1">⚡{perf.qdrant_search_ms}ms</span>
                </div>
              )}
              {perf.context_eval_ms && (
                <div
                  className="bg-yellow-500 flex items-center justify-center text-xs text-white font-medium"
                  style={{ width: `${Math.max((perf.context_eval_ms / perf.total_ms) * 100, 1)}%` }}
                  title={`Context Eval: ${perf.context_eval_ms}ms (${((perf.context_eval_ms/perf.total_ms)*100).toFixed(2)}%)`}
                >
                  <span className="px-1">Eval</span>
                </div>
              )}
              {perf.llm_generation_ms && perf.llm_generation_ms > 0 && (
                <div
                  className="bg-red-500 flex items-center justify-center text-xs text-white font-bold border-l border-white"
                  style={{ width: `${(perf.llm_generation_ms / perf.total_ms) * 100}%` }}
                  title={`Groq LLM: ${perf.llm_generation_ms}ms (${((perf.llm_generation_ms/perf.total_ms)*100).toFixed(1)}%)`}
                >
                  {perf.llm_generation_ms > 200 && <span className="px-1">🤖 {perf.llm_generation_ms}ms</span>}
                </div>
              )}
              {perf.internet_search_ms && (
                <div
                  className="bg-green-600 flex items-center justify-center text-xs text-white font-bold border-l-2 border-white"
                  style={{ width: `${(perf.internet_search_ms / perf.total_ms) * 100}%` }}
                  title={`Perplexity Internet: ${perf.internet_search_ms}ms (${((perf.internet_search_ms/perf.total_ms)*100).toFixed(1)}%)`}
                >
                  {perf.internet_search_ms > 200 && <span className="px-2">🌐 Internet {perf.internet_search_ms}ms</span>}
                </div>
              )}
              {perf.cache_store_ms && (
                <div
                  className="bg-gray-500 flex items-center justify-center text-xs text-white"
                  style={{ width: `${Math.max((perf.cache_store_ms / perf.total_ms) * 100, 1)}%` }}
                  title={`Cache Store: ${perf.cache_store_ms}ms`}
                >
                  <span className="px-1">Store</span>
                </div>
              )}
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-2 px-1">
              <span>0ms</span>
              <span>{(perf.total_ms / 1000).toFixed(1)}s total</span>
            </div>
            <p className="text-xs text-gray-500 mt-1 text-center italic">
              Visual timeline showing component performance (even tiny components visible)
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function PerformanceBar({
  label,
  time,
  total,
  color
}: {
  label: string;
  time: number;
  total: number;
  color: string;
}) {
  const percentage = (time / total) * 100;
  
  // Format percentage with appropriate precision
  const formatPercentage = (pct: number) => {
    if (pct < 0.1) return pct.toFixed(3) + '%';  // 0.001%
    if (pct < 1) return pct.toFixed(2) + '%';    // 0.01%
    if (pct < 10) return pct.toFixed(1) + '%';   // 0.1%
    return pct.toFixed(0) + '%';                 // 1%
  };
  
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-600 w-40 font-medium">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
        <div
          className={`${color} h-full transition-all duration-300 flex items-center justify-end pr-2`}
          style={{ width: `${Math.max(percentage, 3)}%` }}  // Minimum 3% width for visibility
        >
          {time > 20 && (
            <span className="text-xs text-white font-medium">{time}ms</span>
          )}
        </div>
      </div>
      <span className="text-xs text-gray-700 w-24 text-right font-mono">
        {time}ms <span className="text-gray-500">({formatPercentage(percentage)})</span>
      </span>
    </div>
  );
}

