import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from telegram import Bot
from get_nba import obter_calendario_completo
from database import connect, registrar_enquete

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))


def _extrair_canal(jogo: dict) -> str | None:
    """Tenta extrair um canal de TV amigável da estrutura broadcasters."""
    b = jogo.get("broadcasters", {}) or {}

    # ordem de preferência
    chaves = [
        "intlTvBroadcasters",
        "nationalTvBroadcasters",
        "homeTvBroadcasters",
        "awayTvBroadcasters",
    ]

    for chave in chaves:
        arr = b.get(chave) or []
        for item in arr:
            if item.get("broadcasterMedia") == "tv":
                return item.get("broadcasterDisplay")
    return None


def jogos_do_dia():
    """Retorna jogos do 'dia' considerando GMT-3 e janela até 02h da manhã."""
    agora_utc = datetime.utcnow()
    agora_local = agora_utc - timedelta(hours=3)
    hoje_local = agora_local.date()
    amanha_local = hoje_local + timedelta(days=1)

    datas = obter_calendario_completo()
    jogos = []

    for dia in datas:
        for jogo in dia["games"]:
            game_datetime = jogo.get("gameDateTimeUTC")
            if not game_datetime:
                continue

            dt_utc = datetime.fromisoformat(game_datetime.replace("Z", ""))
            dt_local = dt_utc - timedelta(hours=3)

            data_local = dt_local.date()
            hora_local = dt_local.hour

            # critério de "dia de hoje":
            #  - todos os jogos da data local == hoje
            #  - jogos da data local == amanhã e hora_local < 2 (0h–1h59)
            if data_local == hoje_local or (data_local == amanha_local and hora_local < 2):
                jogos.append((jogo, dt_local))

    return jogos


async def criar_enquetes():
    bot = Bot(BOT_TOKEN)
    jogos = jogos_do_dia()

    if not jogos:
        print("Nenhum jogo hoje.")
        return

    conn = connect()
    cur = conn.cursor()

    for jogo, dt_local in jogos:
        game_id = jogo["gameId"]
        home = jogo["homeTeam"]
        away = jogo["awayTeam"]

        # localizar jogo no banco
        cur.execute("SELECT id_jogo FROM JOGO WHERE game_id_nba = ?", (game_id,))
        row = cur.fetchone()
        if not row:
            print(f"Jogo {game_id} não está no banco.")
            continue

        id_jogo = row[0]

        mandante_nome = f"{home['teamCity']} {home['teamName']}"
        visitante_nome = f"{away['teamCity']} {away['teamName']}"

        # siglas
        mandante_sigla = home.get("teamTricode", "")
        visitante_sigla = away.get("teamTricode", "")

        # horário local formatado
        hora_local_str = dt_local.strftime("%Hh%M")

        # canal (se existir)
        canal = _extrair_canal(jogo)
        if canal:
            titulo_info = f"{hora_local_str}  {canal}  —  {visitante_sigla} x {mandante_sigla}"
        else:
            titulo_info = f"{hora_local_str}  —  {visitante_sigla} x {mandante_sigla}"

        # mensagem de contexto (horário + canal + times)
        await bot.send_message(
            chat_id=GROUP_ID,
            text=titulo_info
        )

        # opções da enquete: visitante em cima, mandante embaixo
        op_visitante = f"{visitante_sigla} - {visitante_nome}"
        op_mandante = f"{mandante_sigla} - {mandante_nome}"

        poll = await bot.send_poll(
            chat_id=GROUP_ID,
            question="Quem vence hoje?",
            options=[op_visitante, op_mandante],
            is_anonymous=False
        )

        # registrar enquete no banco (message_id é a chave que usamos na aplicação)
        registrar_enquete(id_jogo, poll.message_id)

        # comando para voto oficial (privado)
        await bot.send_message(
            chat_id=GROUP_ID,
            text=f"Para palpite oficial (ranking):\n👉 /votar_{poll.message_id}"
        )

    conn.close()
    print("Enquetes criadas com sucesso!")


if __name__ == "__main__":
    asyncio.run(criar_enquetes())
