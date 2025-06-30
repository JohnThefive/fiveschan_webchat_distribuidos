import socket
import threading
import json
from db import Database # NOVO: Importa a classe do banco de dados
import os
from dotenv import load_dotenv
load_dotenv()


# --- Configurações (sem alterações) ---
IP = "127.0.0.1"
CHAT_PORT = 5566
INFO_PORT = 5567
ADDR_CHAT = (IP, CHAT_PORT)
ADDR_INFO = (IP, INFO_PORT)
FORMAT = "utf-8"
DISCONNECT_MSG = "!DESCONECTAR"
SIZE = 1024

# --- Inicialização (sem alterações) ---
db = Database()
rooms = {}
rooms_lock = threading.Lock()

def broadcast(message, room_code, sender_conn, sender_name_override=None):
    with rooms_lock:
        if room_code not in rooms:
            return # Se a sala não existe mais, não faz nada
            
        sender_name = sender_name_override if sender_name_override is not None else rooms[room_code]["membros"].get(sender_conn, "Alguém")
        
        full_message = f"[{sender_name}] {message}"
        
        try:
            db.add_message(message, sender_name, room_code)
        except Exception as e:
            print(f"[ERRO DB] Falha ao salvar mensagem de '{sender_name}': {e}")

        for conn in list(rooms[room_code]["membros"]):
            try:
                conn.send(full_message.encode(FORMAT))
            except Exception:
                print(f"Erro ao enviar para um cliente, será removido na desconexão.")

def pro_cliente(conn, addr):
    print(f"[NOVA CONEXÃO] {addr} conectado.")
    room_code = None
    name = None
    try:
        join_request = conn.recv(SIZE).decode(FORMAT)
        parts = join_request.split(":")
        
        if len(parts) >= 3 and parts[0] == "JOIN":
            room_code = parts[1].upper()
            name = parts[2]
            
            with rooms_lock:
                if room_code not in rooms:
                    rooms[room_code] = {"membros": {}}
                    print(f"[NOVA SALA] Sala {room_code} criada em memória por {name}.")
                    db.create_sala(room_code)
                rooms[room_code]["membros"][conn] = name

            try:
                history = db.get_messages_by_sala(room_code)
                for msg_tuple in history:
                    formatted_msg = f"[{msg_tuple[2]}] {msg_tuple[1]}"
                    conn.send((formatted_msg + "\n").encode(FORMAT))
                print(f"[HISTÓRICO] Enviado {len(history)} mensagens do DB para {name} na sala {room_code}.")
            except Exception as e:
                print(f"[ERRO DB] Falha ao buscar histórico para a sala {room_code}: {e}")
            
            broadcast(f"entrou na sala.", room_code, conn)
            print(f"[{name}] entrou na sala [{room_code}]. Membros: {len(rooms[room_code]['membros'])}")
        else:
            print(f"[ERRO] Requisição de entrada inválida de {addr}. Desconectando.")
            conn.close()
            return

        conectado = True
        while conectado:
            msg = conn.recv(SIZE).decode(FORMAT)
            if not msg or msg == DISCONNECT_MSG:
                conectado = False
            else:
                broadcast(msg, room_code, conn)

    except (ConnectionResetError, BrokenPipeError):
        print(f"[AVISO] Conexão com {addr} foi fechada abruptamente pelo cliente.")
    except Exception as e:
        print(f"[ERRO] Erro inesperado com {addr}: {e}")
    finally:
        broadcast_leave_message = False
        if room_code and name:
            # CORREÇÃO: Verificamos se a sala ainda existe antes de tentar acessá-la
            with rooms_lock:
                if room_code in rooms and conn in rooms[room_code]["membros"]:
                    del rooms[room_code]["membros"][conn]
                    print(f"[{name}] saiu da sala [{room_code}].")
                    
                    broadcast_leave_message = True
                    
                    # Ele verifica se a lista de membros está vazia e, se estiver,
                    # remove a sala do dicionário em memória.
                    if not rooms[room_code]["membros"]:
                        del rooms[room_code]
                        print(f"[SALA VAZIA] Sala {room_code} removida da memória.")
            if broadcast_leave_message:
                broadcast(f"saiu da sala.", room_code, conn, sender_name_override=name)
        
        conn.close()
        print(f"[CONEXÃO FECHADA] {addr}.")

# --- Funções do Servidor de Informações e Main (sem alterações) ---
def info_server_handler():
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
    
    info_thread = threading.Thread(target=info_server_handler, daemon=True)
    info_thread.start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR_CHAT)
    server.listen()
    print(f"[CHAT SERVER] Escutando em {IP}:{CHAT_PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=pro_cliente, args=(conn, addr))
        thread.start()
        print(f"[CONEXÕES ATIVAS] {threading.active_count() - 2}")

if __name__ == "__main__":
    main()
