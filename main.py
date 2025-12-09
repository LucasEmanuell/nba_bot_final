import os
import re
from dotenv import load_dotenv

load_dotenv()

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

from database import (
    create_tables,
    registrar_usuario,
    registrar_voto,
    connect
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))


# ----------------------------
# /start – cria cadastro
# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    registrar_usuario(user.id, user.username or user.first_name)

    await update.message.reply_text(
        "Cadastro concluído! Você agora participa do Ranking Oficial 🏀"
    )


# ----------------------------
# /votar_X  (X = message_id da enquete)
# ----------------------------
async def votar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    # aceita /votar_16 e /votar_16@nbaenquete_bot
    match = re.match(r"^/votar_(\d+)", texto)
    if not match:
        await update.message.reply_text("Formato inválido. Exemplo: /votar_123456")
        return

    message_id_enquete = int(match.group(1))

    # Buscar times no banco para montar os botões com nomes
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT j.time_visitante, j.time_mandante
        FROM ENQUETE e
        JOIN JOGO j ON j.id_jogo = e.id_jogo
        WHERE e.message_id = ?
    """, (message_id_enquete,))
    row = cur.fetchone()
    conn.close()

    if not row:
        await update.message.reply_text(
            "Não encontrei esta enquete no banco. Tente novamente mais tarde."
        )
        return

    visitante, mandante = row

    botoes = [
        [InlineKeyboardButton(f"{visitante}", callback_data=f"{message_id_enquete}|V")],
        [InlineKeyboardButton(f"{mandante}",  callback_data=f"{message_id_enquete}|M")]
    ]

    await update.message.reply_text(
        "Escolha seu palpite oficial:",
        reply_markup=InlineKeyboardMarkup(botoes)
    )


# ----------------------------
# Callback do palpite oficial
# ----------------------------
async def callback_voto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data   # ex: "16|V"
    message_id_enquete_str, opcao = data.split("|")
    message_id_enquete = int(message_id_enquete_str)

    # Descobrir id_enquete real + jogo para confirmação
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.id_enquete,
               j.time_visitante,
               j.time_mandante
        FROM ENQUETE e
        JOIN JOGO j ON j.id_jogo = e.id_jogo
        WHERE e.message_id = ?
    """, (message_id_enquete,))
    row = cur.fetchone()

    if not row:
        conn.close()
        await query.edit_message_text(
            "Erro ao localizar a enquete no banco. Tente novamente mais tarde."
        )
        return

    id_enquete, visitante, mandante = row

    # verificar se usuário existe
    cur.execute("""
        SELECT id_usuario_participante
        FROM USUARIO_PARTICIPANTE
        WHERE telegram_user_id = ?
    """, (query.from_user.id,))
    row_u = cur.fetchone()
    conn.close()

    if not row_u:
        await query.edit_message_text("Use /start para criar seu cadastro.")
        return

    id_usuario = row_u[0]

    # registra voto com id_enquete correto
    registrar_voto(id_usuario, id_enquete, opcao)

    # montar texto de confirmação
    if opcao == "V":
        time_escolhido = visitante
    else:
        time_escolhido = mandante

    texto = (
        f"Seu palpite oficial foi registrado! ✅\n\n"
        f"Jogo: {visitante} x {mandante}\n"
        f"Seu palpite: **Vitória do {time_escolhido}**"
    )

    await query.edit_message_text(texto, parse_mode="Markdown")


# ----------------------------
# /ranking
# ----------------------------
async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT apelido, pontuacao, frequencia_participacao
        FROM USUARIO_PARTICIPANTE
        ORDER BY pontuacao DESC, frequencia_participacao DESC
    """)
    linhas = cur.fetchall()
    conn.close()

    if not linhas:
        await update.message.reply_text("Ainda não há participantes no ranking.")
        return

    texto = "🏆 RANKING OFICIAL 🏆\n\n"
    for nome, pts, freq in linhas:
        texto += f"{nome}: {pts} pontos | {freq} palpites\n"

    await update.message.reply_text(texto)


# ----------------------------
# ENTRYPOINT
# ----------------------------
if __name__ == "__main__":
    create_tables()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ranking", ranking))

    # captura qualquer /votar_X ou /votar_X@bot
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^/votar_\d+(@\w+)?$"),
            votar
        )
    )

    app.add_handler(CallbackQueryHandler(callback_voto))

    print("🤖 Bot iniciado...")
    app.run_polling()
