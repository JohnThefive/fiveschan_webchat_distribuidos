
import socket
import threading

IP = "127.0.0.1"  # Escutar apenas localmente para o gateway se conectar
PORT = 5566
ADDR = (IP, PORT)
FORMAT = "utf-8"
DISCONNECT_MSG = "!DESCONECTAR"
SIZE = 1024

# Dicionário para gerenciar as salas, membros e mensagens
# Estrutura: {"CODIGO_DA_SALA": {"membros": {conn: nome}, "mensagens": []}}
rooms = {}
rooms_lock = threading.Lock() # Lock para proteger o acesso ao dicionário 'rooms'

def broadcast(message, room_code, sender_conn):
    with rooms_lock:
        if room_code in rooms:
            # Pega o nome do remetente
            sender_name = rooms[room_code]["membros"].get(sender_conn, "Alguém")
            full_message = f"[{sender_name}] {message}"
            
            # Guarda a mensagem no histórico da sala
            rooms[room_code]["mensagens"].append(full_message)

            for conn in list(rooms[room_code]["membros"]):
                if conn != sender_conn:
                    try:
                        conn.send(full_message.encode(FORMAT))
                    except Exception:
                        # Se houver erro, remove o membro
                        del rooms[room_code]["membros"][conn]


def pro_cliente(conn, addr):
    print(f"[NOVA CONEXÃO] {addr} conectado.")
    
    room_code = None
    name = None
    try:
        # A primeira mensagem DEVE ser para entrar na sala. Formato: "JOIN:CODIGO:NOME"
        join_request = conn.recv(SIZE).decode(FORMAT)
        parts = join_request.split(":")
        
        if len(parts) == 3 and parts[0] == "JOIN":
            room_code = parts[1]
            name = parts[2]
            
            with rooms_lock:
                # Se a sala não existe, cria ela
                if room_code not in rooms:
                    rooms[room_code] = {"membros": {}, "mensagens": []}
                    print(f"[NOVA SALA] Sala {room_code} criada por {name}.")

                # Adiciona o membro à sala
                rooms[room_code]["membros"][conn] = name

            # Envia o histórico de mensagens para o novo membro
            with rooms_lock:
                history = rooms[room_code]["mensagens"]
                for msg in history:
                    conn.send(msg.encode(FORMAT))
            
            # Anuncia a entrada do novo membro
            broadcast(f"entrou na sala.", room_code, conn)
            print(f"[{name}] entrou na sala [{room_code}]. Membros: {len(rooms[room_code]['membros'])}")

        else:
            print(f"[ERRO] Requisição de entrada inválida de {addr}. Desconectando.")
            conn.close()
            return

        # Loop principal para receber mensagens do cliente
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
        # Limpeza ao desconectar
        if room_code and name and room_code in rooms:
            with rooms_lock:
                # Remove o membro da sala
                if conn in rooms[room_code]["membros"]:
                    del rooms[room_code]["membros"][conn]
                    print(f"[{name}] saiu da sala [{room_code}].")
                    
                    # Se a sala ficar vazia, remove ela
                    if not rooms[room_code]["membros"]:
                        del rooms[room_code]
                        print(f"[SALA VAZIA] Sala {room_code} removida.")
                    else:
                        # Anuncia a saída do membro
                        broadcast(f"saiu da sala.", room_code, conn)
        
        conn.close()
        print(f"[CONEXÃO FECHADA] {addr}.")

def main():
    print("[INICIANDO] Servidor de Chat TCP está iniciando...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen()
    print(f"[ESCUTANDO] Servidor está escutando em {IP}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=pro_cliente, args=(conn, addr))
        thread.start()
        active_connections = threading.active_count() - 1
        print(f"[CONEXÕES ATIVAS] {active_connections}")

if __name__ == "__main__":
    main()
