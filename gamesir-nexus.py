#!/usr/bin/env python3
import os
import json
import struct
import sys
from threading import Thread

# Importação da arquitetura estável do Qt para o Flatpak
try:
    sys.path.append('/app/lib/python3.11/site-packages')
    from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QProgressBar, QGroupBox
    from PySide6.QtCore import Qt, QMetaObject, Q_ARG, Slot
except ImportError:
    print("[!] Erro: PySide6 não encontrado localmente no host.")
    print("[*] Nota: Isso é normal no host. O Flatpak fará o download e build de forma isolada.")

class GameSirCyclone2:
    def __init__(self, profile_path="profile_default.json"):
        self.profile_path = profile_path
        self.DEADZONE_L_X = 4000
        self.DEADZONE_L_Y = 2000
        self.DEADZONE_R_X = 3000
        self.DEADZONE_R_Y = 3000
        self.mappings = {}
        self.profile_name = "Padrão de Fábrica"
        self.load_profile()

    def load_profile(self):
        # Tenta carregar na pasta local ou na pasta binária do Flatpak
        paths = [self.profile_path, f"/app/bin/{self.profile_path}"]
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, 'r') as f:
                        data = json.load(f)
                    dz = data.get("deadzones", {})
                    self.DEADZONE_L_X = dz.get("left_analog_x", 4000)
                    self.DEADZONE_L_Y = dz.get("left_analog_y", 2000)
                    self.DEADZONE_R_X = dz.get("right_analog_x", 3000)
                    self.DEADZONE_R_Y = dz.get("right_analog_y", 3000)
                    self.mappings = data.get("mappings", {})
                    self.profile_name = data.get("profile_name", "Padrão de Fábrica")
                    return
                except Exception:
                    pass

    def apply_deadzone(self, raw_value, deadzone):
        if abs(raw_value) < deadzone:
            return 0
        if raw_value > 0:
            return int(((raw_value - deadzone) / (32767 - deadzone)) * 32767)
        else:
            return int(((raw_value + deadzone) / (32767 - deadzone)) * -32767)

