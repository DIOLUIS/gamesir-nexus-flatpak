#!/usr/bin/env python3
import sys

def main():
    print("=========================================")
    print("   GameSir Cyclone 2 - Utilitário Linux  ")
    print("=========================================")
    
    # IDs de hardware consolidados no mapeamento
    VENDOR_ID = 0x054c  # Sony Corp.
    PRODUCT_ID = 0x09cc # DualShock 4 [CUH-ZCT2x]
    
    print(f"[*] Buscando controle GameSir Cyclone 2 (ID {VENDOR_ID:04x}:{PRODUCT_ID:04x})...")
    
    try:
        import usb.core
        import usb.util
    except ImportError:
        print("[!] Erro: Biblioteca PyUSB não encontrada no sistema host.")
        print("[*] Nota: Isso é normal no host. O Flatpak conterá essa dependência de forma isolada.")
        sys.exit(0)
        
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    
    if dev is None:
        print("[X] Controle não encontrado. Certifique-se de que está conectado ao Hub USB.")
    else:
        print("[[O] Controle localizado com sucesso no barramento USB!")
        print(f" -> Dispositivo: {dev.product} (Fabricante: {dev.manufacturer})")

if __name__ == "__main__":
    main()
