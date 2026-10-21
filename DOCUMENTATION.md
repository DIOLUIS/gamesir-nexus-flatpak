# GameSir Nexus - Linux Edition (Documentação Técnica)
**Versão:** 0.9.5 Beta
**Desenvolvedor:** Diotec Software (Dionísio Luís)

## 1. Visão Geral da Arquitetura
Aplicação de Engenharia Reversa desenvolvida em Python 3 + PySide6 (Qt6) para controlo, telemetria e gestão de comandos GameSir (otimizado para o modelo Cyclone 2) em sistemas Linux, empacotada de forma isolada via Flatpak sobre o runtime KDE 6.6.

## 2. Descobertas de Engenharia Reversa e Hardware
- **Telemetria de Baixo Nível (`/dev/input/js*`):** Leitura direta em binário (`struct.unpack('IhBB')`) sem bloqueio (`os.set_blocking(..., False)`), permitindo monitorização a 60Hz (16ms) dos analógicos L3/R3 (com cálculo de Deadzone) e gatilhos analógicos LT/RT.
- **Motor Hot-Plug Resiliente:** Tratamento explícito de `BlockingIOError` (repouso) vs `b''` / `OSError` (desconexão física do cabo USB), evitando falhas de desalocação de memória (`none_dealloc`) no ciclo de eventos do Qt6.
- **Vibração Tática (`evdev`):** Injeção de efeitos `FF_RUMBLE` assíncronos para controlo individual dos motores pesado (esquerdo) e leve (direito).
- **Captura das Pás Traseiras (M1 / M2):** Reconhecimento híbrido tanto dos IDs nativos (14 e 15) como do espelhamento de botões via hardware, contornando a limitação do driver XInput padrão no Linux.
- **Injeção de Cores no LED Central (Broadcast HID):** Descoberta do relatório de 64 bytes com prefixo `0x05` (`0x05, 0x02/0x03, 0x04, 0x00, Weak, Strong, R, G, B...`). O software faz broadcast para todos os nós `/dev/hidraw*` associados ao comando para contornar as múltiplas interfaces virtuais criadas pelo firmware.

## 3. Especificações do Empacotamento Flatpak
- **Runtime / SDK:** `org.kde.Platform//6.6` e `org.kde.Sdk//6.6`
- **Dependências Python (`python-deps`):** Instalação isolada em `/app` via `pip install --prefix=/app PySide6 evdev` com permissão de rede restrita apenas à fase de compilação (`--share=network`).
- **Permissões de Execução (`finish-args`):**
  - `--socket=x11`, `--socket=wayland`, `--socket=fallback-x11`
  - `--env=QT_QPA_PLATFORM=wayland;xcb` (Garante compatibilidade total com janelas Frameless e posicionamento manual da janela)
  - `--device=dri` e `--device=all` (Acesso direto a aceleração gráfica e portas `/dev/input/*` e `/dev/hidraw*`)

## 4. Contacto e Apoio
- **Relatórios de Compatibilidade e Bugs:** diotec.soft@gmail.com
- **Apoio ao Projeto (PIX Santander):** a6e35576-02ec-4f43-a243-3e65ee8e9c3d
