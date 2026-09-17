# ===== S5 / agent.py =====
import os, json, datetime, chromadb, requests
from openai import OpenAI

# ================= 常量与路径（改造 A） =================
# 【照抄】把"当前文件所在的文件夹"取出来，得到本py文件所在文件夹，作为基准路径，程序以后放哪里都能跑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 拼接出配置文件、向量库目录的绝对路径，防止运行位置改变导致找不到文件
COLLECTION_FILE = os.path.join(BASE_DIR, "current_collection.txt")     # ← 以"文件自己"为基准
CHROMA_DIR      = os.path.join(BASE_DIR, "chroma_db")                  # ← 跟工作目录【无关

with open(COLLECTION_FILE,encoding="utf-8") as f:
    COLLECTION_NAME=f.read().strip()

_answer_cache = {}
max_quota=3
_call_count={}

# ================= 两个 client（改造 B） =================
embed_client = OpenAI(api_key=os.environ.get("ZHIPU_API_KEY"),
                      base_url="https://open.bigmodel.cn/api/paas/v4/")
chat_client = OpenAI(api_key=os.environ.get("ali-deepseek-api-key"),
         base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",)
chat_model = "deepseek-v4.1-flash"

# ================= 向量库 =================
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
col_b = chroma_client.get_collection(name=COLLECTION_NAME)

# ================= 4 个工具函数 =================

def search_notes(question):# 把问题转换成向量数据，然后取第一个数据的向量
    qv = embed_client.embeddings.create(model="embedding-3", input=[question]).data[0].embedding
    result= col_b.query(query_embeddings=[qv], n_results=3)  # 问题向量与chunk向量对比相似度，取n_result个结果
    docs, meta = result["documents"][0], result["metadatas"][0]
    result = ""
    for i, (doc,source_meta) in enumerate(zip(docs,meta)):
        result += f"【片段{i + 1}】（来源：{source_meta['小节']}）\n{doc}\n\n"
    return result


def get_weather(city):
    url = f"https://wttr.in/{city}?format=j1"
    try:  # json() 先执行 → 对着 500 的错误页解析 → 抛 JSONDecodeError
        # JSONDecodeError 不是 RequestException 的子类 → except requests.exceptions.RequestException 接不住
        # → 异常穿透所有 except → 程序崩
        # 移到前面 → 抛的是 HTTPError（是 RequestException 的子类）→ 接住 → 返回人话 → Agent 活着
        resp = requests.get(url, timeout=10)  # 不设超时，你的程序会永久挂起，线程/请求全被堵住
        resp.raise_for_status()  # 主动抛异常
        data = resp.json()  # resp.json() 本质上就是 json.loads() 的包装
        # —— 它内部帮你做了两件事：从响应里取出正文文本（resp.text）、猜对编码，然后交给 json.loads() 解析。
        temp = data["current_condition"][0]["temp_C"]
        humidity = data["current_condition"][0]["humidity"]
        desc = data["current_condition"][0]["weatherDesc"][0]["value"]
        return f"{city}当前天气：{desc}，气温 {temp}°C，湿度 {humidity}%。"
    except requests.exceptions.RequestException as e:
        return f"查询{city}天气失败：{e}"


def get_time():
    now = datetime.datetime.now()  # 调用datetime模块的datetime类的now方法
    return now.strftime('%Y-%m-%d %H:%M:%S')  # 直接返回字符串，不要花括号


def calculate(a, b, op):
    a = int(a)
    b = int(b)
    if op == "+":
        return f"{a} + {b} = {a + b}"
    elif op == "-":
        return f"{a} - {b} = {a - b}"
    elif op == "*":
        return f"{a} * {b} = {a * b}"
    elif op == "/":
        if b == 0:
            return "错误：除数不能为 0"
        return f"{a} / {b} = {a / b}"
    else:
        return f"不支持的运算符：{op}"

# ================= tools + tools_map =================
# TODO 4：从 S4 主程序【原样搬】tools 列表（4 个工具定义）和 tools_map
#   一字不改，连 description 的中文都不用动
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询某个城市的当前天气。",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名，如 北京"}},
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "获取当前的日期和时间。当用户询问现在几点、今天几号时使用。",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "对两个整数执行四则运算并返回结果。当用户需要做加减乘除计算时使用.",
            "parameters": {
                "type": "object",
                "properties": {"a": {"type": "integer", "description": "第一个运算数"},
                               "b": {"type": "integer", "description": "第二个运算数"},
                               "op":{"type": "string",
                                     "enum":["+","-","*","/"],   #enum = 枚举，作用是把取值限定在给定的列表里
                                     "description":"要执行的运算类型。"}
                               },
                "required": ["a","b","op"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "根据用户提出的问题检索文本得到答案，当用户询问有关高中数学知识的问题时，调用此函数。",
            "parameters": {
                            "type": "object",
                            "properties": {"question":{
                                               "type":"string",
                                               "description": "从笔记里查询问题答案，答案尽可能科学严谨。"}
                            },
                            "required": ["question"] }
            }
    },
]

tools_map={
    "get_weather":get_weather,
    "get_time":get_time,
    "calculate":calculate,
    "search_notes":search_notes
}                           # 4 个工具的说明书

# ================= 核心：answer() =================
def answer(question):
    """输入问题(str) → 返回答案(str)。"""
    messages = [
        {"role": "system", "content": """你是一个严谨的老师，用户询问关于高中数学有关的知识时，
        你要根据文本检索相关内容并标明出处回答，若该知识文本没有请回复没有检索到相关内容。
        用户询问天气、时间或需要计算时，调用相应的工具。"""},
        {"role": "user", "content": question},
    ]

    while True:                                   # ← 只留【内层】：管"模型 ↔ 工具"的循环
        resp = chat_client.chat.completions.create(   # 修②：不要引号，不带 s
            model=chat_model,
            messages=messages,
            tools=tools,
        )
        msg = resp.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:                    # 模型不再要工具 → 这就是最终答案
            return msg.content                    # 修③：返回，不打印

        for tool_call in msg.tool_calls:          # 修④：下面 4 行必须是【for 里面】的
            function_name = tool_call.function.name
            arg = json.loads(tool_call.function.arguments)
            result = tools_map[function_name](**arg)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

#带缓存的问答：同一个问题问过就不再花钱重算.
def answer_cached(question):
    Today=datetime.date.today()
    if question in _answer_cache:
        return _answer_cache[question]
    else:
        count=_call_count.get(Today,0)
        count+=1
        _call_count[Today]=count
        if _call_count[Today] > max_quota:
            result=("今天额度已用完，明天再来吧")
        else:
            result=answer(question)
            _answer_cache[question]=result
    return result



# ================= 自测（改造 D） =================
if __name__ == "__main__":
    print("自检：", col_b.name, col_b.count())          # 期望：math_note_V7 59
    print(answer("奇变偶不变是什么口诀？"))


