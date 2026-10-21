#!/usr/bin/env python3
import sys
from evdev import InputDevice, list_devices, ecodes

devices = [InputDevice(path) for path in list_devices()]
target = None
for dev in devices:
    if 'controller' in dev.name.lower() or 'gamesir' in dev.name.lower() or 'pad' in dev.name.lower():
        target = dev
        break

if not target:
    print("[ERRO] Nenhum comando detetado pelo evdev. Verifique as permissões ou se o dispositivo está conectado.")
    sys.exit(1)

print(f"[*] A escutar eventos de: {target.name} ({target.path})")
print("[*] Prima os botões traseiros (M1 e M2). Pressione Ctrl+C para sair.\n")

try:
    for event in target.read_loop():
        if event.type == ecodes.EV_KEY:
            key_name = ecodes.bytype[ecodes.EV_KEY].get(event.code, f"CODE_{event.code}")
            state = "PRESSIONADO" if event.value == 1 else ("SOLTO" if event.value == 0 else "REPETIDO")
            print(f"-> Botão: {key_name} | Código Bruto: {event.code} | Estado: {state}")
except KeyboardInterrupt:
    print("\n[+] Captura terminada.")
