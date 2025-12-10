import os
import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
DB_NAME = "nba.db"

# Fechar enquete 10 minutos antes do jogo
MINUTOS_ANTES = 10


async def fechar_enquetes_do_dia():
    """Fecha automaticamente enquetes 10 minutos antes de cada jogo"""
    bot = Bot(BOT_TOKEN)
    
    # Conectar ao banco
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Buscar jogos de hoje com enquetes ainda abertas
    hoje = datetime.utcnow().date()
    
    cur.execute("""
        SELECT j.game_id_nba, j.time_visitante, j.time_mandante, 
               j.data_utc, j.hora_utc, e.message_id, j.enquete_encerrada
        FROM JOGO j
        JOIN ENQUETE e ON j.id_jogo = e.id_jogo
        WHERE j.data_utc = ? 
          AND j.status = 'scheduled'
          AND j.enquete_encerrada = 0
        ORDER BY j.hora_utc
    """, (hoje.strftime("%Y-%m-%d"),))
    
    jogos = cur.fetchall()
    
    if not jogos:
        print("Nenhuma enquete aberta para fechar hoje.")
        return
    
    agora_utc = datetime.utcnow()
    enquetes_fechadas = 0
    
    for jogo in jogos:
        game_id = jogo['game_id_nba']
        visitante = jogo['time_visitante']
        mandante = jogo['time_mandante']
        data_utc = jogo['data_utc']
        hora_utc = jogo['hora_utc']
        message_id = jogo['message_id']
        
        # Criar datetime do jogo
        jogo_datetime_str = f"{data_utc} {hora_utc}"
        try:
            jogo_dt = datetime.strptime(jogo_datetime_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print(f"Erro ao parsear data/hora do jogo {game_id}")
            continue
        
        # Calcular quando fechar (10 minutos antes)
        fechar_em = jogo_dt - timedelta(minutes=MINUTOS_ANTES)
        
        # Se já passou do horário de fechar
        if agora_utc >= fechar_em:
            try:
                # Fechar a enquete no Telegram
                await bot.stop_poll(
                    chat_id=GROUP_ID,
                    message_id=message_id
                )
                
                # Marcar como encerrada no banco
                cur.execute("""
                    UPDATE JOGO
                    SET enquete_encerrada = 1
                    WHERE game_id_nba = ?
                """, (game_id,))
                
                print(f"✅ Enquete fechada: {visitante} x {mandante} (Jogo às {hora_utc} UTC)")
                enquetes_fechadas += 1
                
            except Exception as e:
                print(f"❌ Erro ao fechar enquete {game_id}: {e}")
        else:
            # Calcular quanto tempo até fechar
            tempo_restante = fechar_em - agora_utc
            horas, resto = divmod(tempo_restante.seconds, 3600)
            minutos, segundos = divmod(resto, 60)
            
            print(f"⏳ {visitante} x {mandante}: Fecha em {horas}h{minutos}m (Jogo às {hora_utc} UTC)")
    
    conn.commit()
    conn.close()
    
    if enquetes_fechadas > 0:
        print(f"\n🎯 Total de enquetes fechadas: {enquetes_fechadas}")


def fechar_todas_enquetes_do_dia():
    """Função síncrona para uso em scripts agendados"""
    asyncio.run(fechar_enquetes_do_dia())


if __name__ == "__main__":
    fechar_todas_enquetes_do_dia()