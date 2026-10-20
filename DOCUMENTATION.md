# Documentação Oficial: GameSir Nexus (Painel de Controlo Avançado para Linux)

## 1. Visão Geral do Projeto
O **GameSir Nexus** é uma aplicação de desktop desenvolvida em **Python** com interface gráfica em **PySide6**, projetada para operar no ecossistema **Flatpak** em distribuições Linux (como o Ubuntu). O objetivo é fornecer suporte avançado e de baixo nível para o comando **GameSir Cyclone 2**, equiparando e superando recursos do software proprietário de Windows.

## 2. Arquitetura e Tecnologias
- **Linguagem & Runtime:** Python 3.11 sob ambiente Flatpak.
- **Interface Gráfica:** PySide6 (Qt6) em tema escuro nativo com `QColorDialog`, seletores dinâmicos e monitores em tempo real.
- **Camada de Hardware & Kernels:**
  - Subsistema clássico de joystick do kernel (`/dev/input/js*`).
  - Subsistema de eventos e Force Feedback (`evdev.ff`).
  - Comunicação direta USB/HID via descritores `hidraw` (`Output Report 0x05`).

## 3. Módulos e Funcionalidades Consolidadas

### 3.1. Telemetria e Diagnóstico de Eixos
- Polling assíncrono a 60Hz (16ms) dos 4 eixos analógicos principais (Analógico Esquerdo X/Y e Analógico Direito X/Y).
- Visualização instantânea em barras de progresso responsivas com filtragem de zonas mortas matemáticas.

### 3.2. Vibração Híbrida (Force Feedback & Direct HID)
- Disparo primário via `evdev.ff` com união tipada estrita `ff.EffectType(ff_rumble_effect=...)`.
- Fall-back simultâneo via pacotes de Output Report USB (`0x05`) direto no endpoint `hidraw`, garantindo retorno tátil em qualquer perfil de driver.

### 3.3. Controlo de Iluminação RGB
- Seletor de cores nativo com atalhos predefinidos e feedback de luminância visual.
- Escrita direta e segura no nó `/dev/hidraw5` sem provocar desconexões (`Errno 19`) no barramento USB.

### 3.4. Captura Dinâmica e Mapeamento dos Botões Traseiros (M1 / M2)
- **Modo de Aprendizagem Interativa:** Botões dedicados na interface que aguardam o acionamento físico das pás M1 e M2 e capturam automaticamente o evento emitido pelo firmware.
- **Monitor Global de Eventos:** Indicador em tempo real do último botão e código de evento recebido, filtrando eventos sintéticos do kernel (`JS_EVENT_INIT = 0x80`).
- **Feedback Visual Instantâneo:** Labels responsivos que sinalizam os estados `PRESSIONADO` e `SOLTO` de cada pá com base no ID lógico mapeado.

### 3.5. Persistência de Perfis (JSON)
- Armazenamento modular de deadzones, preferências de iluminação RGB e tabela de mapeamento de botões no caminho padrão do sandbox:
  `~/.var/app/com.github.dioluis.gamesir-nexus/config/profile_default.json`
