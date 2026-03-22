# Voice RAG — 产品与工程技术规格说明书

**版本：** 0.6  
**状态：** 草案（与项目计划对齐；实现待定）  
**读者：** 贡献者、B2B 集成方、安全与合规审阅者  
**关联文档：** [`docs/PLAN.zh.md`](docs/PLAN.zh.md)（产品叙事）；[`docs/IMPLEMENTATION_PLAN.zh.md`](docs/IMPLEMENTATION_PLAN.zh.md)（由本 SPEC 派生的**实施计划**，当前对应 **v0.6**）

| 版本 | 摘要 |
|------|------|
| **v0.6** | 审阅订正：§0 文档导航；§4.5 **FR-R7**（`disabled` 检索过滤）；§12 `jobs` 路径统一为 `/api/v1/jobs/{job_id}`；§13 错误码与 §12.0 对齐说明 |
| v0.5.1 | 元数据 `source_uri`/`disabled`/`warnings`/`updated_at`；§12.0；§10.1 MUST；NFR-11 |
| v0.5 | 管理前端 §4.9、§17 |

**修订说明（v0.3）：** 检索单元与引用、配置、通话流水线、Demo HTTP、错误码、存储布局、术语表。  
**修订说明（v0.4）：** 新增**传统文本知识源**（网址、图文/网页、既有文档库导出等）入库，经 **语音就绪（Voice-ready）转化** 生成**短知识、可电话逐步指引**的检索单元，与通话原声管线并列。  
**修订说明（v0.4.1）：** 明确 **「文字指代配图」** 类帮助（如「如遇下方报错」+ 截图）的**强制语音改写规则**；配图信息须经 OCR/多模态进入语义，禁止保留纯视觉指代；见 **§4.2 FR-T7**、**§18** 典型示例。  
**修订说明（v0.5）：** 新增 **语音知识管理前端（控制台）** 需求：导入、查看、编辑、导出等；见 **§4.9**、**§17**。  
**修订说明（v0.5.1）：** 对齐 **§6** 元数据与 FR（`source_uri`、`disabled`、`warnings`、`updated_at`）；**§12** 补充 ingest 同步/异步、管理端分页与导出、CORS、`VOICERAG_ADMIN_TOKEN` 行为；**§13** 补充管理端/导出错误码；**§10** 增加 MUST 约束；**§5** NFR-11 抓取与内容责任边界。

### 0. 文档导航（阅读顺序）

1. **§1–3** 目标、原则、用例  
2. **§4** 功能需求（入库 / 检索 / 管理前端）  
3. **§5–6** 非功能与数据模型（**`disabled` 与检索语义见 §6.2**）  
4. **§7–9** Python API、配置、分阶段交付  
5. **§10** 评估与 **§10.1 实现 MUST**  
6. **§11–12** 流水线与 HTTP（**§12.0 行为约定**）  
7. **§13** 错误码；**§14** 存储；**§16** 待决；**§17** 管理 UI；**§18** 附录示例  

---

## 1. 文档目的

### 1.1 要解决的问题

B2B 组织往往已有成熟的**文本**知识库与**文本 RAG**，同时大量**可执行知识仅存在于语音**（外呼、客服、会议）。一方面要把**通话录音**转化为可检索的语音知识；另一方面要把**官网、帮助中心、Confluence/Notion 导出、图文页面**等传统文本源中的长文、结构化说明，**改写为适合电话沟通的短知识**（可逐步让用户操作），二者需进入**同一套向量索引**，供 Voice AI 与坐席辅助一致使用。目前仍较分散：团队要么把 ASR 脚本与临时分块拼在一起，要么依赖闭源联络中心全家桶。

### 1.2 产品目标

**Voice RAG** 是一条**开源、可组合**的流水线，能够：

1. 同时支持入库 **① 通话/会议原声音频**，**② 本地静态文档**，**③ 网址与图文等传统文本知识源**（见 §4.2）；
2. 产出**多粒度检索单元**：通话侧为摘要/主题/问答等；文本侧除基础分块外，支持 **语音就绪单元**——**以短知识为主**，内容限定为**可在电话里说清楚、并适合一步一步带着用户操作**（见 §4.2、§6.1）；均带**可追溯依据**（时间戳、URL、源文件、可选说话人）；
3. 为**文本与/或语音查询**提供统一查询路径，底层为**向量索引**与可插拔 **LLM** 生成；
4. 通过 **LiteLLM** 风格的多厂商 LLM/嵌入接口与 **Docker 优先**的 demo，降低集成摩擦；
5. 提供 **语音知识管理前端**（浏览器控制台），支持知识**导入、查看、编辑、导出**等日常运营能力（见 **§4.9**、**§17**），减少对纯 CLI 的依赖。

### 1.3 非目标（v1）

- 替代电话系统、外呼器或完整 CCaaS。
- 承诺在无人工审核选项下实现全自动合规或 100% 抽取质量。
- 生产级电话线路上的实时亚秒级流式 ASR（可作为后续扩展；demo 以**上传整段音频**为主）。

### 1.4 术语表

| 术语 | 含义 |
|------|------|
| ASR | 自动语音识别，输出带或不带时间戳的文本 |
| 检索单元 | 入库向量索引的一条逻辑记录，含 `text`、`unit_type`、元数据 |
| 通话管线 | 从音频到多条检索单元的处理链（ASR→分段→抽取→嵌入） |
| 融合 | 多路检索结果合并排序，如 RRF 或加权 |
| 租户过滤 | 查询时按 `tenant_id`（或等价字段）限制可见文档 |
| **语音就绪知识** | 经转化后、面向电话场景的短条目；优先短句、可顺序执行，避免长段落 |
| **传统文本源** | 网址、本地/远程图文（HTML/Markdown）、帮助中心导出等，区别于通话原声 |
| **指代表述** | 依赖版面的话术，如「如下」「下图」「见下方」「如图所示」——语音中无效，须改写 |
| **图文一体知识** | 短文字说明 + 截图/UI 共同表达一条排障知识；语音化时必须合并为可听指令 |

---

## 2. 与业界实践对齐的设计原则

