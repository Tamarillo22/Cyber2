import socket
import os
from datetime import datetime
from PyQt5 import QtWidgets, QtCore, QtGui
from utils import generate_key, decrypt_data


KEY = generate_key()
SAVE_DIR = "screenshots"
os.makedirs(SAVE_DIR, exist_ok=True)

CLIENT_IP = '127.0.0.1'
CLIENT_PORT = 6000


class ServerThread(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)

    def run(self):
        server = socket.socket()
        server.bind(('0.0.0.0', 5000))
        server.listen(5)
        self.log_signal.emit("Serwer nasłuchuje na porcie 5000...")

        while True:
            client, addr = server.accept()
            request_type = client.recv(1024)

            if request_type == b"GET_KEY":
                client.send(KEY)
                self.log_signal.emit(f"Klient {addr} pobrał klucz szyfrowania.")
            elif request_type == b"SCREENSHOT":
                client.send(b"OK")
                image_data = b''
                while True:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    image_data += chunk
                try:
                    decrypted = decrypt_data(image_data, KEY)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filepath = os.path.join(SAVE_DIR, f"{addr[0]}_{timestamp}.png")
                    with open(filepath, 'wb') as f:
                        f.write(decrypted)
                    self.log_signal.emit(f"Odebrano i zapisano zrzut ekranu: {filepath}")
                except Exception as e:
                    self.log_signal.emit(f"Błąd odszyfrowywania: {e}")
            client.close()


class ServerApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Serwer Monitorowania Pulpitu")
        self.resize(800, 650)

        
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.log_box = QtWidgets.QTextEdit()
        self.log_box.setReadOnly(True)
        self.layout.addWidget(self.log_box)

        self.button = QtWidgets.QPushButton("Pobierz zrzut ekranu od klienta")
        self.button.clicked.connect(self.request_screenshot)
        self.layout.addWidget(self.button)

        self.live_button = QtWidgets.QPushButton("Start podgląd na żywo")
        self.live_button.setCheckable(True)
        self.live_button.clicked.connect(self.toggle_live_view)
        self.layout.addWidget(self.live_button)

        self.image_label = QtWidgets.QLabel("Podgląd zrzutu")
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setFixedHeight(400)
        self.layout.addWidget(self.image_label)

        self.server_thread = ServerThread()
        self.server_thread.log_signal.connect(self.update_log)
        self.server_thread.start()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.fetch_live_screenshot)

    def update_log(self, message):
        self.log_box.append(message)

    def request_screenshot(self):
        try:
            self.update_log(f"[MANUAL] Żądam screena od {CLIENT_IP}:{CLIENT_PORT}")
            img = self.get_screenshot_from_client("GET_SCREENSHOT")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(SAVE_DIR, f"screenshot_on_demand_{timestamp}.png")
            with open(path, 'wb') as f:
                f.write(img)
            self.update_log(f"Zrzut zapisany: {path}")
        except Exception as e:
            self.update_log(f"Błąd: {e}")

    def toggle_live_view(self):
        if self.live_button.isChecked():
            self.live_button.setText("Stop podgląd na żywo")
            self.timer.start(1000)  # co 1 sekunda
        else:
            self.live_button.setText("Start podgląd na żywo")
            self.timer.stop()

    def fetch_live_screenshot(self):
        try:
            img = self.get_screenshot_from_client("GET_LIVE_SCREENSHOT")
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(img)
            scaled = pixmap.scaled(self.image_label.size(), QtCore.Qt.KeepAspectRatio)
            self.image_label.setPixmap(scaled)
        except Exception as e:
            self.update_log(f"[LIVE] Błąd: {e}")

    def get_screenshot_from_client(self, command):
        s = socket.socket()
        s.settimeout(3)
        s.connect((CLIENT_IP, CLIENT_PORT))
        s.send(command.encode())

        data = b''
        while True:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
            except socket.timeout:
                break
        s.close()
        return decrypt_data(data, KEY)

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    window = ServerApp()
    window.show()
    app.exec_()
