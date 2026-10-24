#!/usr/bin/env python3
import os, json, struct, sys, glob, traceback, zlib, platform
import threading, queue, time

for p in glob.glob('/app/lib/python3.*/site-packages'):
    sys.path.append(p)

from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                               QWidget, QProgressBar, QPushButton, QSlider, 
                               QHBoxLayout, QTextEdit, QFormLayout, QComboBox, 
                               QCheckBox, QStackedWidget, QFrame, QGridLayout,
                               QColorDialog, QListWidget, QLineEdit)
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QColor, QPixmap, QClipboard

try:
    from evdev import InputDevice, ecodes, ff, list_devices
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False

# Herança mudada para threading.Thread nativo do Python! Nada de PySide6 aqui.
class HardwareMonitor(threading.Thread):
    def __init__(self, controller, q):
        super().__init__()
        self.controller = controller
        self.q = q
        self.running = True
        self.fd = None
        self.hid_fd = None
        self.last_pct = {0: 50, 1: 50, 2: 0, 3: 50, 4: 50, 5: 0}
        self.daemon = True

    def get_gamesir_nodes(self):
        import glob, os
        nodes = []
        for node in sorted(glob.glob('/dev/hidraw*')):
            uevent_path = f"/sys/class/hidraw/{os.path.basename(node)}/device/uevent"
            if os.path.exists(uevent_path):
                try:
                    with open(uevent_path, 'r') as f:
                        txt = f.read().lower()
                        if 'gamesir' in txt or '054c' in txt or 'chicken' in txt: nodes.append(node)
                except: pass
        return nodes

    def run(self):
        import struct, fcntl
        fn_format = 'IhBB'
        event_size = struct.calcsize(fn_format)
        
        while self.running:
            gui_needs_update = False
            
            if not self.fd:
                paths = ['/dev/input/js0', '/dev/input/js1', '/dev/input/js2']
                device_path = next((p for p in paths if os.path.exists(p)), None)
                if device_path:
                    try:
                        self.fd = open(device_path, 'rb')
                        flags = fcntl.fcntl(self.fd.fileno(), fcntl.F_GETFL)
                        fcntl.fcntl(self.fd.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)
                        self.q.put(('status', "🟢 Cyclone 2 (Ativo)", "#34d399"))
                    except Exception: pass
                else:
                    self.q.put(('status', "🔴 Desconectado", "#ef4444"))
            
            if not self.hid_fd:
                nodes = self.get_gamesir_nodes()
                for node in nodes:
                    try:
                        self.hid_fd = open(node, 'rb')
                        flags = fcntl.fcntl(self.hid_fd.fileno(), fcntl.F_GETFL)
                        fcntl.fcntl(self.hid_fd.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)
                        break
                    except Exception: pass

            if self.hid_fd:
                try:
                    hid_data = self.hid_fd.read(64)
                    if hid_data and len(hid_data) > 6:
                        m1_pressed = 1 if (hid_data[5] & 0x10) or (hid_data[6] & 0x01) else 0
                        m2_pressed = 1 if (hid_data[5] & 0x20) or (hid_data[6] & 0x02) else 0
                        self.q.put(('m_btn', 'm1', m1_pressed))
                        self.q.put(('m_btn', 'm2', m2_pressed))
                except OSError:
                    try: self.hid_fd.close()
                    except: pass
                    self.hid_fd = None
                except Exception: pass

            if self.fd:
                events_processed = 0
                while events_processed < 64:
                    try:
                        event = self.fd.read(event_size)
                        if not event or len(event) < event_size: break
                        events_processed += 1
                        time_val, value, ev_type, number = struct.unpack(fn_format, event)
                        
                        if ev_type & 0x80: continue
                        
                        if ev_type == 1:
                            if self.controller.mappings.get("swap_ab_xy", False):
                                if number == 0: number = 1
                                elif number == 1: number = 0
                                elif number == 2: number = 3
                                elif number == 3: number = 2
                            
                            self.q.put(('btn', int(number), int(value)))
                            
                        elif ev_type == 2:
                            if number in [0, 1, 3, 4]:
                                dz = self.controller.DEADZONE_L_X if number in [0, 1] else self.controller.DEADZONE_R_X
                                f = self.controller.apply_deadzone(value, dz)
                                pct = int(((f + 32767) / 65534) * 100)
                                if self.last_pct.get(number) != pct:
                                    self.last_pct[number] = pct; gui_needs_update = True
                            elif number in [2, 5]:
                                pct = int(((value + 32767) / 65534) * 100)
                                if self.controller.mappings.get("hair_triggers", False):
                                    if pct > 5:
                                        pct = 100
                                if self.last_pct.get(number) != pct:
                                    self.last_pct[number] = pct; gui_needs_update = True
                    except OSError:
                        try: self.fd.close()
                        except: pass
                        self.fd = None
                        self.q.put(('status', "🔴 Desconectado", "#ef4444"))
                        break
                    except Exception: 
                        break
            
            if gui_needs_update:
                pct_str = f"{self.last_pct[0]},{self.last_pct[1]},{self.last_pct[2]},{self.last_pct[3]},{self.last_pct[4]},{self.last_pct[5]}"
                self.q.put(('telemetry', pct_str))
                
            time.sleep(0.016)

    def stop(self):
        self.running = False

