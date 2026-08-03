# Inference-Optimization

Investigation on LLM inference scheduling optimization for complex multi-agent tasks with multi-dimensional optimizations: request, token, GPU memory, prefill-decode interleaving and speculative decoding.

## Request-level Scheduling
  
1. [NeurIPS'23](https://www.proceedings.com/content/075/075280-2859open.pdf) Response Length Perception and Sequence Scheduling

   keywords: Response Length Prediction, Sequence Scheduling, Static Batching

   Motivation: 1) Static batches must wait for the longest response, causing padding and redundant computation. 2) Response lengths are unknown before generation, making length-aware batching difficult. 3) Prediction errors may leave unfinished requests and delay the entire batch.

   Design: 1) Fine-tune Vicuna-7B with LoRA to predict the maximum response-length interval. 2) Sort requests by predicted lengths and group similar requests into micro-batches. 3) Use Failure Collection and Recomputation (FCR) to isolate and reprocess underestimated requests. 4) Use Variable Batch Size (VBS) to assign larger batches to shorter responses.

   Result: 1) Improves Alpaca throughput from 1.22 to 2.27 samples/s, achieving an 86% improvement. 2) Reduces the average processed tokens per batch from 377 to 208. 3) Achieves 1.24 samples/s on Instruction-in-the-Wild, compared with 0.78 samples/s for conventional batching.


### More++....

## Token-level Scheduling

1. [OSDI'22](https://www.usenix.org/conference/osdi22/presentation/yu) Orca: A Distributed Serving System for Transformer-Based Generative Models

   keywords: Iteration-level Scheduling, Selective Batching, Continuous Batching

   Motivation: 1) Request-level batching prevents completed requests from leaving until the entire batch finishes. 2) Newly arrived requests cannot use batch slots released during generation. 3) Different input lengths and generation stages make dynamically selected requests difficult to batch efficiently.

   Design: 1) Introduce iteration-level scheduling to reconstruct the batch after every generation iteration. 2) Use selective batching to batch Linear and normalization operators while separately processing request-specific Attention. 3) Apply iteration-level FCFS to avoid starvation of early requests. 4) Reserve KV Cache according to the maximum generation length to prevent runtime OOM.

   Result: 1) Supports dynamic request joining and leaving during generation. 2) Achieves up to 36.9× higher throughput than FasterTransformer at comparable normalized latency for the 175B model. 3) Scales inference from a single GPU to 32 GPUs for models up to 341B parameters.

2. [arXiv'24](https://arxiv.org/abs/2401.08671) DeepSpeed-FastGen: High-Throughput Text Generation for LLMs via MII and DeepSpeed-Inference

   keywords: Dynamic SplitFuse, Chunked Prefill, Token Budget

   Motivation: 1) Decode-only batches contain too few tokens to fully utilize GPU computation. 2) Processing an entire long Prompt in one iteration significantly delays ongoing Decode requests. 3) Prefill- and Decode-dominated forwards cause unstable workloads and poor throughput-latency trade-offs.

   Design: 1) Split long Prompts into smaller Prefill chunks distributed across multiple iterations. 2) Fuse Prefill chunks, short Prompts, and Decode tokens into the same forward pass. 3) Control the total tokens in each forward with a fixed token budget. 4) Integrate Dynamic SplitFuse with DeepSpeed-Inference and MII for distributed serving and replica scaling.

   Result: 1) Achieves up to 2.3× higher effective throughput than the evaluated vLLM version. 2) Reduces average latency by up to 2×. 3) Reduces P95 per-token generation latency by up to 3.7×.

3. [OSDI'24](https://www.usenix.org/conference/osdi24/presentation/agrawal) Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve

   keywords: Chunked Prefill, Stall-free Batching, TBT SLO, Pipeline Parallelism

   Motivation: 1) Full Prefill requests interrupt ongoing generation and cause long generation stalls. 2) Average latency cannot reflect severe tail time-between-tokens experienced by users. 3) Unstable iteration workloads create pipeline bubbles in pipeline-parallel deployments. 4) Small Prefill chunks reduce stalls but introduce additional execution overhead.

   Design: 1) Divide long Prompts into fixed-size Prefill chunks. 2) Apply Decode-first scheduling to guarantee one token for each active Decode request before scheduling Prefill. 3) Fill the remaining token budget with Prefill chunks to construct stall-free hybrid batches. 4) Select the token budget through offline profiling according to the P99 TBT SLO. 5) Construct uniform-compute batches to reduce pipeline bubbles across pipeline stages.

   Result: 1) Improves serving capacity by up to 2.6× for Mistral-7B and 3.7× for Yi-34B over vLLM. 2) Achieves up to 6.31× higher serving capacity than Orca under pipeline parallelism. 3) Maintains lower P99 TBT under both chat and long-document summarization workloads.

### How Does Chunked Prefill Preserve Token Dependencies?

Chunked Prefill does not divide a Prompt into independent requests. It first tokenizes the complete Prompt and divides the resulting Token sequence into consecutive chunks. When processing the first chunk, the system stores its Key and Value tensors in the KV Cache at every Transformer layer. For each subsequent chunk, it computes Q, K, and V only for the new Tokens, while their Queries can still attend to the cached Keys and Values of all preceding chunks. A causal mask preserves dependencies within the current chunk, and the original positional indices continue across chunk boundaries. Therefore, Chunked Prefill changes only when different parts of the Prompt are computed, without breaking causal Attention dependencies. It allows long Prefill requests to be interleaved with Decode requests, although smaller chunks introduce additional forward and scheduling overhead. Orca does not split Prompt Prefill; DeepSpeed-FastGen and Sarathi-Serve implement different forms of token-budget-controlled Chunked Prefill.

## Resource-level Scheduling

1. [TACO'25](https://dl.acm.org/doi/10.1145/3732941) ShuffleInfer: Disaggregate LLM Inference for Mixed Downstream Workloads

   keywords: Prefill-Decode Disaggregation, Resource Interference, Two-level Scheduling

   Motivation: 1) Prefill and Decode have different computation, memory-capacity, and memory-bandwidth requirements. 2) Mixing heterogeneous downstream workloads causes severe Prefill-Prefill, Prefill-Decode, and Decode-Decode interference. 3) Naive request placement may create Decode hotspots and head-of-line blocking. 4) Existing serving systems do not jointly consider request characteristics and predicted resource usage.

   Design: 1) Partition Prompts into fixed-size chunks to keep Prefill instances near computation saturation. 2) Disaggregate Prefill and Decode into independent instances to isolate phase interference. 3) Group requests according to Prompt and Decode characteristics to reduce intra-instance interference. 4) Use a two-level scheduler with predicted resource usage to select instances and avoid Decode hotspots. 5) Dynamically coordinate requests across disaggregated resources for mixed downstream workloads.

   Result: 1) Uses 38% fewer resources than the evaluated baselines. 2) Reduces average TTFT by 97%. 3) Reduces average job completion time by 47% while improving performance per dollar.
