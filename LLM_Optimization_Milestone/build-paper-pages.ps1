$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
$outDir = Join-Path $PSScriptRoot "papers"
$milestonePage = Get-ChildItem -LiteralPath $PSScriptRoot -File -Filter "8.30_*.html" | Select-Object -First 1
if (-not $milestonePage) { throw "Milestone page not found" }
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$papers = @(
  @{ Id = 11; Title = "Orca: A Distributed Serving System for Transformer-Based Generative Models"; SourcePattern = "8.09*.md"; Marker = "## Orca"; Level = "##" },
  @{ Id = 12; Title = "Response Length Perception and Sequence Scheduling"; SourcePattern = "8.09*.md"; Marker = "## Response Length Perception"; Level = "##" },
  @{ Id = 13; Title = "DeepSpeed-FastGen"; SourcePattern = "8.09*.md"; Marker = "## DeepSpeed-FastGen"; Level = "##" },
  @{ Id = 15; Title = "Sarathi-Serve"; SourcePattern = "8.09*.md"; Marker = "## Sarathi-Serve"; Level = "##" },
  @{ Id = 16; Title = "Inference without Interference / ShuffleInfer"; SourcePattern = "8.09*.md"; Marker = "## Inference without Interference"; Level = "##" },
  @{ Id = 20; Title = "Parrot: Efficient Serving of LLM-based Applications with Semantic Variables"; SourcePattern = "8.11_DAG_scheduling.md"; Marker = "## Parrot"; Level = "##" },
  @{ Id = 21; Title = "MuxServe: Flexible Spatial-Temporal Multiplexing for Multiple LLM Serving"; SourcePattern = "8.11_DAG_scheduling.md"; Marker = "## MuxServe"; Level = "##" },
  @{ Id = 22; Title = "Ayo: Towards End-to-End Optimization of LLM-based Applications"; SourcePattern = "8.11_DAG_scheduling.md"; Marker = "## Towards End-to-End Optimization"; Level = "##" },
  @{ Id = 23; Title = "KVFlow: Efficient Prefix Caching for Accelerating LLM-Based Multi-Agent Workflows"; SourcePattern = "8.11_DAG_scheduling.md"; Marker = "## KVFlow"; Level = "##" },
  @{ Id = 24; Title = "Agentix: An Efficient Serving Engine for LLM Agents as General Programs"; SourcePattern = "8.11_DAG_scheduling.md"; Marker = "## Agentix"; Level = "##" },
  @{ Id = 26; Title = "Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache Time-to-Live"; SourcePattern = "8.18_Agentic_workflow_scheduling.md"; Marker = "## Continuum"; Level = "##" },
  @{ Id = 27; Title = "ThunderAgent: A Fast, Simple, and Program-Aware Agentic Inference System"; SourcePattern = "8.18_Agentic_workflow_scheduling.md"; Marker = "## ThunderAgent"; Level = "##" },
  @{ Id = 28; Title = "CONCUR: High-Throughput Agentic Batch Inference of LLM via Congestion-Based Concurrency Control"; SourcePattern = "8.18_Agentic_workflow_scheduling.md"; Marker = "## CONCUR"; Level = "##" },
  @{ Id = 29; Title = "PASTE: Parallelizing Tool Execution and LLM Generation for Low-Latency Agent Serving"; SourcePattern = "8.18_Agentic_workflow_scheduling.md"; Marker = "## PASTE"; Level = "##" },
  @{ Id = 38; Title = "Pythia: Exploiting Workflow Predictability for Efficient Agent-Native LLM Serving"; SourcePattern = "8.27_Agentic_KV*"; Marker = "# Pythia"; Level = "#" },
  @{ Id = 39; Title = "CacheScout: Learning Agent Execution for KV-Cache Management"; SourcePattern = "8.27_Agentic_KV*"; Marker = "# CacheScout"; Level = "#" },
  @{ Id = 40; Title = "OasisKV: Scaling In-Decode KV Cache Beyond HBM"; SourcePattern = "8.27_Agentic_KV*"; Marker = "# OasisKV"; Level = "#" },
  @{ Id = 32; Title = "Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models"; SourcePattern = "8.11_Continuum*"; Marker = "## 1. Agentic Context Engineering"; Level = "##" },
  @{ Id = 33; Title = "Beyond Accuracy: Unveiling Inefficiency Patterns in Tool-Integrated Reasoning"; SourcePattern = "8.11_Continuum*"; Marker = "## 3. Beyond Accuracy"; Level = "##" },
  @{ Id = 34; Title = "UniCache: Unifying Prefix Cache Eviction for Heterogeneous LLM Serving Workloads"; SourcePattern = "8.11_Continuum*"; Marker = "## 4. UniCache"; Level = "##" },
  @{ Id = 35; Title = "Reasoning Language Model Inference Serving Unveiled: An Empirical Study"; SourcePattern = "8.11_Continuum*"; Marker = "## 5. Reasoning Language Model"; Level = "##" }
)