下表概括本规格采纳的常见做法（参考文献见 **§15**）：

| 原则 | 对 Voice RAG 的含义 |
|------|---------------------|
| **检索作为一等子系统** | 嵌入、索引、检索、重排各有配置与指标；避免只靠「改提示词」救场。 |
| **混合检索与重排** | 在可行范围内支持稠密检索 + 可选词法/BM25 或交叉编码器重排。 |
| **治理与访问控制** | 租户/团队/来源等元数据；过滤钩子；禁止静默跨租户串数据。 |
| **质量与评估** | 文档化典型失败形态；可选评估钩子（黄金问答集、引用一致性检查）。 |
| **联络中心分析范式** | 转写 →（可选）脱敏/PII 策略 → **结构化洞察抽取**（摘要、动因、意图等）→ 下游消费。 |
| **成本感知的 LLM 使用** | 「重」抽取与「轻」分类可配置不同模型；可选本地开源权重路径。 |
| **转写文本分块** | 优先**语义/说话人感知**边界，而非简单固定窗口。 |
| **统一 LLM 网关** | 单一抽象（LiteLLM）对接多厂商与本地 OpenAI 兼容服务。 |
| **电话优先表述** | 从网页/长文档抽取时，默认改写为口语友好、步骤化（「第一步…第二步…」），控制单次播报长度（可配置 token/字数上限）。 |
| **无视觉依赖** | 帮助页常见「如遇下方报错」+ 配图：语音输出**不得**假设用户能看到图；须把**报错文案、字段名、操作顺序**说清楚（见 §4.2 FR-T7）。 |

---

## 3. 用户画像与用例

### 3.1 用户画像

- **平台/基础架构工程师**：自托管；需要清晰环境变量、Docker、可审计日志。
- **应用 ML / AI 工程师**：替换嵌入/LLM 模型；调优抽取提示词。
- **呼叫中心 / CX 负责人**：关注摘要、主题、类 FAQ 检索，用于坐席辅助或语音机器人。

### 3.2 主用例（B2B）

- **通话资产**：给定一通约 **15 分钟**（可配置）录音 + 可选 CRM/工单元数据 → 入库，使后续会话能检索该通话中的事实与结论。  
- **文本资产语音化**：给定 **URL 列表、帮助中心导出包、或图文页面**，将其中知识 **抽取并改写为语音就绪短知识**（FAQ、操作步骤、确认话术），与通话知识**共用索引**，供电话机器人/坐席按步引导用户。

### 3.3 次要用例

- 仅入库 **PDF/Markdown/纯文本**（不做语音化，走 `document_chunk`）。
- **Demo**：上传音频 **或** 提交 URL/粘贴图文 → 查看抽取结果 → 模拟电话侧问答（文本或短录音）。

---

## 4. 功能需求

### 4.1 入库 — 本地文档（基础分块）

- **FR-D1**：接受目录或文件列表；最低支持 `.txt`、`.md`；扩展目标：通过可选依赖支持 `.pdf`。
- **FR-D2**：可配置块大小与重叠；持久化稳定的 **chunk_id** 与 **source_uri**。
- **FR-D3**：未启用语音化时，文档类检索单元的 `unit_type` 为 `document_chunk`（与通话类、语音就绪类区分）。

### 4.2 入库 — 传统文本知识源与「语音就绪」转化（v0.4）

面向 **网址、图文网页、企业内部 Wiki/帮助中心导出** 等（**非**通话原声）。在基础抓取/解析之后，经 **LLM 结构化改写**，生成适合 **电话场景** 的检索单元。

- **FR-T1（来源）**：支持至少一种：**HTTP(S) URL 列表**（GET 拉取正文）、**本地 HTML/Markdown 文件**、**批量导出包**（如 zip 内含 md/html）。需记录 **canonical URL 或文件路径** 作为 `source_uri`。
- **FR-T2（正文提取）**：从 HTML 提取主正文（可读性算法或轻量规则），去除导航/页脚；Markdown 直接分段。对正文**内嵌图片**：须保留与正文的**相邻关系**（顺序、所属段落），供 T3/T4 做图文联合理解。  
  - **OCR/多模态**：**P2** 起对截图执行 OCR 或视觉理解，提取**报错文案、字段标签、按钮名**等；若页面为「短文字 + 强依赖截图」结构，实现应**优先**拉通 OCR（v1 无多模态时可降级为 `[图片:未识别]` 并打 `warnings`，但不得将含「如下/下图」的原文直接入库为语音就绪单元，见 FR-T7）。
- **FR-T3（语音就绪策略）**：当 `VOICERAG_VOICE_TRANSFORM=1`（默认建议开启）时，对提取文本（及 FR-T2 合并的 OCR 文本）做 **语音化抽取**，输出以 **短知识为主** 的单元，满足：
  - **电话可用**：单条 `text` 适合单次播报的长度上限（见 `VOICERAG_VOICE_MAX_CHARS`，默认如 500，可配）；
  - **可逐步操作**：优先产出 **分步指引**（「第一步…第二步…」）或短 FAQ，避免长篇大论；
  - **口语友好**：允许提示词要求使用第二人称、避免表格与复杂 Markdown（实现通过 `prompts/voice_transform*.txt`）。
- **FR-T4（unit_type 扩展）**：语音就绪转化产生的单元使用下列类型（与 §4.3 通话类并列，均可被同一检索查询）：

  | `unit_type` | 说明 |
  |-------------|------|
  | `voice_faq` | 短问短答，适合一线客服/机器人快读快答 |
  | `voice_steps` | **分步操作**知识，强调顺序与用户可执行动作（电话里一步一步带）；可一条单元内编号多步，或拆成多条并用 `step_index` 排序（见 §6.2） |
  | `phone_script` | 可选：标准确认话术、开场/收尾短句（仍须短） |
  | `document_chunk` | 仅当关闭语音化或降级模式时保留的原文分块 |

