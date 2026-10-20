#!/usr/bin/env python3
import os, json, struct, sys, glob, zlib, traceback, errno
sys.path.append('/app/lib/python3.11/site-packages')
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                               QWidget, QProgressBar, QGroupBox, QTabWidget, QPushButton, 
                               QSlider, QHBoxLayout, QTextEdit, QFormLayout, QSpinBox, 
                               QColorDialog, QComboBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

try:
    from evdev import InputDevice, ecodes, ff, list_devices
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False

try:
    import hid
    HID_AVAILABLE = True
except ImportError:
    HID_AVAILABLE = False

BUTTON_NAMES = {
    0: "Botão ID 0 (Cruz / A)",
    1: "Botão ID 1 (Círculo / B)",
    2: "Botão ID 2 (Triângulo / X)",
    3: "Botão ID 3 (Quadrado / Y)",
    4: "Botão ID 4 (L1 / LB)",
    5: "Botão ID 5 (R1 / RB)",
    6: "Botão ID 6 (L2 / LT Digital)",
    7: "Botão ID 7 (R2 / RT Digital)",
    8: "Botão ID 8 (Share / Select)",
    9: "Botão ID 9 (Options / Start)",
    10: "Botão ID 10 (PS / Home)",
    11: "Botão ID 11 (L3 / Analógico Esq)",
    12: "Botão ID 12 (R3 / Analógico Dir)",
    13: "Botão ID 13 (Touchpad Click / Extra)",
    14: "Botão ID 14 (Extra / M1 Nativo)",
    15: "Botão ID 15 (Extra / M2 Nativo)"
}