function Convert-Images([string] $html) {
  $html = $html -replace 'src="(?!https?://|data:|/|\.\./)([^"]+\.(?:png|jpg|jpeg|gif|svg))"', 'src="../../$1"'
  $html = $html -replace 'href="(?!https?://|/|\.\./|#)([^" ]+\.(?:pdf|md))"', 'href="../../$1"'
  return $html
}

foreach ($paper in $papers) {
  $sourceFile = Get-ChildItem -LiteralPath $root -File -Filter $paper.SourcePattern | Select-Object -First 1
  if (-not $sourceFile) { throw "Source file not found: $($paper.SourcePattern)" }
  $sourcePath = $sourceFile.FullName
  $lines = Get-Content -LiteralPath $sourcePath -Encoding UTF8
  $start = -1
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i].StartsWith($paper.Marker)) { $start = $i; break }
  }
  if ($start -lt 0) { throw "Section not found: $($paper.Marker) in $($paper.SourcePattern)" }
  $nextHeading = "^" + [regex]::Escape($paper.Level) + "\s+"
  $end = $lines.Count
  for ($i = $start + 1; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match $nextHeading) { $end = $i; break }
  }
  $section = ($lines[$start..($end - 1)] -join "`n")
  $tempMd = Join-Path $env:TEMP ("llm-paper-" + $paper.Id + ".md")
  $tempHtml = Join-Path $env:TEMP ("llm-paper-" + $paper.Id + ".html")
  Set-Content -LiteralPath $tempMd -Value $section -Encoding UTF8
  & pandoc.exe --from markdown+tex_math_dollars --to html5 --wrap=none --output $tempHtml $tempMd
  if ($LASTEXITCODE -ne 0) { throw "Pandoc failed: $($paper.Title)" }
  $body = Convert-Images (Get-Content -LiteralPath $tempHtml -Raw -Encoding UTF8)
  $safeTitle = [System.Net.WebUtility]::HtmlEncode($paper.Title)
  $page = @"
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>$safeTitle - Paper Reading Note</title>
  <link rel="stylesheet" href="../milestone.css">
  <link rel="stylesheet" href="../source-paper.css">
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div class="brand"><div class="mark">L</div><div><strong>LLM OPTIMIZATION</strong><span>Paper reading note - copied from Markdown</span></div></div>
      <nav class="toplinks" aria-label="Page navigation"><a href="../$($milestonePage.Name)#phases">Back to Milestone</a><a href="../../$($sourceFile.Name)">Open source Markdown</a></nav>
    </header>
    <main class="source-page">
      <p class="eyebrow">Paper Reading Note - Source Markdown</p>
      <h1>$safeTitle</h1>
      <div class="source-meta"><span>Paper $($paper.Id)</span><span>Source: $($sourceFile.Name)</span><span>Original images, formulas and tables preserved</span></div>
      <p class="source-note">This page is directly converted from the corresponding Markdown section; the original wording and figures are retained.</p>
      <article class="source-content">$body</article>
    </main>
    <footer>Source-derived reading page - $safeTitle</footer>
  </div>
</body>
</html>
"@
  Set-Content -LiteralPath (Join-Path $outDir ("paper-" + $paper.Id + ".html")) -Value $page -Encoding UTF8
}
Write-Output ("Generated " + $papers.Count + " paper pages in " + $outDir)
