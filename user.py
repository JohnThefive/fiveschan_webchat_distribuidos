#Biblioteca de criptografia
import bcrypt

class UserManager:
    def __init__(self, db):
        self.db = db
    #Vê se o nome já existe. Se não existir:Criptografa a senha e Guarda no banco
    def register(self, username, password):
        if self.db.user_exists(username):
            return False
        password_bytes = password.encode('utf-8')
        hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        self.db.create_user(username, hashed_password)
        return True
    #Quando você faz login:Ele pega a senha guardada e Compara com a que você digitou (de forma segura)
    def authenticate(self, username, password):
        stored_hash = self.db.get_user_password_hash(username)
        if not stored_hash:
            return False
        password_bytes = password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, stored_hash)