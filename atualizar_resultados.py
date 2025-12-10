from database import connect, atualizar_pontuacao
from get_nba import obter_json_nba

def atualizar():
    dados = obter_json_nba()
    jogos = dados["scoreboard"]["games"]

    conn = connect()
    cur = conn.cursor()

    for g in jogos:
        if g["gameStatusText"] != "Final":
            continue

        game_id = g["gameId"]
        mandante = g["homeTeam"]["teamTricode"]
        visitante = g["awayTeam"]["teamTricode"]

        pm = g["homeTeam"]["score"]
        pv = g["awayTeam"]["score"]
        vencedor = "M" if pm > pv else "V"

        # atualiza jogo
        cur.execute("""
            UPDATE JOGO
            SET vencedor=?, placar_mandante=?, placar_visitante=?
            WHERE game_id_nba=?
        """, (vencedor, pm, pv, game_id))

        # buscar enquete
        cur.execute("""
            SELECT id_enquete FROM ENQUETE 
            WHERE id_jogo=(SELECT id_jogo FROM JOGO WHERE game_id_nba=?)
        """, (game_id,))
        row = cur.fetchone()

        if not row:
            continue

        enquete_id = row[0]

        # votos
        cur.execute("""
            SELECT id_usuario_participante, escolha 
            FROM VOTO WHERE id_enquete=?
        """, (enquete_id,))
        votos = cur.fetchall()

        for uid, escolha in votos:
            acertou = escolha == vencedor
            atualizar_pontuacao(uid, acertou)

    conn.commit()
    conn.close()
    print("Resultados atualizados!")


if __name__ == "__main__":
    atualizar()