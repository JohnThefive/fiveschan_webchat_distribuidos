# usraemos Flask e flask socketio para fazer o chat 


from flask import Flask, render_template, request, session,redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
import os 
from dotenv import load_dotenv

# importando a chave
load_dotenv()

# esse é o basico de como funciona um server flask 
fiveschan = Flask(__name__)
fiveschan.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
socketio = SocketIO(fiveschan)

# todas as possiveis salas vão estar dentro de um dicionario
rooms = {}

def generate_unique_code(qtd_de_algarismos):
    while True:
        code = ""
        for _ in range(qtd_de_algarismos):
            code += random.choice(ascii_uppercase)
        if code not in rooms:
            break
    return code      

@fiveschan.route("/", methods=["POST", "GET"])
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
            # A lista de mensagens é criada com a chave "mensagens" (plural), não confundir com mensage ou mensagem
            rooms[room] = {"membros": 0, "mensagens": []}
        
        elif code not in rooms:
            return render_template("pagina_inicial.html", error="A sala não existe.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("pagina_inicial.html")

@fiveschan.route("/room")
def room():
    room_code = session.get("room")
    if room_code is None or session.get("name") is None or room_code not in rooms:
        return redirect(url_for("pagina_inicial"))
    
    # Passando a variável 'room' para o template usar
    return render_template("room.html", room=room_code)

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")

    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
        
    join_room(room)
    
    # A função send() só envia para o cliente atual se não especificarmos um 'to'
    for msg in rooms[room]["mensagens"]:
        send(msg)

    send({"name": name, "message": "entrou na sala"}, to = room)
    rooms[room]["membros"] += 1 
    print(f"{name} se juntou a sala {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["membros"] -= 1
        if rooms[room]["membros"] <= 0:
            del rooms[room]
        else:
            send({"name": name, "message": "saiu da sala"}, to = room)     
            print(f"{name} saiu da sala {room}")   

#estamos "guardando" as mensagens na RAM, se o servidor reiniciar as mensganes são perdidas(aplicar banco de dados?) 
# o proximo passo seria substituir o dicionário rooms, que vive na memória RAM, por um banco de dados 
#depois hospedar o site em um serviço de hospegem de site e depois fazer protocolos de segurança ( o que fazer quando um servidor cair?)
@socketio.on("message")
def message(data):
    room = session.get("room")
    name = session.get("name")
    if room not in rooms:
        return
        
    content = {
        "name": name,
        "message": data["message"],
    }   
    send(content, to=room)
    rooms[room]["mensagens"].append(content)      
    print(f"{name} disse: {data['message']}")


if __name__ == "__main__":
    socketio.run(fiveschan, debug=True)

