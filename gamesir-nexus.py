#!/usr/bin/env python3
import os
import json
import struct
import sys

class GameSirCyclone2:
    def __init__(self, profile_path="profile_default.json"):
        self.profile_path = profile_path
        # Valores padrão de fallback caso o JSON falhe
        self.DEADZONE_L_X = 4000
        self.DEADZONE_L_Y = 2000
        self.DEADZONE_R_X = 3000
        self.DEADZONE_R_Y = 3000
        self.mappings = {}
        
        self.load_profile()

    def load_profile(self):
        """Carrega dinamicamente as configurações de zona morta e mapeamento do JSON"""
        if not os.path.exists(self.profile_path):
            print(f"[*] Perfil {self.profile_path} não encontrado. Usando padrões do kernel.")
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
            
            print(f"[O] Perfil '{data.get('profile_name', 'Sem Nome')}' carregado com sucesso!")
        except Exception as e:
            print(f"[X] Erro ao processar arquivo de perfil: {e}")

    def apply_deadzone(self, raw_value, deadzone):
        """Filtra as oscilações e estabiliza o analógico no centro (zero)"""
        if abs(raw_value) < deadzone:
            return 0
        if raw_value > 0:
            return int(((raw_value - deadzone) / (32767 - deadzone)) * 32767)
        else:
            return int(((raw_value + deadzone) / (32767 - deadzone)) * -32767)

def main():
    print("=========================================")
    print("   GameSir Cyclone 2 - Utilitário Linux  ")
    print("       Carregamento Dinâmico de Perfis   ")
    print("=========================================")
    
    device_path = '/dev/input/js0'
    if not os.path.exists(device_path):
        print(f"[X] Erro: {device_path} não encontrado. Conecte o controle.")
        sys.exit(1)
        
    controller = GameSirCyclone2()
    print("[*] Aguardando inputs do hardware... (Ctrl+C para sair)")
    print("-----------------------------------------")
    
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
                
                # Exemplo de uso do mapeamento dinâmico ao pressionar botões digitais
                if actual_type == 1 and value == 1:
                    btn_key = f"btn_{number}"
                    mapped_name = controller.mappings.get(btn_key, f"Desconhecido ({number})")
                    print(f"[AÇÃO MAPEADA] Botão Físico ID {number} -> Acionou Função: {mapped_name}")
                        
    except KeyboardInterrupt:
        print("\n[*] Monitoramento dinâmico finalizado.")
    except PermissionError:
        print("[X] Erro de permissão. Execute com 'sudo python3 gamesir-nexus.py'")

if __name__ == "__main__":
    main()