- **FR-T5（元数据）**：`source_kind` 设为 `web` 或 `text_kb`（见 §6.2）；必填 **`source_uri`**（URL 或文件路径）、可选 `page_title`、`fetched_at`、内容哈希用于幂等。
- **FR-T6（安全与合规）**：URL 抓取遵守可配置 **域名白名单** `VOICERAG_URL_ALLOWLIST`（空则仅允许 CLI/显式传入的 URL，demo 须默认限制）；超时、最大重定向次数、 robots 尊重为 **待决**（见 §16）。
- **FR-T7（图文指代改写，v0.4.1，强制）**：针对 **「先文字后配图」** 类帮助（例如「如遇下方报错，请检查…」并附表单/报错截图），语音就绪转化**必须**遵守：
  1. **禁止**输出仅依赖视觉的指代：删除或改写「如下」「下图」「下方」「如图所示」等，改为**可听觉定位的条件**（具体**报错原文**、字段中文名、校验规则摘要等）。
  2. **合并图文语义**：截图中的关键信息（如输入框旁红字、校验提示「请输入 N 位」、字段高亮含义）须通过 OCR/多模态进入上下文，并写入同一条 **`voice_steps` 或 `voice_faq`**；不得单独保留「请看图片」式无效单元。
  3. **可单独执行**：用户**只听电话**也能按步骤操作；若信息不足（OCR 失败），单元应标记 `warnings` 或降级为 `document_chunk` + 人工补全提示，而非伪造步骤。
  4. **触发问法**：`voice_faq` 的「问」侧宜使用用户自然说法（如「提示 IBAN 要 20 位怎么办」），与页面标题关键词对齐，便于检索命中。

上述规则在 `prompts/voice_transform*.txt` 中须有**显式条款**；评测集建议包含至少一类「指代 + 配图」样本（见 §10）。

### 4.3 入库 — 语音（通话原声管线）

- **FR-V1**：接受音频文件；**推荐** WAV/MP3；容器内可用 ffmpeg 转为单声道 16 kHz PCM 以提升 ASR 稳定性（实现可选，规格不强制单一格式）。
- **FR-V2**：运行带**时间戳**的 **ASR**；在引擎支持时优先词级或段级时间戳。
- **FR-V3（可选）**：开启时做**说话人分离（diarization）**；在可得时为片段附加 `speaker_id` 或角色标签。
- **FR-V4**：按时间与/或主题**分段**转写；在开启 diarization 时尽量避免在话轮中间硬切（尽力而为）。
- **FR-V5**：通过 LLM 做**知识抽取**，输出多种可配置的 **unit_type**：

  | `unit_type` | 说明 |
  |-------------|------|
  | `call_summary` | 整通或主要片段的短摘要 |
  | `topic_span` | 带主题标签的片段摘要 + 指向原文时间范围 |
  | `qa_pair` | 客户问 / 坐席答 / 结果 式条目 |
  | `raw_segment` | 可选原文片段，用于词面 grounding |

- **FR-V6**：附加**元数据**（见 §6.2 `RetrievalUnitMetadata`）。

### 4.4 索引与存储

- **FR-I1**：**向量存储**抽象层，至少一种实现（如 LanceDB 或 Chroma），持久化到磁盘以保证 demo 重启后索引仍在。
- **FR-I2**：嵌入：**本地** `sentence-transformers` **或** 经同一 LiteLLM 配置面的 API 嵌入（`VOICERAG_EMBED_MODE`）。
- **FR-I3**：所有入库单元携带**检索元数据**，用于渲染引用与过滤。
- **FR-I4**：支持按 `tenant_id` 查询过滤；未设置 `tenant_id` 的单元行为由 `VOICERAG_STRICT_TENANT` 定义（默认宽松，见 v0.3 说明）。**生产多租户部署应使用** `VOICERAG_STRICT_TENANT=1`；宽松模式仅适用于单机试用与 demo。

### 4.5 检索与生成

- **FR-R1**：支持以 `text` 和/或 `audio` 查询（v1：音频先 ASR 再走文本嵌入查询）。
- **FR-R2**：Top-k 检索，可配置 `k` 与可选**分数阈值** `min_score`。
- **FR-R3**：存在多路检索列表时，支持 **RRF**（默认 `k_rrf=60`，可配置）或**加权融合**；可选对 **`unit_type` 加权**（例如电话场景提高 `voice_steps` / `voice_faq` 权重，配置项预留）。
- **FR-R4**：LLM 回答必须返回 **citations**（结构见 §6.5）。
- **FR-R5**：LLM 调用经 **LiteLLM**（或兼容薄封装）；核心逻辑不重复堆叠各厂商 SDK。
- **FR-R6**：可选 **query 侧重排**（P2 预留）。
- **FR-R7（v0.6）**：`/query` 与 CLI `ask` 在默认模式下**不得**将 `metadata.disabled=true` 的检索单元纳入 Top-k 候选或作为生成依据（与 §6.2「检索语义」一致）；管理端「试检索」若需包含已禁用项，须显式参数（如 `include_disabled=true`），并在 README 标明。

### 4.6 大模型提供方配置

- **FR-L1**：支持显式 `VOICERAG_LLM_MODEL` 与标准 API Key（按 LiteLLM 约定）。
- **FR-L2**：可选**自动选择**：未设模型时按**文档化顺序**根据已存在的 Key 选默认小模型；启动时**打印**解析后的 provider/model。
- **FR-L3**：健康检查或诊断接口/日志行暴露当前模型，便于 demo 核对。
- **FR-L4**：可选 `VOICERAG_EXTRACT_MODEL`；未设置则与主模型相同。
- **FR-L5（v0.4）**：`VOICERAG_VOICE_TRANSFORM_MODEL` 可选；若未设置，语音化改写与 `VOICERAG_EXTRACT_MODEL` 或主模型一致。

### 4.7 命令行

- **FR-C1**：`ingest-call` — 单文件或目录批量音频；支持 `--tenant-id`、`--call-id`（未提供则自动生成）。
- **FR-C2**：`index-docs` — 文档语料路径；支持 `--voice-transform` 对本地文档做语音就绪转化（同 §4.2）。
- **FR-C3**：`ingest-url` / `ingest-text-kb` — URL 列表或导出目录（**v0.4**）；支持 `--tenant-id`、`--no-voice-transform` 仅保留 `document_chunk`。
- **FR-C4**：`ask` — 对已有索引做一次查询（脚本化）；支持 `--tenant-id`。

