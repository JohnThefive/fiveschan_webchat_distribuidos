import sqlite3
import bcrypt

class Database:
    def __init__(self, db_path="chat.db"):
        # Garante que a conexão pode ser usada por múltiplas threads (necessário para Flask)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_user_table()

    def create_user_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash BLOB NOT NULL
            )
        """)
        self.conn.commit()

    def user_exists(self, username):
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE username=?", (username,))
        return cursor.fetchone() is not None

    def create_user(self, username, password_plain):
    
        password_hash = bcrypt.hashpw(password_plain.encode('utf-8'), bcrypt.gensalt())
        
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        self.conn.commit()

    def verify_password(self, username, password_plain):
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username=?", (username,))
        result = cursor.fetchone()
        
        if result:
            # Pega o hash salvo (que já está em bytes)
            stored_hash = result[0]
            # Codifica a senha que o usuário digitou (string -> bytes) para comparar
            return bcrypt.checkpw(password_plain.encode('utf-8'), stored_hash)
            
        return False
