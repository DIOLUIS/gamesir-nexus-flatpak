#!/usr/bin/env python3
import os, json, struct, sys
sys.path.append('/app/lib/python3.11/site-packages')
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                               QWidget, QProgressBar, QGroupBox, QTabWidget, QPushButton, QHBoxLayout)
from PySide6.QtCore import Qt, QTimer

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
        paths = [self.profile_path, f"/app/bin/{self.profile_path}"]
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, 'r') as f: data = json.load(f)
                    dz = data.get("deadzones", {})
                    self.DEADZONE_L_X = dz.get("left_analog_x", 4000)
                    self.DEADZONE_L_Y = dz.get("left_analog_y", 2000)
                    self.DEADZONE_R_X = dz.get("right_analog_x", 3000)
                    self.DEADZONE_R_Y = dz.get("right_analog_y", 3000)
                    self.mappings = data.get("mappings", {})
                    self.profile_name = data.get("profile_name", "Padrão de Fábrica")
                    return
                except Exception: pass

    def apply_deadzone(self, raw_value, deadzone):
        if abs(raw_value) < deadzone: return 0
        if raw_value > 0: return int(((raw_value - deadzone) / (32767 - deadzone)) * 32767)
        else: return int(((raw_value + deadzone) / (32767 - deadzone)) * -32767)

class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("GameSir Nexus - Painel de Controlo")
        self.resize(600, 550)
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; color: #ffffff; }
            QTabWidget::pane { border: 1px solid #444; border-radius: 4px; }
            QTabBar::tab { background: #2d2d2d; color: #aaa; padding: 10px 20px; border: 1px solid #444; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #0055ff; color: white; font-weight: bold; }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        title = QLabel("GAMESIR NEXUS")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        self.profile_label = QLabel(f"Perfil Ativo: {self.controller.profile_name}")
        self.profile_label.setStyleSheet("color: #00ff66; margin-bottom: 10px;")
        self.profile_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.profile_label)

        # Sistema de Abas (Tabs)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.setup_tab_diagnostico()
        self.setup_tab_iluminacao()
        self.setup_tab_vibracao()
        self.setup_tab_mapeamento()

        self.last_pct = {0: 50, 1: 50, 3: 50, 4: 50}
        self.fd = None
        self.init_hardware()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_hardware)
        self.timer.start(16)

    def setup_tab_diagnostico(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.status_label = QLabel("Aguardando input do controle...")
        self.status_label.setStyleSheet("color: #aaaaaa; background-color: #2d2d2d; padding: 15px; border-radius: 4px; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        group_l = QGroupBox(" Analógico Esquerdo (Hall Effect) ")
        group_l.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #444; border-radius: 6px; margin-top: 10px; padding: 10px; }")
        layout_l = QVBoxLayout(group_l)
        self.bar_lx = QProgressBar(); self.bar_lx.setRange(0, 100); self.bar_lx.setValue(50)
        self.bar_ly = QProgressBar(); self.bar_ly.setRange(0, 100); self.bar_ly.setValue(50)
        self.bar_lx.setStyleSheet("QProgressBar::chunk { background-color: #00ff66; }")
        self.bar_ly.setStyleSheet("QProgressBar::chunk { background-color: #00ff66; }")
        layout_l.addWidget(QLabel("Eixo X (Horizontal):")); layout_l.addWidget(self.bar_lx)
        layout_l.addWidget(QLabel("Eixo Y (Vertical):")); layout_l.addWidget(self.bar_ly)
        layout.addWidget(group_l)
        
        group_r = QGroupBox(" Analógico Direito (Hall Effect) ")
        group_r.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #444; border-radius: 6px; margin-top: 10px; padding: 10px; }")
        layout_r = QVBoxLayout(group_r)
        self.bar_rx = QProgressBar(); self.bar_rx.setRange(0, 100); self.bar_rx.setValue(50)
        self.bar_ry = QProgressBar(); self.bar_ry.setRange(0, 100); self.bar_ry.setValue(50)
        self.bar_rx.setStyleSheet("QProgressBar::chunk { background-color: #00ff66; }")
        self.bar_ry.setStyleSheet("QProgressBar::chunk { background-color: #00ff66; }")
        layout_r.addWidget(QLabel("Eixo X (Horizontal):")); layout_r.addWidget(self.bar_rx)
        layout_r.addWidget(QLabel("Eixo Y (Vertical):")); layout_r.addWidget(self.bar_ry)
        layout.addWidget(group_r)
        
        self.tabs.addTab(tab, "Diagnóstico")

    def setup_tab_iluminacao(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        info = QLabel("Configuração de Cores e Efeitos RGB\n\n(A aguardar engenharia reversa do protocolo USB HID)")
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("color: #aaaaaa; font-size: 14px;")
        layout.addWidget(info)
        self.tabs.addTab(tab, "Iluminação")

    def setup_tab_vibracao(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        info = QLabel("Controlo dos Motores de Vibração (Punhos e Gatilhos)\n\n(A aguardar implementação evdev/ff)")
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("color: #aaaaaa; font-size: 14px;")
        layout.addWidget(info)
        self.tabs.addTab(tab, "Vibração")

    def setup_tab_mapeamento(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        info = QLabel("Mapeamento de Botões Traseiros (M1 / M2) e Macros\n\n(Em desenvolvimento)")
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("color: #aaaaaa; font-size: 14px;")
        layout.addWidget(info)
        self.tabs.addTab(tab, "Mapeamento")

    def init_hardware(self):
        paths = ['/dev/input/js0', '/dev/input/js1', '/dev/input/js2']
        device_path = next((p for p in paths if os.path.exists(p)), None)
        if device_path:
            self.fd = open(device_path, 'rb')
            os.set_blocking(self.fd.fileno(), False)
        else:
            self.status_label.setText("Controle não detectado em /dev/input/js*")

    def poll_hardware(self):
        if not self.fd: return
        fn_format = 'IhBB'
        event_size = struct.calcsize(fn_format)
        gui_needs_update = False
        last_btn = None
        
        try:
            while True:
                event = self.fd.read(event_size)
                if not event or len(event) < event_size: break
                time_val, value, ev_type, number = struct.unpack(fn_format, event)
                actual_type = ev_type & ~0x80
                
                if actual_type == 1 and value == 1:
                    btn_key = f"btn_{number}"
                    last_btn = self.controller.mappings.get(btn_key, f"ID {number}")
                elif actual_type == 2 and number in self.last_pct:
                    dz = self.controller.DEADZONE_L_X if number==0 else (self.controller.DEADZONE_L_Y if number==1 else (self.controller.DEADZONE_R_X if number==3 else self.controller.DEADZONE_R_Y))
                    f = self.controller.apply_deadzone(value, dz)
                    pct = int(((f + 32767) / 65534) * 100)
                    if self.last_pct[number] != pct:
                        self.last_pct[number] = pct
                        gui_needs_update = True
        except BlockingIOError: pass
        except Exception: pass
            
        if last_btn:
            self.status_label.setText(f"Botão Pressionado: {last_btn}")
            self.status_label.setStyleSheet("color: #ffffff; background-color: #0055ff; padding: 15px; border-radius: 4px; font-weight: bold;")
            
        if gui_needs_update:
            self.bar_lx.setValue(self.last_pct[0])
            self.bar_ly.setValue(self.last_pct[1])
            self.bar_rx.setValue(self.last_pct[3])
            self.bar_ry.setValue(self.last_pct[4])

def main():
    app = QApplication(sys.argv)
    controller = GameSirCyclone2()
    window = MainWindow(controller)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
