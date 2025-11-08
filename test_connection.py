#!/usr/bin/env python
"""
Quick diagnostic script to test SocketIO connection
"""
import socketio
import time

# Create a test client
sio = socketio.Client(
    logger=True,
    engineio_logger=True
)

@sio.event
def connect():
    print("[TEST] Connected to server!")
    print(f"[TEST] Transport: {sio.transport()}")
    print(f"[TEST] SID: {sio.sid}")

@sio.event
def disconnect():
    print("[TEST] Disconnected from server")

@sio.on('session_info')
def on_session_info(data):
    print(f"[TEST] Received session_info: {data}")

@sio.on('set_filters')
def on_set_filters(data):
    print(f"[TEST] Received set_filters: {data}")

@sio.on('file_processing_complete')
def on_ack(data):
    print(f"[TEST] Received ACK: {data}")

if __name__ == '__main__':
    import sys
    server_url = sys.argv[1] if len(sys.argv) > 1 else 'https://test-narroyo.apps.cloudapps.unc.edu'
    user_id = 'test-user-123'

    print(f"[TEST] Connecting to {server_url}")
    print(f"[TEST] User ID: {user_id}")

    try:
        # Connect as agent
        sio.connect(
            f"{server_url}?user_id={user_id}",
            headers={'User-Agent': 'Test-Agent/1.0'},
            transports=['polling', 'websocket'],
            wait_timeout=30
        )

        print(f"[TEST] Connection established, transport: {sio.transport()}")

        # Wait for session info
        time.sleep(2)

        # Send a test file
        print("[TEST] Sending test data...")
        test_data = {
            'filename': 'test.txt',
            'content': 'x' * 1000  # 1KB test
        }

        sio.emit('stream_instrument_data', test_data)
        print("[TEST] Test data sent")

        # Wait for response
        time.sleep(10)

        sio.disconnect()
        print("[TEST] Test complete")

    except Exception as e:
        print(f"[TEST] ERROR: {e}")
        import traceback
        traceback.print_exc()
