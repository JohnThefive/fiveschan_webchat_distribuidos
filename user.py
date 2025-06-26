class UserManager:
    def __init__(self, db):
        self.db = db

    def register(self, username, password):
        if not username or not password:
            print("[MANAGER-ERROR] Tentativa de registro com usuário ou senha vazios.")
            return False
        if self.db.user_exists(username):
            print(f"[MANAGER-INFO] Tentativa de registro falhou: usuário '{username}' já existe.")
            return False
        try:
            self.db.create_user(username, password)
            print(f"[MANAGER-INFO] Usuário '{username}' registrado com sucesso.")
            return True
        except Exception as e:
            print(f"[MANAGER-ERROR] Erro ao registrar usuário '{username}': {e}")
            return False
    
    def authenticate(self, username, password):
        if not username or not password:
            return False
        try:
            is_valid = self.db.verify_password(username, password)
            if is_valid:
                print(f"[MANAGER-INFO] Autenticação bem-sucedida para '{username}'.")
            else:
                print(f"[MANAGER-INFO] Autenticação falhou para '{username}'.")
            return is_valid
        except Exception as e:
            print(f"[MANAGER-ERROR] Erro ao autenticar usuário '{username}': {e}")
            return False