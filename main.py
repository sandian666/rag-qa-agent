# ===== S5 / main.py =====
# 门面：负责"谁会来敲门、敲哪个门、把话递给谁"。
#流程：
# ①  别人在浏览器敲： http://127.0.0.1:8000/hello
#                     └ 找 127.0.0.1 这台机器的 8000 端口
#                                    ↓
# ②  uvicorn 正在这个端口上【听】 → 听到敲门，接下这个请求
#                                    ↓
# ③  uvicorn 把请求交给 FastAPI： "有人找 /hello"
#                                    ↓
# ④  FastAPI 查【注册表】 →  查到： /hello 归 hello 函数管
#                                    ↓
# ⑤  调用 hello() → 执行函数体 → 拿到返回值 "你好…"
#                                    ↓
# ⑥  FastAPI 把返回值转成 JSON（正文带引号）
#                                    ↓
# ⑦  uvicorn 把它作为 HTTP 响应发回去
#                                    ↓
# ⑧  浏览器显示： 你好，这是 S5 的第一个接口。
import os

from fastapi import FastAPI     #← 从 fastapi 这个库里，取出 FastAPI 这个"类"，（库名小写 fastapi；类名大写 FastAPI，别写混）
import uvicorn,os                  #← 整个库都要用，所以直接 import 库名
from agent import answer_cached        #← 从我自己的 agent.py 里，把 answer 函数拿进来
from fastapi.responses import HTMLResponse

app = FastAPI()   #   造一个 app 对象。（括号不能省；名字就叫 app，后面两处都要用这个名字

# ===== 第 3 件东西：接口函数
#   注意顺序：装饰器必须在【函数定义的上一行】，紧挨着，中间不能空行、不能有别的东西
@app.get("/hello")    #登记一条路由：告诉 app 这张表 —— "网址 /hello 归下面那个函数管"
async def hello():    # ← 定义当一个请求打到 /hello 时，要执行哪个函数体
    return "你好，这是 S5 的第一个接口。"

@app.get("/ask")
async def ask(question: str):  #函数签名：接收一个参数，名字叫 question，类型是 str
    resp = answer_cached(question)
    return {"answer": resp}


@app.get("/",response_class=HTMLResponse)
async def index():
    current_dir=os.path.dirname(os.path.abspath(__file__))  #得到本文件夹路径去
    html_path=os.path.join(current_dir,"index.html")   #把本文件夹路径和网页路径拼在一起
    with open(html_path,"r", encoding="utf-8" ) as f:
        return f.read()


#   缩进 4 空格，里面调用 uvicorn.run(...)
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True,
                reload_dirs=[os.path.dirname(os.path.abspath(__file__))])


