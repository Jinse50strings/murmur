# Murmur

每天早晨，一份关于**复杂网络、社会网络分析与计算社会科学**的论文精选。

```
arXiv + 核心期刊(OpenAlex)
        ↓  去重 / 规则粗筛 / DeepSeek 打分 + 中文导读
   docs/feed.json  ←  GitHub Actions 每日 00:30 自动更新
        ↓
GitHub Pages  →  iOS / macOS / watchOS App + 桌面磁贴（M2 起开发）
        ↓
   docs/wechat_draft.html  →  公众号草稿（手动或定时发表）
```

## 当前进度

- [x] **M0** 数据管道（arXiv + OpenAlex → 筛选 → 中文摘要）
- [x] **M1** 自动发布（GitHub Actions + Pages）
- [x] 网页版收藏（浏览器 localStorage，可导出 JSON）
- [ ] **M2** iPhone App + 主屏磁贴
- [ ] **M3** MacBook 桌面磁贴
- [ ] **M4** Apple Watch App + Smart Stack 磁贴
- [ ] **M5** 打磨与每周续签流程

## 目录结构

```
config.toml              数据源、关键词、期刊、LLM 配置
pipeline/
  sources.py             arXiv / OpenAlex 抓取
  relevance.py           去重、规则筛选、规则打分
  llm.py                 DeepSeek 批量打分 + 中文 TL;DR
  output.py              feed.json / 网页 / 公众号草稿 / 归档
  main.py                命令行入口
docs/                    GitHub Pages 输出（自动生成，勿手改）
data/seen.json           已处理论文 ID，避免重复
.github/workflows/      每日定时任务
.env                     本地密钥（已 gitignore）
```

## 本地运行

要求：Python 3.11+（macOS 自带或 Anaconda 均可）。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY（可选填 OPENALEX_MAILTO）

# 先不调用 LLM，验证抓取和渲染
.venv/bin/python -m pipeline.main --no-llm

# 正式运行（需要 DeepSeek Key）
.venv/bin/python -m pipeline.main
```

产出：

- `docs/feed.json` — App 读取的每日 Feed（含归档 `docs/archive/`）
- `docs/index.html` — 网页预览（本地可直接双击打开）
- `docs/wechat_draft.html` — 公众号草稿（见下文）

`--no-llm` 模式不会写入 `data/seen.json`，方便反复调试；正式模式才会记录已处理论文。

## 网页收藏

网页版每张卡片右上角有书签按钮，收藏保存在当前浏览器的 `localStorage`：

- 收藏跨天保留，换一天打开仍能在「收藏」里看到
- 只存在本机浏览器，不上传服务器；换浏览器、清缓存或换设备不会同步
- 「收藏」视图可导出 JSON 备份
- 目前不提供跨设备同步；换设备时可用导出的 JSON 手动备份

## 网页归档

顶部「归档」视图按日期回看往期日报：

- 日期列表来自 `docs/archive/index.json`，每天自动追加
- 点击日期加载当天精选；收藏按钮与「收藏」视图互通
- 归档 JSON 由每日 Actions 自动提交到 `docs/archive/`

## 配置说明

`config.toml` 中主要可调项：

| 配置 | 作用 |
|---|---|
| `arxiv.categories` | arXiv 分类：cs.SI、physics.soc-ph、cond-mat.stat-mech、nlin.AO、cs.CY |
| `arxiv.core_categories` | 直接保留的分类（cs.SI、physics.soc-ph） |
| `arxiv.gated_categories` | 需要命中关键词才保留的分类 |
| `openalex.journals` | 追踪的期刊与 ISSN；`broad = true` 的综合性期刊需要命中关键词 |
| `filter.keywords` | 计算社科/网络科学关键词 |
| `filter.negative_keywords` | 排除材料、生物、医学等无关论文 |
| `filter.max_candidates` | 每天送入 LLM 的候选上限（控制成本） |
| `filter.min_score` | 入选分数线（0-10） |
| `app.top_n` / `wechat_top_n` | 每日精选数量 / 公众号展示数量 |
| `llm.model` | DeepSeek 模型（默认 `deepseek-chat`） |

## 部署到 GitHub（免费）

1. 在 <https://github.com/new> 创建 **public** 空仓库 `murmur`（不要勾选 README/gitignore）
2. 添加 Actions Secret：仓库 → Settings → Secrets and variables → Actions
   - `DEEPSEEK_API_KEY`（必填）
   - `OPENALEX_MAILTO`（可选，填你的邮箱可提升 OpenAlex 配额）
3. 推送代码到 `main` 分支
4. 开启 Pages：Settings → Pages → Source 选择 **Deploy from a branch** → `main` / **`/docs`**
5. 在 Actions 页手动运行一次 `daily-digest` 验证

上线后：

- 网页：`https://<用户名>.github.io/murmur/`
- Feed：`https://<用户名>.github.io/murmur/feed.json`

定时任务为每天 **00:30（北京时间）**，早上 8:00 前数据已就绪。免费版 Actions 偶尔延迟几分钟，不影响。

## 微信公众号（补充渠道）

1. 注册个人订阅号（微信公众平台），每天可群发 1 次
2. 管道运行后打开 `docs/wechat_draft.html`，全选复制
3. 粘贴到公众号编辑器（内联样式会保留基本格式）
4. 在后台设置**定时发表**到次日 8:00（个人订阅号无法调用群发 API，需手动这一步）
5. 公众号正文链接不可点击是正常现象，可在文末「阅读原文」处填当天网页地址

> 注意：只发布标题、自己的中文解读和原文链接；不要整段搬运期刊摘要。

## 成本

- GitHub Actions / Pages：免费
- DeepSeek：每天约 50-100 篇候选，约 **¥0.2/天**（¥5-15/月）
- 域名：不需要

## 数据源

- **arXiv**：cs.SI、physics.soc-ph、cond-mat.stat-mech、nlin.AO、cs.CY（近 72 小时）
- **OpenAlex**：EPJ Data Science、JASSS、Big Data & Society、Social Science Computer Review、Network Science、Journal of Complex Networks、Social Networks、Journal of Computational Social Science、IEEE TNSE、Nature Human Behaviour、Nature Communications、PNAS、Science Advances、PNAS Nexus

## 备注

- 免费 Google Scholar / Scopus 均无稳定 API，故不采用
- OpenAlex 已限制 `created_date` 增量接口，本项目使用 `from_publication_date`
- 周末 arXiv 不放新论文时，自动从最近 7 天归档补足「往期精选」（最多 3 篇）
- 摘要是 AI 辅助生成，仅作为筛选线索，请以论文原文为准
