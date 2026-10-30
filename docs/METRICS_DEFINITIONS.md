# Devmate Empirical Metrics & Benchmark Definitions

This document defines the mathematical formulation, evaluation methodology, and acceptance criteria for all benchmarked metrics across Devmate. In accordance with Hard Rule 2, these definitions are specified and committed prior to baseline and optimization experiments.

---

## 1. Retrieval Metrics

All retrieval evaluations are conducted against the fixed ground truth dataset `evals/datasets/retrieval_ground_truth.json` (50 queries against the `devmate` reference codebase). Each sample $q_i \in Q$ has a human-labeled ground truth pair $(F^*_i, S^*_i)$ denoting the target file and target symbol (class or function).

### 1.1 Hit@K
A query $q_i$ is a hit at rank $K$ if the correct file $F^*_i$ (or symbol $S^*_i$) appears in the top $K$ retrieved chunks:

$$\text{Hit@K}(q_i) = \begin{cases} 1 & \text{if } (F^*_i, S^*_i) \in \text{TopK}(q_i) \\ 0 & \text{otherwise} \end{cases}$$

$$\text{Hit@K} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \text{Hit@K}(q_i)$$

Reported for $K=1$ and $K=5$.

### 1.2 Mean Reciprocal Rank (MRR)
MRR measures how high the first relevant chunk appears in the ranked results:

$$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$

where $\text{rank}_i$ is the 1-based index of the first ground-truth match. If no match appears in the retrieved results, $\frac{1}{\text{rank}_i} = 0$.

### 1.3 Precision@K
The fraction of retrieved chunks in the top $K$ that are relevant:

$$\text{Precision@K} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{|\text{Relevant chunks in TopK}(q_i)|}{K}$$

For single-target ground truth, this corresponds to $\frac{\text{Hit@K}(q_i)}{K}$.

### 1.4 Context Token Size
The total prompt tokens consumed by feeding retrieved context into the agent prompt:

$$\text{Context Size Reduction (\%)} = \left( 1 - \frac{\text{Context Tokens}_{\text{optimized}}}{\text{Context Tokens}_{\text{baseline}}} \right) \times 100\%$$

---

## 2. Bug-Fix Completion Benchmark

The Bug-Fix Benchmark (`evals/datasets/bugfix_bench/`) evaluates autonomous debugging on 25 isolated tasks (Python and JavaScript/TypeScript).

### 2.1 Pass Criteria (Binary per Task)
A task $T_j$ is resolved ($\text{Resolved}(T_j) = 1$) if and only if:
1. **Failing Test Passes**: The test that initially reproduced the bug passes after agent edits.
2. **Hidden Invariant Tests Pass**: Pre-authored hidden tests testing boundary and regression cases pass.
3. **Existing Tests Remain Passing**: All tests that previously passed still pass (0 regressions).
4. **Budget Constraints**: The fix is achieved within $\le 5$ tool steps and $\le 120$ seconds wall-clock time.

$$\text{Bug-Fix Resolution Rate (\%)} = \left( \frac{1}{|T|} \sum_{j=1}^{|T|} \text{Resolved}(T_j) \right) \times 100\%$$

### 2.2 Execution Protocol
- Every task runs in a fresh temporary directory (`tempfile.mkdtemp()`).
- Tests are executed via standard test runners (`pytest` for Python, `node --test` for JS).
- Agent cannot view hidden test files during execution; hidden tests are injected only during evaluation grading.

---

## 3. Cost, Token, and Latency Metrics

Evaluated on the fixed 100-query developer workload (`evals/datasets/workload_100_queries.json`).

### 3.1 Workload Composition
- **Unique Queries**: 60 (60%)
- **Exact Duplicate Queries**: 20 (20%) — identical strings executed at later steps
- **Paraphrased Queries**: 20 (20%) — semantically identical queries phrased differently

### 3.2 Total Tokens and Token Reduction
Total tokens = $\sum (\text{input\_tokens} + \text{output\_tokens})$ across all calls.

$$\text{Token Reduction (\%)} = \left( 1 - \frac{\text{Total Tokens}_{\text{optimized}}}{\text{Total Tokens}_{\text{baseline}}} \right) \times 100\%$$

### 3.3 Prompt Caching & Cache Read Share
$$\text{Prompt Cache Read Share (\%)} = \left( \frac{\sum \text{cached\_input\_tokens}}{\sum \text{input\_tokens}} \right) \times 100\%$$

Cached tokens must come strictly from provider usage metadata (`prompt_tokens_details.cached_tokens`, `usage_metadata.input_token_details.cache_read`, or `response_metadata.usage.cache_read_input_tokens`). No estimates.

### 3.4 Semantic Cache Hit Rate
$$\text{Semantic Cache Hit Rate (\%)} = \left( \frac{\text{Semantic Cache Hits}}{\text{Total Workload Queries (100)}} \right) \times 100\%$$

### 3.5 API Cost and Cost Reduction
Cost is computed per invocation using official provider rates specified in `config.yaml`:

$$\text{Cost} = \frac{\text{uncached\_input} \times R_{\text{input}} + \text{cached\_input} \times R_{\text{cached}} + \text{output} \times R_{\text{output}}}{1,000,000}$$

$$\text{Cost Reduction (\%)} = \left( 1 - \frac{\text{Total Cost}_{\text{optimized}}}{\text{Total Cost}_{\text{baseline}}} \right) \times 100\%$$

### 3.6 Latency (p50, p95, Mean)
Latency is measured via `time.perf_counter()` over the round-trip API / agent invocation.
- $p50$: Median latency (50th percentile)
- $p95$: 95th percentile latency
- Mean: Arithmetic mean latency

$$\text{Latency Reduction (\%)} = \left( 1 - \frac{\text{Latency}_{\text{optimized}}}{\text{Latency}_{\text{baseline}}} \right) \times 100\%$$

---

## 4. Hardware & Software Specification
- **Operating System**: Windows (win32)
- **Python Runtime**: Python 3.14.6
- **Primary LLM**: `gpt-4o-mini` (or `gpt-4o` for strong model comparisons)
- **Embedding Model**: `text-embedding-3-small` (1536 dims)
- **Stochastic Controls**: Temperature = 0 where supported; 3 repeated runs for stochastic evaluations reporting mean and per-run values.

