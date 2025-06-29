import socket
import threading
import json
from db import Database # NOVO: Importa a classe do banco de dados

# --- Configurações ---
IP = "127.0.0.1"
CHAT_PORT = 5566
INFO_PORT = 5567 # NOVO: Porta separada para o serviço de informações
ADDR_CHAT = (IP, CHAT_PORT)
ADDR_INFO = (IP, INFO_PORT)
FORMAT = "utf-8"
DISCONNECT_MSG = "!DESCONECTAR"
SIZE = 1024

# --- Inicialização ---
db = Database() # NOVO: Cria uma instância global do banco de dados

# ALTERAÇÃO: O dicionário 'rooms' não armazena mais o histórico de mensagens.
# O histórico agora vive permanentemente no banco de dados.
# Estrutura: {"CODIGO_DA_SALA": {"membros": {conn: nome}}}
rooms = {}
rooms_lock = threading.Lock() # Lock para proteger o acesso ao dicionário 'rooms'

def broadcast(message, room_code, sender_conn):
    with rooms_lock:
        if room_code in rooms:
            sender_name = rooms[room_code]["membros"].get(sender_conn, "Alguém")
            full_message = f"[{sender_name}] {message}"
            
            # ALTERAÇÃO (Tolerância a Falhas): A mensagem é salva no banco de dados.
            # A lista de mensagens em memória foi removida.
            try:
                db.add_message(message, sender_name, room_code)
            except Exception as e:
                print(f"[ERRO DB] Falha ao salvar mensagem de '{sender_name}': {e}")

            # Envia a mensagem em tempo real para todos os membros atualmente conectados na sala.
            for conn in list(rooms[room_code]["membros"]):
                # ALTERAÇÃO: Removido 'if conn != sender_conn' para que o remetente também veja sua própria mensagem.
                try:
                    conn.send(full_message.encode(FORMAT))
                except Exception:
                    # Se houver erro no envio, o membro é removido (a limpeza final cuidará disso)
                    print(f"Erro ao enviar para um cliente, será removido na desconexão.")

def pro_cliente(conn, addr):
    print(f"[NOVA CONEXÃO] {addr} conectado.")
    room_code = None
    name = None
    try:
        join_request = conn.recv(SIZE).decode(FORMAT)
        parts = join_request.split(":")
        
        # A validação do JOIN continua a mesma, está correta.
        if len(parts) == 3 and parts[0] == "JOIN":
            room_code = parts[1].upper() # Padroniza para maiúsculas
            name = parts[2]
            
            with rooms_lock:
                if room_code not in rooms:
                    # ALTERAÇÃO: Apenas cria a estrutura de membros, sem a lista de mensagens.
                    rooms[room_code] = {"membros": {}}
                    print(f"[NOVA SALA] Sala {room_code} criada em memória por {name}.")
                    # NOVO: Garante que a sala exista no banco de dados para futuras mensagens.
                    db.create_sala(room_code)

                rooms[room_code]["membros"][conn] = name

            # ALTERAÇÃO (Tolerância a Falhas): Busca o histórico do banco de dados, não da memória.
            try:
                history = db.get_messages_by_sala(room_code)
                for msg_tuple in history:
                    # O retorno do DB é uma tupla: (id, conteudo, nome_autor, nome_sala)
                    formatted_msg = f"[{msg_tuple[2]}] {msg_tuple[1]}"
                    conn.send((formatted_msg + "\n").encode(FORMAT))
                print(f"[HISTÓRICO] Enviado {len(history)} mensagens do DB para {name} na sala {room_code}.")
            except Exception as e:
                print(f"[ERRO DB] Falha ao buscar histórico para a sala {room_code}: {e}")
            
            # Anuncia a entrada do novo membro para todos na sala.
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
        if room_code and name and room_code in rooms:
            with rooms_lock:
                if conn in rooms[room_code]["membros"]:
                    # Remove o membro da sala
                    del rooms[room_code]["membros"][conn]
                    print(f"[{name}] saiu da sala [{room_code}].")
                    
                    # Anuncia a saída do membro para os que restaram
                    broadcast(f"saiu da sala.", room_code, conn)
                    
                    # Se a sala ficar vazia em memória, remove ela da lista de salas ativas.
                    if not rooms[room_code]["membros"]:
                        del rooms[room_code]
                        print(f"[SALA VAZIA] Sala {room_code} removida da memória.")
        
        conn.close()
        print(f"[CONEXÃO FECHADA] {addr}.")

# NOVO: Função para o servidor de informações. Roda em uma thread separada.
def info_server_handler():
    info_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    info_socket.bind(ADDR_INFO)
    info_socket.listen()
    print(f"[INFO SERVER] Escutando por requisições de salas em {IP}:{INFO_PORT}")

    while True:
        conn, addr = info_socket.accept()
        try:
            with rooms_lock:
                # Pega a lista de códigos das salas que têm membros ativos
                active_rooms_list = list(rooms.keys())
                # Converte a lista para o formato JSON string
                data_to_send = json.dumps(active_rooms_list)
            conn.send(data_to_send.encode(FORMAT))
        except Exception as e:
            print(f"[INFO SERVER ERRO] {e}")
        finally:
            conn.close()

def main():
    print("[INICIANDO] Servidor de Chat está iniciando...")
    
    # NOVO: Inicia o servidor de informação em sua própria thread.
    info_thread = threading.Thread(target=info_server_handler)
    info_thread.daemon = True # Permite que o programa principal feche mesmo se a thread estiver rodando.
    info_thread.start()

    # O servidor principal de chat continua o mesmo.
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR_CHAT)
    server.listen()
    print(f"[CHAT SERVER] Escutando em {IP}:{CHAT_PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=pro_cliente, args=(conn, addr))
        thread.start()
        # ALTERAÇÃO: O número de conexões ativas agora desconta 2 (thread principal e thread info_server)
        print(f"[CONEXÕES ATIVAS] {threading.active_count() - 2}")

if __name__ == "__main__":
    main()