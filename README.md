# 🚀 Fiveschan Webchat - Instruções de Execução

Este repositório contém o código-fonte de um sistema de chat. Abaixo você encontrará todas as instruções necessárias para clonar, configurar e executar a aplicação localmente.

---

## 📥 Clonando o Repositório

Clone este repositório ou baixe o código-fonte manualmente:

```bash
git clone git@github.com:JohnThefive/fiveschan_webchat_distribuidos.git
cd fiveschan_webchat_distribuidos.git
```
---

## 🐍 Ambiente Virtual (venv)

**É altamente recomendado** criar um ambiente virtual para evitar conflitos entre bibliotecas.

### Criar o ambiente virtual:

```bash
python3 -m venv projeto
```

### Ativar o ambiente virtual:

- **macOS / Linux**:

```bash
source projeto/bin/activate
```

- **Windows**:

```bash
projeto\Scripts\activate
```

> **Observação:** todos os comandos a seguir devem ser executados com o ambiente virtual ativado.

---

## 📦 Instalação de Dependências

Com o ambiente virtual ativo, instale todas as dependências necessárias:

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuração do Ambiente

Crie um arquivo chamado `.env` na raiz do projeto com o seguinte conteúdo:

```
SERVER_IP=127.0.0.1
CHAT_PORT= podem ser alteradas de acordo com sua disponibilidade
INFO_PORT= igualmente
SECRET_KEY= segredo necessário
```

> Substitua os valores conforme necessário para seu ambiente local.

---

## ▶️ Executando a Aplicação

### 1. Inicie os servidores:

```bash
python start_servers.py
```

Este comando iniciará simultaneamente os dois servidores.

### 2. Execute o gateway web:

Em um novo terminal (com o ambiente virtual ainda ativado), execute:

```bash
python web_gateway.py
```

---

## ✅ Pronto!

Se tudo estiver corretamente configurado, a aplicação estará rodando localmente! 🎉

---

## 🛠️ Dúvidas ou Problemas?

Em caso de dúvidas, verifique os arquivos de logs de erro ou entre em contato com nossa equipe 
 
 ```bash
 Atensiosamente,
 Karol, João e Let
```