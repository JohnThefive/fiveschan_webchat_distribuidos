import socket
import threading
import json
from db import Database
import os
from dotenv import load_dotenv # Para carregar variáveis de ambiente de um arquivo .env
load_dotenv()

# --- Configurações ( IP e portas configuráveis via .env) ---
IP = os.getenv("SERVER_IP", "127.0.0.1")  # IP do servidor configurável
CHAT_PORT = int(os.getenv("CHAT_PORT", 5566))  # Porta de chat configurável
INFO_PORT = int(os.getenv("INFO_PORT", 5567))  # Porta de informações configurável
ADDR_CHAT = (IP, CHAT_PORT)
ADDR_INFO = (IP, INFO_PORT)
FORMAT = "utf-8"
DISCONNECT_MSG = "!DESCONECTAR"
SIZE = 1024

# --- Inicialização ---
db = Database()
rooms = {}
rooms_lock = threading.Lock() #Lock é usado para garantir que apenas uma thread possa acessar o dicionário por vez

def broadcast(message, room_code, sender_conn, sender_name_override=None):
    # Garante acesso exclusivo ao dicionário 'rooms'
    with rooms_lock:
         # ... (lógica de verificação da sala) ...
        if room_code not in rooms:
            return
        
        # Determina o nome do remetente    
        sender_name = sender_name_override if sender_name_override is not None else rooms[room_code]["membros"].get(sender_conn, "Alguém")
        full_message = f"[{sender_name}] {message}"

          # Salva a mensagem no banco de dados
        try:
            db.add_message(message, sender_name, room_code)
        except Exception as e:
            print(f"[ERRO DB] Falha ao salvar mensagem de '{sender_name}': {e}")

        # Envia a mensagem para todos os membros da sala
        for conn in list(rooms[room_code]["membros"]):
            try:
                conn.send(full_message.encode(FORMAT))
            except Exception:
                print(f"Erro ao enviar para um cliente, será removido na desconexão.")

def pro_cliente(conn, addr):
    print(f"[NOVA CONEXÃO] {addr} conectado.")
    room_code = None
    name = None
    # ... (lógica de conexão) ...
    try:
        # Espera a requisição de entrada (JOIN:CODIGO_SALA:NOME)
        join_request = conn.recv(SIZE).decode(FORMAT)
        parts = join_request.split(":")
        
        if len(parts) >= 3 and parts[0] == "JOIN":
            room_code = parts[1].upper()
            name = parts[2]

            # Adiciona o cliente à sala (em memória)
            with rooms_lock:
                if room_code not in rooms:
                    rooms[room_code] = {"membros": {}}
                    print(f"[NOVA SALA] Sala {room_code} criada em memória por {name}.")
                    db.create_sala(room_code)
                rooms[room_code]["membros"][conn] = name

            # Envia o histórico de mensagens para o novo cliente
            try:
                history = db.get_messages_by_sala(room_code)
                for msg_tuple in history:
                    formatted_msg = f"[{msg_tuple[2]}] {msg_tuple[1]}"
                    conn.send((formatted_msg + "\n").encode(FORMAT))
                print(f"[HISTÓRICO] Enviado {len(history)} mensagens do DB para {name} na sala {room_code}.")
            except Exception as e:
                print(f"[ERRO DB] Falha ao buscar histórico para a sala {room_code}: {e}")
            
            # Notifica a sala que o novo membro entrou
            broadcast(f"entrou na sala.", room_code, conn)
            print(f"[{name}] entrou na sala [{room_code}]. Membros: {len(rooms[room_code]['membros'])}")
        else:
            print(f"[ERRO] Requisição de entrada inválida de {addr}. Desconectando.")
            conn.close()
            return
        
        # Loop principal de recebimento de mensagens
        conectado = True
        while conectado:
            msg = conn.recv(SIZE).decode(FORMAT)
            if not msg or msg == DISCONNECT_MSG:
                conectado = False
            else:
                broadcast(msg, room_code, conn)

     # ... (tratamento de erros de conexão) ...
    except (ConnectionResetError, BrokenPipeError):
        print(f"[AVISO] Conexão com {addr} foi fechada abruptamente pelo cliente.")
    except Exception as e:
        print(f"[ERRO] Erro inesperado com {addr}: {e}")
  
    finally:
        broadcast_leave_message = False

        # Lógica de limpeza (executa sempre, com erro ou não)  
        if room_code and name:
            with rooms_lock:
                if room_code in rooms and conn in rooms[room_code]["membros"]:
                    # Remove o cliente da sala
                    del rooms[room_code]["membros"][conn]
                    print(f"[{name}] saiu da sala [{room_code}].")
                    
                    broadcast_leave_message = True
                    
                    if not rooms[room_code]["membros"]:
                        del rooms[room_code]
                        print(f"[SALA VAZIA] Sala {room_code} removida da memória.")
            if broadcast_leave_message:
                broadcast(f"saiu da sala.", room_code, conn, sender_name_override=name)
        
        conn.close()
        print(f"[CONEXÃO FECHADA] {addr}.")

# --- Funções do Servidor de Informações e Main ---
def info_server_handler():
     # ... (cria e configura um socket na porta de informações) ...
    info_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    info_socket.bind(ADDR_INFO)
    info_socket.listen()
    print(f"[INFO SERVER] Escutando por requisições de salas em {IP}:{INFO_PORT}")

    while True:
        conn, addr = info_socket.accept()
        try:
            with rooms_lock:
                active_rooms_list = list(rooms.keys())
                data_to_send = json.dumps(active_rooms_list)
            conn.send(data_to_send.encode(FORMAT))
        except Exception as e:
            print(f"[INFO SERVER ERRO] {e}")
        finally:
            conn.close()

def main():
    print("[INICIANDO] Servidor de Chat está iniciando...")

     # Inicia o servidor de informações em uma thread separada
    info_thread = threading.Thread(target=info_server_handler, daemon=True)
    info_thread.start()

    # Cria e configura o servidor de chat principal
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR_CHAT)
    server.listen()
    print(f"[CHAT SERVER] Escutando em {IP}:{CHAT_PORT}")

    # Loop principal para aceitar novas conexões de chat
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=pro_cliente, args=(conn, addr))
        thread.start()
        # - 2 descontando as portas ativas (CHAT E PORT INFO)
        print(f"[CONEXÕES ATIVAS] {threading.active_count() - 2}")

if __name__ == "__main__":
    main()