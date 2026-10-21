#!/usr/bin/env python3
import struct, os, sys, glob

paths = sorted(glob.glob('/dev/input/js*'))
if not paths:
    print("[ERRO] Nenhum joystick encontrado em /dev/input/js*")
    sys.exit(1)

dev_path = paths[0]
print(f"[*] A escutar: {dev_path}")
print("[*] Prima M1 e M2 (ou outros botões). Ctrl+C para sair.\n")

EVENT_FORMAT = 'IhBB'
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

with open(dev_path, 'rb') as f:
    try:
        while True:
            data = f.read(EVENT_SIZE)
            if not data or len(data) < EVENT_SIZE:
                break
            time_val, value, ev_type, number = struct.unpack(EVENT_FORMAT, data)
            actual_type = ev_type & ~0x80
            
            # Tipo 1 = Botão (0 = Solto, 1 = Pressionado)
            if actual_type == 1:
                state = "PRESSIONADO" if value == 1 else "SOLTO"
                print(f"-> Botão ID: {number} | Estado: {state} | RawType: {ev_type}")
    except KeyboardInterrupt:
        print("\n[+] Captura terminada.")