BUTTON_NAMES = {
    -1: "🚫 Nenhum / Desativado",
    0: "A", 1: "B", 2: "X", 3: "Y",
    4: "L1", 5: "R1", 6: "L2 (Digital)", 7: "R2 (Digital)",
    8: "Select", 9: "Start", 10: "Home",
    11: "L3", 12: "R3", 13: "Touch",
    14: "M1 Nativo", 15: "M2 Nativo"
}

class GameSirCyclone2:
    def __init__(self, profile_path="profile_default.json"):
        self.profile_path = profile_path
        self.profile_name = "Perfil 1"
        self.DEADZONE_L_X = 4000; self.DEADZONE_L_Y = 2000
        self.DEADZONE_R_X = 3000; self.DEADZONE_R_Y = 3000
        self.led_mode = "Fluxo"
        self.led_brightness = 100
        self.led_speed = 50
        self.led_r = 255; self.led_g = 0; self.led_b = 0
        self.vib_strong = 100; self.vib_weak = 100
        self.mappings = { "m1_button_id": 2, "m2_button_id": 1, "swap_ab_xy": False, "hair_triggers": False }
        self.load_profile()

    def load_profile(self):
        paths = [
            self.profile_path, f"/app/bin/{self.profile_path}",
            os.path.expanduser("~/.var/app/io.github.dioluis.gamesir_nexus/config/profile_default.json")
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, 'r') as f: data = json.load(f)
                    dz = data.get("deadzones", {})
                    self.DEADZONE_L_X = dz.get("left_analog_x", 4000)
                    self.DEADZONE_L_Y = dz.get("left_analog_y", 2000)
                    self.DEADZONE_R_X = dz.get("right_analog_x", 3000)
                    self.DEADZONE_R_Y = dz.get("right_analog_y", 3000)
                    led = data.get("lighting", {})
                    self.led_r = led.get("r", 255); self.led_g = led.get("g", 0); self.led_b = led.get("b", 0)
                    self.led_mode = led.get("mode", "Fluxo")
                    self.led_brightness = led.get("brightness", 100)
                    self.led_speed = led.get("speed", 50)
                    vib = data.get("vibration", {})
                    self.vib_strong = vib.get("strong_motor_pct", 100)
                    self.vib_weak = vib.get("weak_motor_pct", 100)
                    mp = data.get("mappings", {})
                    self.mappings["m1_button_id"] = mp.get("m1_button_id", 2)
                    self.mappings["m2_button_id"] = mp.get("m2_button_id", 1)
                    self.mappings["swap_ab_xy"] = mp.get("swap_ab_xy", False)
                    self.mappings["hair_triggers"] = mp.get("hair_triggers", False)
                    return
                except Exception: pass

    def save_profile(self):
        config_dir = os.path.expanduser("~/.var/app/io.github.dioluis.gamesir_nexus/config")
        os.makedirs(config_dir, exist_ok=True)
        target_path = os.path.join(config_dir, "profile_default.json")
        data = {
            "profile_name": self.profile_name,
            "deadzones": { "left_analog_x": self.DEADZONE_L_X, "left_analog_y": self.DEADZONE_L_Y, "right_analog_x": self.DEADZONE_R_X, "right_analog_y": self.DEADZONE_R_Y },
            "lighting": { "r": self.led_r, "g": self.led_g, "b": self.led_b, "mode": self.led_mode, "brightness": self.led_brightness, "speed": self.led_speed },
            "vibration": { "strong_motor_pct": self.vib_strong, "weak_motor_pct": self.vib_weak },
            "mappings": self.mappings
        }
        try:
            with open(target_path, 'w') as f: json.dump(data, f, indent=4)
            return True
        except Exception: return False

    def apply_deadzone(self, raw_value, deadzone):
        if abs(raw_value) < deadzone: return 0
        if raw_value > 0: return int(((raw_value - deadzone) / (32767 - deadzone)) * 32767)
        else: return int(((raw_value + deadzone) / (32767 - deadzone)) * -32767)

class TitleBar(QFrame):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setStyleSheet("background-color: #16161b; border-bottom: 1px solid #2a2a32; padding: 10px 20px; border-top-left-radius: 12px; border-top-right-radius: 12px;")
        self.setFixedHeight(60)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            window_handle = self.parent_window.windowHandle()
            if window_handle:
                window_handle.startSystemMove()

