# 🎨 Agent Workflow Visualization

## New Features Added

### 1. Real-Time Decision Log
Shows exactly what the agent is doing:

```
🔍 Checking semantic cache...
❌ Cache MISS - processing query...
📚 Searching local knowledge base (Qdrant)...
   Found 3 local sources (took 1329ms)
🔬 Evaluating context quality...
   Quality: 0.452 | Sufficient: False (took 200ms)
   Local knowledge base has partial information, internet search recommended
🔀 Agent Decision: HYBRID (enhancing local with internet)
   Hybrid search completed (13715ms)
💾 Caching result for future queries...
✓ Complete! Total time: 16003ms
```

### 2. Performance Breakdown
Detailed timing for each component:

| Component | Time | % of Total |
|-----------|------|------------|
| Cache Check | 756ms | 5% |
| **Qdrant Search** | **1,329ms** | **8%** |
| Context Evaluation | 200ms | 1% |
| **Internet Search** | **13,715ms** | **86%** ← Slowest! |
| Cache Storage | 65ms | <1% |
| **Total** | **16,003ms** | **100%** |

### 3. Visual Timeline
Proportional bar chart showing time distribution:

```
|████ Qdrant |█ Eval |█████████████████████████████████ Internet |████ Cache|
0ms          1.3s    1.5s                              15.2s              16.0s
```

---

## Example Outputs

### Scenario 1: Cache Hit
```json
{
  "decision_log": [
    "🔍 Checking semantic cache...",
    "⚡ Cache HIT! (similarity: 1.000)",
    "✓ Returning cached result (6 min old)"
  ],
  "performance_breakdown": {
    "total_ms": 790,
    "cache_check_ms": 790  ← 100% of time (instant!)
  }
}
```

**User sees**: ⚡ **Lightning fast** cache response!

---

### Scenario 2: Local Search (Good Context)
```json
{
  "decision_log": [
    "🔍 Checking semantic cache...",
    "❌ Cache MISS",
    "📚 Searching local knowledge base (Qdrant)...",
    "   Found 2 sources (took 892ms)",
    "🔬 Evaluating context quality...",
    "   Quality: 0.82 | Sufficient: True (took 1250ms)",
    "✅ Agent Decision: LOCAL ONLY (context sufficient)",
    "✓ Complete! Total time: 2200ms"
  ],
  "performance_breakdown": {
    "total_ms": 2200,
    "cache_check_ms": 58,
    "qdrant_search_ms": 892,     ← Qdrant took 40%
    "context_eval_ms": 1250      ← LLM eval took 57%
  }
}
```

**User sees**: Qdrant is fast, LLM evaluation takes longer

---

### Scenario 3: Internet Search (No Local Data)
```json
{
  "decision_log": [
    "🔍 Checking semantic cache...",
    "❌ Cache MISS",
    "📚 Searching local knowledge base (Qdrant)...",
    "   Found 0 sources (took 45ms)",
    "🔬 Evaluating context quality...",
    "   Quality: 0.0 | Sufficient: False",
    "🌐 Agent Decision: INTERNET ONLY (very limited local data)",
    "   Internet search completed (8250ms)",
    "💾 Caching...",
    "✓ Complete! Total time: 8560ms"
  ],
  "performance_breakdown": {
    "total_ms": 8560,
    "cache_check_ms": 42,
    "qdrant_search_ms": 45,           ← Fast (no results)
    "context_eval_ms": 65,
    "internet_search_ms": 8250,       ← 96% of time!
    "cache_store_ms": 158
  }
}
```

**User sees**: Perplexity API is the bottleneck when searching internet

---

### Scenario 4: Hybrid Search
```json
{
  "decision_log": [
    "🔍 Checking semantic cache...",
    "❌ Cache MISS",
    "📚 Searching local knowledge base (Qdrant)...",
    "   Found 3 sources (took 1329ms)",
    "🔬 Evaluating context quality...",
    "   Quality: 0.452 | Sufficient: False (took 200ms)",
    "   Local knowledge base has partial information",
    "🔀 Agent Decision: HYBRID (enhancing local with internet)",
    "   Hybrid search completed (13715ms)",
    "💾 Caching...",
    "✓ Complete! Total time: 16003ms"
  ],
  "performance_breakdown": {
    "total_ms": 16003,
    "cache_check_ms": 756,
    "qdrant_search_ms": 1329,         ← 8% - Qdrant
    "context_eval_ms": 200,           ← 1% - Quality check
    "internet_search_ms": 13715,      ← 86% - Perplexity (slowest!)
    "cache_store_ms": 65              ← <1% - Cache storage
  }
}
```

**User sees**: Internet search dominates total time (86%)

---

## Frontend UI Components

### Agent Metadata Bar
```
⚡ CACHED (similarity: 1.000) | Context Quality: 45% (partial) | 
Agent Decision: hybrid_partial_local | 16003ms
```

### Decision Log Panel
```
🤖 Agent Workflow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 🔍 Checking semantic cache...
2. ❌ Cache MISS - processing query...
3. 📚 Searching local knowledge base (Qdrant)...
4.    Found 3 local sources (took 1329ms)
5. 🔬 Evaluating context quality...
6.    Quality: 0.452 | Sufficient: False (took 200ms)
7.    Local knowledge base has partial information
8. 🔀 Agent Decision: HYBRID (enhancing local with internet)
9.    Hybrid search completed (13715ms)
10. 💾 Caching result for future queries...
11. ✓ Complete! Total time: 16003ms
```

### Performance Breakdown
```
⏱️ Performance Breakdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Time:              16,003ms

Cache Check:      [████] 756ms (5%)
Qdrant Search:    [████████] 1,329ms (8%)
Context Eval:     [█] 200ms (1%)
Internet Search:  [████████████████████████████] 13,715ms (86%)
Cache Storage:    [█] 65ms (<1%)

Timeline: |██|███|█|███████████████████████████|█|
         Cache Qdrant Eval Internet          Store
```

---

## Key Insights for Users

### Performance Insights:

1. **Qdrant is fast** (~1-2 seconds for search + embedding)
2. **Internet search is slow** (~8-15 seconds via Perplexity)
3. **Cache is instant** (~0.7 seconds vs 16 seconds)
4. **Context evaluation is cheap** (~200ms with LLM)

### Decision Making Transparency:

Users can see:
- **Why** agent chose specific mode
- **What** quality scores were
- **How long** each step took
- **Where** bottlenecks are

---

## Testing

**Visit**: http://localhost:3000/query

**Try these queries** to see different workflows:

1. **"What is Anarchism?"** (2nd time)
   - See: ⚡ Cache hit, instant response
   - Timing: ~700ms total (cache only)

2. **"Tell me about Anthropology"** (fresh query)
   - See: Full workflow with all steps
   - Timing: Qdrant + LLM eval + decision
   - Breakdown shows where time went

3. **"Latest tech news today?"**
   - See: Agent skips to internet (no local data)
   - Timing: Shows Perplexity dominates
   - Breakdown: 90%+ internet search

---

## Benefits

✅ **Transparency**: Users understand agent decisions
✅ **Performance**: Clear bottleneck identification  
✅ **Trust**: See the reasoning process
✅ **Education**: Learn when/why different modes used
✅ **Debugging**: Quickly identify slow components

---

**The UI now shows the complete agent workflow!** 🎉

Open http://localhost:3000/query to see it in action!

