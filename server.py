import socket
import threading
import json 

# --- Configurações ---
IP = "127.0.0.1"
CHAT_PORT = 5566 # Porta principal do chat
INFO_PORT = 5567 # NOVA porta para informações
ADDR_CHAT = (IP, CHAT_PORT)
ADDR_INFO = (IP, INFO_PORT)
FORMAT = "utf-8"
DISCONNECT_MSG = "!DESCONECTAR"
SIZE = 1024

# --- Estrutura de Dados ---
# Modificado para incluir o nome da sala
# Estrutura: {"CODIGO_DA_SALA": {"name": "Nome da Sala", "membros": {conn: nome}, "mensagens": []}}
rooms = {}
rooms_lock = threading.Lock()

# --- Funções do Chat (broadcast e pro_cliente) ---

def broadcast(message, room_code, sender_conn):
    with rooms_lock:
        if room_code in rooms:
            sender_name = rooms[room_code]["membros"].get(sender_conn, "Alguém")
            full_message = f"[{sender_name}] {message}"
            rooms[room_code]["mensagens"].append(full_message)

            for conn in list(rooms[room_code]["membros"]):
                if conn != sender_conn:
                    try:
                        conn.send(full_message.encode(FORMAT))
                    except Exception:
                        del rooms[room_code]["membros"][conn]

def pro_cliente(conn, addr):
    print(f"[NOVA CONEXÃO DE CHAT] {addr} conectado.")
    room_code = None
    name = None
    try:
        # Modificado para aceitar o nome da sala na criação. Formato: "JOIN:CODIGO:NOME_USER:NOME_SALA"
        join_request = conn.recv(SIZE).decode(FORMAT)
        parts = join_request.split(":", 3) # Divide no máximo 3 vezes

        if len(parts) >= 3 and parts[0] == "JOIN":
            room_code = parts[1]
            name = parts[2]
            # O nome da sala é opcional, enviado apenas na criação
            room_name_on_create = parts[3] if len(parts) > 3 else room_code

            with rooms_lock:
                if room_code not in rooms:
                    rooms[room_code] = {"name": room_name_on_create, "membros": {}, "mensagens": []}
                    print(f"[NOVA SALA] Sala '{room_name_on_create}' ({room_code}) criada por {name}.")
                
                rooms[room_code]["membros"][conn] = name

            with rooms_lock:
                history = rooms[room_code]["mensagens"]
                for msg in history:
                    conn.send(msg.encode(FORMAT))
            
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

    except Exception as e:
        print(f"[ERRO] Erro com {addr}: {e}")
    finally:
        if room_code and name and room_code in rooms:
            with rooms_lock:
                if conn in rooms[room_code]["membros"]:
                    del rooms[room_code]["membros"][conn]
                    print(f"[{name}] saiu da sala [{room_code}].")
                    if not rooms[room_code]["membros"]:
                        del rooms[room_code]
                        print(f"[SALA VAZIA] Sala {room_code} removida.")
                    else:
                        broadcast(f"saiu da sala.", room_code, conn)
        conn.close()
        print(f"[CONEXÃO DE CHAT FECHADA] {addr}.")

# --- NOVA SEÇÃO: Servidor de Informações ---

def get_rooms_info():
    """Cria uma lista de dicionários com informações das salas para ser convertida em JSON."""
    with rooms_lock:
        info_list = []
        for code, data in rooms.items():
            info_list.append({
                "code": code,
                "name": data.get("name", code),
                "user_count": len(data["membros"])
            })
        return info_list

def handle_info_request(conn, addr):
    """Lida com uma única requisição na porta de informações."""
    print(f"[NOVA CONEXÃO DE INFO] {addr} conectado.")
    try:
        # A única coisa que este servidor faz é enviar a lista de salas e fechar.
        rooms_list = get_rooms_info()
        json_data = json.dumps(rooms_list) # Converte a lista para uma string JSON
        conn.send(json_data.encode(FORMAT))
    except Exception as e:
        print(f"[ERRO DE INFO] {e}")
    finally:
        conn.close()
        print(f"[CONEXÃO DE INFO FECHADA] {addr}")

def start_info_server():
    """Inicia o servidor que escuta na porta de informações em uma thread separada."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR_INFO)
    server.listen()
    print(f"[ESCUTANDO INFO] Servidor de informações escutando em {IP}:{INFO_PORT}")
    while True:
        conn, addr = server.accept()
        # Não precisa de uma nova thread para cada conexão, pois é uma tarefa rápida
        handle_info_request(conn, addr)

# --- Função Principal ---

def main():
    print("[INICIANDO] Servidor de Chat TCP está iniciando...")

    # Inicia o servidor de informações em uma thread daemon
    info_thread = threading.Thread(target=start_info_server, daemon=True)
    info_thread.start()

    # Inicia o servidor de chat principal
    chat_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    chat_server.bind(ADDR_CHAT)
    chat_server.listen()
    print(f"[ESCUTANDO CHAT] Servidor de chat escutando em {IP}:{CHAT_PORT}")

    while True:
        conn, addr = chat_server.accept()
        thread = threading.Thread(target=pro_cliente, args=(conn, addr))
        thread.start()
        active_connections = threading.active_count() - 2 # -1 para a thread principal, -1 para a info_thread
        print(f"[CONEXÕES DE CHAT ATIVAS] {active_connections}")

if __name__ == "__main__":
    main()