### 4.8 演示 — 问答（Web）

- **FR-W1**：`cp .env.example .env` 填入最少 Key 后 `docker compose up` 可起服务。
- **FR-W2**：上传长音频 **或** 提交 **URL / 粘贴图文正文**（可配置最大时长、最大体积、URL 条数）。
- **FR-W3**：问答界面（文本；可选短音频作为查询上传）；展示命中单元类型（区分通话知识 vs 语音就绪知识）。

### 4.9 语音知识管理前端 — 控制台（v0.5）

面向 **运营、知识管理员、客服主管** 等，在浏览器中完成语音知识的**全生命周期管理**（与 §4.7 CLI、§12 API 能力对齐，**不得**仅依赖命令行才能完成核心运营动作）。

- **FR-U1（知识导入）**：提供统一 **「导入」** 入口，至少包含：
  - **原声**：上传音频文件（含拖拽）、填写/选择 `tenant_id`、`call_id`（可自动生成）、可选工单字段；触发与 `ingest/call` 等价的处理；展示进度/结果（`CallIngestResult` 摘要、warnings）。
  - **图文 / 网址**：输入 **URL 列表**（多行或批量）、上传 **zip 导出包**、或 **粘贴 HTML/Markdown 正文**；开关 **语音就绪改写**（`voice_transform`）；域名须符合 `VOICERAG_URL_ALLOWLIST`（前端提示错误原因）。
- **FR-U2（知识查看）**：**列表页**：分页、按 `unit_type`、`source_kind`（`call` / `web` / …）、`tenant_id`、时间范围、关键词搜索（对 `text` 与 `topic_label`）；**详情页**：展示单条检索单元全文、元数据（来源 URL、通话时间轴链接、`step_index` 等）、原始来源追溯（打开 `source_uri` 或播放原音频片段若已落盘）。
- **FR-U3（知识编辑）**：对单条 `RetrievalUnit` 支持：
  - 编辑 **`text`**（改口播稿、纠错）、**`topic_label`**、**`step_index`**（分步排序）；
  - **启用/禁用**（软删除，查询默认不可见但可恢复，或硬删除策略二选一并在 UI 明确标注）；
  - 编辑后 **重新嵌入**该条向量（或标记待批量重嵌，实现二选一，须在 README 说明）。
- **FR-U4（知识导出）**：支持将筛选条件下的知识导出为：
  - **JSON Lines**（每行一条单元，含 id、unit_type、text、metadata）；
  - **CSV**（列集固定为最小可交换子集）；
  - 可选 **按 `tenant_id` 打包 zip**；导出操作生成 **`trace_id`** 便于审计。
- **FR-U5（辅助能力，可分阶段）**：
  - **试检索**：在管理端输入问题，预览 Top-k 命中（与正式 `/query` 一致），用于验收入库质量；
  - **统计**：索引条数按类型/租户分布、最近一次入库时间；
  - **异步任务**：若 ingest 为异步，展示任务列表与状态（对齐 `GET /jobs/{id}`）。
- **FR-U6（路由与一体部署）**：管理前端与问答演示 **同一 Docker Compose** 可一并启动；建议路由前缀 `/`（问答）与 **`/admin`**（控制台）分离，静态资源由同一后端或反向代理提供。

---

## 5. 非功能需求

| 编号 | 类别 | 要求 |
|------|------|------|
| NFR-1 | **性能** | README 文档化 15 分钟通话的数量级耗时；提供 `max_duration`、`summary_only` 等降级模式。 |
| NFR-2 | **可靠性** | 幂等入库：通话为 `call_id` + 音频 SHA256；**URL/文本源**为 `source_uri` + 正文哈希；一致时跳过或版本化（`ingest_version`）。 |
| NFR-3 | **可观测性** | 结构化日志：步骤、模型 id、token 用量（若 LiteLLM 返回）；每条入库请求 `trace_id`（UUID）。 |
| NFR-4 | **安全** | 无硬编码密钥；PII/脱敏由部署方负责；可选送 LLM 前钩子（见 §14 扩展点）。 |
| NFR-5 | **合规姿态** | README 声明录音同意与数据驻留为客户责任；本库不默认宣称 HIPAA/SOC2。 |
| NFR-6 | **许可** | 第三方模型在 README 列出。 |
| NFR-7 | **测试** | 分块/融合/citation schema 单测；CI 中 LLM/ASR mock。 |
| NFR-8（v0.3） | **Demo 限流** | 单实例建议默认限制并发 ingest（如 2）与单文件大小（如 100MB，可配置），避免 OOM。 |
| NFR-9（v0.5） | **管理端安全** | 开源默认可无登录（与 demo 一致）；生产须通过 **`VOICERAG_ADMIN_TOKEN`**（请求头）或反向代理鉴权；文档禁止将管理面暴露公网而无防护。 |
| NFR-10（v0.5） | **管理端可用性** | 管理 UI 文案默认中文（可 i18n）；关键操作（删除、全量导出）需**二次确认**。 |
| NFR-11（v0.5.1） | **内容与抓取** | 对第三方站点的抓取频率、版权与适用条款（ToS）由**部署方**负责；本规格仅提供白名单、超时、体积等**技术约束**，不承诺代为规避付费墙或违反站点条款。 |

---

## 6. 数据模型（逻辑）

### 6.1 `RetrievalUnit`（检索单元）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | UUID | 是 | 全局唯一 |
| `unit_type` | 枚举 | 是 | 通话类见 §4.3；语音就绪类见 §4.2 |
| `text` | string | 是 | 用于嵌入与上下文 |
| `embedding_id` | string | 否 | 向量库内部行 id |
| `metadata` | object | 是 | 见 §6.2 |

### 6.2 `RetrievalUnitMetadata`（检索单元元数据）

