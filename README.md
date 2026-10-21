# 🎮 GameSir Connect - Linux Edition (v0.9.5 Beta)

Software open-source para configuração, telemetria e gestão de comandos **GameSir** (focado no **GameSir Cyclone 2**) em sistemas Linux.

Desenvolvido por **Diotec Software (Dionísio Luís)**.

---

## ✨ Funcionalidades Principais

* **Telemetria em Tempo Real:** Monitorização dos analógicos (L3/R3) com ajuste de Zona Morta (*Deadzone*) e leitura analógica dos gatilhos (LT/RT).
* **Controlo de Vibração:** Ajuste independente dos motores pesado (esquerdo) e leve (direito) com botão de teste em tempo real.
* **Botões Traseiros (M1/M2):** Modo de captura rápida (*learning*) e indicador luminoso na interface.
* **Iluminação RGB (LED Central):** Aplicação de cores sólidas diretamente no hardware via comunicação USB HID.
* **Hot-Plug Automático:** Reconhecimento instantâneo ao ligar ou desligar o cabo USB sem fechar a aplicação.
* **Perfis Persistentes:** Gravação automática em JSON dentro do diretório de configuração do utilizador.

---

## 🚀 Como Compilar e Instalar (Flatpak)

### 1. Instalar o SDK do KDE 6.6
No terminal, execute:
    flatpak install flathub org.kde.Platform//6.6 org.kde.Sdk//6.6

### 2. Compilar e Instalar no Utilizador
Na pasta do projeto (contendo `gamesir-nexus.py`, `com.github.dioluis.gamesir-nexus.yaml`, `com.github.dioluis.gamesir-nexus.desktop`, `logo.jpeg` e `chave.png`), execute:
    flatpak-builder --user --install --force-clean build-dir com.github.dioluis.gamesir-nexus.yaml

### 3. Executar a Aplicação
Procure por **GameSir Connect** no menu de aplicações do seu sistema ou execute no terminal:
    flatpak run com.github.dioluis.gamesir-nexus

---

## 📦 Gerar Instalador Único (.flatpak)

Para criar um ficheiro único distribuível:
    flatpak build-export repo build-dir
    flatpak build-bundle repo gamesir-nexus-v0.9.5-beta.flatpak com.github.dioluis.gamesir-nexus

---

## 🤝 Compatibilidade e Feedback

Atualmente validado no **GameSir Cyclone 2**. Testou noutro modelo da GameSir ou encontrou algum bug?
Envie o seu relato para: **diotec.soft@gmail.com**

## ☕ Apoie o Projeto

Este projeto é open-source. Se lhe foi útil, apoie o desenvolvimento contínuo via **PIX (Santander)**:
* **Chave PIX:** `a6e35576-02ec-4f43-a243-3e65ee8e9c3d`
