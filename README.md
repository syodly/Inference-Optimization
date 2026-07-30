# Inference-Optimization

Investigation on LLM inference scheduling optimization for complex multi-agent tasks with multi-dimensional optimizations: request, token, GPU memory, prefill-decode interleaving and speculative decoding.

## Request-level Scheduling
  
1. [NeurIPS'23](https://www.proceedings.com/content/075/075280-2859open.pdf) Response Length Perception and Sequence Scheduling

   keywords: Response Length Prediction, Sequence Scheduling, Static Batching

   Motivation: 1) Static batches must wait for the longest response, causing padding and redundant computation. 2) Response lengths are unknown before generation, making length-aware batching difficult. 3) Prediction errors may leave unfinished requests and delay the entire batch.

   Design: 1) Fine-tune Vicuna-7B with LoRA to predict the maximum response-length interval. 2) Sort requests by predicted lengths and group similar requests into micro-batches. 3) Use Failure Collection and Recomputation (FCR) to isolate and reprocess underestimated requests. 4) Use Variable Batch Size (VBS) to assign larger batches to shorter responses.

   Result: Improves throughput from 1.22 to 2.27 samples/s on Alpaca, achieving an 86% improvement over conventional batching.


### More++....

## Token-level Scheduling

1.[OSDI'22](https://www.usenix.org/conference/osdi22/presentation/yu) Orca
To be updated

2.[arXiv'24](https://www.proceedings.com/content/075/075280-2859open.pdf) DeepSpeed-FastGen
To be updated

3.[OSDI'24](https://www.proceedings.com/content/075/075280-2859open.pdf) Sarathi-Serve
To be updated

## Resource-level Scheduling