与 FR-V6、FR-T5、FR-U3 对齐；字段在实现中允许扩展，**以下为 v1 最小集**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `source_kind` | `"call"` \| `"document"` \| `"web"` \| `"text_kb"` | 是 | `web`/`text_kb` 用于网址与导出类文本源 |
| `source_uri` | string | 条件必填 | **`document` / `web` / `text_kb`**：文件路径或 canonical URL；**`call`**：建议 `call:{call_id}` 或与 §6.5 `Citation.source_uri` 约定一致，便于引用展示 |
| `call_id` | string | 通话类必填 | 一次通话的稳定 id |
| `tenant_id` | string | 否 | 多租户隔离 |
| `created_at` | ISO8601 | 是 | 入库时间 |
| `updated_at` | ISO8601 | 否 | 最后修改时间；管理端编辑后由实现写入（§17.3 审计扩展前至少时间戳） |
| `disabled` | bool | 否 | 默认 `false`。`true` 表示**软禁用**：默认不参与 `/query` 检索，管理端仍可见（与 FR-U3 一致） |
| `warnings` | string[] | 否 | 单元级告警（如 OCR 降级、指代改写不完整提示）；**不得**单独替代 `text` 参与嵌入 |
| `source_filename` | string | 否 | 原始文件名 |
| `page_title` | string | 否 | 网页标题（URL 来源） |
| `fetched_at` | ISO8601 | 否 | URL 抓取时间 |
| `t_start_ms` | int | 否 | 音频内起始毫秒（通话类建议填） |
| `t_end_ms` | int | 否 | 结束毫秒 |
| `speaker` | string | 否 | 说话人标签或 id |
| `topic_label` | string | 否 | `topic_span`、同一主题的 `voice_steps` 分组等 |
| `step_index` | int | 否 | 同一主题下分步顺序（`voice_steps` 多条拆分时） |
| `external_ids` | object | 否 | 如 `ticket_id`、`crm_case_id` |
| `content_sha256` | string | 否 | 源文件哈希，用于幂等 |
| `ingest_version` | string | 否 | 管线版本，便于重跑迁移 |

**检索语义（默认）：** `/query` 与 CLI `ask` **不得**返回 `metadata.disabled=true` 的单元，除非显式调试/管理预览接口另有规定（须在 README 说明）。

### 6.3 `TranscriptSegment`（转写片段）

| 字段 | 类型 | 说明 |
|------|------|------|
| `seg_id` | string | 片段 id |
| `text` | string | 文本 |
| `start_ms` | int | 起始 |
| `end_ms` | int | 结束 |
| `speaker` | string \| null | 可选 |
| `confidence` | float \| null | ASR 置信度，若有 |

### 6.4 `CallIngestResult`（通话入库结果）

| 字段 | 类型 | 说明 |
|------|------|------|
| `call_id` | string |  |
| `transcript` | `TranscriptSegment[]` | 有序列表 |
| `units_created` | `RetrievalUnit[]` |  |
| `warnings` | string[] | 如 diarization 跳过 |
| `trace_id` | string | 可观测性关联 |
| `stats` | object | 可选：`asr_seconds`、`llm_calls`、`tokens` |

### 6.5 `Citation`（引用）

满足 FR-R4，**最小字段集**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `unit_id` | string | 指向检索单元 `id` |
| `unit_type` | string | 冗余存储便于展示 |
| `source_kind` | string | `call` / `document` / `web` / `text_kb` |
| `source_uri` | string | 文档路径、`call:{call_id}` 或 **URL** |
| `t_start_ms` | int \| null | 通话类引用 |
| `t_end_ms` | int \| null |  |
| `snippet` | string \| null | 短摘录 |

### 6.6 `Answer`（回答）

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 模型回答正文 |
| `citations` | `Citation[]` |  |
| `model_used` | string | 实际推理模型 |
| `trace_id` | string \| null | 可选 |

### 6.7 `IndexStats`（建库统计）

| 字段 | 类型 | 说明 |
|------|------|------|
| `documents_indexed` | int |  |
| `chunks_created` | int |  |
| `duration_ms` | int | 可选 |

---

## 7. 对外库 API（Python）

```text
VoiceRAGConfig.from_env(overrides: dict | None) -> VoiceRAGConfig

build_index_from_documents(
    paths: list[Path],
    config: VoiceRAGConfig,
    *,
    voice_transform: bool = False,
) -> IndexStats

ingest_text_kb(
    sources: list,  # URL 字符串或 Path，由实现收敛类型
    config: VoiceRAGConfig,
    *,
    voice_transform: bool = True,
    tenant_id: str | None = None,
) -> IndexStats

ingest_call(
    audio: Path,
    metadata: dict,
    config: VoiceRAGConfig,
    *,
    idempotency_key: str | None = None,  # 默认使用 (call_id 或生成) + content_sha256
) -> CallIngestResult

query(
    text: str | None,
    audio: Path | bytes | None,
    config: VoiceRAGConfig,
    *,
    tenant_id: str | None = None,
    top_k: int = 5,
) -> Answer
```

- 允许对 I/O 密集方法提供 `async` 变体（实现阶段决定）。
- **与 CLI 对应关系**：`ingest_text_kb` 与 **`ingest-url` / `ingest-text-kb`**（§4.7）语义一致，仅入口不同；`build_index_from_documents` 对应 **`index-docs`**；`ingest_call` 对应 **`ingest-call`**；`query` 对应 **`ask`**。
- **管理操作（可选）**：实现可提供 `list_units`、`get_unit`、`update_unit`、`export_units` 等 Python API，与 **§12.2** 语义一致，供脚本与前端共用。
- 异常类型见 **§13**。

---

## 8. 配置（环境变量）

**完整表（v0.6）**；最终实现以 `.env.example` 为准。

