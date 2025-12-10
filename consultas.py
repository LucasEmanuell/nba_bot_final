from database import connect

def consulta_agrupamento():
    """Consulta com GROUP BY e HAVING"""
    conn = connect()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT u.apelido, COUNT(v.id_voto) as total_votos, SUM(CASE WHEN v.escolha = j.vencedor THEN 1 ELSE 0 END) as acertos
        FROM USUARIO_PARTICIPANTE u
        LEFT JOIN VOTO v ON u.id_usuario_participante = v.id_usuario_participante
        LEFT JOIN ENQUETE e ON v.id_enquete = e.id_enquete
        LEFT JOIN JOGO j ON e.id_jogo = j.id_jogo
        WHERE j.vencedor IS NOT NULL
        GROUP BY u.id_usuario_participante
        HAVING COUNT(v.id_voto) > 0
        ORDER BY acertos DESC, total_votos DESC
    """)
    
    resultados = cur.fetchall()
    conn.close()
    return resultados

def consulta_ordenacao(ascendente=True):
    """Consulta com ordenação personalizada"""
    conn = connect()
    cur = conn.cursor()
    
    ordem = "ASC" if ascendente else "DESC"
    
    cur.execute(f"""
        SELECT apelido, pontuacao, frequencia_participacao
        FROM USUARIO_PARTICIPANTE
        ORDER BY pontuacao {ordem}, frequencia_participacao {ordem}
    """)
    
    resultados = cur.fetchall()
    conn.close()
    return resultados

def busca_substring(campo, substring):
    """Busca case-insensitive com substring"""
    conn = connect()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT * FROM USUARIO_PARTICIPANTE
        WHERE LOWER({campo}) LIKE LOWER(?)
    """, (f'%{substring}%',))
    
    resultados = cur.fetchall()
    conn.close()
    return resultados

def consulta_join_complexo():
    """Consulta com diferentes tipos de JOIN"""
    conn = connect()
    cur = conn.cursor()
    
    # LEFT JOIN para mostrar todos os usuários, mesmo sem votos
    cur.execute("""
        SELECT u.apelido, COUNT(v.id_voto) as total_votos
        FROM USUARIO_PARTICIPANTE u
        LEFT JOIN VOTO v ON u.id_usuario_participante = v.id_usuario_participante
        GROUP BY u.id_usuario_participante
    """)
    
    resultados = cur.fetchall()
    conn.close()
    return resultados

def consulta_com_any():
    """Consulta usando ANY"""
    conn = connect()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT apelido, pontuacao
        FROM USUARIO_PARTICIPANTE u1
        WHERE pontuacao > ANY (
            SELECT pontuacao 
            FROM USUARIO_PARTICIPANTE u2 
            WHERE u2.apelido LIKE '%bot%'
        )
    """)
    
    resultados = cur.fetchall()
    conn.close()
    return resultados