#!/usr/bin/env python3
import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QRadioButton, QButtonGroup, 
                             QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

# Ensure we can import the core logic
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)
import vpngate_cli as vpncore

class Worker(QThread):
    finished = pyqtSignal(bool, str)
    
    def __init__(self, action, server=None, proto=None):
        super().__init__()
        self.action = action
        self.server = server
        self.proto = proto
        
    def run(self):
        try:
            if self.action == "connect":
                success, msg = vpncore.connect_vpn(self.server, force_proto=self.proto)
            else:
                success, msg = vpncore.disconnect_vpn()
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, str(e))

class VPNWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VPN Gate Client (Qt/Wayland)")
        self.setMinimumSize(950, 650)
        self.all_servers = []
        self.filtered_servers = []
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        
        # 1. TOP: Server List
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Idx", "Proto", "Country", "IP", "Score", "Ping"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.main_layout.addWidget(self.table)
        
        # 2. MIDDLE: Detailed Status
        self.status_container = QWidget()
        self.status_layout = QVBoxLayout(self.status_container)
        
        self.status_label = QLabel("Status: DISCONNECTED")
        self.status_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_layout.addWidget(self.status_label)
        
        self.stats_label = QLabel("")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet("font-family: monospace; color: #555;")
        self.status_layout.addWidget(self.stats_label)
        
        self.status_container.setStyleSheet("background: #f9f9f9; border: 1px solid #ddd; border-radius: 8px; margin: 5px;")
        self.main_layout.addWidget(self.status_container)
        
        # 3. BOTTOM: Controls
        controls_layout = QHBoxLayout()
        
        self.radio_group = QButtonGroup(self)
        self.radio_udp = QRadioButton("UDP Preference")
        self.radio_tcp = QRadioButton("TCP Preference")
        self.radio_all = QRadioButton("Show All")
        self.radio_udp.setChecked(True)
        
        self.radio_group.addButton(self.radio_udp)
        self.radio_group.addButton(self.radio_tcp)
        self.radio_group.addButton(self.radio_all)
        self.radio_group.buttonClicked.connect(self.apply_filter)
        
        controls_layout.addWidget(self.radio_udp)
        controls_layout.addWidget(self.radio_tcp)
        controls_layout.addWidget(self.radio_all)
        controls_layout.addStretch()
        
        self.btn_refresh = QPushButton("Refresh List")
        self.btn_refresh.clicked.connect(self.load_servers)
        
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        self.btn_connect.setMinimumHeight(40)
        self.btn_connect.clicked.connect(self.start_connect)
        
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        self.btn_disconnect.setMinimumHeight(40)
        self.btn_disconnect.clicked.connect(self.start_disconnect)
        
        controls_layout.addWidget(self.btn_refresh)
        controls_layout.addWidget(self.btn_connect)
        controls_layout.addWidget(self.btn_disconnect)
        
        self.main_layout.addLayout(controls_layout)
        
        # Timer for stats update (every 2 seconds)
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.refresh_stats)
        self.stats_timer.start(2000)
        
        self.load_servers()
        self.update_ui_state()

    def update_ui_state(self, is_busy=False):
        active = vpncore.is_active()
        
        if active:
            self.status_label.setText("Status: VPN IS ACTIVE")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 16px; font-weight: bold;")
        else:
            self.status_label.setText("Status: DISCONNECTED")
            self.status_label.setStyleSheet("color: #c0392b; font-size: 16px; font-weight: bold;")
            self.stats_label.setText("")

        if is_busy:
            self.table.setEnabled(False)
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(False)
            self.btn_refresh.setEnabled(False)
            for b in self.radio_group.buttons(): b.setEnabled(False)
        else:
            self.table.setEnabled(not active)
            self.btn_connect.setEnabled(not active)
            self.btn_refresh.setEnabled(not active)
            self.btn_disconnect.setEnabled(active)
            for b in self.radio_group.buttons(): b.setEnabled(not active)

    def refresh_stats(self):
        if vpncore.is_active():
            stats = vpncore.get_stats()
            if stats:
                up, down, ping, loss = stats
                self.stats_label.setText(f"DOWNLOAD: {down:.1f} KB/s  |  UPLOAD: {up:.1f} KB/s  |  PING: {ping}  |  LOSS: {loss}")
        else:
            # If it was active but now it's not (disconnected externally)
            if "ACTIVE" in self.status_label.text():
                self.update_ui_state()

    def load_servers(self):
        self.status_label.setText("Status: Fetching servers...")
        QApplication.processEvents()
        self.all_servers = vpncore.get_servers()
        self.apply_filter()

    def apply_filter(self):
        self.filtered_servers = []
        pref_udp = self.radio_udp.isChecked()
        pref_tcp = self.radio_tcp.isChecked()
        pref_all = self.radio_all.isChecked()
        
        for s in self.all_servers:
            if pref_all: self.filtered_servers.append(s)
            elif pref_udp and s['has_udp']: self.filtered_servers.append(s)
            elif pref_tcp and s['has_tcp']: self.filtered_servers.append(s)
            
        self.filtered_servers.sort(key=lambda x: int(x['Score']), reverse=True)
        self.update_table()
        self.update_ui_state()

    def update_table(self):
        self.table.setRowCount(0)
        pref_tcp = self.radio_tcp.isChecked()
        for i, s in enumerate(self.filtered_servers[:100]):
            self.table.insertRow(i)
            # Display logic
            p_display = "TCP" if (pref_tcp and s['has_tcp']) or not s['has_udp'] else "UDP"
            self.table.setItem(i, 0, QTableWidgetItem(str(i)))
            self.table.setItem(i, 1, QTableWidgetItem(p_display))
            self.table.setItem(i, 2, QTableWidgetItem(s['CountryShort']))
            self.table.setItem(i, 3, QTableWidgetItem(s['IP']))
            self.table.setItem(i, 4, QTableWidgetItem(s['Score']))
            self.table.setItem(i, 5, QTableWidgetItem(s['Ping']))

    def start_connect(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a server.")
            return
            
        server = self.filtered_servers[row]
        proto = "tcp" if self.radio_tcp.isChecked() else "udp"
        
        self.status_label.setText(f"Status: Connecting to {server['IP']}...")
        self.update_ui_state(is_busy=True)
        
        self.worker = Worker("connect", server, proto)
        self.worker.finished.connect(self.on_action_finished)
        self.worker.start()

    def start_disconnect(self):
        self.status_label.setText("Status: Disconnecting...")
        self.update_ui_state(is_busy=True)
        self.worker = Worker("disconnect")
        self.worker.finished.connect(self.on_action_finished)
        self.worker.start()

    def on_action_finished(self, success, message):
        if not success:
            QMessageBox.critical(self, "VPN Error", message)
        self.status_label.setText(f"Status: {message}")
        self.update_ui_state(is_busy=False)

if __name__ == "__main__":
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
    app = QApplication(sys.argv)
    window = VPNWindow()
    window.show()
    sys.exit(app.exec())
