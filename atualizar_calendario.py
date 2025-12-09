import os
from datetime import datetime
from get_nba import obter_calendario_completo
from database import inserir_jogo

"""
Atualiza a tabela JOGO com TODOS os jogos da temporada NBA.
Este arquivo é compatível com o modelo físico final do projeto.
"""

def atualizar_calendario():
    datas = obter_calendario_completo()

    total_processados = 0
    total_erros = 0

    for dia in datas:
        for jogo in dia["games"]:
            try:
                game_id = jogo["gameId"]

                # data e hora em UTC (preciso para conversão posterior)
                game_datetime_utc = jogo.get("gameDateTimeUTC")
                if not game_datetime_utc:
                    print(f"⚠️ Jogo {game_id} sem campo gameDateTimeUTC — ignorado.")
                    total_erros += 1
                    continue

                dt_utc = datetime.fromisoformat(game_datetime_utc.replace("Z", ""))
                data_utc = dt_utc.strftime("%Y-%m-%d")
                hora_utc = dt_utc.strftime("%H:%M:%S")

                home = jogo["homeTeam"]
                away = jogo["awayTeam"]

                mandante = f"{home['teamCity']} {home['teamName']}"
                visitante = f"{away['teamCity']} {away['teamName']}"

                status = jogo.get("gameStatusText", "scheduled")

                inserir_jogo(
                    game_id_nba=game_id,
                    mandante=mandante,
                    visitante=visitante,
                    data_utc=data_utc,
                    hora_utc=hora_utc,
                    status=status
                )

                total_processados += 1

            except Exception as e:
                print(f"❌ Erro ao processar jogo {game_id}: {e}")
                total_erros += 1

    print("="*50)
    print("🏀 CALENDÁRIO DA NBA ATUALIZADO")
    print(f"   • Jogos processados: {total_processados}")
    print(f"   • Jogos ignorados / erro: {total_erros}")
    print("="*50)


if __name__ == "__main__":
    atualizar_calendario()
