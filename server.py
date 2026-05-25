from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64

app = Flask(__name__)
CORS(app)

# ==========================================
# 核心配置：换入你的 Key。由于要读图，我们调用标准的 openai 格式视觉模型
# ==========================================
DEEPSEEK_API_KEY = "sk-957d8126d3984a76976bed0a8d56a22d".strip()
API_URL = "https://api.deepseek.com/v1/chat/completions" # 如果使用的是标准OpenAI格式中继，支持视觉模型

latest_data = {
    "status": "等待硬件镜头接入...",
    "raw_image_base64": "",
    "translated_text": "暂无翻译"
}

@app.route('/k230_upload_img', methods=['POST'])
def receive_k230_img():
    global latest_data
    try:
        # 1. 接收 K230 传过来的原始图片二进制数据
        img_bytes = request.data
        if not img_bytes:
            return jsonify({"status": "error", "message": "收到空图片"}), 400
        
        print(f"\n📸 [K230 边缘端传回图像]: 成功接收图片帧，大小: {len(img_bytes)} 字节")
        
        # 2. 转换为前端和 AI 都能直接读取的 Base64 编码
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        latest_data["status"] = "AI 正在对图像进行高级多模态同传解析..."
        latest_data["raw_image_base64"] = img_base64
        
        # 3. 构建多模态大模型请求报文（提示词深度润色）
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat", # 这里可以根据你Key的权限无缝改为支持视觉的模型如 gpt-4o-mini 或 qwen-vl-max
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "你是一个搭载在高端智能网联车座舱里的多模态同传翻译官。请仔细分析这张图片：1. 提取出图片中所有的英文文本（如路牌、菜单或警告）；2. 将其翻译成地道、流利的中文。注意：为了符合车机大屏规范，请直接返回核心中文翻译结果，绝对不要带多余的问候语。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                    ]
                }
            ],
            "max_tokens": 300
        }
        
        # 4. 发起多模态推理
        print("正在向云端发起多模态大模型分析请求...")
        response = requests.post(API_URL, json=payload, headers=headers, timeout=12)
        res_json = response.json()
        
        translated_text = res_json['choices'][0]['message']['content'].strip()
        latest_data["status"] = "多模态翻译完成！"
        latest_data["translated_text"] = translated_text
        print(f"🌟 [AI 分析结果]: {translated_text}")
        
        return jsonify({"status": "success", "result": translated_text})
        
    except Exception as e:
        latest_data["status"] = f"多模态解析异常: {str(e)}"
        print(f"❌ 错误: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_ui_data', methods=['GET'])
def get_ui_data():
    return jsonify(latest_data)

if __name__ == '__main__':
    # 显式让服务器同时监听本地和你的真实热点局域网 IP
    app.run(host='10.83.194.247', port=5000, debug=True)