| 变量 | 类型/枚举 | 说明 |
|------|-----------|------|
| `VOICERAG_LLM_MODEL` | string | 主对话/生成模型（LiteLLM） |
| `VOICERAG_EXTRACT_MODEL` | string | 可选；通话/文本抽取；默认同主模型 |
| `VOICERAG_VOICE_TRANSFORM` | `0` \| `1` | 对传统文本源做语音就绪改写；默认 `1` |
| `VOICERAG_VOICE_TRANSFORM_MODEL` | string | 可选；专用于语音化改写 |
| `VOICERAG_VOICE_MAX_CHARS` | int | 单条语音就绪单元建议最大字符数 |
| `VOICERAG_URL_ALLOWLIST` | string | 逗号分隔域名，空则依赖 CLI 显式 URL（建议生产必配） |
| `VOICERAG_URL_FETCH_TIMEOUT_SEC` | int | 单 URL 请求超时 |
| `VOICERAG_EMBED_MODE` | `local` \| `litellm` | 嵌入来源 |
| `VOICERAG_EMBED_MODEL` | string | local 时为 ST 模型名；litellm 时为 API 模型 id |
| `OPENAI_API_KEY` 等 | secret | 各厂商按 LiteLLM 文档 |
| `OLLAMA_BASE_URL` | url | 本地 OpenAI 兼容 |
| `VOICERAG_DATA_DIR` | path | 数据与索引根目录 |
| `VOICERAG_MAX_CALL_DURATION_MIN` | int | 单通音频上限（分钟） |
| `VOICERAG_MAX_UPLOAD_MB` | int | Demo 单文件上限 |
| `VOICERAG_CHUNK_SIZE` | int | 单位（字符 / token / 句子）由实现选定并在 **README 固定**；本表为占位，与 §16「chunk_size 单位」一致 |
| `VOICERAG_CHUNK_OVERLAP` | int | 重叠 |
| `VOICERAG_TOP_K` | int | 默认检索条数 |
| `VOICERAG_RRF_K` | int | RRF 常数，默认 60 |
| `VOICERAG_STRICT_TENANT` | `0` \| `1` | 严格租户隔离；默认 0 |
| `VOICERAG_SUMMARY_ONLY` | `0` \| `1` | 仅摘要级抽取，降成本 |
| `VOICERAG_LOG_LEVEL` | log level | 默认 INFO |
| `VOICERAG_ADMIN_TOKEN` | secret | 若设置，则 `/admin/*` 与 `/api/v1/admin/*` 须带 `Authorization: Bearer`；**空则不对管理 API 校验**（demo/开发），见 **§12.0** |

---

## 9. 分阶段交付

| 阶段 | 范围 |
|------|------|
| **P0** | 文本 RAG + LiteLLM + 向量库 + citations；本地文档 + **可选** `voice_transform` |
| **P1** | 通话管线：ASR → 分段 → 抽取 → `CallIngestResult` |
| **P1.1** | **URL/文本库入库** + 语音就绪转化（`voice_faq` / `voice_steps`）；域名白名单 |
| **P1.2** | **管理前端 MVP**：导入 + 列表/详情查看 + 导出（JSONL）；可选简易编辑 |
| **P2** | diarization；混合/RRF；CLI `ingest-url` 齐全；图文 OCR（可选）；**完整编辑**（软删、重嵌） |
| **P3** | 音频嵌入；PDF；query 重排 |

---

## 10. 评估与质量

### 10.1 不可破坏约束（实现 MUST）

- **引用**：`Answer.citations` 中每条须含 **`unit_id`**（与 §6.5 一致）；无检索命中时 `citations` 可为空数组，**不得**伪造引用。
- **租户**：`VOICERAG_STRICT_TENANT=1` 时，查询与 ingest 携带的 `tenant_id` 组合**不得**返回或写入其他租户的单元（须有单测覆盖）。
- **软禁用**：默认检索路径**不得**命中 `metadata.disabled=true`（与 **FR-R7**、§6.2 一致）。
- **FR-T7**：入库为 `voice_faq` / `voice_steps` / `phone_script` 的单元**不得**在仅含版面指代、无可听条件的情况下作为主文；CI 可对 fixtures 做禁止词或结构检查（建议）。

### 10.2 指标与抽检（建议）

- **检索**：黄金集上 nDCG@k / 命中率。
- **生成**：引用与标准片段重叠率。
- **运营**：抽取失败率、人工修正率（若后续有 UI）。
- **语音化专项**：至少一类 **「指代 + 配图」** 页（§18）：检查输出中是否仍含「如下/下图」、是否含 OCR 中的关键报错文案、步骤是否可脱离屏幕执行。
- **管理端**：关键路径 E2E（导入 → 列表可见 → 导出文件非空）可作为发布门槛（可选 CI）。

---

## 11. 处理流水线与 LLM 调用边界

### 11.1 通话原声管线

| 阶段 | 输入 | 输出 | LLM？ |
|------|------|------|--------|
| S1 音频准备 | 原始文件 | 规范化音频（可选） | 否 |
| S2 ASR | 音频 | `TranscriptSegment[]` + 全文 | 否 |
| S3 分段 | 片段列表 | 粗/细粒度 span | 否（规则）；可选 LLM 主题切分 |
| S4 知识抽取 | spans + 配置 | 多条 `RetrievalUnit`（`call_summary` / `qa_pair` 等） | **是**（可多次调用） |
| S5 嵌入 | 单元文本 | 向量 | 否（ST）或 API |
| S6 持久化 | 向量 + 元数据 | 索引更新 | 否 |

- **降级**：`VOICERAG_SUMMARY_ONLY=1` 时，S4 仅生成 `call_summary` 与少量 `raw_segment`，跳过细粒度 QA。
- **提示词**：`prompts/extract_call_*.txt`。

### 11.2 传统文本源 → 语音就绪知识（v0.4）

将 **网址、图文、Wiki 导出** 等转为 **短知识、可电话逐步执行** 的单元（与 11.1 **独立**，可复用同一嵌入与向量存储）。

| 阶段 | 输入 | 输出 | LLM？ |
|------|------|------|--------|
| T1 获取 | URL / 文件路径 | 原始字节或文本 | 否 |
| T2 正文提取 | HTML/Markdown | 干净正文、标题 | 否（解析库） |
| T3（可选）图文 | 内嵌图片 | OCR 文本片段 | 否/多模态（P2） |
| T4 语音化改写 | 正文 + 配置 | `voice_faq` / `voice_steps` / `phone_script` 等 | **是** |
| T5 嵌入 | 单元文本 | 向量 | 否（ST）或 API |
| T6 持久化 | 向量 + 元数据 | 索引更新 | 否 |

