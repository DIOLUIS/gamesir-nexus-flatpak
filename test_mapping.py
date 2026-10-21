#!/usr/bin/env python3
import os
import struct
import sys

def main():
    print("==================================================")
    print("   GameSir Cyclone 2 - Teste de Mapeamento Nativo ")
    print("==================================================")
    print("[*] Procurando por dispositivos de entrada de jogos...")
    
    base_dir = '/dev/input/'
    joysticks = [os.path.join(base_dir, f) for f in os.listdir(base_dir) if f.startswith('js')]
    
    if not joysticks:
        print("[X] Nenhum controle encontrado em /dev/input/jsX.")
        print("[*] Certifique-se de que o controle está conectado e funcional.")
        sys.exit(1)
        
    # Seleciona o primeiro joystick encontrado (geralmente js0)
    device_path = joysticks[0]
    print(f"[O] Dispositivo detectado: {device_path}")
    print("[*] Pressione os botões do controle para ver o mapeamento do Linux.")
    print("[*] Pressione Ctrl+C para encerrar o teste.")
    print("--------------------------------------------------")
    
    # Estrutura do evento Joydev do Linux:
    # time (4 bytes), value (2 bytes), type (1 byte), number (1 byte)
    fn_format = 'IhBB'
    event_size = struct.calcsize(fn_format)
    
    try:
        with open(device_path, 'rb') as fd:
            while True:
                event = fd.read(event_size)
                if not event:
                    break
                
                time, value, ev_type, number = struct.unpack(fn_format, event)
                
                # Desconsidera a inicialização do driver (bit 0x80)
                actual_type = ev_type & ~0x80
                
                if actual_type == 1: # Tipo 1 = Botão
                    status = "Pressionado" if value else "Solto"
                    print(f"[BOTÃO] Número ID: {number:3d} -> Status: {status}")
                elif actual_type == 2: # Tipo 2 = Eixo (Analógicos e Gatilhos)
                    print(f"[EIXO]  Número ID: {number:3d} -> Posição/Valor: {value:6d}")
                    
    except KeyboardInterrupt:
        print("\n[*] Teste encerrado pelo desenvolvedor.")
    except PermissionError:
        print("[X] Erro de permissão. Tente rodar o script com 'sudo python3 test_mapping.py'")

if __name__ == "__main__":
    main()
