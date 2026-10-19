#!/usr/bin/env python3
import os, json, struct, sys
sys.path.append('/app/lib/python3.11/site-packages')
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QProgressBar, QGroupBox
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
        self.setWindowTitle("GameSir Cyclone 2 - Painel Linux (Qt)")
        self.resize(500, 520)
        self.setStyleSheet("QMainWindow { background-color: #1e1e1e; }")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        title = QLabel("GAMESIR NEXUS LINUX")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.profile_label = QLabel(f"Perfil Ativo: {self.controller.profile_name}")
        self.profile_label.setStyleSheet("color: #00ff66;")
        self.profile_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.profile_label)
        
        self.status_label = QLabel("Aguardando input do controle...")
        self.status_label.setStyleSheet("color: #aaaaaa; background-color: #2d2d2d; padding: 15px; border-radius: 4px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        group_l = QGroupBox(" Efeito Hall - Analógico Esquerdo ")
        group_l.setStyleSheet("QGroupBox { font-weight: bold; color: #ffffff; border: 1px solid #444444; border-radius: 6px; margin-top: 10px; padding: 10px; }")
        layout_l = QVBoxLayout(group_l)
        self.bar_lx = QProgressBar(group_l)
        self.bar_lx.setRange(0, 100); self.bar_lx.setValue(50)
        self.bar_lx.setStyleSheet("QProgressBar::chunk { background-color: #00ff66; }")
        layout_l.addWidget(self.bar_lx)
        self.bar_ly = QProgressBar(group_l)
        self.bar_ly.setRange(0, 100); self.bar_ly.setValue(50)
        self.bar_ly.setStyleSheet("QProgressBar::chunk { background-color: #00ff66; }")
        layout_l.addWidget(self.bar_ly)
        layout.addWidget(group_l)
        
        group_r = QGroupBox(" Efeito Hall - Analógico Direito ")
        group_r.setStyleSheet("QGroupBox { font-weight: bold; color: #ffffff; border: 1px solid #444444; border-radius: 6px; margin-top: 10px; padding: 10px; }")
        layout_r = QVBoxLayout(group_r)
        self.bar_rx = QProgressBar(group_r)
        self.bar_rx.setRange(0, 100); self.bar_rx.setValue(50)
        self.bar_rx.setStyleSheet("QProgressBar::chunk { background-color: #00ff66; }")
        layout_r.addWidget(self.bar_rx)
        self.bar_ry = QProgressBar(group_r)
        self.bar_ry.setRange(0, 100); self.bar_ry.setValue(50)
        self.bar_ry.setStyleSheet("QProgressBar::chunk { background-color: #00ff66; }")
        layout_r.addWidget(self.bar_ry)
        layout.addWidget(group_r)

        self.last_pct = {0: 50, 1: 50, 3: 50, 4: 50}
        self.fd = None
        self.init_hardware()

        # O Coração Assíncrono Seguro: Loop a ~60 FPS (16ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_hardware)
        self.timer.start(16)

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
            # Esvazia a fila de eventos do Linux o mais rápido possível
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
                        
        except BlockingIOError:
            pass # Lemos todos os eventos aguardando no hardware
        except Exception:
            pass
            
        # Atualiza a interface UMA ÚNICA VEZ por frame, eliminando sobrecarga no PySide6
        if last_btn:
            self.status_label.setText(f"Botão Pressionado: {last_btn}")
            self.status_label.setStyleSheet("color: #ffffff; background-color: #0055ff; padding: 15px;")
            
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
