# Inference-Optimization

Investigation on LLM inference scheduling optimization for complex multi-agent tasks with multi-dimensional optimizations: request, token, GPU memory, prefill-decode interleaving and speculative decoding.

## Request-level Scheduling

  1.[NeurIPS'23](https://www.proceedings.com/content/075/075280-2859open.pdf) Response Length Perception and Sequence Scheduling
  
  keywords: Response Length Prediction, Sequence Scheduling, Static Batching
  
  Motivation: Unknown response lengths cause severe padding and redundant computation when requests with different generation lengths are placed in the same static batch.
  
  Design: Fine-tune Vicuna-7B to predict response lengths, group requests with similar predicted lengths, and use failure collection and variable batch sizes to handle prediction errors.
  
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