- **约束**：T4 提示词须强调 **电话场景**、**短句**、**分步可执行**、**无指代无视觉依赖**，并遵守 `VOICERAG_VOICE_MAX_CHARS`。
- **提示词**：`prompts/voice_transform_*.txt`；与通话抽取提示词分离，便于独立迭代；须包含 **FR-T7** 禁止/改写清单（指代词、图文合并）。

---

## 12. HTTP API（草案）

基路径假设 `/api/v1`。认证：**问答与 ingest** 在开源 demo 中可不设；**管理类接口**（`/admin/*`）在配置了 `VOICERAG_ADMIN_TOKEN` 时须校验 Bearer（见 **§12.0**）。

### 12.0 行为约定（v0.5.1）

- **同步与异步（ingest）**：默认 `POST /ingest/call` 与 `POST /ingest/text-kb` **同步**完成处理并返回 **`200`** + `CallIngestResult` 或 `IndexStats`（含 `trace_id`）。若实现支持异步（如超长音频、大批量 URL），返回 **`202`** + `{ "job_id": "...", "status": "queued", "trace_id": "..." }`。**同一接口**不得混用两种响应体形状；触发异步的条件、超时与队列上限由 **README 固定**。
- **`VOICERAG_ADMIN_TOKEN`**：**未设置**时，§12.2 管理 API **不校验** Bearer（与开源 demo 一致）；**已设置**时，请求须带 `Authorization: Bearer <token>`，否则 **`401`** + `VOICERAG_UNAUTHORIZED`。**生产**须设置 token 或经反向代理鉴权，且禁止将管理面无防护暴露公网（见 NFR-9）。
- **分页（`GET /admin/units`）**：默认 `page=1`，`page_size=20`；`page_size` **上限 100**（实现可略低，README 固定）。`q` 为对 `text`、`topic_label` 的**子串**匹配；大小写是否敏感由实现定义并文档化。
- **导出（`POST /admin/export`）**：响应为 **流式下载** 或返回**短期有效**的下载 URL（建议 **15 分钟内**过期）；导出体积与 **NFR-8** 单文件上限对齐；超出实现上限时 **`413`** + `VOICERAG_EXPORT_TOO_LARGE`。
- **CORS**：若浏览器直连 API，实现须在 README 说明允许的 `Origin`；生产建议**同域**反向代理，避免 `*` 放宽凭证请求。

### 12.1 健康与入库、查询

| 方法 | 路径 | 请求 | 响应 |
|------|------|------|------|
| `GET` | `/health` | — | `{ "status": "ok", "llm_model": "...", "embed_mode": "..." }` |
| `POST` | `/ingest/call` | `multipart/form-data`：`file` + 可选字段 `tenant_id`、`call_id`、`ticket_id` | 默认 **`200`** + `CallIngestResult`；异步时为 **`202`** + `job_id` 对象（见 §12.0） |
| `POST` | `/ingest/text-kb` | JSON：`{ "urls": ["https://..."], "voice_transform": true, "tenant_id": null }` 或上传 zip | 默认 **`200`** + `IndexStats`；异步时为 **`202`** + `job_id` 对象 |
| `POST` | `/query` | JSON：`{ "text": "...", "tenant_id": null, "top_k": 5 }` 或带 `audio` 的 multipart | `Answer` |
| `GET` | `/calls/{call_id}` | — | 可选；返回元数据与单元列表（仅 demo） |

### 12.2 语音知识管理（v0.5）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/admin/units` | 分页与筛选：`tenant_id`、`unit_type`、`source_kind`、`q`、`page`、`page_size` |
| `GET` | `/admin/units/{unit_id}` | 单条详情（含 metadata） |
| `PATCH` | `/admin/units/{unit_id}` | 部分更新：`text`、`topic_label`、`step_index`、`disabled` 等 |
| `DELETE` | `/admin/units/{unit_id}` | 软删或硬删（`?hard=1`），行为在 README 固定 |
| `POST` | `/admin/export` | JSON：`filters` + `format`（`jsonl` \| `csv`）+ 可选 `tenant_id`；返回下载 URL 或流 |
| `POST` | `/admin/reindex` | 可选；触发单条或批量重嵌（P2） |
| `GET` | `/jobs/{job_id}` | 异步任务状态（ingest 等）；完整路径 **`/api/v1/jobs/{job_id}`**（与 **§4.9 FR-U5** 对齐） |

- **异步（可选）**：长音频或大批量 URL 返回 `job_id`，客户端轮询 **`GET /api/v1/jobs/{job_id}`**（与 §12.0 一致；路径始终带 `/api/v1` 前缀）。
- **错误体**：见 **§13**。

---

## 13. 错误模型与可恢复性

### 13.1 错误响应体（HTTP / 可映射到 CLI 退出码）

```json
{
  "error_code": "VOICERAG_AUDIO_TOO_LONG",
  "message": "human readable",
  "trace_id": "uuid",
  "details": {}
}
```

### 13.2 错误码（初版枚举）

| `error_code` | HTTP | 说明 | 可恢复 |
|--------------|------|------|--------|
| `VOICERAG_VALIDATION` | 400 | 参数非法 | 是 |
| `VOICERAG_AUDIO_TOO_LONG` | 413 | 超 `MAX_CALL_DURATION` | 是 |
| `VOICERAG_FILE_TOO_LARGE` | 413 | 超 `MAX_UPLOAD_MB` | 是 |
| `VOICERAG_ASR_FAILED` | 502 | ASR 失败 | 重试可能 |
| `VOICERAG_LLM_FAILED` | 502 | LLM 调用失败 | 重试可能 |
| `VOICERAG_INDEX_NOT_FOUND` | 404 | 未建索引 | 是 |
| `VOICERAG_TENANT_FORBIDDEN` | 403 | 严格模式下越权 | 否 |
| `VOICERAG_URL_NOT_ALLOWED` | 403 | 域名不在白名单 | 是 |
| `VOICERAG_FETCH_FAILED` | 502 | URL 抓取失败 | 重试可能 |
| `VOICERAG_INTERNAL` | 500 | 未预期错误 | 视情况 |
| `VOICERAG_UNAUTHORIZED` | 401 | 已配置 `VOICERAG_ADMIN_TOKEN` 但请求**缺少或 Bearer 无效** | 是 |
| `VOICERAG_ADMIN_FORBIDDEN` | 403 | 已认证但**无权**执行该操作（预留；与 `VOICERAG_TENANT_FORBIDDEN` 区分） | 否 |
| `VOICERAG_UNIT_NOT_FOUND` | 404 | `GET/PATCH/DELETE /admin/units/{id}` 目标不存在 | 是 |
| `VOICERAG_EXPORT_TOO_LARGE` | 413 | 导出结果超过实现上限 | 是 |

