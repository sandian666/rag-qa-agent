# 高中数学笔记 Agent（S5）

把本地数学笔记做成知识库，用一个能"自己决定要不要查资料"的 Agent 来回答问题，
并通过网页直接访问。个人学习项目：用本地笔记练习 RAG 检索与多工具 Agent，并封装成 Web 服务。

## 它能做什么
1: 查询当天天气（调用 wttr.in），并给出出行建议
2：获取当前日期时间
3：进行四则运算
4：回答高中数学有关知识点，并标明出处
5：带内存缓存：同一个问题在服务运行期间内重复提问可秒回（重启后清空）

## 快速开始

### 1. 装依赖

创建虚拟环境并安装依赖：

    python -m venv .venv
    .venv\Scripts\activate           # Windows
    pip install -r requirements.txt

### 2. 配置 API Key

本项目通过**环境变量**读取两个 Key（代码里用 `os.environ.get(...)` 读取：

| 变量名 | 用途 | 用在哪 |
|---|---|---|
| `ZHIPU_API_KEY` | 智谱：文本向量化（`embedding-3`） | 建库 + 检索 |
| `ali-deepseek-api-key` | 阿里云百炼：聊天模型（`deepseek-v4.1-flash`） | 生成回答 |

**Windows 下设置（永久生效）**：

    setx ZHIPU_API_KEY "你的智谱key"
    setx ali-deepseek-api-key "你的百炼key"

设置后需要**重开终端 / 重启 IDE** 才会生效。

**验证是否配好**（能打印出 Key 就对了）：

    python -c "import os; print(bool(os.environ.get('ZHIPU_API_KEY')), bool(os.environ.get('ali-deepseek-api-key')))"

应输出：`True True`

### 3. 建向量库

    python create_db.py

### 4. 启动服务

    python main.py

启动后浏览器访问 <http://127.0.0.1:8000/>
接口文档：<http://127.0.0.1:8000/docs>

**验证是否成功**：

- 打开 <http://127.0.0.1:8000/> 应看到标题、输入框和「提问」按钮
- 打开 <http://127.0.0.1:8000/docs> 应看到 3 个接口：`/`、`/hello`、`/ask`

## 项目结构

**验证是否成功**：

- 打开 <http://127.0.0.1:8000/> 应看到标题、输入框和「提问」按钮
- 打开 <http://127.0.0.1:8000/docs> 应看到 3 个接口：`/`、`/hello`、`/ask`

## 技术栈

| 类别 | 用了什么 | 用途 |
|---|---|---|
| 语言 | Python 3.14 | — |
| Web 框架 | FastAPI | 提供 HTTP 接口、自动生成接口文档 |
| 服务器 | Uvicorn | 运行 ASGI 服务 |
| LLM 调用 | OpenAI SDK（兼容模式） | 统一调用百炼 / 智谱的兼容接口 |
| 聊天模型 | `deepseek-v4.1-flash`（阿里云百炼） | 生成回答、决定调用哪个工具 |
| 向量模型 | `embedding-3`（智谱） | 文本向量化 |
| 向量库 | ChromaDB（PersistentClient，cosine 距离） | 存储与检索笔记片段 |
| 前端 | 原生 HTML + JavaScript（`fetch`） | 提问界面，无框架 |
| 其他 | requests（调用 wttr.in 查天气） | Agent 的外部工具之一 |、

## 接口说明

服务启动后，访问 <http://127.0.0.1:8000/docs> 可查看自动生成的接口文档。

### `GET /`

返回提问页面（`index.html`）。

### `GET /hello`

连通性测试，返回一句问候。

### `GET /ask`

问答接口，通过查询参数传入问题，返回模型生成的答案。

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `question` | query | string | 是 | 要提问的问题 |

**请求示例**

    GET /ask?question=奇变偶不变是什么口诀？

**响应示例**（`200 OK`，`Content-Type: application/json`）

    {
      "answer": "「奇变偶不变，符号看象限」……（出处：## 三、三角函数与解三角形）"
    }

**说明**：答案中的换行、引号等字符在 JSON 中会被转义（如 `\n`、`\"`），网页端解析后正常显示。

## 设计说明

1:尝试过 500 字硬切：相似度 0.4175；改按段落（~130 字）：0.5996 
→ 结论：切片字数过多会造成语义稀释，这里选用段落切片更优

2：system提示词“禁止AI脱离材料回答”→防止产生AI幻觉，
“必须标明出处”→让答案可追溯，实测发现模型能够灵活解释

3：answer() 每次用全新的 messages → 多用户互不串味，防止上下文过长造成回答偏差
代价：不支持多轮追问

4：实测发现用户重新提问仍然要等待响应时间，因此添加缓存，
重复问题可直接在缓存里取出重新回答，减少调用支出，代价：重启清空，且无失效机制


## 已知限制 / 待改进

· 单文件资料、只支持一个知识库
· 无记忆（不支持多轮追问）
· 首次问答 10~50 秒（LLM 多轮调用）
· 缓存不持久（重启清空）、无失效机制
· Markdown/LaTeX 在网页上原样显示，未渲染
· 只在本机 127.0.0.1 可用，未部署
· 【未使用版本管理（`.venv` / `__pycache__` / `chroma_db` 均不应入库，
、可通过 requirements.txt + create_db.py 重建）】