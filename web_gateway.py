# --- web_gateway.py (Arquivo completo com suporte a múltiplos servidores) ---

from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
import socket
import threading
import os
import json
from dotenv import load_dotenv

from user import UserManager
from db import Database

# Carrega variáveis de ambiente
load_dotenv()
db = Database()
user_manager = UserManager(db)

# Configuração do Flask e SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

# Estruturas para gerenciar conexões TCP e threads
tcp_sockets = {}  # Mantém os sockets TCP ativos
tcp_threads = {}  # Mantém as threads de escuta ativas

# Lista de servidores disponíveis
SERVERS = [
    {"ip": "127.0.0.1", "chat_port": 5566, "info_port": 5567},
    {"ip": "127.0.0.1", "chat_port": 5576, "info_port": 5577},
]

# Função para verificar servidores ativos
def get_active_server():
    # Itera sobre a lista de servidores e verifica qual está ativo
    for server in SERVERS:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((server["ip"], server["info_port"]))
            sock.close()
            return server
        except Exception:
            continue
    return None

# Função para escutar mensagens do servidor TCP
def listen_from_tcp(sid, tcp_sock):
    # Escuta mensagens recebidas do servidor e as retransmite via SocketIO
    while True:
        try:
            data = tcp_sock.recv(1024)
            if data:
                socketio.emit('server_message', {'data': data.decode('utf-8')}, room=sid)
            else:
                break
        except Exception:
            break
    print(f"[GATEWAY] Thread de escuta para {sid} terminada.")

# Função para buscar lista de salas do servidor ativo
def get_rooms_from_server():
    # Conecta ao servidor ativo e recupera a lista de salas disponíveis
    try:
        server = get_active_server()  # Procura sempre o servidor ativo
        if not server:
            return []
        info_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        info_socket.connect((server["ip"], server["info_port"]))
        data = info_socket.recv(4096).decode('utf-8')
        info_socket.close()
        return json.loads(data)
    except Exception as e:
        print(f"[GATEWAY ERROR] Não foi possível buscar a lista de salas: {e}")
        return []

# --- Rotas Flask ---
@app.route("/")
def index():
    # Redireciona para a página de login ou home, dependendo da sessão
    if "name" in session:
        return redirect(url_for("home"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    # Gerencia o login do usuário
    if "name" in session:
        return redirect(url_for("home"))
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if user_manager.authenticate(username, password):
            session["name"] = username
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Usuário ou senha incorretos.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    # Gerencia o registro de novos usuários
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if not all([username, password, confirm_password]):
             return render_template("register.html", error="Todos os campos são obrigatórios.")
        if password != confirm_password:
            return render_template("register.html", error="As senhas não coincidem.")
        if user_manager.register(username, password):
            return redirect(url_for("login"))
        else:
            return render_template("register.html", error="Usuário já existe ou ocorreu um erro.")
    return render_template("register.html")

@app.route("/logout")
def logout():
    # Limpa a sessão e redireciona para a página de login
    session.clear()
    return redirect(url_for("login"))

@app.route("/home", methods=["POST", "GET"])
def home():
    # Exibe a página inicial com a lista de salas disponíveis
    if "name" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        room_name = request.form.get("room_name")
        if not room_name:
            rooms_list = get_rooms_from_server()
            return render_template("home.html", name=session.get("name"), rooms=rooms_list, error="O nome da sala não pode ser vazio.")

        session["room"] = room_name
        return redirect(url_for("room_page", room_identifier=room_name))

    rooms_list = get_rooms_from_server()
    return render_template("home.html", name=session.get("name"), rooms=rooms_list)

@app.route("/room/<string:room_identifier>")
def room_page(room_identifier):
    # Exibe a página de uma sala específica
    if "name" not in session or "room" not in session:
        return redirect(url_for("home"))
    return render_template("room.html", room=room_identifier, name=session.get("name"))

# --- Lógica do SocketIO ---
@socketio.on('connect')
def handle_connect():
    # Gerencia a conexão de um cliente via SocketIO
    sid = request.sid
    room = session.get("room")
    name = session.get("name")

    if not room or not name:
        return

    server = get_active_server()
    if not server:
        emit('server_message', {'data': 'ERRO: Nenhum servidor ativo disponível.'})
        return

    try:
        tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_client.connect((server["ip"], server["chat_port"]))

        join_request = f"JOIN:{room}:{name}"
        tcp_client.send(join_request.encode('utf-8'))

        tcp_sockets[sid] = tcp_client
        thread = threading.Thread(target=listen_from_tcp, args=(sid, tcp_client))
        thread.daemon = True
        thread.start()
        tcp_threads[sid] = thread
        print(f"[GATEWAY] Cliente '{name}' ({sid}) conectado ao servidor {server['ip']} na sala '{room}'.")

    except Exception as e:
        print(f"[GATEWAY-ERRO] Falha ao conectar ao servidor: {e}")
        emit('server_message', {'data': f'ERRO: Não foi possível conectar ao servidor. ({e})'})

@socketio.on('client_message')
def handle_client_message(data):
    # Envia mensagens do cliente para o servidor TCP
    sid = request.sid
    message = data.get('data')
    if sid in tcp_sockets and message:
        try:
            tcp_sockets[sid].send(message.encode('utf-8'))
        except Exception as e:
            print(f"[GATEWAY-ERRO] Falha ao enviar mensagem para TCP: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    # Gerencia a desconexão de um cliente
    sid = request.sid
    if sid in tcp_sockets:
        tcp_sock = tcp_sockets.pop(sid)
        try:
            tcp_sock.send("!DESCONECTAR".encode('utf-8'))
        except Exception: pass
        finally: tcp_sock.close()
    if sid in tcp_threads:
        del tcp_threads[sid]
    print(f"[GATEWAY] Cliente {sid} desconectado.")

# Inicialização do servidor Flask com SocketIO
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)