CLI：映射为退出码 1（用户可修复）、2（配置/环境）、3（上游不可用）。

---

## 14. 本地存储布局

在 `VOICERAG_DATA_DIR` 下建议目录约定（实现可微调，但需文档化）：

```text
{VOICERAG_DATA_DIR}/
  vector_store/          # LanceDB/Chroma 等
  artifacts/
    calls/{call_id}/     # 可选：转写 JSON、调试中间结果
    web/{content_hash}/  # 可选：抓取快照 HTML、便于审计与重跑
  logs/                  # 可选：按日滚动
```

- **不落盘策略**：若配置 `VOICERAG_EPHEMERAL=1`，通话 artifacts 可在入库结束后删除，仅保留向量（企业隐私向选项）。

---

## 15. 参考文献（业界实践）

1. Microsoft Azure — 通话中心分析架构 — [架构中心](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/openai/architecture/call-center-openai-analytics)  
2. AWS — Transcribe Call Analytics — [博文](https://aws.amazon.com/blogs/machine-learning/enhance-customer-service-efficiency-with-ai-powered-summarization-using-amazon-transcribe-call-analytics)  
3. arXiv:2503.19090 — 联络中心 LLM 洞察抽取  
4. Haystack — 说话人分离与 RAG — [博客](https://haystack.deepset.ai/blog/level-up-rag-with-speaker-diarization)  
5. Redwerk / Azumo 等 — 企业 RAG 实践  
6. LiteLLM — [文档](https://docs.litellm.ai/docs)  
7. VoxRAG — 免转写方向（长期）

---

## 16. 待决事项

| 事项 | 说明 |
|------|------|
| 默认嵌入模型 | 质量 vs 体积 vs 许可证 |
| PII 脱敏 | v1 是否内置规则，或仅钩子 |
| 异步 ingest | 是否 P1 必做或 P2 |
| `chunk_size` 单位 | 按字符、token 或句子；需在实现 README 固定 |
| URL 抓取策略 | 是否默认遵守 robots.txt；企业内网 URL 的认证方式 |
| 语音化质量 | 人工抽检以管理端「试检索 + 编辑」为主闭环 |
| OCR 失败时策略 | 禁止入库「纯指代+无 OCR」的 `voice_*`；或人工队列 |
| 管理端认证 | OIDC / SSO 由集成方在网关层实现，或后续版本内置 |

---

## 17. 语音知识管理前端（产品说明，v0.5）

**验收与功能范围以 §4.9 为准；本节为信息架构与实现提示。若与 §4.9 或 §12.2 冲突，以 §4.9 / §12.2 为准。**

### 17.1 信息架构（建议）

| 路由 | 模块 | 说明 |
|------|------|------|
| `/` 或 `/playground` | 问答试跑 | 与 **§4.8** 一致；可嵌入「试检索」简化版 |
| `/admin` | 控制台首页 | 快捷入口：导入、知识库、导出、系统状态 |
| `/admin/import` | 知识导入 | Tab：**原声** \| **网址/图文**；表单字段与 FR-U1 一致 |
| `/admin/knowledge` | 知识列表 | 表格 + 筛选器 + 批量选择（为批量导出/禁用铺路） |
| `/admin/knowledge/:id` | 知识详情与编辑 | 表单编辑 **FR-U3**；展示 citations 预览（只读） |
| `/admin/export` | 导出 | 选择筛选条件与格式，下载或生成临时链接 |

### 17.2 与后端的对应关系

- 所有管理操作 **优先** 调用 **§12.2** REST；前端可为 **SPA**（Vite/React/Vue 等）或 **服务端模板**，由实现选型，规格不强制。
- **静态资源**：`docker compose` 构建为「单镜像含 API + 静态前端」或「双容器」，需在 README 说明。

### 17.3 非功能（前端）

- **国际化**：首版中文；文案 key 化便于英文。
- **无障碍**：建议按钮与表单带 label（WCAG 为加分项，非 P1 阻塞）。
- **审计（P2）**：展示「最后编辑人/时间」需后端字段支持，当前可仅 `updated_at`。

---

## 18. 附录：典型改写示例（资料性，非规范性测试向量）

以下说明 **FR-T7** 期望的语义效果；真实产品文案以业务为准。

**场景（图文帮助页）**：上文写「若遇**下方**报错，请检查银行所在地是否选对；若欧元账户以 **IE** 开头，请将银行所在地选为**爱尔兰**后重新绑定。」下文配**网页表单截图**，图中 **IBAN** 输入框标红，校验提示为「银行账户/IBAN 请输入 20 位」等。

| 劣质（禁止作为 `voice_faq` / `voice_steps` 主文） | 优质（目标形态示意） |
|--------------------------------------------------|------------------------|
| 保留「如遇**下方**报错…」且未给出具体报错内容 | 改为可听条件：「如果系统提示 **银行账户或 IBAN 需要填 20 位**，且您的账号以字母 I、E 开头…」 |
| 假设用户能看到红色框、截图 | 口述字段名与操作顺序：「请先打开银行所在地，选 **爱尔兰**，再回到账号框确认位数，然后保存或重新绑定。」 |
| 图文割裂，仅索引正文 | 将截图中的校验提示（经 OCR）并入同一条步骤或 FAQ，使检索词能命中「20 位」「IE」「爱尔兰」等 |

**元数据建议**：`topic_label` 如「收款账户绑定 / IBAN 校验」；`source_kind=web`；`source_uri` 指向原帮助页便于审计。

---

*规格书结束*
