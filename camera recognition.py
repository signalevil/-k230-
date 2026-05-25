import network
import time
import socket
import json
import aidemo

# ----------------------------------------------------
# 【官方正统多媒体导入】根据文档完美修正
# ----------------------------------------------------
from media.sensor import *

# ==========================================
# 1. 基础配置（请确保 Wi-Fi 账号密码正确）
# ==========================================
WIFI_SSID = "林北"
WIFI_PASS = "5288202lhy"
COMPUTER_IP = "10.83.194.247"  # 你电脑的真实局域网 IP
PORT = 5000

# ==========================================
# 2. 局域网通信函数（原生 Socket 传输）
# ==========================================
def send_to_computer(text_content):
    test_data = {
        "device": "K230_Sensor_Lens",
        "msg": text_content
    }
    json_bytes = json.dumps(test_data).encode('utf-8')

    try:
        ai_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ai_socket.settimeout(1.5)  # 超时防卡死
        ai_socket.connect((COMPUTER_IP, PORT))

        http_request = (
            "POST /k230_data HTTP/1.1\r\n"
            "Host: {}:{}\r\n"
            "Content-Type: application/json\r\n"
            "Content-Length: {}\r\n"
            "Connection: close\r\n\r\n"
        ).format(COMPUTER_IP, PORT, len(json_bytes)).encode('utf-8') + json_bytes

        ai_socket.sendall(http_request)
        ai_socket.close()
        print(f" [成功发送至大屏]: '{text_content}'")
        return True
    except Exception as e:
        print(" [发送大屏失败]:", e)
        return False

# ==========================================
# 3. Wi-Fi 连接逻辑
# ==========================================
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("正在连接 Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        for _ in range(20):
            if wlan.isconnected(): break
            time.sleep(0.5)

    if wlan.isconnected():
        print("Wi-Fi 连接成功! 本地 IP:", wlan.ifconfig()[0])
        return True
    return False

# ==========================================
# 4. 主程序：官方 Sensor 管线 + 本地 OCR 推理
# ==========================================
def main():
    if not connect_wifi():
        print("网络连接失败，退出程序")
        return

    # ----------------------------------------------------
    # 【核心修正】根据官方文档初始化 Sensor 摄像头
    # ----------------------------------------------------
    print("\n正在初始化 K230 摄像头模块...")
    try:
        # 构造第一个摄像头对象，设置分辨率为常用的 640x480
        sensor = Sensor(id=0, width=640, height=480, fps=30)
        sensor.reset() # 复位摄像头
        print(" 摄像头硬件初始化成功！")
    except Exception as e:
        print(" 摄像头初始化失败，错误原因:", e)
        return

    print("\n正在加载 K230 本地 PaddleOCR 硬件加速模型...")
    # 调起底层硬件 KPU 专属的 OCR 算子
    ocr = aidemo.ocr()
    print("AI 视觉扫描镜已就绪！请将摄像头对准英文文本...")

    last_sent_text = ""
    last_sent_time = 0

    while True:
        # 1. 抓取当前摄像头的一帧画面
        # 注：部分固件版本抓图方法是 snapshot() 或者是 capture()
        # 根据 OpenMV 标准，这里使用常用的 snapshot()
        img = sensor.snapshot()

        # 2. 跑本地离线 OCR 推理（利用 K230 的 6TOPS KPU 算力加速）
        ocr_results = ocr.run(img)

        current_frame_text = ""

        # 3. 提取文字结果并画框
        if ocr_results:
            for result in ocr_results:
                text = result.text.strip()
                if len(text) > 2:
                    current_frame_text += text + " "
                    # 在本地图像上画绿框框，给导师展示纯正的视觉工作量
                    img.draw_rectangle(result.box[0], result.box[1], result.box[2], result.box[3], color=(0, 255, 0), thickness=2)

        # 4. 局域网隔空同步逻辑
        if current_frame_text and current_frame_text != last_sent_text:
            current_time = time.time()
            # 文本发生变化且距离上次发送大于 1.5 秒，防止高频轰炸云端
            if current_time - last_sent_time > 1.5:
                print(f"\n[OCR 捕获英文]: {current_frame_text}")
                send_to_computer(current_frame_text)
                last_sent_text = current_frame_text
                last_sent_time = current_time

        # 适当降低主循环频率，给板子留出散热空间
        time.sleep_ms(30)

if __name__ == "__main__":
    main()
