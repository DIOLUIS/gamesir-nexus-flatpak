# Documentação Oficial: GameSir Nexus (Painel de Controlo Avançado para Linux)

## 1. Visão Geral do Projeto
O **GameSir Nexus** é uma aplicação de desktop desenvolvida em **Python** com interface gráfica em **PySide6**, projetada especificamente para operar no **Ubuntu** sob o ecossistema **Flatpak**. O seu principal objetivo é equiparar e superar as funcionalidades do software proprietário de Windows para o comando **GameSir Cyclone 2**, oferecendo telemetria em tempo real, ajuste avançado de zonas mortas, testes de vibração via Force Feedback, controlo de iluminação e gestão de perfis de hardware.

## 2. Arquitetura e Tecnologias
- **Linguagem:** Python 3.11
- **Interface Gráfica:** PySide6 (Qt6) com tema escuro personalizado, suporte a diálogos nativos (`QColorDialog`) e seletores dinâmicos de botões.
- **Empacotamento:** Flatpak para isolamento e portabilidade robusta em distribuições Linux.
- **Camada de Hardware:** 
  - Subsistema de joysticks do kernel (`/dev/input/js*`).
  - Subsistema de eventos e Force Feedback (`evdev`).
  - Comunicação de baixo nível de relatórios USB (`hidraw`).

## 3. Módulos e Funcionalidades Principais
### 3.1. Diagnóstico e Telemetria de Eixos
- Leitura contínua e assíncrona dos eixos dos analógicos com atualização a 60Hz (16ms).
- Barras de progresso dinâmicas integradas para visualização imediata da resposta dos manípulos esquerdo e direito.

### 3.2. Motor Matemático de Zonas Mortas (*Deadzones*)
- Algoritmo de filtragem que remove ruídos mecânicos e desvios de centro dos analógicos com base em limiares configuráveis pelo utilizador.

### 3.3. Gestão e Persistência de Perfis (JSON)
- Sistema de gravação e leitura automática de configurações no diretório de dados locais do Flatpak (`~/.var/app/com.github.dioluis.gamesir-nexus/config/profile_default.json`).
- Suporta persistência de zonas mortas, preferências de iluminação personalizada e tabela de remapeamento lógico dos botões traseiros.

### 3.4. Vibração Dinâmica (*Force Feedback*)
- Integração direta com o módulo `evdev.ff` do kernel Linux com encapsulamento de `ff.EffectType(ff_rumble_effect=...)` para execução de testes nos motores de vibração do comando.

### 3.5. Controlo de Iluminação RGB por Software
- Módulo integrado com seletor visual de cores (`QColor` / `QColorDialog`) e atalhos rápidos de palete.
- Envio seguro de pacotes estruturados via descritores `hidraw` sem interrupções ou micro-reinícios no barramento USB.

### 3.6. Mapeamento e Telemetria dos Botões Traseiros (M1 / M2)
- Validação do comportamento das pás traseiras: espelhamento direto no microcontrolador via memória flash interna.
- Monitorização em tempo real do estado de pressão (`PRESSIONADO` / `SOLTO`) com indicadores gráficos responsivos na aba Mapeamento.
- Seletores visuais para atribuição lógica e documentação das pás dentro de cada perfil.
