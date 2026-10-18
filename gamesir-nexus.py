#!/usr/bin/env python3
import os
import struct
import sys

class GameSirCyclone2:
    def __init__(self):
        # Limiares de Zona Morta para os Analógicos (Esquerdo e Direito)
        self.DEADZONE_L_X = 4000
        self.DEADZONE_L_Y = 2000
        self.DEADZONE_R_X = 3000  # Margem inicial para o Analógico Direito
        self.DEADZONE_R_Y = 3000

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
    print("      Monitoramento Completo de Eixos    ")
    print("=========================================")
    
    device_path = '/dev/input/js0'
    if not os.path.exists(device_path):
        print(f"[X] Erro: {device_path} não encontrado. Conecte o controle.")
        sys.exit(1)
        
    controller = GameSirCyclone2()
    print("[*] Motor completo pronto. Movimente os Analógicos ou o D-Pad...")
    print("[*] Pressione Ctrl+C para encerrar o teste.")
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
                
                if actual_type == 2: # Tipo Eixo
                    # Analógico Esquerdo
                    if number == 0:
                        f = controller.apply_deadzone(value, controller.DEADZONE_L_X)
                        print(f"[ANALOG. ESQ X] Bruto: {value:6d} -> Filtrado: {f:6d}")
                    elif number == 1:
                        f = controller.apply_deadzone(value, controller.DEADZONE_L_Y)
                        print(f"[ANALOG. ESQ Y] Bruto: {value:6d} -> Filtrado: {f:6d}")
                    
                    # Analógico Direito
                    elif number == 3:
                        f = controller.apply_deadzone(value, controller.DEADZONE_R_X)
                        print(f"[ANALOG. DIR X] Bruto: {value:6d} -> Filtrado: {f:6d}")
                    elif number == 4:
                        f = controller.apply_deadzone(value, controller.DEADZONE_R_Y)
                        print(f"[ANALOG. DIR Y] Bruto: {value:6d} -> Filtrado: {f:6d}")
                    
                    # D-Pad (Direcional)
                    elif number == 6:
                        dir_str = "Direita" if value > 0 else ("Esquerda" if value < 0 else "Solto")
                        print(f"[D-PAD HORIZ.] Valor: {value:6d} -> Direção: {dir_str}")
                    elif number == 7:
                        dir_str = "Baixo" if value > 0 else ("Cima" if value < 0 else "Solto")
                        print(f"[D-PAD VERT. ] Valor: {value:6d} -> Direção: {dir_str}")
                        
    except KeyboardInterrupt:
        print("\n[*] Monitoramento finalizado.")
    except PermissionError:
        print("[X] Erro de permissão. Execute com 'sudo python3 gamesir-nexus.py'")

if __name__ == "__main__":
    main()
