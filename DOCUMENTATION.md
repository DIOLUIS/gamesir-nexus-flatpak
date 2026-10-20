# Documentação Oficial: GameSir Nexus (Painel de Controlo Avançado para Linux)

## 1. Visão Geral do Projeto
O **GameSir Nexus** é uma aplicação de desktop desenvolvida em **Python** com interface gráfica em **PySide6**, projetada para operar no ecossistema **Flatpak** no Ubuntu. O objetivo é fornecer suporte avançado e de baixo nível para o comando **GameSir Cyclone 2**, equiparando recursos do software proprietário de Windows.

## 2. Arquitetura e Tecnologias
- **Linguagem & Runtime:** Python 3.11 sob ambiente Flatpak.
- **Camada de Hardware & Kernels:**
  - Subsistema clássico de joystick (`/dev/input/js*`).
  - Subsistema de eventos e Force Feedback (`evdev.ff`).
  - Comunicação direta USB/HID via descritores `hidraw`.

## 3. Módulos e Funcionalidades Consolidadas

### 3.1. Telemetria Completa (6 Eixos)
- Monitorização a 60Hz dos analógicos (Esq X/Y, Dir X/Y) e Gatilhos Traseiros Analógicos (L2 e R2 de 0 a 100%).
- Filtragem matemática de zonas mortas configurável.

### 3.2. Vibração Híbrida Independente
- Controlo granular (0-100%) de intensidade separado para o Motor Forte (Esquerdo) e Motor Fraco (Direito).
- Disparo primário via `evdev.ff` e fall-back via pacote HID (Output Report `0x05`).

### 3.3. Controlo de Iluminação RGB
- Seletor de cores nativo com atalhos predefinidos e escrita direta no endpoint `hidraw` sem desconexões no barramento.

### 3.4. Captura Dinâmica M1 / M2 e Funcionalidades Globais
- **Modo de Aprendizagem Interativa:** Captura de botões on-the-fly para M1 e M2.
- **Swaps Globais:** Suporte em software para troca de layout (A/B X/Y) e modo "Hair Trigger" (gatilho rápido digital).

### 3.5. Persistência de Perfis (JSON)
- Armazenamento centralizado em `~/.var/app/com.github.dioluis.gamesir-nexus/config/profile_default.json`.
