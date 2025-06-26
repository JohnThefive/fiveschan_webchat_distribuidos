from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
import socket
import threading
import random
from string import ascii_uppercase
import os 
from dotenv import load_dotenv
from user import UserManager
from db import Database
import bcrypt
import json 


# --- Inicialização ---
db = Database()
user_manager = UserManager(db)
# importando a chave do .env
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
tcp_sockets = {}
tcp_threads = {}

# --- Lógica da Ponte ---
def listen_from_tcp(sid, tcp_sock):
    # Roda em uma thread para ouvir o servidor TCP e retransmitir para o browser.
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

# --- Lógica do Site ---
def generate_unique_code(length):
    # No nosso caso, o gateway não precisa saber se o código existe,
    # pois o servidor TCP é quem gerencia as salas.
    # Apenas geramos um código aleatório.
    return "".join(random.choice(ascii_uppercase) for _ in range(length))

@app.route("/")
def index_já_logado():
    if "name" in session:
        return redirect(url_for("home"))
    return render_template("pagina_inicial.html")

# ROTA LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # Autentica usando user_manager
        if user_manager.authenticate(username, password):
            session["name"] = username
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Usuário ou senha incorretos.")
    return render_template("login.html")


# ROTA REGISTRO DE NOVO USUÁRIO
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form.get("confirm_password")

        if not username or not password or not confirm_password:
             return render_template("register.html", error="Todos os campos são obrigatórios.")
        if password != confirm_password:
            return render_template("register.html", error="As senhas não coincidem.")
        
        # O método register já deve retornar False se o usuário existe
        if user_manager.register(username, password):
            # flash('Usuário registrado com sucesso! Faça o login.', 'success') # Opcional, se usar flash
            return redirect(url_for("login"))
        else:
            return render_template("register.html", error="Usuário já existe.")
    return render_template("register.html")
       
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))       

#Conecta-se à porta de informações do servidor TCP para obter a lista de salas.
def get_rooms_from_server():
    
    try:
        # Conecta ao servidor de informações
        info_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        info_socket.connect(("127.0.0.1", 5567)) # Conecta na porta de INFO

        # Recebe os dados (pode precisar de um loop se os dados forem grandes)
        data = info_socket.recv(4096).decode('utf-8')
        info_socket.close()

        # Converte a string JSON de volta para uma lista Python
        return json.loads(data)
    except Exception as e:
        print(f"[GATEWAY ERROR] Não foi possível buscar a lista de salas: {e}")
        return [] # Retorna uma lista vazia em caso de erro


@app.route("/home", methods=["POST", "GET"])
def home():
    if "name" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        name = session.get("name")
        join = "join" in request.form
        create = "create" in request.form
        
        if create:
            room_name = request.form.get("create_room_name")
            if not room_name:
                # Se o nome estiver vazio, retorna um erro
                rooms_list = get_rooms_from_server()
                return render_template("home.html", name=name, rooms=rooms_list, error="O nome da sala não pode ser vazio.")
            
            # Gera um código único para a nova sala
            room_code = generate_unique_code(4) 
            session["room"] = room_code
            session["room_name"] = room_name # Guarda o nome da sala na sessão
            return redirect(url_for("room_page", room_code=room_code))

        elif join:
            code = request.form.get("code")
            if not code:
                rooms_list = get_rooms_from_server()
                return render_template("home.html", name=name, rooms=rooms_list, error="Por favor, coloque um código de sala.")
            
            session["room"] = code
            # Remove o nome da sala da sessão para não renomear uma sala existente
            session.pop("room_name", None) 
            return redirect(url_for("room_page", room_code=code))

    # Busca a lista de salas do servidor para exibir na página
    rooms_list = get_rooms_from_server()
    return render_template("home.html", name=session.get("name"), rooms=rooms_list)


@app.route("/room/<string:room_code>")
def room_page(room_code):
    session["room"] = room_code
    name = session.get("name")
    if name is None:
        return redirect(url_for("login"))
    
    # Renderiza a página, passando o nome do usuário e o código da sala
    return render_template("room.html", room=room_code, name=name)


# --- Lógica do SocketIO (A Ponte) ---
@socketio.on('connect')
def handle_connect():
    sid = request.sid
    room = session.get("room")
    name = session.get("name")
    # Pega o nome da sala da sessão, se existir (usado na criação)
    room_name = session.get("room_name", "") 
    if not room or not name:
        return
    try:
        tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_client.connect(("127.0.0.1", 5566)) # Conecta na porta de CHAT
        
        # Envia a requisição para entrar na sala no novo formato
        join_request = f"JOIN:{room}:{name}:{room_name}"
        tcp_client.send(join_request.encode('utf-8'))
        
        # ... (resto da sua função handle_connect)
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