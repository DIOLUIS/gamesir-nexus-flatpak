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

### Gatilhos Analógicos (L2 / R2)
- **Gatilho Esquerdo (L2)**: `Eixo ID 2` (Valores de -32767 a 32767) + `Botão ID 6` (Digital)
- **Gatilho Direito (R2)**: `Eixo ID 5` (Valores de -32767 a 32767) + `Botão ID 7` (Digital)

### Analógico Esquerdo
- **Eixo Horizontal (X)**: `Eixo ID 0` (Valores de -32767 a 32767)
- **Eixo Vertical (Y)**: `Eixo ID 1` (Valores de -32767 a 32767)

*Nota de Desenvolvimento*: O hardware demonstrou oscilação de resíduo físico de eixo (drift/centralização incorreta de até ~11%) ao retornar ao repouso no Linux, exigindo a implementação de tratamento de zona morta (deadzone) customizada via software dentro do nosso utilitário Flatpak para espelhar a precisão encontrada no Windows.
