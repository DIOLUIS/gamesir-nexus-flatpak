#!/usr/bin/env python3
import os
import struct
import sys

class GameSirCyclone2:
    def __init__(self):
        # Limiares de Zona Morta calculados com base no hardware real
        self.DEADZONE_X = 4000  # Cobre os desvios de ~3800 observados no Eixo X
        self.DEADZONE_Y = 2000  # Cobre os desvios de ~1500 observados no Eixo Y

    def apply_deadzone(self, raw_value, deadzone):
        """Filtra as oscilações e estabiliza o analógico no centro (zero)"""
        if abs(raw_value) < deadzone:
            return 0
        # Normalização para garantir aceleração suave fora da zona morta
        if raw_value > 0:
            return int(((raw_value - deadzone) / (32767 - deadzone)) * 32767)
        else:
            return int(((raw_value + deadzone) / (32767 - deadzone)) * -32767)

def main():
    print("=========================================")
    print("   GameSir Cyclone 2 - Utilitário Linux  ")
    print("      Teste de Filtragem de Deadzone     ")
    print("=========================================")
    
    device_path = '/dev/input/js0'
    if not os.path.exists(device_path):
        print(f"[X] Erro: {device_path} não encontrado. Conecte o controle.")
        sys.exit(1)
        
    controller = GameSirCyclone2()
    print("[*] Motor de calibração pronto. Movimente o Analógico Esquerdo...")
    print("[*] Pressione Ctrl+C para encerrar o teste.")
    print("-----------------------------------------")
    
    # Estrutura Joydev do Linux
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
                
                # Monitora apenas os eixos do Analógico Esquerdo (0 e 1)
                if actual_type == 2 and number in (0, 1):
                    if number == 0:
                        filtered = controller.apply_deadzone(value, controller.DEADZONE_X)
                        print(f"[EIXO X] Bruto: {value:6d} -> Filtrado (Com Deadzone): {filtered:6d}")
                    elif number == 1:
                        filtered = controller.apply_deadzone(value, controller.DEADZONE_Y)
                        print(f"[EIXO Y] Bruto: {value:6d} -> Filtrado (Com Deadzone): {filtered:6d}")
                        
    except KeyboardInterrupt:
        print("\n[*] Teste de leitura contínua finalizado.")
    except PermissionError:
        print("[X] Erro de permissão. Execute com 'sudo python3 gamesir-nexus.py'")

if __name__ == "__main__":
    main()
