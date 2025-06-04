import socket
import pyautogui
import io
from utils import encrypt_data

CLIENT_HOST = '0.0.0.0'
CLIENT_PORT = 6000
SERVER_IP = '127.0.0.1'
SERVER_PORT = 5000

def get_encryption_key():
    s = socket.socket()
    s.connect((SERVER_IP, SERVER_PORT))
    s.send(b"GET_KEY")
    key = s.recv(1024)
    s.close()
    return key

def handle_request(conn, key):
    cmd = conn.recv(1024)
    if cmd in [b"GET_SCREENSHOT", b"GET_LIVE_SCREENSHOT"]:
        screenshot = pyautogui.screenshot()
        buf = io.BytesIO()
        screenshot.save(buf, format='PNG')
        encrypted = encrypt_data(buf.getvalue(), key)
        conn.sendall(encrypted)
    conn.close()

def start_client_listener():
    key = get_encryption_key()
    s = socket.socket()
    s.bind((CLIENT_HOST, CLIENT_PORT))
    s.listen(1)
    print(f"[KLIENT] Nasłuchuje na porcie {CLIENT_PORT}...")
    while True:
        conn, addr = s.accept()
        handle_request(conn, key)

if __name__ == '__main__':
    start_client_listener()
