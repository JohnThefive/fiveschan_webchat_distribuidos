class UserManager:
    def __init__(self, db):
        self.db = db

    def register(self, username, password):
        # Validação de entradas
        if not username or not password:
            print("[MANAGER-ERROR] Tentativa de registro com usuário ou senha vazios.")
            return False
        # Verifica se o usuário já existe
        if self.db.user_exists(username):
            print(f"[MANAGER-INFO] Tentativa de registro falhou: usuário '{username}' já existe.")
            return False
        try:
            # Tenta criar o usuário no banco de dados
            self.db.create_user(username, password)
            print(f"[MANAGER-INFO] Usuário '{username}' registrado com sucesso.")
            return True
        except Exception as e:
            # Captura de erros inesperados do DB
            print(f"[MANAGER-ERROR] Erro ao registrar usuário '{username}': {e}")
            return False
    
    def authenticate(self, username, password):
        # Validação de entradas
        if not username or not password:
            return False
        try:
            #  Tenta verificar as credenciais no banco de dados
            is_valid = self.db.verify_password(username, password)
            if is_valid:
                print(f"[MANAGER-INFO] Autenticação bem-sucedida para '{username}'.")
            else:
                print(f"[MANAGER-INFO] Autenticação falhou para '{username}'.")
            return is_valid
        except Exception as e:
             #  Captura de erros inesperados do DB
            print(f"[MANAGER-ERROR] Erro ao autenticar usuário '{username}': {e}")
            return False