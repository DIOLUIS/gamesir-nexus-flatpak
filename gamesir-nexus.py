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
        self.root.geometry("520x540")
        self.root.configure(bg="#1e1e1e")
        
        # Estilo para os medidores
        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure("TProgressbar", thickness=12, troughcolor="#2d2d2d", background="#00ff66")
        
        # Rótulo de Cabeçalho
        self.title_label = tk.Label(root, text="GAMESIR NEXUS LINUX", font=("Helvetica", 16, "bold"), fg="#ffffff", bg="#1e1e1e")
        self.title_label.pack(pady=15)
        
        # Exibição do Perfil Ativo
        self.profile_label = tk.Label(root, text=f"Perfil Ativo: {self.controller.profile_name}", font=("Helvetica", 11), fg="#00ff66", bg="#1e1e1e")
        self.profile_label.pack(pady=5)
        
        # Monitor de Interação de Botões
        self.status_label = tk.Label(root, text="Aguardando input do controle...", font=("Helvetica", 12), fg="#aaaaaa", bg="#2d2d2d", width=40, height=2, relief="groove")
        self.status_label.pack(pady=10)
        
        # --- PAINEL ANALÓGICO ESQUERDO ---
        self.frame_left = tk.LabelFrame(root, text=" Efeito Hall - Analógico Esquerdo ", font=("Helvetica", 10, "bold"), fg="#ffffff", bg="#1e1e1e", padx=10, pady=5)
        self.frame_left.pack(pady=5, fill="x", padx=20)
        
        tk.Label(self.frame_left, text="Eixo X (Horizontal):", fg="#cccccc", bg="#1e1e1e", font=("Helvetica", 9)).pack(anchor="w")
        self.progress_lx = ttk.Progressbar(self.frame_left, orient="horizontal", length=440, mode="determinate", style="TProgressbar")
        self.progress_lx.pack(pady=3)
        self.progress_lx['value'] = 50
        
        tk.Label(self.frame_left, text="Eixo Y (Vertical):", fg="#cccccc", bg="#1e1e1e", font=("Helvetica", 9)).pack(anchor="w")
        self.progress_ly = ttk.Progressbar(self.frame_left, orient="horizontal", length=440, mode="determinate", style="TProgressbar")
        self.progress_ly.pack(pady=3)
        self.progress_ly['value'] = 50

        # --- PAINEL ANALÓGICO DIREITO ---
        self.frame_right = tk.LabelFrame(root, text=" Efeito Hall - Analógico Direito ", font=("Helvetica", 10, "bold"), fg="#ffffff", bg="#1e1e1e", padx=10, pady=5)
        self.frame_right.pack(pady=5, fill="x", padx=20)
        
        tk.Label(self.frame_right, text="Eixo X (Horizontal):", fg="#cccccc", bg="#1e1e1e", font=("Helvetica", 9)).pack(anchor="w")
        self.progress_rx = ttk.Progressbar(self.frame_right, orient="horizontal", length=440, mode="determinate", style="TProgressbar")
        self.progress_rx.pack(pady=3)
        self.progress_rx['value'] = 50
        
        tk.Label(self.frame_right, text="Eixo Y (Vertical):", fg="#cccccc", bg="#1e1e1e", font=("Helvetica", 9)).pack(anchor="w")
        self.progress_ry = ttk.Progressbar(self.frame_right, orient="horizontal", length=440, mode="determinate", style="TProgressbar")
        self.progress_ry.pack(pady=3)
        self.progress_ry['value'] = 50
        
        # Nota de rodapé técnica
        self.footer_label = tk.Label(root, text="Filtro ativo contra drift nos Analógicos de Efeito Hall", font=("Helvetica", 9, "italic"), fg="#777777", bg="#1e1e1e")
        self.footer_label.pack(side="bottom", pady=10)

    def update_input_display(self, button_name):
        self.root.after(0, lambda: self.status_label.config(text=f"Botão Pressionado: {button_name}", fg="#ffffff", bg="#0055ff"))

    def update_analog_display(self, axis_id, filtered_value):
        """Mapeia linearmente: -32767 -> 0% | 0 -> 50% | 32767 -> 100%"""
        percentage = ((filtered_value + 32767) / 65534) * 100
        if axis_id == 0:
            self.root.after(0, lambda: self.progress_lx.config(value=percentage))
        elif axis_id == 1:
            self.root.after(0, lambda: self.progress_ly.config(value=percentage))
        elif axis_id == 3:
            self.root.after(0, lambda: self.progress_rx.config(value=percentage))
        elif axis_id == 4:
            self.root.after(0, lambda: self.progress_ry.config(value=percentage))

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
                
                # 2. Captura de Eixos com Deadzone Dinâmica
                elif actual_type == 2:
                    if number == 0:
                        f = controller.apply_deadzone(value, controller.DEADZONE_L_X)
                        gui.update_analog_display(0, f)
                    elif number == 1:
                        f = controller.apply_deadzone(value, controller.DEADZONE_L_Y)
                        gui.update_analog_display(1, f)
                    elif number == 3:
                        f = controller.apply_deadzone(value, controller.DEADZONE_R_X)
                        gui.update_analog_display(3, f)
                    elif number == 4:
                        f = controller.apply_deadzone(value, controller.DEADZONE_R_Y)
                        gui.update_analog_display(4, f)
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
