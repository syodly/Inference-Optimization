# LLM 推理优化论文档案

本仓库提供两个公开入口：

- [论文 Milestone](https://syodly.github.io/Inference-Optimization/LLM_Optimization_Milestone/LLM_Optimization_Milestone.html)：77 篇论文索引、主题分类、搜索筛选与图文摘要。
- [系统剖面](https://syodly.github.io/Inference-Optimization/LLM_Optimization_Milestone/architecture-3d.html)：按系统层次查看论文和跨层关联。

## 本地浏览

运行 `python -m http.server 8000 --directory site`，打开 <http://localhost:8000>。

## 维护与发布

网站文件集中在 `site/`；`public-files.json` 是明确的发布清单。
提交前运行 `python tools/check_public_site.py`，检查页面范围、依赖链接、论文目录和发布路径。
GitHub Actions 通过检查后，仅将 `site/` 部署到 GitHub Pages。
新增论文图片或摘要时，同时更新发布清单。

源码沿用 Apache-2.0 许可。论文与论文图表的权利归各自权利人所有。
