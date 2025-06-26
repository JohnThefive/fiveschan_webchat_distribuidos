
class UserManager:
    def __init__(self, db):
        self.db = db

# Verifica se o usuário já existe. Se não, delega a criação do usuário (incluindo o hashing da senha) 
# para a classe Database.
    def register(self, username, password):
        if self.db.user_exists(username):
            return False  # Retorna False se o usuário já existe
        self.db.create_user(username, password)
        return True
    
# Delega a autenticação inteiramente para a classe Database.
# O método 'verify_password' já faz a busca do hash e a comparação segura.
    def authenticate(self, username, password):
        # Este método faz tudo: busca o usuário e confere se a senha bate.
        # Retorna True se a autenticação for bem-sucedida, False caso contrário.
        return self.db.verify_password(username, password)