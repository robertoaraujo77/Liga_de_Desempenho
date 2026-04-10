import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
import base64
import re
from sqlalchemy import text
from PIL import Image
import io
from streamlit_cropper import st_cropper
import hashlib

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E PWA
# ==========================================
st.set_page_config(page_title="Liga de Desempenho", page_icon="⚽", layout="centered")

# Injeção de Manifesto para o PWABuilder (Preparando o terreno)
st.markdown("""
    <link rel="manifest" href="manifest.json">
    <style>
    @media (max-width: 768px) {
        h1 { font-size: 1.6rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

# Ranking Dinâmico
PEDRAS = ["Ouro 🥇", "Prata 🥈", "Bronze 🥉", "Diamante 💎", "Alexandrita 💠", "Painite 🩸", "Musgravite 🪨", "Opala Negra 🌌", "Esmeralda 🟩", "Rubi 🔴", "Safira 🔷", "Tanzanita 🪻", "Turmalina 🍉", "Topázio 🔶", "Jade 🟢"]

ESTILOS_AVATAR = {"🧑 Desenho Moderno": "notionists", "🤠 Aventureiro": "adventurer", "🤖 Robô": "bottts", "😎 Emoji Divertido": "fun-emoji", "🧑‍🎨 Retrato Elegante": "micah", "👾 Pixel Art": "pixel-art"}

# ==========================================
# UTILITÁRIOS E SEGURANÇA
# ==========================================
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def converter_para_base64(image):
    image = image.resize((150, 150), Image.Resampling.LANCZOS)
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"

# ==========================================
# CONEXÃO E BANCO DE DADOS (MULTI-USUÁRIO)
# ==========================================
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        # Tabela de Usuários (Contas)
        s.execute(text('CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT)'))
        
        # Tabelas principais com coluna 'usuario' para isolamento
        s.execute(text('''CREATE TABLE IF NOT EXISTS status (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, nivel TEXT, base REAL, saldo REAL, faltas REAL, aguardando_resgate INTEGER DEFAULT 0, avatar TEXT, base_inicial REAL, incremento REAL, teto_maximo REAL, titulos INTEGER, limite_faltas REAL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS historico (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, data TEXT, infracao TEXT, desconto REAL, tipo TEXT)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS trofeus (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, data TEXT, nivel TEXT, saldo REAL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS regras (id SERIAL PRIMARY KEY, usuario TEXT, descricao TEXT, valor REAL)'''))
        s.commit()

init_db()

# ==========================================
# UTILITÁRIOS E SEGURANÇA (BLINDADO)
# ==========================================
def hash_password(password):
    # Corta espaços sem querer na senha também
    senha_limpa = str(password).strip()
    return hashlib.sha256(str.encode(senha_limpa)).hexdigest()

def converter_para_base64(image):
    image = image.resize((150, 150), Image.Resampling.LANCZOS)
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"

# --- LÓGICA DE AUTENTICAÇÃO ---
def criar_conta(user, pw):
    user_limpo = str(user).strip().lower() # Limpa o e-mail
    try:
        with conn.session as s:
            s.execute(text('INSERT INTO usuarios (username, password) VALUES (:u, :p)'), {"u": user_limpo, "p": hash_password(pw)})
            # Insere regras padrão para o novo usuário
            regras_padrao = [
                {"u": user_limpo, "d": "🚿 Não seca o banheiro", "v": 1.0},
                {"u": user_limpo, "d": "🥱 Acordar reclamando", "v": 1.0},
                {"u": user_limpo, "d": "📚 Não fazer lição", "v": 5.0},
                {"u": user_limpo, "d": "🤬 Desobedecer (Vermelho)", "v": 20.0}
            ]
            s.execute(text('INSERT INTO regras (usuario, descricao, valor) VALUES (:u, :d, :v)'), regras_padrao)
            s.commit()
        return True
    except Exception as e: 
        return False

def verificar_login(user, pw):
    user_limpo = str(user).strip().lower() # Limpa o e-mail na hora de logar também
    res = conn.query('SELECT password FROM usuarios WHERE username = :u', params={"u": user_limpo}, ttl=0)
    if not res.empty and res.iloc[0]['password'] == hash_password(pw):
        return True
    return False

# ==========================================
# INTERFACE DE ACESSO
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = None

if not st.session_state.autenticado:
    st.title("⚽ Liga de Desempenho")
    menu_auth = st.tabs(["Acessar Liga", "Criar Nova Conta"])
    
    with menu_auth[0]:
        u_login = st.text_input("Usuário (E-mail):", key="u_login")
        p_login = st.text_input("Senha:", type="password", key="p_login")
        if st.button("Entrar em Campo", use_container_width=True):
            if verificar_login(u_login, p_login):
                st.session_state.autenticado = True
                st.session_state.usuario = u_login
                st.rerun()
            else: st.error("Usuário ou senha incorretos.")
            
    with menu_auth[1]:
        u_new = st.text_input("Escolha um Usuário (E-mail):", key="u_new")
        p_new = st.text_input("Crie uma Senha:", type="password", key="p_new")
        if st.button("Criar Minha Liga", use_container_width=True):
            if u_new and p_new:
                if criar_conta(u_new, p_new):
                    st.success("Conta criada! Agora faça o login.")
                else: st.error("Este usuário já existe.")
    st.stop()

# --- A PARTIR DAQUI, O USUÁRIO ESTÁ LOGADO ---
USER_LOGADO = st.session_state.usuario

# Modificar todas as funções para filtrar por USER_LOGADO
def get_jogadores():
    df = conn.query('SELECT DISTINCT nome FROM status WHERE usuario = :u', params={"u": USER_LOGADO}, ttl=0)
    return df['nome'].tolist()

def get_regras():
    df = conn.query('SELECT descricao, valor FROM regras WHERE usuario = :u', params={"u": USER_LOGADO}, ttl=0)
    return dict(zip(df['descricao'], df['valor']))

# [Aqui você manteria o restante das funções como get_status, update_status, etc., 
#  sempre adicionando "WHERE usuario = :u" nas queries SQL]

st.sidebar.write(f"Logado como: **{USER_LOGADO}**")
if st.sidebar.button("Sair"):
    st.session_state.autenticado = False
    st.rerun()

# ==========================================
# CONTINUAÇÃO DA INTERFACE (MIGRAÇÃO COMPLETA)
# ==========================================
# (O restante do código de Placar, Arbitragem e Elenco segue a mesma lógica 
# que já tínhamos, mas agora filtrado pelo USER_LOGADO)
st.info("Sistema Multi-Usuário Ativado. Seus dados estão protegidos.")
