import sqlite3
from datetime import datetime

DB_NAME = "nba.db"


def connect():
    conn = sqlite3.connect(DB_NAME, timeout=5)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def create_tables():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS USUARIO_PARTICIPANTE (
            id_usuario_participante INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER UNIQUE NOT NULL,
            apelido TEXT NOT NULL,
            pontuacao INTEGER DEFAULT 0,
            frequencia_participacao INTEGER DEFAULT 0
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS JOGO (
            id_jogo INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id_nba TEXT UNIQUE NOT NULL,
            time_visitante TEXT NOT NULL,
            time_mandante TEXT NOT NULL,
            data_utc TEXT NOT NULL,
            hora_utc TEXT NOT NULL,
            status TEXT DEFAULT 'scheduled',
            vencedor TEXT CHECK (vencedor IN ('M','V')),
            placar_mandante INTEGER,
            placar_visitante INTEGER,
            enquete_encerrada BOOLEAN DEFAULT 0  -- NOVO CAMPO ADICIONADO AQUI
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ENQUETE (
            id_enquete INTEGER PRIMARY KEY AUTOINCREMENT,
            id_jogo INTEGER NOT NULL,
            message_id INTEGER UNIQUE NOT NULL,
            FOREIGN KEY (id_jogo) REFERENCES JOGO (id_jogo)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS VOTO (
            id_voto INTEGER PRIMARY KEY AUTOINCREMENT,
            id_usuario_participante INTEGER NOT NULL,
            id_enquete INTEGER NOT NULL,
            escolha TEXT NOT NULL CHECK (escolha IN ('M','V')),
            data_hora TEXT NOT NULL,
            FOREIGN KEY (id_usuario_participante) REFERENCES USUARIO_PARTICIPANTE,
            FOREIGN KEY (id_enquete) REFERENCES ENQUETE
        );
    """)

    conn.commit()
    conn.close()


def registrar_usuario(telegram_user_id, apelido):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO USUARIO_PARTICIPANTE (telegram_user_id, apelido)
        VALUES (?, ?)
    """, (telegram_user_id, apelido))
    conn.commit()
    conn.close()


def inserir_jogo(game_id_nba, mandante, visitante, data_utc, hora_utc, status='scheduled'):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO JOGO (game_id_nba, time_mandante, time_visitante, data_utc, hora_utc, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (game_id_nba, mandante, visitante, data_utc, hora_utc, status))
    conn.commit()
    conn.close()


def registrar_enquete(id_jogo, message_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO ENQUETE (id_jogo, message_id)
        VALUES (?, ?)
    """, (id_jogo, message_id))
    conn.commit()
    conn.close()


def registrar_voto(id_usuario, id_enquete, escolha):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO VOTO (id_usuario_participante, id_enquete, escolha, data_hora)
        VALUES (?, ?, ?, ?)
    """, (id_usuario, id_enquete, escolha, datetime.utcnow().isoformat()))

    # atualiza estatísticas
    cur.execute("""
        UPDATE USUARIO_PARTICIPANTE
        SET frequencia_participacao = frequencia_participacao + 1
        WHERE id_usuario_participante = ?
    """, (id_usuario,))

    conn.commit()
    conn.close()


def atualizar_pontuacao(id_usuario, acertou):
    conn = connect()
    cur = conn.cursor()
    if acertou:
        cur.execute("""
            UPDATE USUARIO_PARTICIPANTE
            SET pontuacao = pontuacao + 1
            WHERE id_usuario_participante = ?
        """, (id_usuario,))
    conn.commit()
    conn.close()


def marcar_enquete_encerrada(game_id_nba):
    """Marca uma enquete como encerrada no banco"""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        UPDATE JOGO
        SET enquete_encerrada = 1
        WHERE game_id_nba = ?
    """, (game_id_nba,))
    conn.commit()
    conn.close()


def criar_triggers():
    """Cria triggers para o banco de dados"""
    conn = connect()
    cur = conn.cursor()
    
    # Trigger para atualizar automaticamente o status quando placar é atualizado
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS atualiza_status_jogo
        AFTER UPDATE OF placar_mandante, placar_visitante ON JOGO
        BEGIN
            UPDATE JOGO 
            SET status = 'Finalizado'
            WHERE NEW.placar_mandante IS NOT NULL 
              AND NEW.placar_visitante IS NOT NULL
              AND id_jogo = NEW.id_jogo;
        END;
    """)
    
    # Trigger para evitar votos duplicados na mesma enquete
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS evitar_voto_duplicado
        BEFORE INSERT ON VOTO
        FOR EACH ROW
        BEGIN
            SELECT CASE
                WHEN EXISTS (
                    SELECT 1 FROM VOTO 
                    WHERE id_usuario_participante = NEW.id_usuario_participante 
                    AND id_enquete = NEW.id_enquete
                ) THEN
                    RAISE(ABORT, 'Usuário já votou nesta enquete')
            END;
        END;
    """)
    
    conn.commit()
    conn.close()


# -------------------------------
# Execução direta para criar tabelas
# -------------------------------
if __name__ == "__main__":
    create_tables()
    criar_triggers()
    print(f"Tabelas e triggers criadas/validadas em {DB_NAME}.")