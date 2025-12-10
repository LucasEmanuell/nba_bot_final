import os
import asyncio
import html
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


def limpar_texto_telegram(texto: str) -> str:
    """Remove caracteres problemáticos para o parse do Telegram."""
    # Substituir caracteres que podem causar problemas no parse
    texto = html.escape(texto)
    # Remover múltiplos espaços
    texto = ' '.join(texto.split())
    return texto


async def criar_enquetes():
    bot = Bot(BOT_TOKEN)
    jogos = jogos_do_dia()

    if not jogos:
        print("Nenhum jogo hoje.")
        return

    conn = connect()
    cur = conn.cursor()

    # Enviar mensagem principal com todos os jogos do dia (sem formatação para evitar erros)
    mensagem_principal = "🏀 APOSTAS DE HOJE! 🏀\n\n"
    
    for jogo, dt_local in jogos:
        home = jogo["homeTeam"]
        away = jogo["awayTeam"]
        mandante_sigla = home.get("teamTricode", "")
        visitante_sigla = away.get("teamTricode", "")
        hora_local_str = dt_local.strftime("%Hh%M")
        canal = _extrair_canal(jogo)
        
        if canal:
            mensagem_principal += f"• {hora_local_str} {canal} — {visitante_sigla} x {mandante_sigla}\n"
        else:
            mensagem_principal += f"• {hora_local_str} — {visitante_sigla} x {mandante_sigla}\n"
    
    mensagem_principal += "\nParticipe do ranking oficial usando /votar_ID após cada enquete!"
    
    # Enviar mensagem principal (sem parse_mode para evitar erros)
    try:
        pinned_msg = await bot.send_message(
            chat_id=GROUP_ID,
            text=mensagem_principal
        )
        
        # Tentar fixar a mensagem
        try:
            await bot.pin_chat_message(
                chat_id=GROUP_ID,
                message_id=pinned_msg.message_id,
                disable_notification=True
            )
        except Exception as e:
            print(f"Aviso: Não foi possível fixar a mensagem: {e}")
    except Exception as e:
        print(f"Erro ao enviar mensagem principal: {e}")
        # Continuar mesmo se falhar a mensagem principal

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
        
        # Criar título da enquete com horário e canal
        if canal:
            titulo_enquete = f"{hora_local_str} {canal} — {visitante_sigla} x {mandante_sigla}"
        else:
            titulo_enquete = f"{hora_local_str} — {visitante_sigla} x {mandante_sigla}"
        
        # Limpar o título para evitar problemas de parse
        titulo_enquete = limpar_texto_telegram(titulo_enquete)

        # opções da enquete: visitante em cima, mandante embaixo
        op_visitante = f"{visitante_sigla} - {visitante_nome}"
        op_mandante = f"{mandante_sigla} - {mandante_nome}"
        
        # Limpar as opções também
        op_visitante = limpar_texto_telegram(op_visitante)
        op_mandante = limpar_texto_telegram(op_mandante)

        # Enviar enquete única com todas as informações no título
        try:
            poll = await bot.send_poll(
                chat_id=GROUP_ID,
                question=titulo_enquete,
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
        except Exception as e:
            print(f"Erro ao criar enquete para jogo {game_id}: {e}")
            continue

    conn.close()
    print("Enquetes criadas com sucesso!")


if __name__ == "__main__":
    asyncio.run(criar_enquetes())