class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("GameSir Connect - Linux Edition")
        self.resize(1250, 800)
        self.learning_target = None
        
        self.setStyleSheet("""
            * { color: #f4f4f5; font-family: "Segoe UI", "Ubuntu", sans-serif; }
            #main_container { background-color: #0b0b0e; border-radius: 12px; border: 1px solid #3f3f46; }
            QListWidget { background-color: #16161b; border-right: 1px solid #2a2a32; padding-top: 15px; outline: none; border-bottom-left-radius: 12px; }
            QListWidget::item { padding: 14px 20px; color: #a1a1aa; border-radius: 8px; margin: 4px 12px; font-weight: bold; font-size: 14px; }
            QListWidget::item:hover { background-color: #2a2a32; color: #f4f4f5; }
            QListWidget::item:selected { background-color: #ed4e4e; color: #ffffff; }
            QFrame#card { background-color: #1c1c22; border-radius: 12px; border: 1px solid #2a2a32; }
            QLabel#card_title { color: #a1a1aa; font-size: 14px; font-weight: bold; }
            QSlider::groove:horizontal { background: #3f3f46; height: 6px; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #ed4e4e; border-radius: 3px; }
            QSlider::handle:horizontal { background: #ed4e4e; width: 16px; margin: -5px 0; border-radius: 8px; border: 2px solid #ed4e4e; }
            QSlider::handle:horizontal:hover { background: #ffffff; }
            QProgressBar { background-color: #27272a; border-radius: 4px; text-align: center; color: transparent; height: 8px; border: none; }
            QProgressBar::chunk { background-color: #ed4e4e; border-radius: 4px; }
            QPushButton { background-color: #2a2a32; color: #ffffff; border: 1px solid #3f3f46; border-radius: 6px; padding: 10px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background-color: #3f3f46; border: 1px solid #ed4e4e; }
            QPushButton:pressed { background-color: #ed4e4e; color: white; }
            QPushButton#btn_accent { background-color: #ed4e4e; border: none; }
            QPushButton#btn_accent:hover { background-color: #dc2626; }
            QPushButton#btn_led_mode { background-color: #1c1c22; border: 1px solid #3f3f46; border-radius: 6px; padding: 8px; }
            QPushButton#btn_led_mode:checked { background-color: #ed4e4e; color: white; border: 1px solid #ed4e4e; }
            QComboBox { background-color: #2a2a32; color: #ffffff; border: 1px solid #3f3f46; border-radius: 6px; padding: 8px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: #2a2a32; color: #ffffff; selection-background-color: #ed4e4e; border: 1px solid #3f3f46; outline: none; }
            QCheckBox { font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; background-color: #2a2a32; border: 1px solid #3f3f46; }
            QCheckBox::indicator:checked { background-color: #ed4e4e; border: 1px solid #3f3f46; }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout_base = QVBoxLayout(central_widget)
        main_layout_base.setContentsMargins(10, 10, 10, 10)
        
        self.main_container = QFrame()
        self.main_container.setObjectName("main_container")
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.header = TitleBar(self)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0,0,0,0)
        
        btn_close = QPushButton(); btn_close.setFixedSize(14, 14); btn_close.setStyleSheet("background-color: #ff5f56; border-radius: 7px; border: none;"); btn_close.clicked.connect(self.close)
        btn_min = QPushButton(); btn_min.setFixedSize(14, 14); btn_min.setStyleSheet("background-color: #ffbd2e; border-radius: 7px; border: none;"); btn_min.clicked.connect(self.showMinimized)
        btn_max = QPushButton(); btn_max.setFixedSize(14, 14); btn_max.setStyleSheet("background-color: #27c93f; border-radius: 7px; border: none;"); btn_max.clicked.connect(self.toggle_maximize)
        
        header_layout.addWidget(btn_close); header_layout.addWidget(btn_min); header_layout.addWidget(btn_max); header_layout.addSpacing(15)
        header_layout.addWidget(QLabel("🎮 GAMESIR CONNECT")); header_layout.addStretch()
        
        self.btn_perfil = QPushButton(self.controller.profile_name)
        self.btn_perfil.setStyleSheet("background-color: transparent; border: none; border-bottom: 3px solid #ed4e4e; border-radius: 0px; font-size: 14px; padding: 5px 20px; color: #ffffff;")
        header_layout.addWidget(self.btn_perfil); header_layout.addStretch()
        
        self.conn_status = QLabel("🔴 Desconectado"); self.conn_status.setStyleSheet("font-weight: bold; color: #ef4444;")
        header_layout.addWidget(self.conn_status)
        main_layout.addWidget(self.header)

        content_layout = QHBoxLayout()
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.addItems(["🕹️ Dashboard", "ℹ️ Sobre o Projeto"])
        content_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        
        self.dashboard_wrapper = QWidget()
        dash_layout = QVBoxLayout(self.dashboard_wrapper)
        dash_layout.setContentsMargins(20, 20, 20, 20)

        center_img_layout = QHBoxLayout()
        img_lbl = QLabel("CYCLONE 2")
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setStyleSheet("font-size: 20px; font-weight: 900; color: #ffffff; padding: 10px;")
        center_img_layout.addWidget(img_lbl)
        dash_layout.addLayout(center_img_layout)

        grid = QGridLayout()
        grid.setSpacing(15)

        col1_layout = QVBoxLayout()
        card_luzes, lay_luzes = self.create_card("💡", "Luzes e Predefinições")
        led_grid = QGridLayout()
        modos = ["Fluxo", "Arco-íris", "Pulso", "Equilíbrio", "Alarme", "Desativado"]
        self.led_btns = []
        r = c = 0
        for m in modos:
            btn = QPushButton(m)
            btn.setObjectName("btn_led_mode")
            btn.setCheckable(True)
            if m == self.controller.led_mode: btn.setChecked(True)
            btn.clicked.connect(lambda checked, mode=m: self.set_led_mode(mode))
            self.led_btns.append(btn)
            led_grid.addWidget(btn, r, c)
            c += 1
            if c > 1: c = 0; r += 1
        lay_luzes.addLayout(led_grid)
        lay_luzes.addSpacing(10)
        lay_luzes.addWidget(QLabel("Brilho"))
        self.slider_brilho = QSlider(Qt.Horizontal); self.slider_brilho.setRange(0, 100); self.slider_brilho.setValue(self.controller.led_brightness)
        lay_luzes.addWidget(self.slider_brilho)
        self.slider_brilho.valueChanged.connect(self.update_led_settings)
        lay_luzes.addWidget(QLabel("Velocidade"))
        self.slider_vel = QSlider(Qt.Horizontal); self.slider_vel.setRange(0, 100); self.slider_vel.setValue(self.controller.led_speed)
        lay_luzes.addWidget(self.slider_vel)
        self.slider_vel.valueChanged.connect(self.update_led_settings)
        btn_cor = QPushButton("Aplicar Cor Sólida no Comando"); btn_cor.clicked.connect(self.open_color_picker)
        lay_luzes.addWidget(btn_cor)
        col1_layout.addWidget(card_luzes)
        
        card_vib, lay_vib = self.create_card("📳", "Motores de Vibração")
        lay_vib.addWidget(QLabel("Motor Pesado (Esq)")); self.slider_strong = QSlider(Qt.Horizontal); self.slider_strong.setRange(0, 100); self.slider_strong.setValue(self.controller.vib_strong); lay_vib.addWidget(self.slider_strong)
        lay_vib.addWidget(QLabel("Motor Leve (Dir)")); self.slider_weak = QSlider(Qt.Horizontal); self.slider_weak.setRange(0, 100); self.slider_weak.setValue(self.controller.vib_weak); lay_vib.addWidget(self.slider_weak)
        btn_test = QPushButton("Testar Vibração"); btn_test.setObjectName("btn_accent"); btn_test.clicked.connect(self.trigger_rumble_test)
        lay_vib.addWidget(btn_test)
        col1_layout.addWidget(card_vib)

        card_sticks, lay_sticks = self.create_card("🕹️", "Sticks e Botões (Em Tempo Real)")
        lay_sticks.addWidget(QLabel("Analógico Esquerdo (L3)"))
        self.bar_lx = QProgressBar(); self.bar_lx.setRange(0, 100); self.bar_lx.setValue(50)
        self.bar_ly = QProgressBar(); self.bar_ly.setRange(0, 100); self.bar_ly.setValue(50)
        lay_sticks.addWidget(self.bar_lx); lay_sticks.addWidget(self.bar_ly)
        lay_sticks.addSpacing(15)
        lay_sticks.addWidget(QLabel("Analógico Direito (R3)"))
        self.bar_rx = QProgressBar(); self.bar_rx.setRange(0, 100); self.bar_rx.setValue(50)
        self.bar_ry = QProgressBar(); self.bar_ry.setRange(0, 100); self.bar_ry.setValue(50)
        lay_sticks.addWidget(self.bar_rx); lay_sticks.addWidget(self.bar_ry)
        lay_sticks.addSpacing(25)
        
        self.ui_buttons = {}
        row_bumpers = QHBoxLayout()
        for b_id, txt in [(4, "L1"), (5, "R1")]:
            lbl = QLabel(txt)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("background-color: #2a2a32; color: #a1a1aa; border-radius: 6px; padding: 8px; font-weight: bold;")
            self.ui_buttons[b_id] = lbl
            row_bumpers.addWidget(lbl)
        lay_sticks.addLayout(row_bumpers)
        lay_sticks.addSpacing(10)
        
        grid_face = QGridLayout()
        lbl_y = QLabel("Y"); lbl_y.setAlignment(Qt.AlignCenter); lbl_y.setStyleSheet("background-color: #2a2a32; color: #a1a1aa; border-radius: 18px; min-width: 36px; max-width: 36px; min-height: 36px; max-height: 36px; font-weight: bold;")
        lbl_x = QLabel("X"); lbl_x.setAlignment(Qt.AlignCenter); lbl_x.setStyleSheet("background-color: #2a2a32; color: #a1a1aa; border-radius: 18px; min-width: 36px; max-width: 36px; min-height: 36px; max-height: 36px; font-weight: bold;")
        lbl_b = QLabel("B"); lbl_b.setAlignment(Qt.AlignCenter); lbl_b.setStyleSheet("background-color: #2a2a32; color: #a1a1aa; border-radius: 18px; min-width: 36px; max-width: 36px; min-height: 36px; max-height: 36px; font-weight: bold;")
        lbl_a = QLabel("A"); lbl_a.setAlignment(Qt.AlignCenter); lbl_a.setStyleSheet("background-color: #2a2a32; color: #a1a1aa; border-radius: 18px; min-width: 36px; max-width: 36px; min-height: 36px; max-height: 36px; font-weight: bold;")
        
        self.ui_buttons[3] = lbl_y; self.ui_buttons[2] = lbl_x; self.ui_buttons[1] = lbl_b; self.ui_buttons[0] = lbl_a
        grid_face.addWidget(lbl_y, 0, 1); grid_face.addWidget(lbl_x, 1, 0); grid_face.addWidget(lbl_b, 1, 2); grid_face.addWidget(lbl_a, 2, 1); grid_face.setAlignment(Qt.AlignCenter)
        lay_sticks.addLayout(grid_face)
        lay_sticks.addStretch()

        col3_layout = QVBoxLayout()
        card_gatilhos, lay_gatilhos = self.create_card("📐", "Gatilhos")
        self.bar_l2 = QProgressBar(); self.bar_l2.setRange(0, 100); self.bar_l2.setValue(0)
        self.bar_r2 = QProgressBar(); self.bar_r2.setRange(0, 100); self.bar_r2.setValue(0)
        lay_gatilhos.addWidget(QLabel("LT (Esquerdo)")); lay_gatilhos.addWidget(self.bar_l2)
        lay_gatilhos.addWidget(QLabel("RT (Direito)")); lay_gatilhos.addWidget(self.bar_r2)
        col3_layout.addWidget(card_gatilhos)
        
        card_map, lay_map = self.create_card("⚙️", "Atalhos (Software)")
        lbl_m1 = QLabel("M1 (Esq)"); self.led_m1 = QLabel("⚫")
        btn_learn_m1 = QPushButton("🎯"); btn_learn_m1.setToolTip("Capturar Botão"); btn_learn_m1.clicked.connect(lambda: self.start_learning('m1'))
        row_m1 = QHBoxLayout(); row_m1.addWidget(lbl_m1); row_m1.addWidget(self.led_m1); row_m1.addStretch(); row_m1.addWidget(btn_learn_m1)
        lay_map.addLayout(row_m1)
        self.combo_m1 = QComboBox()
        for bid, bname in BUTTON_NAMES.items(): self.combo_m1.addItem(bname, bid)
        idx_m1 = self.combo_m1.findData(self.controller.mappings.get("m1_button_id", 2))
        if idx_m1 >= 0: self.combo_m1.setCurrentIndex(idx_m1)
        lay_map.addWidget(self.combo_m1)
        lay_map.addSpacing(10)
        lbl_m1.hide(); self.led_m1.hide(); btn_learn_m1.hide(); self.combo_m1.hide()

        lbl_m2 = QLabel("M2 (Dir)"); self.led_m2 = QLabel("⚫")
        btn_learn_m2 = QPushButton("🎯"); btn_learn_m2.setToolTip("Capturar Botão"); btn_learn_m2.clicked.connect(lambda: self.start_learning('m2'))
        row_m2 = QHBoxLayout(); row_m2.addWidget(lbl_m2); row_m2.addWidget(self.led_m2); row_m2.addStretch(); row_m2.addWidget(btn_learn_m2)
        lay_map.addLayout(row_m2)
        self.combo_m2 = QComboBox()
        for bid, bname in BUTTON_NAMES.items(): self.combo_m2.addItem(bname, bid)
        idx_m2 = self.combo_m2.findData(self.controller.mappings.get("m2_button_id", 1))
        if idx_m2 >= 0: self.combo_m2.setCurrentIndex(idx_m2)
        lay_map.addWidget(self.combo_m2)
        lbl_m2.hide(); self.led_m2.hide(); btn_learn_m2.hide(); self.combo_m2.hide()
        
        self.chk_hair = QCheckBox("Modo Gatilho Ultrasensível"); self.chk_hair.setChecked(self.controller.mappings.get("hair_triggers", False))
        self.chk_swap = QCheckBox("Alternar para layout Switch"); self.chk_swap.setChecked(self.controller.mappings.get("swap_ab_xy", False))
        self.chk_hair.stateChanged.connect(self.update_software_mappings)
        self.chk_swap.stateChanged.connect(self.update_software_mappings)
        lay_map.addSpacing(10)
        lay_map.addWidget(self.chk_hair); lay_map.addWidget(self.chk_swap)
        col3_layout.addWidget(card_map)

        grid.addLayout(col1_layout, 0, 0); grid.addWidget(card_sticks, 0, 1); grid.addLayout(col3_layout, 0, 2)
        grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1); grid.setColumnStretch(2, 1)
        dash_layout.addLayout(grid)

        bottom_bar = QHBoxLayout()
        self.log_lbl = QLabel("Aguardando telemetria...")
        self.log_lbl.setStyleSheet("color: #a1a1aa; font-family: monospace;")
        btn_save = QPushButton("💾 Gravar no Comando (EEPROM)")
        btn_save.setObjectName("btn_accent")
        btn_save.setFixedWidth(300)
        btn_save.clicked.connect(self.save_all)
        btn_save.hide() 
        bottom_bar.addWidget(self.log_lbl); bottom_bar.addStretch(); bottom_bar.addWidget(btn_save)
        dash_layout.addLayout(bottom_bar)
        
        self.stack.addWidget(self.dashboard_wrapper)
        
        self.about_wrapper = QWidget()
        about_layout = QVBoxLayout(self.about_wrapper)
        about_layout.setAlignment(Qt.AlignCenter)
        dev_title = QLabel("GameSir Connect - Linux Edition"); dev_title.setStyleSheet("font-size: 28px; font-weight: bold; color: #ffffff;"); dev_title.setAlignment(Qt.AlignCenter)
        dev_info = QLabel("Desenvolvido por: Diotec Software (Dionísio Luís)\nVersão: 0.9.6 Beta\n\nSoftware de Engenharia Reversa para Comandos GameSir no Linux."); dev_info.setAlignment(Qt.AlignCenter); dev_info.setStyleSheet("font-size: 16px; color: #a1a1aa; margin-top: 10px; margin-bottom: 20px;")
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        diotec_path = os.path.join(base_dir, "logo.jpeg") if os.path.exists(os.path.join(base_dir, "logo.jpeg")) else "/app/bin/logo.jpeg"
        diotec_lbl = QLabel()
        if os.path.exists(diotec_path):
            pixmap = QPixmap(diotec_path).scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation); diotec_lbl.setPixmap(pixmap)
        diotec_lbl.setAlignment(Qt.AlignCenter)
        
        compat_info = QLabel("Compatibilidade Atual: GameSir Cyclone 2.\nO seu modelo funcionou ou encontrou algum erro?\nAjude-nos a adicionar suporte para novos comandos!"); compat_info.setAlignment(Qt.AlignCenter); compat_info.setStyleSheet("font-size: 14px; color: #34d399; margin-bottom: 10px; margin-top: 20px;")
        
        btn_diag = QPushButton("🐞 Copiar Relatório de Diagnóstico para Email"); btn_diag.setStyleSheet("background-color: #3f3f46; color: white; padding: 10px; border-radius: 6px; font-weight: bold;"); btn_diag.setFixedWidth(450); btn_diag.clicked.connect(self.copy_diagnostics)
        
        donate_lbl = QLabel("Apoie o desenvolvimento contínuo (PIX):"); donate_lbl.setAlignment(Qt.AlignCenter); donate_lbl.setStyleSheet("font-weight: bold; color: #ffffff; margin-top: 15px;")
        btn_donate = QPushButton("📋 Copiar Chave PIX (a6e35576-02ec-4f43-a243-3e65ee8e9c3d)"); btn_donate.setObjectName("btn_accent"); btn_donate.setFixedWidth(450); btn_donate.clicked.connect(self.copy_pix)
        
        about_layout.addWidget(dev_title); about_layout.addWidget(dev_info); about_layout.addWidget(diotec_lbl); about_layout.addWidget(compat_info); about_layout.addWidget(btn_diag, alignment=Qt.AlignCenter); about_layout.addWidget(donate_lbl); about_layout.addWidget(btn_donate, alignment=Qt.AlignCenter)
        self.stack.addWidget(self.about_wrapper)
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        content_layout.addWidget(self.stack)
        main_layout.addLayout(content_layout)
        main_layout_base.addWidget(self.main_container)

        self.last_pct = {0: 50, 1: 50, 2: 0, 3: 50, 4: 50, 5: 0}
        self.fd = None; self.hid_fd = None; self.evdev_device = None; self.active_effect_id = None
        self.init_hardware()
        
        # --- A GRANDE MUDANÇA: FILA DE DADOS ---
        self.q = queue.Queue()
        self.hw_thread = HardwareMonitor(self.controller, self.q)
        self.hw_thread.start()
        
        # O Qt interage com a fila no ambiente seguro da Main Thread
        self.queue_timer = QTimer(self)
        self.queue_timer.timeout.connect(self.process_queue)
        self.queue_timer.start(16)

    def process_queue(self):
        while not self.q.empty():
            try:
                msg = self.q.get_nowait()
                if msg[0] == 'status': self.update_status(msg[1], msg[2])
                elif msg[0] == 'telemetry': self.update_telemetry(msg[1])
                elif msg[0] == 'm_btn': self.update_m_btn(msg[1], msg[2])
                elif msg[0] == 'btn': self.handle_button(msg[1], msg[2])
                elif msg[0] == 'log': self.add_log(msg[1], msg[2])
            except Exception:
                pass

    def copy_diagnostics(self):
        diag = "--- Relatorio de Diagnostico GameSir Connect ---\n"
        diag += f"Versao: 0.9.6 Beta\nSistema: {platform.system()} {platform.release()}\n\n"
        diag += "== DISPOSITIVOS HIDRAW (USB/Dongle) ==\n"
        for node in sorted(glob.glob('/sys/class/hidraw/*')):
            try:
                with open(os.path.join(node, 'device/uevent'), 'r') as f:
                    conteudo = f.read().strip()
                    if 'HID_NAME' in conteudo:
                        diag += f"[{os.path.basename(node)}]\n{conteudo}\n\n"
            except: pass
            
        diag += "== DISPOSITIVOS JOYSTICK (Telemetria) ==\n"
        for node in sorted(glob.glob('/dev/input/js*')):
            diag += f"Encontrado: {node}\n"
            
        diag += "\n------------------------------------------------\n"
        diag += "Por favor, envie este relatorio para: diotec.soft@gmail.com\n"
        diag += "Indique no email: O seu comando funcionou? Qual e o modelo exato?"
        
        QApplication.clipboard().setText(diag)
        self.add_log("Relatório copiado! Cole no seu email e envie-nos o feedback.", 1)

    def update_software_mappings(self):
        self.controller.mappings["hair_triggers"] = self.chk_hair.isChecked()
        self.controller.mappings["swap_ab_xy"] = self.chk_swap.isChecked()
        self.controller.save_profile() 
        status_msg = "Mapeamento atualizado: "
        status_msg += "Gatilho Ultra ON | " if self.chk_hair.isChecked() else "Gatilho Normal | "
        status_msg += "Layout Switch" if self.chk_swap.isChecked() else "Layout Xbox"
        self.add_log(status_msg, 1)

    def toggle_maximize(self):
        if self.isMaximized(): self.showNormal()
        else: self.showMaximized()

    def set_led_mode(self, mode):
        for btn in self.led_btns: btn.setChecked(btn.text() == mode)
        self.controller.led_mode = mode
        self.add_log(f"Modo de LED selecionado: {mode} (Sólido requer escolha de cor)", 1)

    def update_led_settings(self):
        self.controller.led_brightness = self.slider_brilho.value()
        self.controller.led_speed = self.slider_vel.value()
        self.send_controller_led(self.controller.led_r, self.controller.led_g, self.controller.led_b)
        self.add_log(f"Brilho ajustado para {self.controller.led_brightness}%", 1)

    def open_color_picker(self):
        c = QColorDialog.getColor(QColor(self.controller.led_r, self.controller.led_g, self.controller.led_b), self, "Cor dos LEDs")
        if c.isValid(): self.send_controller_led(c.red(), c.green(), c.blue())

    def create_card(self, icon, title):
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        header = QHBoxLayout()
        header.addWidget(QLabel(icon)); header.addWidget(QLabel(title, objectName="card_title")); header.addStretch()
        layout.addLayout(header)
        div = QFrame(); div.setFixedHeight(1); div.setStyleSheet("background-color: #2a2a32;")
        layout.addWidget(div)
        return frame, layout

    def copy_pix(self):
        QApplication.clipboard().setText("a6e35576-02ec-4f43-a243-3e65ee8e9c3d")
        self.add_log("Chave PIX copiada para a área de transferência! Obrigado pelo apoio.", 1)

    def add_log(self, message, is_success=0):
        if hasattr(self, 'log_lbl'):
            color = "#34d399" if is_success == 1 else "#a1a1aa"
            self.log_lbl.setStyleSheet(f"color: {color}; font-family: monospace; font-weight: bold;")
            self.log_lbl.setText(f"> {message}")

    def start_learning(self, target):
        self.learning_target = target
        self.log_lbl.setStyleSheet("color: #ffbd2e; font-family: monospace; font-weight: bold;")
        self.log_lbl.setText(f"> AGUARDANDO: Pressione o botão para associar à pá {target.upper()}...")

    def get_gamesir_nodes(self):
        nodes = []
        for node in sorted(glob.glob('/dev/hidraw*')):
            base = os.path.basename(node)
            uevent_path = f"/sys/class/hidraw/{base}/device/uevent"
            if os.path.exists(uevent_path):
                try:
                    with open(uevent_path, 'r') as f:
                        txt = f.read().lower()
                        if 'gamesir' in txt or '054c' in txt or 'chicken' in txt: nodes.append(node)
                except: pass
        return nodes if nodes else (['/dev/hidraw1'] if os.path.exists('/dev/hidraw1') else [])

    def send_hardware_mapping(self, m1_id, m2_id):
        targets = self.get_gamesir_nodes()
        if not targets: return False
        success = False
        for target in targets:
            try:
                payload = bytearray([0x03, 0x18, 0x01, m1_id & 0xFF, m2_id & 0xFF]) + bytearray([0x00] * 63)
                crc = zlib.crc32(payload) & 0xFFFFFFFF
                report = payload + struct.pack('<I', crc)
                with open(target, 'wb') as f:
                    f.write(report)
                    f.flush()
                success = True
            except: pass
        return success

    def save_all(self):
        self.controller.vib_strong = self.slider_strong.value()
        self.controller.vib_weak = self.slider_weak.value()
        self.controller.led_brightness = self.slider_brilho.value()
        self.controller.led_speed = self.slider_vel.value()
        self.controller.mappings["m1_button_id"] = self.combo_m1.currentData()
        self.controller.mappings["m2_button_id"] = self.combo_m2.currentData()
        self.controller.mappings["hair_triggers"] = self.chk_hair.isChecked()
        self.controller.mappings["swap_ab_xy"] = self.chk_swap.isChecked()
        
        json_ok = self.controller.save_profile()
        hw_ok = self.send_hardware_mapping(self.combo_m1.currentData(), self.combo_m2.currentData())
        
        if json_ok and hw_ok:
            self.add_log("Perfil gravado com sucesso no JSON e na EEPROM do Hardware!", 1)
        elif json_ok:
            self.add_log("Perfil gravado (JSON OK, mas sem resposta de Hardware EEPROM).", 1)
        else:
            self.add_log("Erro ao gravar perfil.", 0)

    def send_controller_led(self, r, g, b, weak=0, strong=0, update_rumble=False):
        self.controller.led_r = r; self.controller.led_g = g; self.controller.led_b = b
        pct = self.slider_brilho.value() / 100.0
        r_dim = int(r * pct); g_dim = int(g * pct); b_dim = int(b * pct)
        targets = self.get_gamesir_nodes()
        if not targets: return
        report = bytearray(64)
        report[0] = 0x05; report[1] = 0x03 if update_rumble else 0x02; report[2] = 0x04
        report[4] = weak; report[5] = strong; report[6] = r_dim; report[7] = g_dim; report[8] = b_dim
        for target in targets:
            try:
                with open(target, 'wb') as f: f.write(report); f.flush()
            except: pass

    def trigger_rumble_test(self):
        sv = int(65535 * (self.slider_strong.value() / 100.0))
        wv = int(65535 * (self.slider_weak.value() / 100.0))
        if EVDEV_AVAILABLE and self.evdev_device:
            try:
                rumble = ff.Rumble(strong_magnitude=sv, weak_magnitude=wv)
                eff = ff.Effect(ecodes.FF_RUMBLE, -1, 0, ff.Trigger(0, 0), ff.Replay(1500, 0), ff.EffectType(ff_rumble_effect=rumble))
                if self.active_effect_id is not None:
                    try: self.evdev_device.erase_effect(self.active_effect_id)
                    except: pass
                self.active_effect_id = self.evdev_device.upload_effect(eff)
                self.evdev_device.write(ecodes.EV_FF, self.active_effect_id, 1)
            except: pass
        self.send_controller_led(self.controller.led_r, self.controller.led_g, self.controller.led_b, weak=int(255*(self.slider_weak.value()/100)), strong=int(255*(self.slider_strong.value()/100)), update_rumble=True)
        QTimer.singleShot(1500, lambda: self.send_controller_led(self.controller.led_r, self.controller.led_g, self.controller.led_b, weak=0, strong=0, update_rumble=True))
        self.add_log("Teste de vibração acionado.", 1)

    def init_hardware(self):
        pass

    def update_status(self, text, color):
        self.conn_status.setText(text)
        self.conn_status.setStyleSheet(f"font-weight: bold; color: {color};")

    def update_telemetry(self, data_str):
        try:
            parts = data_str.split(',')
            self.bar_lx.setValue(int(parts[0])); self.bar_ly.setValue(int(parts[1]))
            self.bar_l2.setValue(int(parts[2]))
            self.bar_rx.setValue(int(parts[3])); self.bar_ry.setValue(int(parts[4]))
            self.bar_r2.setValue(int(parts[5]))
        except: pass

    def update_m_btn(self, btn, state):
        led = self.led_m1 if btn == 'm1' else self.led_m2
        if state == 1: led.setText("🟢")
        elif state == 0 and led.text() == "🟢": led.setText("⚫")

    def closeEvent(self, event):
        if hasattr(self, 'hw_thread'):
            self.hw_thread.stop()
        event.accept()

    def handle_button(self, number, value):
        if hasattr(self, 'ui_buttons') and number in self.ui_buttons:
            lbl = self.ui_buttons[number]
            if number in [0, 1, 2, 3]: 
                bg = "#ed4e4e" if value == 1 else "#2a2a32"
                fg = "#ffffff" if value == 1 else "#a1a1aa"
                lbl.setStyleSheet(f"background-color: {bg}; color: {fg}; border-radius: 18px; min-width: 36px; max-width: 36px; min-height: 36px; max-height: 36px; font-weight: bold;")
            else: 
                bg = "#ed4e4e" if value == 1 else "#2a2a32"
                fg = "#ffffff" if value == 1 else "#a1a1aa"
                lbl.setStyleSheet(f"background-color: {bg}; color: {fg}; border-radius: 6px; padding: 8px; font-weight: bold;")
                
        if value == 1: 
            bname = BUTTON_NAMES.get(number, f"B{number}")
            if getattr(self, 'learning_target', None):
                if number not in BUTTON_NAMES:
                    BUTTON_NAMES[number] = f"B{number}"
                    self.combo_m1.addItem(bname, number)
                    self.combo_m2.addItem(bname, number)
                
                if self.learning_target == 'm1':
                    idx = self.combo_m1.findData(number)
                    if idx >= 0: self.combo_m1.setCurrentIndex(idx)
                elif self.learning_target == 'm2':
                    idx = self.combo_m2.findData(number)
                    if idx >= 0: self.combo_m2.setCurrentIndex(idx)
                
                self.add_log(f"✅ Sucesso: Botão {bname} atribuído à pá {self.learning_target.upper()}!", 1)
                self.learning_target = None

def main():
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    window = MainWindow(GameSirCyclone2())
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
