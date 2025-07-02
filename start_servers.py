import subprocess
import os

def iniciar_servidores():
    try:
        # Caminho do Python dentro da venv
        python_executable = os.path.join(".venv", "bin", "python")

        # Iniciar o servidor principal
        subprocess.Popen(
            [python_executable, "server.py"],
            env={**os.environ, "IP": "127.0.0.1", "CHAT_PORT": "5566", "INFO_PORT": "5567"}
        )

        # Iniciar o servidor secundário
        subprocess.Popen(
            [python_executable, "server.py"],
            env={**os.environ, "IP": "127.0.0.1", "CHAT_PORT": "5576", "INFO_PORT": "5577"}
        )

        print("Servidores iniciados com sucesso.")
    except Exception as e:
        print(f"Erro ao iniciar os servidores: {e}")

if __name__ == "__main__":
    iniciar_servidores()