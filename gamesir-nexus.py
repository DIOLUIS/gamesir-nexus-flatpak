#!/usr/bin/env python3
import os, json, struct, sys, glob, traceback, zlib

# Adiciona dinamicamente o caminho das bibliotecas instaladas pelo Flatpak
for p in glob.glob('/app/lib/python3.*/site-packages'):
    sys.path.append(p)

from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                               QWidget, QProgressBar, QPushButton, QSlider, 
                               QHBoxLayout, QTextEdit, QFormLayout, QComboBox, 
                               QCheckBox, QStackedWidget, QFrame, QGridLayout,
                               QColorDialog, QListWidget, QLineEdit)
from PySide6.QtCore import Qt, QTimer, QPoint, QThread, Signal
from PySide6.QtGui import QColor, QPixmap, QClipboard

try:
    from evdev import InputDevice, ecodes, ff, list_devices
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False

class HardwareMonitor(QThread):
    log_signal = Signal(str, bool)
    status_signal = Signal(str, str)
    telemetry_signal = Signal(object)
    m_btn_signal = Signal(str, bool)
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.running = True
        self.fd = None
        self.hid_fd = None
        self.last_pct = {0: 50, 1: 50, 2: 0, 3: 50, 4: 50, 5: 0}

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
        import os, struct
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
                        os.set_blocking(self.fd.fileno(), False)
                        self.status_signal.emit("🟢 Cyclone 2 (Ativo)", "#34d399")
                        self.log_signal.emit("Comando reconhecido e sincronizado.", True)
                    except Exception: pass
                else:
                    self.status_signal.emit("🔴 Desconectado", "#ef4444")
            
            if not self.hid_fd:
                nodes = self.get_gamesir_nodes()
                for node in nodes:
                    try:
                        self.hid_fd = open(node, 'rb')
                        os.set_blocking(self.hid_fd.fileno(), False)
                        break
                    except Exception: pass

            if self.hid_fd:
                try:
                    hid_data = self.hid_fd.read(64)
                    if hid_data and len(hid_data) > 6:
                        m1_pressed = bool(hid_data[5] & 0x10) or bool(hid_data[6] & 0x01)
                        m2_pressed = bool(hid_data[5] & 0x20) or bool(hid_data[6] & 0x02)
                        self.m_btn_signal.emit('m1', m1_pressed)
                        self.m_btn_signal.emit('m2', m2_pressed)
                except: pass

            if self.fd:
                events_processed = 0
                while events_processed < 64:
                    try:
                        event = self.fd.read(event_size)
                        if not event or len(event) < event_size: break
                        events_processed += 1
                        time_val, value, ev_type, number = struct.unpack(fn_format, event)
                        
                        if ev_type & 0x80: continue
                        if ev_type == 2:
                            if number in [0, 1, 3, 4]:
                                dz = self.controller.DEADZONE_L_X if number in [0, 1] else self.controller.DEADZONE_R_X
                                f = self.controller.apply_deadzone(value, dz)
                                pct = int(((f + 32767) / 65534) * 100)
                                if self.last_pct.get(number) != pct:
                                    self.last_pct[number] = pct; gui_needs_update = True
                            elif number in [2, 5]:
                                pct = int(((value + 32767) / 65534) * 100)
                                if self.last_pct.get(number) != pct:
                                    self.last_pct[number] = pct; gui_needs_update = True
                    except: break
            
            if gui_needs_update:
                self.telemetry_signal.emit(self.last_pct)
                
            self.msleep(16)

    def stop(self):
        self.running = False
        self.wait()

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

