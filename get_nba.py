import requests
from datetime import datetime

# Calendário completo da temporada
URL_TEMPORADA = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"

# Placar diário (jogos do dia e seus resultados)
URL_SCOREBOARD = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"


def obter_calendario_completo():
    """
    Baixa o JSON com o calendário completo da temporada.
    Usado em:
      - atualizar_calendario.py
      - criar_enquetes_do_dia.py
    """
    try:
        r = requests.get(URL_TEMPORADA, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data["leagueSchedule"]["gameDates"]
    except Exception as e:
        print("❌ Erro ao baixar calendário completo:", e)
        return []


def obter_json_nba():
    """
    Baixa o JSON de placares do dia (scoreboard).
    Usado em:
      - atualizar_resultados.py
    """
    try:
        r = requests.get(URL_SCOREBOARD, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("❌ Erro ao baixar scoreboard do dia:", e)
        return {"scoreboard": {"games": []}}