class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        self.setWindowTitle("GameSir Cyclone 2 - Painel Linux (Qt)")
        self.resize(500, 520)
        self.setStyleSheet("QMainWindow { background-color: #1e1e1e; }")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Cabeçalho
        title = QLabel("GAMESIR NEXUS LINUX")
        title.setStyleSheet("font-family: 'Helvetica'; font-size: 18px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Perfil
        self.profile_label = QLabel(f"Perfil Ativo: {self.controller.profile_name}")
        self.profile_label.setStyleSheet("font-size: 12px; color: #00ff66;")
        self.profile_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.profile_label)
        
        # Monitor de Input
        self.status_label = QLabel("Aguardando input do controle...")
        self.status_label.setStyleSheet("font-size: 13px; color: #aaaaaa; background-color: #2d2d2d; border: 1px solid #444444; border-radius: 4px; padding: 15px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Grupo Analógico Esquerdo
        group_l = QGroupBox(" Efeito Hall - Analógico Esquerdo ")
        group_l.setStyleSheet("QGroupBox { font-weight: bold; color: #ffffff; border: 1px solid #444444; border-radius: 6px; margin-top: 10px; padding: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; horizontal-alignment: left; }")
        layout_l = QVBoxLayout(group_l)
        
        lbl_lx = QLabel("Eixo X (Horizontal):", group_l)
        lbl_lx.setStyleSheet("color: #cccccc; font-size: 11px;")
        layout_l.addWidget(lbl_lx)
        self.bar_lx = QProgressBar(group_l)
        self.bar_lx.setRange(0, 100)
        self.bar_lx.setValue(50)
        self.bar_lx.setStyleSheet("QProgressBar { background-color: #2d2d2d; border: none; border-radius: 3px; height: 12px; text-align: center; } QProgressBar::chunk { background-color: #00ff66; border-radius: 3px; }")
        layout_l.addWidget(self.bar_lx)
        
        lbl_ly = QLabel("Eixo Y (Vertical):", group_l)
        lbl_ly.setStyleSheet("color: #cccccc; font-size: 11px;")
        layout_l.addWidget(lbl_ly)
        self.bar_ly = QProgressBar(group_l)
        self.bar_ly.setRange(0, 100)
        self.bar_ly.setValue(50)
        self.bar_ly.setStyleSheet("QProgressBar { background-color: #2d2d2d; border: none; border-radius: 3px; height: 12px; text-align: center; } QProgressBar::chunk { background-color: #00ff66; border-radius: 3px; }")
        layout_l.addWidget(self.bar_ly)
        layout.addWidget(group_l)
        
        # Grupo Analógico Direito
        group_r = QGroupBox(" Efeito Hall - Analógico Direito ")
        group_r.setStyleSheet("QGroupBox { font-weight: bold; color: #ffffff; border: 1px solid #444444; border-radius: 6px; margin-top: 10px; padding: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; horizontal-alignment: left; }")
        layout_r = QVBoxLayout(group_r)
        
        lbl_rx = QLabel("Eixo X (Horizontal):", group_r)
        lbl_rx.setStyleSheet("color: #cccccc; font-size: 11px;")
        layout_r.addWidget(lbl_rx)
        self.bar_rx = QProgressBar(group_r)
        self.bar_rx.setRange(0, 100)
        self.bar_rx.setValue(50)
        self.bar_rx.setStyleSheet("QProgressBar { background-color: #2d2d2d; border: none; border-radius: 3px; height: 12px; text-align: center; } QProgressBar::chunk { background-color: #00ff66; border-radius: 3px; }")
        layout_r.addWidget(self.bar_rx)
        
        lbl_ry = QLabel("Eixo Y (Vertical):", group_r)
        lbl_ry.setStyleSheet("color: #cccccc; font-size: 11px;")
        layout_r.addWidget(lbl_ry)
        self.bar_ry = QProgressBar(group_r)
        self.bar_ry.setRange(0, 100)
        self.bar_ry.setValue(50)
        self.bar_ry.setStyleSheet("QProgressBar { background-color: #2d2d2d; border: none; border-radius: 3px; height: 12px; text-align: center; } QProgressBar::chunk { background-color: #00ff66; border-radius: 3px; }")
        layout_r.addWidget(self.bar_ry)
        layout.addWidget(group_r)

    @Slot(str)
    def update_btn_text(self, text):
        self.status_label.setText(f"Botão Pressionado: {text}")
        self.status_label.setStyleSheet("font-size: 13px; color: #ffffff; background-color: #0055ff; border: 1px solid #0044cc; border-radius: 4px; padding: 15px;")

    @Slot(int, float)
    def update_axis_bar(self, axis_id, percentage):
        if axis_id == 0: self.bar_lx.setValue(int(percentage))
        elif axis_id == 1: self.bar_ly.setValue(int(percentage))
        elif axis_id == 3: self.bar_rx.setValue(int(percentage))
        elif axis_id == 4: self.bar_ry.setValue(int(percentage))

def read_hardware(controller, window):
    paths = ['/dev/input/js0', '/dev/input/js1']
    device_path = None
    for p in paths:
        if os.path.exists(p):
            device_path = p
            break
    if not device_path:
        return
        
    fn_format = 'IhBB'
    event_size = struct.calcsize(fn_format)
    
    try:
        with open(device_path, 'rb') as fd:
            while True:
                event = fd.read(event_size)
                if not event: break
                time, value, ev_type, number = struct.unpack(fn_format, event)
                actual_type = ev_type & ~0x80
                
                if actual_type == 1 and value == 1:
                    btn_key = f"btn_{number}"
                    mapped_name = controller.mappings.get(btn_key, f"ID {number}")
                    QMetaObject.invokeMethod(window, "update_btn_text", Qt.QueuedConnection, Q_ARG(str, mapped_name))
                
                elif actual_type == 2:
                    if number in (0, 1, 3, 4):
                        dz = controller.DEADZONE_L_X if number==0 else (controller.DEADZONE_L_Y if number==1 else (controller.DEADZONE_R_X if number==3 else controller.DEADZONE_R_Y))
                        f = controller.apply_deadzone(value, dz)
                        pct = ((f + 32767) / 65534) * 100
                        QMetaObject.invokeMethod(window, "update_axis_bar", Qt.QueuedConnection, Q_ARG(int, number), Q_ARG(float, pct))
    except Exception:
        pass

def main():
    controller = GameSirCyclone2()
    app = QApplication(sys.argv)
    window = MainWindow(controller)
    window.show()
    
    hardware_thread = Thread(target=read_hardware, args=(controller, window), daemon=True)
    hardware_thread.start()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
