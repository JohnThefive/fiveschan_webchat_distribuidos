# --- web_gateway.py (Corrigido para usar NOME DA SALA) ---

from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
import socket
import threading
import os
import json
from dotenv import load_dotenv

from user import UserManager
from db import Database

load_dotenv()
db = Database()
user_manager = UserManager(db)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

tcp_sockets = {}
tcp_threads = {}

def listen_from_tcp(sid, tcp_sock):
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

def get_rooms_from_server():
    try:
        info_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        info_socket.connect(("127.0.0.1", 5567))
        data = info_socket.recv(4096).decode('utf-8')
        info_socket.close()
        # O info_server já retorna os nomes das salas, então isso está correto.
        return json.loads(data)
    except Exception as e:
        print(f"[GATEWAY ERROR] Não foi possível buscar a lista de salas: {e}")
        return []

# --- Rotas Flask ---
@app.route("/")
def index():
    if "name" in session:
        return redirect(url_for("home"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    # Sem alterações aqui, sua lógica de login está perfeita.
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
    # Sem alterações aqui, sua lógica de registro está perfeita.
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
    session.clear()
    return redirect(url_for("login"))

# ALTERAÇÃO CRÍTICA AQUI
@app.route("/home", methods=["POST", "GET"])
def home():
    if "name" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        # ALTERADO: O campo do formulário agora deve ser 'room_name' (ou como você chamar no HTML).
        room_name = request.form.get("room_name") 
        if not room_name:
            rooms_list = get_rooms_from_server()
            return render_template("home.html", name=session.get("name"), rooms=rooms_list, error="O nome da sala não pode ser vazio.")
        
        # O Nome da Sala é o identificador. Ele é salvo na sessão.
        session["room"] = room_name
        # Redireciona para a página da sala usando o nome como identificador na URL.
        return redirect(url_for("room_page", room_identifier=room_name))

    rooms_list = get_rooms_from_server()
    return render_template("home.html", name=session.get("name"), rooms=rooms_list)

# ALTERAÇÃO CRÍTICA AQUI
@app.route("/room/<string:room_identifier>")
def room_page(room_identifier):
    # Apenas garante que a sessão está correta.
    if "name" not in session or "room" not in session:
        return redirect(url_for("home"))
    # Renderiza a página da sala. O 'room_identifier' da URL é o nome da sala.
    return render_template("room.html", room=room_identifier, name=session.get("name"))

# --- Lógica do SocketIO ---
@socketio.on('connect')
def handle_connect():
    sid = request.sid
    # A sessão 'room' agora contém o Nome da Sala, que é o que o server.py precisa.
    room = session.get("room")
    name = session.get("name")
    
    if not room or not name:
        return
        
    try:
        tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_client.connect(("127.0.0.1", 5566))

        # A mensagem de JOIN agora envia o Nome da Sala, que o server.py usará como chave.
        # O formato "JOIN:NOME_DA_SALA:NOME_DO_USUARIO" está correto.
        join_request = f"JOIN:{room}:{name}"
        tcp_client.send(join_request.encode('utf-8'))
        
        tcp_sockets[sid] = tcp_client
        thread = threading.Thread(target=listen_from_tcp, args=(sid, tcp_client))
        thread.daemon = True
        thread.start()
        tcp_threads[sid] = thread
        print(f"[GATEWAY] Cliente '{name}' ({sid}) conectado. Ponte criada para sala '{room}'.")
        
    except Exception as e:
        print(f"[GATEWAY-ERRO] Falha ao criar ponte para {sid}: {e}")
        emit('server_message', {'data': f'ERRO: Não foi possível conectar ao servidor de chat. ({e})'})

# O resto do arquivo (client_message, disconnect, etc.) não precisa de alterações.
# A lógica deles já é compatível.
@socketio.on('client_message')
def handle_client_message(data):
    sid = request.sid
    message = data.get('data')
    if sid in tcp_sockets and message:
        try:
            tcp_sockets[sid].send(message.encode('utf-8'))
        except Exception as e:
            print(f"[GATEWAY-ERRO] Falha ao enviar mensagem para TCP: {e}")

@socketio.on('disconnect')
def handle_disconnect():
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

if __name__ == '__main__':
    socketio.run(app, host="::", port=5000, debug=True)  # "::" escuta em IPv4 e IPv6