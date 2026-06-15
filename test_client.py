import requests
import json
import time

url = "http://127.0.0.1:8000/review"

# 这是一段我们要测试的烂代码
test_code = """
def update_user(name, pwd):
    db_conn = f"mysql://root:{pwd}@localhost/users"
    print("User updated")
"""

print("正在将代码发送给 ReviewBot 服务器...\n")

# 使用 stream=True 来接收流式数据
response = requests.post(url, json={"code": test_code}, stream=True)

# 逐行读取服务器实时推过来的数据
for line in response.iter_lines():
    if line:
        # 解码 SSE 数据格式 (去掉开头的 "data: " 并解析 JSON)
        decoded_line = line.decode('utf-8')
        if decoded_line.startswith("data: "):
            data_str = decoded_line[6:]
            data = json.loads(data_str)
            
            # 如果还在处理中，打印进度条
            if data["status"] == "processing":
                print(data["message"])
                time.sleep(0.5) # 为了视觉效果稍微停顿一下
            
            # 如果处理完了，打印最终报告
            elif data["status"] == "done":
                print("\n================ 最终报告 ================\n")
                print(data["report"])