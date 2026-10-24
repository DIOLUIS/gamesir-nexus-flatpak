# 🎮 GameSir Connect - Linux Edition

**Desenvolvido por:** Diotec Software (Dionísio Luís)  
**Versão:** 0.9.6 Beta  
**Compatibilidade Atual:** GameSir Cyclone 2  

Uma ferramenta nativa de diagnóstico e configuração para comandos GameSir no Linux. Desenvolvido através de engenharia reversa do protocolo USB/Dongle proprietário da GameSir, este software permite controlar as luzes, testar motores de vibração e visualizar telemetria de hardware em tempo real, sem depender de aplicações Windows ou máquinas virtuais.

---

## ✨ Funcionalidades

* **📡 Telemetria em Tempo Real:** Visualizador preciso da pressão dos gatilhos (LT/RT) e posição dos analógicos (L3/R3).
* **🎯 Testador de Botões:** Feedback visual instantâneo dos botões faciais (ABXY) e *bumpers* (L1/R1).
* **💡 Controlo de LEDs (RGB):** Ajuste de Modos (Fluxo, Arco-íris, Pulso, etc.), Brilho, Velocidade e aplicação de Cor Sólida personalizada.
* **📳 Controlo Hápico:** Teste isolado e ajuste de intensidade dos motores de vibração (Pesado/Esquerdo e Leve/Direito).
* **⚡ Mapeamento via Software:**
  * **Modo Gatilho Ultrasensível:** Anula a zona morta do gatilho para resposta imediata (100% ao mínimo toque).
  * **Layout Switch:** Inversão lógica dos botões A/B e X/Y via software.
* **🔌 Suporte Hot-Plug:** A aplicação deteta automaticamente a ligação/desligação do comando sem crashar.

*(Nota: O mapeamento de hardware para as pás traseiras M1/M2 e gravação na EEPROM está atualmente trancado pelo protocolo proprietário via ioctl e aguarda desenvolvimento futuro. Por favor, use os atalhos físicos do comando para mapear o M1 e M2).*

---

## 🛠️ Instalação e Permissões (Muito Importante)

No Linux, aplicações comuns (e Flatpaks) não têm permissão para ler hardware bruto por motivos de segurança. Para o **GameSir Connect** conseguir comunicar com o comando sem precisares da palavra-passe de Administrador (sudo), **tens de adicionar uma regra udev ao teu sistema operativo.**

Abra o teu terminal e executa este comando (apenas uma vez):

    echo 'KERNEL=="hidraw*", SUBSYSTEM=="hidraw", MODE="0666"' | sudo tee /etc/udev/rules.d/99-gamesir-nexus.rules
    sudo udevadm control --reload-rules
    sudo udevadm trigger

### Compilar e Instalar via Flatpak
Garante que tens o flatpak-builder instalado no teu sistema. Na pasta do projeto, executa:

    flatpak-builder --user --install --force-clean build-dir io.github.dioluis.gamesir_nexus.yaml

Após a instalação, podes iniciar a aplicação através do menu das tuas aplicações ou via terminal com:

    flatpak run io.github.dioluis.gamesir_nexus

---

## 🤝 Apoia o Projeto

O desenvolvimento deste software envolveu inúmeras horas de engenharia reversa de pacotes USB (Wireshark) e testes de baixo nível em Linux. Se este software te foi útil, considera apoiar o desenvolvimento contínuo:

**Chave PIX:** a6e35576-02ec-4f43-a243-3e65ee8e9c3d

**Contacto para bugs ou feedback:** diotec.soft@gmail.com
