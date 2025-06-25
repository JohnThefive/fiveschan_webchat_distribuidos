
from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
import socket
import threading
import random
from string import ascii_uppercase
import os 
from dotenv import load_dotenv

# importando a chave
load_dotenv()

# --- Configurações ---
# Servidor de Chat TCP
TCP_IP = "127.0.0.1"
TCP_PORT = 5566
BUFFER_SIZE = 1024
DISCONNECT_MSG = "!DESCONECTAR"

# esse é o basico de como funciona um server flask 
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

# Dicionários para a ponte WebSocket <-> TCP
# {sid_socketio: socket_tcp}
tcp_sockets = {}
# {sid_socketio: thread_escuta}
tcp_threads = {}

# --- Lógica da Ponte ---
def listen_from_tcp(sid, tcp_sock):
   
    #Roda em uma thread para ouvir o servidor TCP e retransmitir para o browser.
    # Isto cumpre o requisito de uma thread dedicada à recepção.
    
    while True:
        try:
            data = tcp_sock.recv(BUFFER_SIZE)
            if data:
                socketio.emit('server_message', {'data': data.decode('utf-8')}, room=sid)
            else:
                break # Conexão fechada pelo servidor
        except Exception:
            break
    print(f"[GATEWAY] Thread de escuta para {sid} terminada.")

# --- Lógica do Site (similar ao seu projeto antigo) ---
def generate_unique_code(length):
    # No nosso caso, o gateway não precisa saber se o código existe,
    # pois o servidor TCP é quem gerencia as salas.
    # Apenas geramos um código aleatório.
    return "".join(random.choice(ascii_uppercase) for _ in range(length))

@app.route("/", methods=["POST", "GET"])
def pagina_inicial():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = "join" in request.form
        create = "create" in request.form

        if not name:
            return render_template("pagina_inicial.html", error="Por favor, coloque um nome.", code=code, name=name)
        
        if join and not code:
            return render_template("pagina_inicial.html", error="Por favor, coloque um código de sala.", code=code, name=name)
        
        room = code
        if create:
            room = generate_unique_code(4)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room_page"))

    return render_template("pagina_inicial.html")

@app.route("/room")
def room_page():
    room = session.get("room")
    name = session.get("name")
    if room is None or name is None:
        return redirect(url_for("pagina_inicial"))
    return render_template("room.html", room=room, name=name)

# --- Lógica do SocketIO (A Ponte) ---
@socketio.on('connect')
def handle_connect():
    sid = request.sid
    room = session.get("room")
    name = session.get("name")

    if not room or not name:
        return # Não conecta se não tiver info da sessão

    try:
        # Conecta ao servidor TCP
        tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_client.connect((TCP_IP, TCP_PORT))
        
        # Envia a requisição para entrar na sala
        join_request = f"JOIN:{room}:{name}"
        tcp_client.send(join_request.encode('utf-8'))
        
        # Guarda o socket e inicia a thread de escuta
        tcp_sockets[sid] = tcp_client
        thread = threading.Thread(target=listen_from_tcp, args=(sid, tcp_client))
        thread.daemon = True
        thread.start()
        tcp_threads[sid] = thread
        
        print(f"[GATEWAY] Cliente {name} ({sid}) conectado e ponte criada para sala {room}.")

    except Exception as e:
        print(f"[GATEWAY] Erro ao criar ponte para {sid}: {e}")
        emit('server_message', {'data': 'ERRO: Não foi possível conectar ao servidor de chat.'})

@socketio.on('client_message')
def handle_client_message(data):
    sid = request.sid
    message = data.get('data')
    if sid in tcp_sockets and message:
        try:
            tcp_sockets[sid].send(message.encode('utf-8'))
        except Exception as e:
            print(f"[GATEWAY] Erro ao enviar mensagem para TCP: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    print(f"[GATEWAY] Cliente {sid} desconectado.")
    if sid in tcp_sockets:
        tcp_sock = tcp_sockets.pop(sid)
        try:
            # Envia a mensagem de desconexão para o servidor TCP fazer a limpeza
            tcp_sock.send(DISCONNECT_MSG.encode('utf-8'))
        except Exception:
            pass
        finally:
            tcp_sock.close()
    
    if sid in tcp_threads:
        del tcp_threads[sid]

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", debug=True)
