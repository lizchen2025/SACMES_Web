#!/usr/bin/env python3
"""
测试文件传输同步机制的简单脚本
"""

import time
import threading
import socketio
import os

# 测试配置
SERVER_URL = "http://localhost:5000"  # 本地测试服务器
AUTH_TOKEN = "your_super_secret_token_here"

# 模拟客户端状态
file_processing_complete = False
pending_file_ack = None

# Socket.IO 客户端
sio = socketio.Client()

@sio.event
def connect():
    print("✓ 已连接到测试服务器")

@sio.event
def disconnect():
    print("✗ 已断开与测试服务器的连接")

@sio.on('file_processing_complete')
def on_file_processing_complete(data):
    global file_processing_complete, pending_file_ack
    received_filename = data.get('filename', '')
    if pending_file_ack and received_filename == pending_file_ack:
        file_processing_complete = True
        print(f"✓ 收到处理完成确认: {received_filename}")
    else:
        print(f"⚠ 意外的处理确认: {received_filename}")

def test_sync_mechanism():
    """测试同步机制"""
    global file_processing_complete, pending_file_ack

    test_filename = "test_100Hz_001.txt"
    test_content = "# Test file content\n1.0\t2.0\n1.1\t2.1\n"

    print(f"→ 发送测试文件: {test_filename}")

    # 重置状态
    file_processing_complete = False
    pending_file_ack = test_filename

    # 发送文件
    sio.emit('stream_instrument_data', {'filename': test_filename, 'content': test_content})

    # 等待确认
    timeout_counter = 0
    max_wait_time = 10  # 10秒超时

    print("等待服务器处理完成确认...")
    while not file_processing_complete and timeout_counter < max_wait_time:
        time.sleep(0.1)
        timeout_counter += 0.1

    if file_processing_complete:
        print(f"✓ 同步机制工作正常，等待时间: {timeout_counter:.1f}秒")
        return True
    else:
        print(f"✗ 超时：{max_wait_time}秒内未收到确认")
        return False

def main():
    print("=== 文件传输同步机制测试 ===")

    try:
        # 连接到服务器
        print("连接到测试服务器...")
        headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
        sio.connect(SERVER_URL, headers=headers, socketio_path='socket.io')

        # 等待连接稳定
        time.sleep(1)

        # 运行测试
        success = test_sync_mechanism()

        if success:
            print("\n✓ 测试通过：同步机制正常工作")
        else:
            print("\n✗ 测试失败：同步机制存在问题")

    except Exception as e:
        print(f"✗ 测试错误: {e}")
    finally:
        if sio.connected:
            sio.disconnect()
        print("测试完成")

if __name__ == "__main__":
    main()