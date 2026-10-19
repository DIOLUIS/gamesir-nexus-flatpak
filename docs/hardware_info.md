# Informações de Hardware - GameSir Cyclone 2

## Perfil de Dispositivo (Conexão via Hub USB)
Quando conectado por cabo através de um Hub USB no Linux, o controle ativa a seguinte interface:

1. **Interface de Emulação de Jogo (DualShock 4)**
   - **VendorID:ProductID**: `054c:09cc`
   - **Função**: Emulação padrão de um controle Sony DualShock 4 (CUH-ZCT2x).

## Mapeamento de Inputs Validado (Joydev /dev/input/js0)

### Botões de Ação Principal
- **Botão A**: `ID 0`
- **Botão B**: `ID 1`
- **Botão Y**: `ID 2`
- **Botão X**: `ID 3`

### Bumpers Superiores
- **Botão L1**: `ID 4`
- **Botão R1**: `ID 5`

### Gatilhos Analógicos (L2 / R2)
- **Gatilho Esquerdo (L2)**: `Eixo ID 2` (Valores de -32767 a 32767) + `Botão ID 6` (Digital)
- **Gatilho Direito (R2)**: `Eixo ID 5` (Valores de -32767 a 32767) + `Botão ID 7` (Digital)

### Botões de Sistema e Cliques
- **Botão Select (Share)**: `ID 8`
- **Botão Start (Options)**: `ID 9`
- **Botão L3 (Clique Analógico Esq.)**: `ID 10`
- **Botão R3 (Clique Analógico Dir.)**: `ID 11`
- **Botão Home / M (Central)**: `ID 12`

### Analógicos
- **Analógico Esquerdo (X/Y)**: `Eixo ID 0` e `Eixo ID 1` (Valores de -32767 a 32767)
- **Analógico Direito (X/Y)**: `Eixo ID 3` e `Eixo ID 4` (Valores de -32767 a 32767)

### D-Pad (Direcional)
- **Eixo Horizontal (Esquerda/Direita)**: `Eixo ID 6`
- **Eixo Vertical (Cima/Baixo)**: `Eixo ID 7`

*Nota de Desenvolvimento*: O hardware demonstrou oscilação de resíduo físico de eixo (drift/centralização incorreta de até ~11%) ao retornar ao repouso no Linux, exigindo a implementação de tratamento de zona morta (deadzone) customizada via software dentro do nosso utilitário Flatpak para espelhar a precisão encontrada no Windows.

## Atualização de Concorrência (PySide6)
- **QSignals e @Slot**: Implementados para isolar a thread de leitura do `/dev/input/js*` da thread principal da interface gráfica.
- **Deadzone Fix**: Correção na sintaxe do cálculo matemático de compensação de drift em analógicos com Efeito Hall.

## Solução Definitiva de Concorrência (Game Loop a 60 FPS)
- **QTimer e Polling**: A arquitetura assíncrona baseada em eventos diretos sobrecarregava o motor C++ do PySide6 (Shiboken) devido à altíssima frequência dos sensores de Efeito Hall, gerando o erro fatal `none_dealloc`. A solução final adota um modelo de Game Loop com Polling a 60 FPS (16ms) via `QTimer`.
- **Esvaziamento de Buffer Otimizado**: O arquivo de hardware em `/dev/input/js*` é lido em modo não-bloqueante e a fila de eventos acumulados no kernel é esvaziada inteiramente a cada frame. A interface gráfica é notificada e renderizada apenas uma vez por ciclo, garantindo 100% de estabilidade visual na leitura dos botões e barras analógicas[cite: 1].
