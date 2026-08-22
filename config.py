# ==========================================
# CONSTANTES E CONFIGURAÇÃO DO PROJETO
# ==========================================
import streamlit as st

# Chave Mestra do Aplicativo (Modo GOD) — lida dos Secrets do Streamlit, nunca hardcoded
# no código (o repositório é público no GitHub). Configure em:
# Streamlit Cloud > Manage app > Settings > Secrets, adicionando a linha:
#   SUPER_ADMIN = "seu-email@exemplo.com"
# Localmente, coloque a mesma linha em .streamlit/secrets.toml (não vai pro git).
try:
    SUPER_ADMIN = st.secrets.get("SUPER_ADMIN", "")
except Exception:
    # Nenhum secrets.toml configurado (ex: ambiente local sem esse arquivo).
    # Modo GOD simplesmente fica inacessível até o secret ser configurado —
    # o resto do app continua funcionando normalmente.
    SUPER_ADMIN = ""

PEDRAS = ["Ouro 🥇", "Prata 🥈", "Bronze 🥉", "Diamante 💎", "Alexandrita 💠", "Painite 🩸", "Musgravite 🪨", "Opala Negra 🌌", "Esmeralda 🟩", "Rubi 🔴", "Safira 🔷", "Tanzanita 🪻", "Turmalina 🍉", "Topázio 🔶", "Jade 🟢"]
ESTILOS_AVATAR = {"🧑 Desenho Moderno": "notionists", "🤠 Aventureiro": "adventurer", "🤖 Robô": "bottts", "😎 Emoji Divertido": "fun-emoji", "🧑‍🎨 Retrato Elegante": "micah", "👾 Pixel Art": "pixel-art"}

CSS_APP = """
<link rel="manifest" href="./app/static/manifest.json" crossorigin="anonymous">
<style>
[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }
button[data-baseweb="tab"] { white-space: nowrap !important; font-size: 14px !important; border-radius: 8px 8px 0 0 !important; }
button[data-baseweb="tab"][aria-selected="true"] { background-color: rgba(40, 167, 69, 0.15) !important; border-bottom: 3px solid #28a745 !important; }
.titulo-responsivo { font-size: 32px; font-weight: bold; margin-top: 10px; margin-bottom: 10px; }
@media (max-width: 768px) {
h1 { font-size: 24px !important; }
h2 { font-size: 22px !important; }
h3 { font-size: 20px !important; }
h4 { font-size: 18px !important; }
.titulo-responsivo { font-size: 20px !important; }
[data-testid="stMetricValue"] { font-size: 1.8rem !important; }
button[data-baseweb="tab"] { font-size: 11px !important; padding: 8px 10px !important; margin-right: 0px !important; }
}
</style>
"""

# ==========================================
# AS NOVAS REGRAS DE OURO BALANCEADAS
# ==========================================
def obter_regras_padrao(usuario):
    return [
        {"u": usuario, "d": "🥱 Acordar reclamando", "v": 1.0, "cv": False},
        {"u": usuario, "d": "👟 Deixa roupa no chão e chuteira", "v": 2.0, "cv": False},
        {"u": usuario, "d": "🚽 Deixar a toalha no chão/privada", "v": 1.0, "cv": False},
        {"u": usuario, "d": "💡 Deixar luz acesa", "v": 1.0, "cv": False},
        {"u": usuario, "d": "🤬 Desobedecer aos pais (Cartão Vermelho)", "v": 20.0, "cv": True},
        {"u": usuario, "d": "🤔 Desobediência no Treino ou Jogo", "v": 3.0, "cv": False},
        {"u": usuario, "d": "📚 Não fazer lição", "v": 5.0, "cv": False},
        {"u": usuario, "d": "🧼 Não ir tomar banho quando solicitado", "v": 2.0, "cv": False},
        {"u": usuario, "d": "🗑️ Não levar o lixo", "v": 3.0, "cv": False},
        {"u": usuario, "d": "🚿 Não seca o banheiro", "v": 1.0, "cv": False},
        {"u": usuario, "d": "🚰 Não tomou água", "v": 2.0, "cv": False},
        {"u": usuario, "d": "😒 Reclamar de ir aos treinos", "v": 2.0, "cv": False},
        {"u": usuario, "d": "🫩 Responder os pais", "v": 3.0, "cv": False},
        {"u": usuario, "d": "🥊 Brigar com o irmão", "v": 5.0, "cv": False},
        {"u": usuario, "d": "🎮 Passar do limite de telas", "v": 3.0, "cv": False},
        {"u": usuario, "d": "🤥 Mentir para os pais", "v": 15.0, "cv": False}
    ]

def obter_bonus_padrao(usuario):
    return [
        {"u": usuario, "d": "🍽️ Ajudou a lavar a louça", "v": 3.0},
        {"u": usuario, "d": "🧹 Ajudou na limpeza da casa", "v": 5.0},
        {"u": usuario, "d": "🛏️ Arrumou a cama cedo", "v": 2.0},
        {"u": usuario, "d": "🥗 Comeu toda a salada/verdura", "v": 2.0},
        {"u": usuario, "d": "🌟 Elogio na escola", "v": 5.0},
        {"u": usuario, "d": "📖 Leu um livro (30 min)", "v": 5.0},
        {"u": usuario, "d": "🏅 Atleta Disciplinado (Semana Perfeita)", "v": 10.0},
        {"u": usuario, "d": "⚽ Destaque e Raça no Treino/Jogo", "v": 5.0},
        {"u": usuario, "d": "😴 Foi dormir no horário sem enrolar", "v": 2.0},
        {"u": usuario, "d": "👩🏻‍🦯 Passou aspirador em casa", "v": 1.0},
        {"u": usuario, "d": "🥅 Fez gol no jogo", "v": 2.0}
    ]