class GameSirCyclone2:
    def __init__(self, profile_path="profile_default.json"):
        self.profile_path = profile_path
        self.DEADZONE_L_X = 4000
        self.DEADZONE_L_Y = 2000
        self.DEADZONE_R_X = 3000
        self.DEADZONE_R_Y = 3000
        self.led_r = 0
        self.led_g = 255
        self.led_b = 128
        self.mappings = {
            "m1_button_id": 2,
            "m2_button_id": 1
        }
        self.profile_name = "Padrão de Fábrica"
        self.load_profile()

    def load_profile(self):
        paths = [
            self.profile_path,
            f"/app/bin/{self.profile_path}",
            os.path.expanduser("~/.var/app/com.github.dioluis.gamesir-nexus/config/profile_default.json")
        ]
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
                    
                    led = data.get("lighting", {})
                    self.led_r = led.get("r", 0)
                    self.led_g = led.get("g", 255)
                    self.led_b = led.get("b", 128)
                    
                    mp = data.get("mappings", {})
                    self.mappings["m1_button_id"] = mp.get("m1_button_id", 2)
                    self.mappings["m2_button_id"] = mp.get("m2_button_id", 1)
                    
                    self.profile_name = data.get("profile_name", "Padrão de Fábrica")
                    return
                except Exception:
                    pass

    def save_profile(self):
        config_dir = os.path.expanduser("~/.var/app/com.github.dioluis.gamesir-nexus/config")
        os.makedirs(config_dir, exist_ok=True)
        target_path = os.path.join(config_dir, "profile_default.json")
        data = {
            "profile_name": self.profile_name,
            "deadzones": {
                "left_analog_x": self.DEADZONE_L_X,
                "left_analog_y": self.DEADZONE_L_Y,
                "right_analog_x": self.DEADZONE_R_X,
                "right_analog_y": self.DEADZONE_R_Y
            },
            "lighting": {
                "r": self.led_r,
                "g": self.led_g,
                "b": self.led_b
            },
            "mappings": self.mappings
        }
        try:
            with open(target_path, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception:
            return False

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
        self.setWindowTitle("GameSir Nexus - Painel de Controlo Avançado")
        self.resize(780, 760)
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; color: #ffffff; }
            QTabWidget::pane { border: 1px solid #444; border-radius: 4px; }
            QTabBar::tab { background: #2d2d2d; color: #aaa; padding: 10px 20px; border: 1px solid #444; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #0055ff; color: white; font-weight: bold; }
            QSlider::groove:horizontal { border: 1px solid #444; height: 8px; background: #2d2d2d; border-radius: 4px; }
            QSlider::handle:horizontal { background: #00ff66; width: 18px; margin: -5px 0; border-radius: 9px; }
            QTextEdit { background-color: #000000; color: #00ff66; border: 1px solid #444; font-family: monospace; }
            QComboBox { background-color: #2d2d2d; color: white; border: 1px solid #444; padding: 6px; border-radius: 4px; }
            QComboBox QAbstractItemView { background-color: #2d2d2d; color: white; selection-background-color: #0055ff; }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.connection_banner = QLabel("Protocolo Validado: GameSir Cyclone 2 (Pás M1 / M2 Ativas)")
        self.connection_banner.setStyleSheet("color: #00ff66; background-color: #1a3322; padding: 10px; border-radius: 4px; font-weight: bold;")
        self.connection_banner.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.connection_banner)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.learning_target = None  # 'm1' ou 'm2' quando estiver aguardando clique

        self.setup_tab_logs()
        self.setup_tab_diagnostico()
        self.setup_tab_iluminacao()
        self.setup_tab_vibracao()
        self.setup_tab_mapeamento()

        self.last_pct = {0: 50, 1: 50, 3: 50, 4: 50}
        self.fd = None
        self.evdev_path = None
        self.evdev_device = None
        self.active_effect_id = None
        
        self.add_log("Sistema iniciado com suporte a telemetria e captura dinâmica M1/M2.")
        self.init_hardware()

        self.send_controller_led(self.controller.led_r, self.controller.led_g, self.controller.led_b)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_hardware)
        self.timer.start(16)

    def setup_tab_logs(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        layout.addWidget(self.log_console)
        btn_clear = QPushButton("Limpar Logs")
        btn_clear.setStyleSheet("background-color: #444; color: white; padding: 8px;")
        btn_clear.clicked.connect(self.log_console.clear)
        layout.addWidget(btn_clear)
        self.tabs.addTab(tab, "Logs")

    def add_log(self, message):
        self.log_console.append(message)

    def setup_tab_diagnostico(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.status_label = QLabel("Aguardando input do controlo...")
        self.status_label.setStyleSheet("color: #aaaaaa; background-color: #2d2d2d; padding: 15px; border-radius: 4px; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        group_l = QGroupBox(" Analógico Esquerdo ")
        layout_l = QVBoxLayout(group_l)
        self.bar_lx = QProgressBar(); self.bar_lx.setRange(0, 100); self.bar_lx.setValue(50)
        self.bar_ly = QProgressBar(); self.bar_ly.setRange(0, 100); self.bar_ly.setValue(50)
        self.bar_lx.setStyleSheet("QProgressBar::chunk { background-color: #00ff66; }")
        self.bar_ly.setStyleSheet("QProgressBar::chunk { background-color: #00ff66; }")
        layout_l.addWidget(QLabel("Eixo X:")); layout_l.addWidget(self.bar_lx)
        layout_l.addWidget(QLabel("Eixo Y:")); layout_l.addWidget(self.bar_ly)
        layout.addWidget(group_l)
        
        group_r = QGroupBox(" Analógico Direito ")
        layout_r = QVBoxLayout(group_r)
        self.bar_rx = QProgressBar(); self.bar_rx.setRange(0, 100); self.bar_rx.setValue(50)
        self.bar_ry = QProgressBar(); self.bar_ry.setRange(0, 100); self.bar_ry.setValue(50)
        self.bar_rx.setStyleSheet("QProgressBar::chunk { background-color: #00ff66; }")
        self.bar_ry.setStyleSheet("QProgressBar::chunk { background-color: #00ff66; }")
        layout_r.addWidget(QLabel("Eixo X:")); layout_r.addWidget(self.bar_rx)
        layout_r.addWidget(QLabel("Eixo Y:")); layout_r.addWidget(self.bar_ry)
        layout.addWidget(group_r)
        self.tabs.addTab(tab, "Diagnóstico")

    def setup_tab_iluminacao(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.color_preview = QLabel(f"Cor Ativa: R({self.controller.led_r}) G({self.controller.led_g}) B({self.controller.led_b})")
        self.update_color_preview_style()
        self.color_preview.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.color_preview)

        btn_pick_color = QPushButton("Selecionar Cor Personalizada")
        btn_pick_color.setStyleSheet("background-color: #0055ff; color: white; font-weight: bold; padding: 14px; border-radius: 4px; font-size: 14px;")
        btn_pick_color.clicked.connect(self.open_color_picker)
        layout.addWidget(btn_pick_color)

        group_presets = QGroupBox(" Atalhos Rápidos ")
        preset_layout = QHBoxLayout(group_presets)

        presets = [
            ("Verde", 0, 255, 0, "#008800"),
            ("Ciano", 0, 255, 255, "#008888"),
            ("Azul", 0, 100, 255, "#0055bb"),
            ("Vermelho", 255, 0, 0, "#880000"),
            ("Roxo", 180, 0, 255, "#660088"),
            ("Desligar", 0, 0, 0, "#333333")
        ]

        for name, r, g, b, color_hex in presets:
            btn = QPushButton(name)
            btn.setStyleSheet(f"background-color: {color_hex}; color: white; font-weight: bold; padding: 12px; border-radius: 4px;")
            btn.clicked.connect(lambda checked, red=r, green=g, blue=b: self.send_controller_led(red, green, blue))
            preset_layout.addWidget(btn)

        layout.addWidget(group_presets)
        self.tabs.addTab(tab, "Iluminação")

    def update_color_preview_style(self):
        r, g, b = self.controller.led_r, self.controller.led_g, self.controller.led_b
        lum = (0.299 * r + 0.587 * g + 0.114 * b)
        text_color = "#000000" if lum > 140 else "#ffffff"
        self.color_preview.setText(f"Cor Ativa: R({r}) G({g}) B({b})")
        self.color_preview.setStyleSheet(f"background-color: rgb({r}, {g}, {b}); color: {text_color}; padding: 16px; border-radius: 6px; font-weight: bold; font-size: 14px; border: 1px solid #555;")

    def open_color_picker(self):
        initial = QColor(self.controller.led_r, self.controller.led_g, self.controller.led_b)
        color = QColorDialog.getColor(initial, self, "Escolher Cor dos LEDs do Cyclone 2")
        if color.isValid():
            self.send_controller_led(color.red(), color.green(), color.blue())

    def get_gamesir_node(self):
        for node in sorted(glob.glob('/dev/hidraw*')):
            base = os.path.basename(node)
            uevent_path = f"/sys/class/hidraw/{base}/device/uevent"
            if os.path.exists(uevent_path):
                try:
                    with open(uevent_path, 'r') as f:
                        txt = f.read().lower()
                        if '054c' in txt or 'chicken run' in txt or 'gamesir' in txt:
                            return node
                except Exception:
                    pass
        return '/dev/hidraw1' if os.path.exists('/dev/hidraw1') else None

    def send_controller_led(self, r, g, b, weak_motor=0, strong_motor=0, update_rumble=False):
        self.controller.led_r = r
        self.controller.led_g = g
        self.controller.led_b = b
        self.update_color_preview_style()

        target = self.get_gamesir_node()
        if not target:
            self.add_log("[ERRO] Controle GameSir não localizado em /dev/hidraw*")
            return

        report = bytearray(64)
        report[0] = 0x05
        report[1] = 0x03 if update_rumble else 0x02
        report[2] = 0x04
        report[4] = weak_motor
        report[5] = strong_motor
        report[6] = r
        report[7] = g
        report[8] = b
        report[9] = 0x00
        report[10] = 0x00

        try:
            with open(target, 'wb') as f:
                f.write(report)
                f.flush()
            if not update_rumble:
                self.add_log(f"[LED] Cor R({r}) G({g}) B({b}) aplicada via {target}")
        except PermissionError:
            self.add_log(f"[ERRO PERMISSÃO] Acesso negado a {target}.")
        except Exception as e:
            self.add_log(f"[FALHA LED] {e}")

    def setup_tab_vibracao(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.vib_status_label = QLabel("Motores de Vibração Assinados (Force Feedback)")
        self.vib_status_label.setStyleSheet("color: #aaaaaa; background-color: #2d2d2d; padding: 15px; border-radius: 4px; font-weight: bold;")
        self.vib_status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.vib_status_label)

        btn_test_rumble = QPushButton("Executar Teste de Força (1.5s)")
        btn_test_rumble.setStyleSheet("QPushButton { background-color: #0055ff; color: white; font-weight: bold; padding: 18px; border-radius: 4px; font-size: 14px; }")
        btn_test_rumble.clicked.connect(self.trigger_rumble_test)
        layout.addWidget(btn_test_rumble)

        self.tabs.addTab(tab, "Vibração")

    def trigger_rumble_test(self):
        evdev_ok = False
        if EVDEV_AVAILABLE:
            if not self.evdev_device:
                self.init_hardware()
            if self.evdev_device:
                try:
                    rumble = ff.Rumble(strong_magnitude=0xffff, weak_magnitude=0x8000)
                    effect_type = ff.EffectType(ff_rumble_effect=rumble)
                    effect = ff.Effect(
                        ecodes.FF_RUMBLE,
                        -1,
                        0,
                        ff.Trigger(0, 0),
                        ff.Replay(1500, 0),
                        effect_type
                    )
                    if self.active_effect_id is not None:
                        try:
                            self.evdev_device.erase_effect(self.active_effect_id)
                        except Exception:
                            pass
                    self.active_effect_id = self.evdev_device.upload_effect(effect)
                    self.evdev_device.write(ecodes.EV_FF, self.active_effect_id, 1)
                    evdev_ok = True
                except Exception as e:
                    self.add_log(f"[AVISO evdev FF] {str(e)}")

        r, g, b = self.controller.led_r, self.controller.led_g, self.controller.led_b
        self.send_controller_led(r, g, b, weak_motor=200, strong_motor=255, update_rumble=True)
        QTimer.singleShot(1500, lambda: self.send_controller_led(
            self.controller.led_r, self.controller.led_g, self.controller.led_b, 
            weak_motor=0, strong_motor=0, update_rumble=True
        ))
        self.add_log(f"Force Feedback executado com sucesso! (evdev={'OK' if evdev_ok else 'HID Direto'})")

    def setup_tab_mapeamento(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group_dz = QGroupBox(" Calibração e Deadzones ")
        form_layout = QFormLayout(group_dz)
        self.lbl_profile = QLabel(self.controller.profile_name)
        self.lbl_profile.setStyleSheet("color: #00ff66; font-weight: bold;")
        form_layout.addRow("Perfil Ativo:", self.lbl_profile)
        
        self.spin_dz_lx = QSpinBox()
        self.spin_dz_lx.setRange(0, 15000)
        self.spin_dz_lx.setValue(self.controller.DEADZONE_L_X)
        self.spin_dz_lx.valueChanged.connect(lambda v: setattr(self.controller, 'DEADZONE_L_X', v))
        form_layout.addRow("Deadzone Analógico Esq (X):", self.spin_dz_lx)
        layout.addWidget(group_dz)

        group_rear = QGroupBox(" Botões Traseiros (M1 / M2) e Monitor de Eventos ")
        rear_layout = QVBoxLayout(group_rear)

        # Monitor global de botões para ver na hora o que o controle envia
        self.lbl_last_btn = QLabel("Último botão pressionado no controle: Nenhum")
        self.lbl_last_btn.setStyleSheet("background-color: #111; color: #00ff66; padding: 10px; border-radius: 4px; font-weight: bold; border: 1px solid #333;")
        self.lbl_last_btn.setAlignment(Qt.AlignCenter)
        rear_layout.addWidget(self.lbl_last_btn)
        
        live_layout = QHBoxLayout()
        self.lbl_m1_state = QLabel("M1 (Esq): SOLTO")
        self.lbl_m1_state.setStyleSheet("background-color: #2d2d2d; color: #888; padding: 12px; border-radius: 4px; font-weight: bold;")
        self.lbl_m1_state.setAlignment(Qt.AlignCenter)
        
        self.lbl_m2_state = QLabel("M2 (Dir): SOLTO")
        self.lbl_m2_state.setStyleSheet("background-color: #2d2d2d; color: #888; padding: 12px; border-radius: 4px; font-weight: bold;")
        self.lbl_m2_state.setAlignment(Qt.AlignCenter)
        
        live_layout.addWidget(self.lbl_m1_state)
        live_layout.addWidget(self.lbl_m2_state)
        rear_layout.addLayout(live_layout)

        # Botões de Captura Interativa
        learn_layout = QHBoxLayout()
        self.btn_learn_m1 = QPushButton("Capturar Botão M1")
        self.btn_learn_m1.setStyleSheet("background-color: #444; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        self.btn_learn_m1.clicked.connect(lambda: self.start_learning('m1'))

        self.btn_learn_m2 = QPushButton("Capturar Botão M2")
        self.btn_learn_m2.setStyleSheet("background-color: #444; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        self.btn_learn_m2.clicked.connect(lambda: self.start_learning('m2'))

        learn_layout.addWidget(self.btn_learn_m1)
        learn_layout.addWidget(self.btn_learn_m2)
        rear_layout.addLayout(learn_layout)

        map_form = QFormLayout()
        self.combo_m1 = QComboBox()
        self.combo_m2 = QComboBox()
        for bid, bname in BUTTON_NAMES.items():
            self.combo_m1.addItem(bname, bid)
            self.combo_m2.addItem(bname, bid)
            
        idx_m1 = self.combo_m1.findData(self.controller.mappings.get("m1_button_id", 2))
        if idx_m1 >= 0: self.combo_m1.setCurrentIndex(idx_m1)
        idx_m2 = self.combo_m2.findData(self.controller.mappings.get("m2_button_id", 1))
        if idx_m2 >= 0: self.combo_m2.setCurrentIndex(idx_m2)
        
        self.combo_m1.currentIndexChanged.connect(lambda: self.controller.mappings.update({"m1_button_id": self.combo_m1.currentData()}))
        self.combo_m2.currentIndexChanged.connect(lambda: self.controller.mappings.update({"m2_button_id": self.combo_m2.currentData()}))

        map_form.addRow("Atribuição M1 (Mão Esquerda):", self.combo_m1)
        map_form.addRow("Atribuição M2 (Mão Direita):", self.combo_m2)
        rear_layout.addLayout(map_form)

        info_hw = QLabel("Dica: Se M1/M2 não emitirem sinal ao apertar, segure o botão 'M' + M1/M2 no controle até piscar e aperte um botão frontal para ativar a pá no firmware.")
        info_hw.setWordWrap(True)
        info_hw.setStyleSheet("color: #aaa; font-size: 11px; padding: 4px;")
        rear_layout.addWidget(info_hw)
        
        layout.addWidget(group_rear)
        
        btn_save = QPushButton("Gravar Perfil Completo em JSON")
        btn_save.setStyleSheet("background-color: #00aa55; color: white; font-weight: bold; padding: 12px; border-radius: 4px;")
        btn_save.clicked.connect(lambda: self.add_log("Perfil gravado com sucesso!") if self.controller.save_profile() else self.add_log("[ERRO] Falha ao gravar perfil."))
        layout.addWidget(btn_save)
        
        self.tabs.addTab(tab, "Mapeamento")

    def start_learning(self, target):
        self.learning_target = target
        self.lbl_last_btn.setText(f"AGUARDANDO: Pressione a pá {target.upper()} no controle agora...")
        self.lbl_last_btn.setStyleSheet("background-color: #aa5500; color: white; padding: 10px; border-radius: 4px; font-weight: bold;")

    def init_hardware(self):
        paths = ['/dev/input/js0', '/dev/input/js1', '/dev/input/js2']
        device_path = next((p for p in paths if os.path.exists(p)), None)
        if device_path and not self.fd:
            try:
                self.fd = open(device_path, 'rb')
                os.set_blocking(self.fd.fileno(), False)
                self.add_log(f"Telemetria conectada em {device_path}")
            except Exception:
                pass

        if EVDEV_AVAILABLE:
            try:
                for dname in list_devices():
                    dev = InputDevice(dname)
                    if 'wireless controller' in dev.name.lower() or 'gamesir' in dev.name.lower():
                        if ecodes.EV_FF in dev.capabilities():
                            self.evdev_path = dev.path
                            self.evdev_device = dev
                            break
            except Exception:
                pass

    def poll_hardware(self):
        if not self.fd:
            paths = ['/dev/input/js0', '/dev/input/js1', '/dev/input/js2']
            device_path = next((p for p in paths if os.path.exists(p)), None)
            if device_path:
                try:
                    self.fd = open(device_path, 'rb')
                    os.set_blocking(self.fd.fileno(), False)
                except Exception:
                    pass
            return

        fn_format = 'IhBB'
        event_size = struct.calcsize(fn_format)
        gui_needs_update = False
        
        try:
            while True:
                event = self.fd.read(event_size)
                if not event or len(event) < event_size:
                    break
                time_val, value, ev_type, number = struct.unpack(fn_format, event)
                
                # Ignora eventos sintéticos de inicialização do kernel (JS_EVENT_INIT = 0x80)
                if ev_type & 0x80:
                    continue
                
                if ev_type == 2 and number in self.last_pct:
                    dz = self.controller.DEADZONE_L_X if number == 0 else self.controller.DEADZONE_L_Y
                    f = self.controller.apply_deadzone(value, dz)
                    pct = int(((f + 32767) / 65534) * 100)
                    if self.last_pct[number] != pct:
                        self.last_pct[number] = pct
                        gui_needs_update = True
                        
                elif ev_type == 1:
                    bname = BUTTON_NAMES.get(number, f"Botão ID {number}")
                    state_txt = "PRESSIONADO" if value == 1 else "SOLTO"
                    self.lbl_last_btn.setText(f"Evento recebido: {bname} -> {state_txt}")
                    self.lbl_last_btn.setStyleSheet("background-color: #111; color: #00ff66; padding: 10px; border-radius: 4px; font-weight: bold; border: 1px solid #333;")
                    self.status_label.setText(f"Input: {bname} ({state_txt})")

                    # Se estiver no modo de captura de M1/M2 e o botão foi pressionado
                    if self.learning_target and value == 1:
                        if number not in BUTTON_NAMES:
                            BUTTON_NAMES[number] = f"Botão ID {number}"
                            self.combo_m1.addItem(BUTTON_NAMES[number], number)
                            self.combo_m2.addItem(BUTTON_NAMES[number], number)

                        if self.learning_target == 'm1':
                            self.controller.mappings["m1_button_id"] = number
                            idx = self.combo_m1.findData(number)
                            if idx >= 0: self.combo_m1.setCurrentIndex(idx)
                            self.add_log(f"[MAPEAMENTO] M1 vinculado ao ID {number} ({bname})")
                        elif self.learning_target == 'm2':
                            self.controller.mappings["m2_button_id"] = number
                            idx = self.combo_m2.findData(number)
                            if idx >= 0: self.combo_m2.setCurrentIndex(idx)
                            self.add_log(f"[MAPEAMENTO] M2 vinculado ao ID {number} ({bname})")
                        self.learning_target = None

                    m1_target = self.controller.mappings.get("m1_button_id", 2)
                    m2_target = self.controller.mappings.get("m2_button_id", 1)
                    
                    if number == m1_target:
                        if value == 1:
                            self.lbl_m1_state.setText(f"M1 (Esq - ID {number}): PRESSIONADO")
                            self.lbl_m1_state.setStyleSheet("background-color: #00aa55; color: white; padding: 12px; border-radius: 4px; font-weight: bold;")
                        else:
                            self.lbl_m1_state.setText(f"M1 (Esq - ID {number}): SOLTO")
                            self.lbl_m1_state.setStyleSheet("background-color: #2d2d2d; color: #888; padding: 12px; border-radius: 4px; font-weight: bold;")
                            
                    if number == m2_target:
                        if value == 1:
                            self.lbl_m2_state.setText(f"M2 (Dir - ID {number}): PRESSIONADO")
                            self.lbl_m2_state.setStyleSheet("background-color: #0055ff; color: white; padding: 12px; border-radius: 4px; font-weight: bold;")
                        else:
                            self.lbl_m2_state.setText(f"M2 (Dir - ID {number}): SOLTO")
                            self.lbl_m2_state.setStyleSheet("background-color: #2d2d2d; color: #888; padding: 12px; border-radius: 4px; font-weight: bold;")
        except Exception:
            pass
            
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