# --- CLASSE DA BARRA DE TÍTULO NATIVA (COMPATÍVEL COM WAYLAND/X11) ---
class TitleBar(QFrame):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.setStyleSheet("background-color: #16161b; border-bottom: 1px solid #2a2a32; padding: 10px 20px; border-top-left-radius: 12px; border-top-right-radius: 12px;")
        self.setFixedHeight(60)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Em vez de calcular posições, pedimos ao Sistema Operativo para mover a janela
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
        
        # O cabeçalho usa a classe nativa agora
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
        
        # --- DASHBOARD ---
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

        card_sticks, lay_sticks = self.create_card("🕹️", "Sticks (Analógicos)")
        lay_sticks.addWidget(QLabel("Analógico Esquerdo (L3)"))
        self.bar_lx = QProgressBar(); self.bar_lx.setRange(0, 100); self.bar_lx.setValue(50)
        self.bar_ly = QProgressBar(); self.bar_ly.setRange(0, 100); self.bar_ly.setValue(50)
        lay_sticks.addWidget(self.bar_lx); lay_sticks.addWidget(self.bar_ly)
        lay_sticks.addSpacing(20)
        lay_sticks.addWidget(QLabel("Analógico Direito (R3)"))
        self.bar_rx = QProgressBar(); self.bar_rx.setRange(0, 100); self.bar_rx.setValue(50)
        self.bar_ry = QProgressBar(); self.bar_ry.setRange(0, 100); self.bar_ry.setValue(50)
        lay_sticks.addWidget(self.bar_rx); lay_sticks.addWidget(self.bar_ry)
        lay_sticks.addStretch()
        
        col3_layout = QVBoxLayout()
        card_gatilhos, lay_gatilhos = self.create_card("📐", "Gatilhos")
        self.bar_l2 = QProgressBar(); self.bar_l2.setRange(0, 100); self.bar_l2.setValue(0)
        self.bar_r2 = QProgressBar(); self.bar_r2.setRange(0, 100); self.bar_r2.setValue(0)
        lay_gatilhos.addWidget(QLabel("LT (Esquerdo)")); lay_gatilhos.addWidget(self.bar_l2)
        lay_gatilhos.addWidget(QLabel("RT (Direito)")); lay_gatilhos.addWidget(self.bar_r2)
        col3_layout.addWidget(card_gatilhos)
        
        card_map, lay_map = self.create_card("⚙️", "Botões Traseiros e Atalhos")
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

        lbl_m2 = QLabel("M2 (Dir)"); self.led_m2 = QLabel("⚫")
        btn_learn_m2 = QPushButton("🎯"); btn_learn_m2.setToolTip("Capturar Botão"); btn_learn_m2.clicked.connect(lambda: self.start_learning('m2'))
        row_m2 = QHBoxLayout(); row_m2.addWidget(lbl_m2); row_m2.addWidget(self.led_m2); row_m2.addStretch(); row_m2.addWidget(btn_learn_m2)
        lay_map.addLayout(row_m2)
        
        self.combo_m2 = QComboBox()
        for bid, bname in BUTTON_NAMES.items(): self.combo_m2.addItem(bname, bid)
        idx_m2 = self.combo_m2.findData(self.controller.mappings.get("m2_button_id", 1))
        if idx_m2 >= 0: self.combo_m2.setCurrentIndex(idx_m2)
        lay_map.addWidget(self.combo_m2)
        
        self.chk_hair = QCheckBox("Modo Gatilho Ultrasensível"); self.chk_hair.setChecked(self.controller.mappings.get("hair_triggers", False))
        self.chk_swap = QCheckBox("Alternar para layout Switch"); self.chk_swap.setChecked(self.controller.mappings.get("swap_ab_xy", False))
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
        bottom_bar.addWidget(self.log_lbl); bottom_bar.addStretch(); bottom_bar.addWidget(btn_save)
        dash_layout.addLayout(bottom_bar)
        
        self.stack.addWidget(self.dashboard_wrapper)
        
        # --- SOBRE TELA ---
        self.about_wrapper = QWidget()
        about_layout = QVBoxLayout(self.about_wrapper)
        about_layout.setAlignment(Qt.AlignCenter)
        
        dev_title = QLabel("GameSir Connect - Linux Edition")
        dev_title.setStyleSheet("font-size: 28px; font-weight: bold; color: #ffffff;")
        dev_title.setAlignment(Qt.AlignCenter)
        
        dev_info = QLabel("Desenvolvido por: Diotec Software (Dionísio Luís)\nVersão: 0.9.6 Beta\n\nSoftware de Engenharia Reversa para Comandos GameSir no Linux.")
        dev_info.setAlignment(Qt.AlignCenter)
        dev_info.setStyleSheet("font-size: 16px; color: #a1a1aa; margin-top: 10px; margin-bottom: 20px;")
        
        diotec_path = "/app/bin/diottec.jpeg" if os.path.exists("/app/bin/diottec.jpeg") else "diottec.jpeg"
        diotec_lbl = QLabel()
        if os.path.exists(diotec_path):
            pixmap = QPixmap(diotec_path).scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            diotec_lbl.setPixmap(pixmap)
        diotec_lbl.setAlignment(Qt.AlignCenter)
        
        compat_info = QLabel("Compatibilidade Atual: GameSir Cyclone 2.\nO seu modelo funcionou? Encontrou algum bug?\nRelate em: diotec.soft@gmail.com")
        compat_info.setAlignment(Qt.AlignCenter)
        compat_info.setStyleSheet("font-size: 14px; color: #34d399; margin-bottom: 20px; margin-top: 20px;")
        
        donate_lbl = QLabel("Apoie o desenvolvimento contínuo deste projeto (PIX):")
        donate_lbl.setAlignment(Qt.AlignCenter)
        donate_lbl.setStyleSheet("font-weight: bold; color: #ffffff;")
        
        btn_donate = QPushButton("📋 Copiar Chave PIX (a6e35576-02ec-4f43-a243-3e65ee8e9c3d)")
        btn_donate.setObjectName("btn_accent")
        btn_donate.setFixedWidth(450)
        btn_donate.clicked.connect(self.copy_pix)
        
        about_layout.addWidget(dev_title)
        about_layout.addWidget(dev_info)
        about_layout.addWidget(diotec_lbl)
        about_layout.addWidget(compat_info)
        about_layout.addWidget(donate_lbl)
        about_layout.addWidget(btn_donate, alignment=Qt.AlignCenter)
        
        self.stack.addWidget(self.about_wrapper)

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        content_layout.addWidget(self.stack)
        main_layout.addLayout(content_layout)
        main_layout_base.addWidget(self.main_container)

        self.last_pct = {0: 50, 1: 50, 2: 0, 3: 50, 4: 50, 5: 0}
        self.fd = None; self.hid_fd = None; self.evdev_device = None; self.active_effect_id = None
        self.init_hardware()
        self.hw_thread = HardwareMonitor(self.controller, self)
        self.hw_thread.log_signal.connect(self.add_log)
        self.hw_thread.status_signal.connect(self.update_status)
        self.hw_thread.telemetry_signal.connect(self.update_telemetry)
        self.hw_thread.m_btn_signal.connect(self.update_m_btn)
        self.hw_thread.start()

    def toggle_maximize(self):
        if self.isMaximized(): self.showNormal()
        else: self.showMaximized()

    def set_led_mode(self, mode):
        for btn in self.led_btns: btn.setChecked(btn.text() == mode)
        self.controller.led_mode = mode
        self.add_log(f"Modo de LED selecionado: {mode} (Sólido requer escolha de cor)", True)

    def update_led_settings(self):
        self.controller.led_brightness = self.slider_brilho.value()
        self.controller.led_speed = self.slider_vel.value()
        self.send_controller_led(self.controller.led_r, self.controller.led_g, self.controller.led_b)
        self.add_log(f"Brilho ajustado para {self.controller.led_brightness}%", True)

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
        self.add_log("Chave PIX copiada para a área de transferência! Obrigado pelo apoio.", True)

    def add_log(self, message, is_success=False):
        if hasattr(self, 'log_lbl'):
            color = "#34d399" if is_success else "#a1a1aa"
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
            self.add_log("Perfil gravado com sucesso no JSON e na EEPROM do Hardware!", True)
        elif json_ok:
            self.add_log("Perfil gravado (JSON OK, mas sem resposta de Hardware EEPROM).", True)
        else:
            self.add_log("Erro ao gravar perfil.", False)

    def send_controller_led(self, r, g, b, weak=0, strong=0, update_rumble=False):
        self.controller.led_r = r; self.controller.led_g = g; self.controller.led_b = b
        
        # Aplica o brilho matematicamente (Software Dimming)
        pct = self.slider_brilho.value() / 100.0
        r_dim = int(r * pct)
        g_dim = int(g * pct)
        b_dim = int(b * pct)

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
        self.add_log("Teste de vibração acionado.", True)

    def init_hardware(self):
        return
        self.poll_hardware()

    def poll_hardware(self):
        return
        # 1. Conexão Evdev / JS0
        if not self.fd:
            paths = ['/dev/input/js0', '/dev/input/js1', '/dev/input/js2']
            device_path = next((p for p in paths if os.path.exists(p)), None)
            if device_path:
                try:
                    self.fd = open(device_path, 'rb')
                    os.set_blocking(self.fd.fileno(), False)
                    self.conn_status.setText("🟢 Cyclone 2 (Ativo)")
                    self.conn_status.setStyleSheet("font-weight: bold; color: #34d399;")
                    self.add_log("Comando reconhecido e sincronizado.", True)
                    self.send_controller_led(self.controller.led_r, self.controller.led_g, self.controller.led_b)
                    
                    if EVDEV_AVAILABLE:
                        for dname in list_devices():
                            dev = InputDevice(dname)
                            if 'wireless controller' in dev.name.lower() or 'gamesir' in dev.name.lower():
                                if ecodes.EV_FF in dev.capabilities(): self.evdev_device = dev; break
                except Exception: pass
            else:
                if self.conn_status.text() != "🔴 Desconectado":
                    self.conn_status.setText("🔴 Desconectado")
                    self.conn_status.setStyleSheet("font-weight: bold; color: #ef4444;")
                return

        # 2. Conexão HIDRAW (M1/M2 nativos)
        if not self.hid_fd:
            nodes = self.get_gamesir_nodes()
            for node in nodes:
                try:
                    self.hid_fd = open(node, 'rb')
                    os.set_blocking(self.hid_fd.fileno(), False)
                    break
                except Exception: pass

        # Processar HIDRAW (Nativo)
        if self.hid_fd:
            try:
                hid_data = self.hid_fd.read(64)
                if hid_data == b'':
                    raise OSError("HID Desconectado")
                if hid_data and len(hid_data) > 6:
                    b5 = hid_data[5]
                    b6 = hid_data[6]
                    m1_pressed = bool(b5 & 0x10) or bool(b6 & 0x01)
                    m2_pressed = bool(b5 & 0x20) or bool(b6 & 0x02)
                    
                    if m1_pressed: 
                        self.led_m1.setText("🟢")
                        self.add_log("M1 acionado (Modo Físico)!", True)
                    elif not m1_pressed and self.led_m1.text() == "🟢":
                        self.led_m1.setText("⚫")
                        
                    if m2_pressed: 
                        self.led_m2.setText("🟢")
                        self.add_log("M2 acionado (Modo Físico)!", True)
                    elif not m2_pressed and self.led_m2.text() == "🟢":
                        self.led_m2.setText("⚫")
            except (BlockingIOError, struct.error):
                pass
            except OSError:
                if self.hid_fd: self.hid_fd.close()
                self.hid_fd = None

        # Processar JS0 (Tradicional) com Proteção contra Event Flooding
        fn_format = 'IhBB'
        event_size = struct.calcsize(fn_format)
        gui_needs_update = False
        events_processed = 0
        MAX_EVENTS_PER_TICK = 64 # Limite absoluto para evitar que o QTimer reentre e crash
        
        try:
            while events_processed < MAX_EVENTS_PER_TICK:
                try:
                    if not self.fd:
                        break
                    event = self.fd.read(event_size)
                except BlockingIOError:
                    break 
                except TypeError:
                    break
                
                if event == b'':
                    raise OSError("Cabo Desconectado")
                if event is None or len(event) < event_size:
                    break
                
                events_processed += 1
                
                try:
                    time_val, value, ev_type, number = struct.unpack(fn_format, event)
                except struct.error:
                    continue # Ignora pacotes corrompidos durante o stress
                
                if ev_type & 0x80: continue
                
                if ev_type == 2:
                    if number in [0, 1, 3, 4]:
                        dz = self.controller.DEADZONE_L_X if number in [0, 1] else self.controller.DEADZONE_R_X
                        f = self.controller.apply_deadzone(value, dz)
                        pct = int(((f + 32767) / 65534) * 100)
                        if self.last_pct[number] != pct:
                            self.last_pct[number] = pct; gui_needs_update = True
                    elif number in [2, 5]:
                        pct = int(((value + 32767) / 65534) * 100)
                        if self.last_pct[number] != pct:
                            self.last_pct[number] = pct; gui_needs_update = True
                            
                elif ev_type == 1:
                    is_trigger_click = (number > 300)
                    if not is_trigger_click or self.learning_target:
                        bname = BUTTON_NAMES.get(number, f"B{number}")
                        st = "Pressionado" if value == 1 else "Solto"
                        self.add_log(f"Input: {bname} -> {st}")

                    if self.learning_target and value == 1:
                        if number not in BUTTON_NAMES:
                            BUTTON_NAMES[number] = f"B{number}"
                            self.combo_m1.addItem(BUTTON_NAMES[number], number)
                            self.combo_m2.addItem(BUTTON_NAMES[number], number)

                        if self.learning_target == 'm1':
                            self.controller.mappings["m1_button_id"] = number
                            idx = self.combo_m1.findData(number)
                            if idx >= 0: self.combo_m1.setCurrentIndex(idx)
                        elif self.learning_target == 'm2':
                            self.controller.mappings["m2_button_id"] = number
                            idx = self.combo_m2.findData(number)
                            if idx >= 0: self.combo_m2.setCurrentIndex(idx)
                        
                        self.learning_target = None
                        self.add_log("Botão capturado com sucesso!", True)

        except OSError:
            if self.fd: 
                try: self.fd.close()
                except: pass
            self.fd = None
            self.conn_status.setText("🔴 Desconectado")
            self.conn_status.setStyleSheet("font-weight: bold; color: #ef4444;")
            self.add_log("Aguardando conexão do comando...")
            
        if gui_needs_update:
            self.bar_lx.setValue(self.last_pct.get(0, 50)); self.bar_ly.setValue(self.last_pct.get(1, 50))
            self.bar_rx.setValue(self.last_pct.get(3, 50)); self.bar_ry.setValue(self.last_pct.get(4, 50))
            self.bar_l2.setValue(self.last_pct.get(2, 0)); self.bar_r2.setValue(self.last_pct.get(5, 0))


    def update_status(self, text, color):
        self.conn_status.setText(text)
        self.conn_status.setStyleSheet(f"font-weight: bold; color: {color};")

    def update_telemetry(self, data):
        self.bar_lx.setValue(data.get(0, 50)); self.bar_ly.setValue(data.get(1, 50))
        self.bar_rx.setValue(data.get(3, 50)); self.bar_ry.setValue(data.get(4, 50))
        self.bar_l2.setValue(data.get(2, 0)); self.bar_r2.setValue(data.get(5, 0))

    def update_m_btn(self, btn, state):
        led = self.led_m1 if btn == 'm1' else self.led_m2
        if state:
            led.setText("🟢")
        elif not state and led.text() == "🟢":
            led.setText("⚫")


    def closeEvent(self, event):
        if hasattr(self, 'hw_thread') and self.hw_thread.isRunning():
            self.hw_thread.stop()
        event.accept()

def main():
    import signal
    # Permite que o Ctrl+C encerre a aplicação sem gerar o Traceback do KeyboardInterrupt
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    window = MainWindow(GameSirCyclone2())
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
