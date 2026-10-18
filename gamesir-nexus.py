#!/usr/bin/env python3
import os
import json
import struct
import sys
import tkinter as tk
from tkinter import ttk
from threading import Thread

class GameSirCyclone2:
    def __init__(self, profile_path="profile_default.json"):
        self.profile_path = profile_path
        self.DEADZONE_L_X = 4000
        self.DEADZONE_L_Y = 2000
        self.DEADZONE_R_X = 3000
        self.DEADZONE_R_Y = 3000
        self.mappings = {}
        self.load_profile()

    def load_profile(self):
        if not os.path.exists(self.profile_path):
            return
        try:
            with open(self.profile_path, 'r') as f:
                data = json.load(f)
            dz = data.get("deadzones", {})
            self.DEADZONE_L_X = dz.get("left_analog_x", 4000)
            self.DEADZONE_L_Y = dz.get("left_analog_y", 2000)
            self.DEADZONE_R_X = dz.get("right_analog_x", 3000)
            self.DEADZONE_R_Y = dz.get("right_analog_y", 3000)
            self.mappings = data.get("mappings", {})
            self.profile_name = data.get("profile_name", "Padrão de Fábrica")
        except Exception:
            self.profile_name = "Padrão de Fábrica (Fallback)"

    def apply_deadzone(self, raw_value, deadzone):
        if abs(raw_value) < deadzone:
            return 0
        if raw_value > 0:
            return int(((raw_value - deadzone) / (32767 - deadzone)) * 32767)
        else:
            return int(((raw_value + deadzone) / (32767 - deadzone)) * -32767)

class AppGUI:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        
        self.root.title("GameSir Cyclone 2 - Painel Linux")
        self.root.geometry("480x420")
        self.root.configure(bg="#1e1e1e")
        
        # Estilo para os medidores
        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure("TProgressbar", thickness=15, troughcolor="#2d2d2d", background="#00ff66")
        
        # Rótulo de Cabeçalho
        self.title_label = tk.Label(root, text="GAMESIR NEXUS LINUX", font=("Helvetica", 16, "bold"), fg="#ffffff", bg="#1e1e1e")
        self.title_label.pack(pady=15)
        
        # Exibição do Perfil Ativo
        self.profile_label = tk.Label(root, text=f"Perfil Ativo: {self.controller.profile_name}", font=("Helvetica", 11), fg="#00ff66", bg="#1e1e1e")
        self.profile_label.pack(pady=5)
        
        # Monitor de Interação de Botões
        self.status_label = tk.Label(root, text="Aguardando input do controle...", font=("Helvetica", 12), fg="#aaaaaa", bg="#2d2d2d", width=35, height=2, relief="groove")
        self.status_label.pack(pady=15)
        
        # Container para Telemetria dos Analógicos
        self.analog_frame = tk.LabelFrame(root, text=" Telemetria Efeito Hall (Analógico Esquerdo) ", font=("Helvetica", 10, "bold"), fg="#ffffff", bg="#1e1e1e", padx=10, pady=10)
        self.analog_frame.pack(pady=10, fill="x", padx=20)
        
        # Medidor Eixo X
        tk.Label(self.analog_frame, text="Eixo X (Horizontal):", fg="#cccccc", bg="#1e1e1e").pack(anchor="w")
        self.progress_x = ttk.Progressbar(self.analog_frame, orient="horizontal", length=400, mode="determinate", style="TProgressbar")
        self.progress_x.pack(pady=5)
        self.progress_x['value'] = 50  # Centralizado por padrão
        
        # Medidor Eixo Y
        tk.Label(self.analog_frame, text="Eixo Y (Vertical):", fg="#cccccc", bg="#1e1e1e").pack(anchor="w")
        self.progress_y = ttk.Progressbar(self.analog_frame, orient="horizontal", length=400, mode="determinate", style="TProgressbar")
        self.progress_y.pack(pady=5)
        self.progress_y['value'] = 50  # Centralizado por padrão
        
        # Nota de rodapé técnica
        self.footer_label = tk.Label(root, text="Filtro ativo contra drift nos Analógicos de Efeito Hall", font=("Helvetica", 9, "italic"), fg="#777777", bg="#1e1e1e")
        self.footer_label.pack(side="bottom", pady=10)

    def update_input_display(self, button_name):
        self.root.after(0, lambda: self.status_label.config(text=f"Botão Pressionado: {button_name}", fg="#ffffff", bg="#0055ff"))

    def update_analog_display(self, axis_id, filtered_value):
        """Converte a escala do hardware (-32767 a 32767) para a escala gráfica do medidor (0 a 100)"""
        # Mapeia linearmente: -32767 -> 0% | 0 -> 50% | 32767 -> 100%
        percentage = ((filtered_value + 32767) / 65534) * 100
        if axis_id == 0:
            self.root.after(0, lambda: self.progress_x.config(value=percentage))
        elif axis_id == 1:
            self.root.after(0, lambda: self.progress_y.config(value=percentage))

def read_hardware(controller, gui):
    device_path = '/dev/input/js0'
    if not os.path.exists(device_path):
        return
        
    fn_format = 'IhBB'
    event_size = struct.calcsize(fn_format)
    
    try:
        with open(device_path, 'rb') as fd:
            while True:
                event = fd.read(event_size)
                if not event:
                    break
                time, value, ev_type, number = struct.unpack(fn_format, event)
                actual_type = ev_type & ~0x80
                
                # 1. Captura de Botões
                if actual_type == 1 and value == 1:
                    btn_key = f"btn_{number}"
                    mapped_name = controller.mappings.get(btn_key, f"ID {number}")
                    gui.update_input_display(mapped_name)
                
                # 2. Captura de Eixos com aplicação da Deadzone
                elif actual_type == 2:
                    if number == 0:
                        f = controller.apply_deadzone(value, controller.DEADZONE_L_X)
                        gui.update_analog_display(0, f)
                    elif number == 1:
                        f = controller.apply_deadzone(value, controller.DEADZONE_L_Y)
                        gui.update_analog_display(1, f)
    except Exception:
        pass

def main():
    device_path = '/dev/input/js0'
    if not os.path.exists(device_path):
        print("[X] Erro: /dev/input/js0 não encontrado. Conecte o controle.")
        sys.exit(1)
        
    controller = GameSirCyclone2()
    root = tk.Tk()
    gui = AppGUI(root, controller)
    
    hardware_thread = Thread(target=read_hardware, args=(controller, gui), daemon=True)
    hardware_thread.start()
    
    root.mainloop()

if __name__ == "__main__":
    main()
