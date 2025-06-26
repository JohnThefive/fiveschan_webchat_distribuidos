import psycopg2
import bcrypt
import base64
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT")
            )
            self.create_tables()
        except psycopg2.OperationalError as e:
            print(f"!!! ERRO CRÍTICO DE BANCO DE DADOS: Não foi possível conectar. Verifique suas credenciais no .env e se o PostgreSQL está rodando. !!!")
            print(f"Detalhe do erro: {e}")
            raise

    def create_tables(self):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Sala (
                    Nome_Sala VARCHAR(1000) PRIMARY KEY
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Usuario (
                    Nome VARCHAR(100) PRIMARY KEY,
                    Senha VARCHAR(500)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Mensagem (
                    id_mensagem SERIAL PRIMARY KEY,
                    conteudo TEXT,
                    Nome VARCHAR(100),
                    Nome_Sala VARCHAR(1000),
                    FOREIGN KEY (Nome) REFERENCES Usuario(Nome),
                    FOREIGN KEY (Nome_Sala) REFERENCES Sala(Nome_Sala)
                );
            """)
        self.conn.commit()

    def sala_exists(self, nome_sala):
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM Sala WHERE Nome_Sala = %s", (nome_sala,))
            return cursor.fetchone() is not None

    def create_sala(self, nome_sala):
        if not self.sala_exists(nome_sala):
            with self.conn.cursor() as cursor:
                cursor.execute("INSERT INTO Sala (Nome_Sala) VALUES (%s)", (nome_sala,))
            self.conn.commit()
            return True
        return False

    def user_exists(self, nome):
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM Usuario WHERE Nome = %s", (nome,))
            return cursor.fetchone() is not None

    def create_user(self, nome, senha_plain):
        senha_hash = bcrypt.hashpw(senha_plain.encode(), bcrypt.gensalt())
        senha_b64 = base64.b64encode(senha_hash).decode('utf-8')

        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO Usuario (Nome, Senha) VALUES (%s, %s)",
                (nome, senha_b64)
            )
        self.conn.commit()

    def verify_password(self, nome, senha_plain):
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT Senha FROM Usuario WHERE Nome = %s", (nome,))
            result = cursor.fetchone()
        if result:
            senha_hash = base64.b64decode(result[0])
            return bcrypt.checkpw(senha_plain.encode(), senha_hash)
        return False

    def add_message(self, conteudo, nome_usuario, nome_sala):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO Mensagem (conteudo, Nome, Nome_Sala) VALUES (%s, %s, %s)",
                (conteudo, nome_usuario, nome_sala)
            )
        self.conn.commit()

    def get_messages_by_sala(self, nome_sala):
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id_mensagem, conteudo, Nome, Nome_Sala
                FROM Mensagem
                WHERE Nome_Sala = %s
                ORDER BY id_mensagem ASC
                """,
                (nome_sala,)
            )
            return cursor.fetchall()