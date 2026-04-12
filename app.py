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
import urllib.parse

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E PWA E CSS
# ==========================================
st.set_page_config(page_title="Liga de Desempenho", page_icon="⚽", layout="centered")

st.markdown("""
    <link rel="manifest" href="https://cdn.jsdelivr.net/gh/robertoaraujo77/Liga_de_Desempenho@main/static/manifest.json" crossorigin="anonymous">
    <style>
    /* Ajustes para Celular e Quebra de Linha nas Abas */
    button[data-baseweb="tab"] {
        white-space: nowrap !important;
        font-size: 14px !important;
    }
    @media (max-width: 768px) {
        h1 { font-size: 1.6rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
        button[data-baseweb="tab"] { 
            font-size: 11px !important; 
            padding: 8px 10px !important; 
            margin-right: 0px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

PEDRAS = ["Ouro 🥇", "Prata 🥈", "Bronze 🥉", "Diamante 💎", "Alexandrita 💠", "Painite 🩸", "Musgravite 🪨", "Opala Negra 🌌", "Esmeralda 🟩", "Rubi 🔴", "Safira 🔷", "Tanzanita 🪻", "Turmalina 🍉", "Topázio 🔶", "Jade 🟢"]
ESTILOS_AVATAR = {"🧑 Desenho Moderno": "notionists", "🤠 Aventureiro": "adventurer", "🤖 Robô": "bottts", "😎 Emoji Divertido": "fun-emoji", "🧑‍🎨 Retrato Elegante": "micah", "👾 Pixel Art": "pixel-art"}

# ==========================================
# UTILITÁRIOS E SEGURANÇA
# ==========================================
def hash_password(password):
    senha_limpa = str(password).strip()
    return hashlib.sha256(str.encode(senha_limpa)).hexdigest()

def converter_para_base64(image):
    image = image.resize((150, 150), Image.Resampling.LANCZOS)
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"

# ==========================================
# CONEXÃO E BANCO DE DADOS
# ==========================================
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        s.execute(text('CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT)'))
        s.execute(text('''CREATE TABLE IF NOT EXISTS status (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, nivel TEXT, base REAL, saldo REAL, faltas REAL, aguardando_resgate INTEGER DEFAULT 0, avatar TEXT, base_inicial REAL, incremento REAL, teto_maximo REAL, titulos INTEGER, limite_faltas REAL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS historico (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, data TEXT, infracao TEXT, desconto REAL, tipo TEXT)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS trofeus (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, data TEXT, nivel TEXT, saldo REAL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS regras (id SERIAL PRIMARY KEY, usuario TEXT, descricao TEXT, valor REAL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS notificacoes (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, mensagem TEXT, lida INTEGER DEFAULT 0, data TEXT)'''))
        
        # Nova Tabela Exclusiva para os Bônus
        s.execute(text('''CREATE TABLE IF NOT EXISTS bonus_regras (id SERIAL PRIMARY KEY, usuario TEXT, descricao TEXT, valor REAL)'''))
        
        res_cols = s.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='status'")).fetchall()
        cols = [r[0] for r in res_cols]
        if 'pin_jogador' not in cols: s.execute(text("ALTER TABLE status ADD COLUMN pin_jogador TEXT"))
        if 'meta_descricao' not in cols: s.execute(text("ALTER TABLE status ADD COLUMN meta_descricao TEXT"))
        if 'meta_valor' not in cols: s.execute(text("ALTER TABLE status ADD COLUMN meta_valor REAL"))
        
        s.commit()

init_db()

# --- LÓGICA DE AUTENTICAÇÃO E REGRAS PADRÃO ---
def criar_conta(user, pw):
    user_limpo = str(user).strip().lower()
    try:
        with conn.session as s:
            s.execute(text('INSERT INTO usuarios (username, password) VALUES (:u, :p)'), 
                      {"u": user_limpo, "p": hash_password(pw)})
            
            # Pack Inicial de Faltas
            regras_padrao = [
                {"u": user_limpo, "d": "🚿 Toalha molhada na cama", "v": 2.0},
                {"u": user_limpo, "d": "🥱 Acordar reclamando", "v": 1.0},
                {"u": user_limpo, "d": "📚 Não fazer a lição de casa", "v": 5.0},
                {"u": user_limpo, "d": "🎮 Passou do limite de telas", "v": 3.0},
                {"u": user_limpo, "d": "🗣️ Desrespeito com os pais", "v": 5.0},
                {"u": user_limpo, "d": "🤬 Palavrão", "v": 3.0},
                {"u": user_limpo, "d": "🛏️ Não arrumou o quarto", "v": 2.0},
                {"u": user_limpo, "d": "🟥 Desobedecer (Vermelho Direto)", "v": 20.0}
            ]
            s.execute(text('INSERT INTO regras (usuario, descricao, valor) VALUES (:u, :d, :v)'), regras_padrao)
            
            # Pack Inicial de Bônus
            bonus_padrao = [
                {"u": user_limpo, "d": "🛏️ Arrumou a cama cedo", "v": 2.0},
                {"u": user_limpo, "d": "🍽️ Ajudou a lavar a louça", "v": 3.0},
                {"u": user_limpo, "d": "📖 Leu um livro (30 min)", "v": 5.0},
                {"u": user_limpo, "d": "🧹 Ajudou na limpeza da casa", "v": 5.0},
                {"u": user_limpo, "d": "🌟 Elogio na escola", "v": 5.0},
                {"u": user_limpo, "d": "🥗 Comeu toda a salada/verdura", "v": 2.0}
            ]
            s.execute(text('INSERT INTO bonus_regras (usuario, descricao, valor) VALUES (:u, :d, :v)'), bonus_padrao)
            
            s.commit()
        return True
    except Exception: return False

def verificar_login_pai(user, pw):
    user_limpo = str(user).strip().lower()
    res = conn.query('SELECT password FROM usuarios WHERE username = :u', params={"u": user_limpo}, ttl=0)
    if not res.empty and res.iloc[0]['password'] == hash_password(pw): return True
    return False

def verificar_login_atleta(user, nome_atleta, pin_digitado):
    user_limpo = str(user).strip().lower()
    res = conn.query('SELECT pin_jogador FROM status WHERE usuario = :u AND LOWER(nome) = LOWER(:n)', params={"u": user_limpo, "n": str(nome_atleta).strip()}, ttl=0)
    if not res.empty:
        pin_banco = res.iloc[0]['pin_jogador']
        if pd.notna(pin_banco) and pin_banco == hash_password(pin_digitado): return True
    return False

# --- FUNÇÕES DE REGRAS E BÔNUS (DINÂMICAS) ---
def get_regras():
    df = conn.query('SELECT descricao, valor FROM regras WHERE usuario = :u', params={"u": USER_LOGADO}, ttl=0)
    res = list(df.itertuples(index=False, name=None))
    def sort_key(item):
        texto = item[0]
        match = re.search(r'[a-zA-ZÀ-ÿ0-9]', texto)
        return texto[match.start():].lower() if match else texto.lower()
    return dict(sorted(res, key=sort_key))

def add_regra(descricao, valor):
    with conn.session as s:
        s.execute(text('INSERT INTO regras (usuario, descricao, valor) VALUES (:u, :d, :v)'), {"u": USER_LOGADO, "d": descricao, "v": valor})
        s.commit()

def update_regra(descricao_antiga, nova_descricao, novo_valor):
    with conn.session as s:
        s.execute(text('UPDATE regras SET descricao = :nd, valor = :nv WHERE descricao = :da AND usuario = :u'), {"nd": nova_descricao, "nv": novo_valor, "da": descricao_antiga, "u": USER_LOGADO})
        s.commit()

def delete_regra(descricao):
    with conn.session as s:
        s.execute(text('DELETE FROM regras WHERE descricao = :d AND usuario = :u'), {"d": descricao, "u": USER_LOGADO})
        s.commit()

def get_bonus_regras():
    df = conn.query('SELECT descricao, valor FROM bonus_regras WHERE usuario = :u', params={"u": USER_LOGADO}, ttl=0)
    # Se a tabela estiver vazia para a sua conta antiga, injeta os bônus padrão automaticamente
    if df.empty:
        bonus_padrao = [
            {"u": USER_LOGADO, "d": "🛏️ Arrumou a cama cedo", "v": 2.0},
            {"u": USER_LOGADO, "d": "🍽️ Ajudou a lavar a louça", "v": 3.0},
            {"u": USER_LOGADO, "d": "📖 Leu um livro (30 min)", "v": 5.0},
            {"u": USER_LOGADO, "d": "🧹 Ajudou na limpeza da casa", "v": 5.0},
            {"u": USER_LOGADO, "d": "🌟 Elogio na escola", "v": 5.0},
            {"u": USER_LOGADO, "d": "🥗 Comeu toda a salada/verdura", "v": 2.0}
        ]
        with conn.session as s:
            s.execute(text('INSERT INTO bonus_regras (usuario, descricao, valor) VALUES (:u, :d, :v)'), bonus_padrao)
            s.commit()
        df = pd.DataFrame(bonus_padrao).rename(columns={"d": "descricao", "v": "valor"})

    res = list(df[['descricao', 'valor']].itertuples(index=False, name=None))
    def sort_key(item):
        texto = item[0]
        match = re.search(r'[a-zA-ZÀ-ÿ0-9]', texto)
        return texto[match.start():].lower() if match else texto.lower()
    return dict(sorted(res, key=sort_key))

def add_bonus_regra(descricao, valor):
    with conn.session as s:
        s.execute(text('INSERT INTO bonus_regras (usuario, descricao, valor) VALUES (:u, :d, :v)'), {"u": USER_LOGADO, "d": descricao, "v": valor})
        s.commit()

def update_bonus_regra(descricao_antiga, nova_descricao, novo_valor):
    with conn.session as s:
        s.execute(text('UPDATE bonus_regras SET descricao = :nd, valor = :nv WHERE descricao = :da AND usuario = :u'), {"nd": nova_descricao, "nv": novo_valor, "da": descricao_antiga, "u": USER_LOGADO})
        s.commit()

def delete_bonus_regra(descricao):
    with conn.session as s:
        s.execute(text('DELETE FROM bonus_regras WHERE descricao = :d AND usuario = :u'), {"d": descricao, "u": USER_LOGADO})
        s.commit()

# --- FUNÇÕES DE NOTIFICAÇÃO (SININHO) ---
def add_notificacao(jogador, mensagem):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    with conn.session as s:
        s.execute(text('INSERT INTO notificacoes (usuario, nome, mensagem, lida, data) VALUES (:u, :n, :m, 0, :d)'), 
                  {"u": USER_LOGADO, "n": str(jogador), "m": str(mensagem), "d": agora})
        s.commit()

def get_notificacoes_nao_lidas(jogador, usuario):
    return conn.query('SELECT id, mensagem, data FROM notificacoes WHERE LOWER(nome) = LOWER(:n) AND usuario = :u AND lida = 0 ORDER BY id ASC', params={"n": jogador, "u": usuario}, ttl=0)

def marcar_notificacoes_lidas(jogador, usuario):
    with conn.session as s:
        s.execute(text('UPDATE notificacoes SET lida = 1 WHERE LOWER(nome) = LOWER(:n) AND usuario = :u AND lida = 0'), {"n": jogador, "u": usuario})
        s.commit()

# --- FUNÇÕES DE STATUS E HISTÓRICO ---
def get_jogadores():
    df = conn.query('SELECT DISTINCT nome FROM status WHERE usuario = :u', params={"u": USER_LOGADO}, ttl=0)
    return df['nome'].tolist()

def get_status(jogador):
    df = conn.query('SELECT nivel, base, saldo, faltas, aguardando_resgate, avatar, base_inicial, incremento, teto_maximo, titulos, limite_faltas, pin_jogador, meta_descricao, meta_valor FROM status WHERE LOWER(nome) = LOWER(:n) AND usuario = :u', params={"n": jogador, "u": USER_LOGADO}, ttl=0)
    if not df.empty:
        row = df.iloc[0].to_dict()
        return (row['nivel'], row['base'], row['saldo'], row['faltas'], row['aguardando_resgate'],
                row['avatar'], row['base_inicial'], row['incremento'], float(row['teto_maximo']), int(row['titulos']), float(row['limite_faltas']), row['pin_jogador'], row['meta_descricao'], float(row['meta_valor'] if row['meta_valor'] else 0))
    return None

def update_status_saldo(jogador, nivel, base, saldo, faltas, aguardando, avatar, titulos, teto_maximo, limite_faltas):
    with conn.session as s:
        s.execute(text('UPDATE status SET nivel=:n, base=:b, saldo=:s, faltas=:f, aguardando_resgate=:ag, avatar=:av, titulos=:t, teto_maximo=:tm, limite_faltas=:lf WHERE LOWER(nome)=LOWER(:nome) AND usuario=:u'), 
                  {"n": str(nivel), "b": float(base), "s": float(saldo), "f": float(faltas), "ag": int(aguardando), "av": str(avatar), "nome": str(jogador), "t": int(titulos), "tm": float(teto_maximo), "lf": float(limite_faltas), "u": USER_LOGADO})
        s.commit()

def add_jogador(nome, estilo_avatar, base_inicial, incremento, teto_maximo, limite_faltas, pin_jogador, meta_desc, meta_val):
    with conn.session as s:
        # AQUI É A MÁGICA DA TEMPORADA ZERO: O Saldo e a Base começam zerados.
        s.execute(text('INSERT INTO status (usuario, nome, nivel, base, saldo, faltas, aguardando_resgate, avatar, base_inicial, incremento, teto_maximo, titulos, limite_faltas, pin_jogador, meta_descricao, meta_valor) VALUES (:u, :n, :niv, :b, :s, :f, :ag, :av, :bi, :inc, :tm, 0, :lf, :pin, :mdesc, :mval)'), 
                  {"u": USER_LOGADO, "n": nome, "niv": "Em Avaliação 🕵️‍♂️", "b": 0.0, "s": 0.0, "f": 0.0, "ag": 0, "av": estilo_avatar, "bi": base_inicial, "inc": incremento, "tm": teto_maximo, "lf": limite_faltas, "pin": hash_password(pin_jogador), "mdesc": meta_desc, "mval": meta_val})
        s.commit()

def edit_jogador(nome_antigo, novo_nome, estilo_avatar, base_inicial, incremento, teto_maximo, limite_faltas, pin_jogador, meta_desc, meta_val, change_pin):
    with conn.session as s:
        query = 'UPDATE status SET nome=:nn, avatar=:av, base_inicial=:bi, incremento=:inc, teto_maximo=:tm, limite_faltas=:lf, meta_descricao=:mdesc, meta_valor=:mval'
        params = {"nn": novo_nome, "av": estilo_avatar, "bi": float(base_inicial), "inc": float(incremento), "tm": float(teto_maximo), "lf": float(limite_faltas), "mdesc": meta_desc, "mval": float(meta_val), "na": nome_antigo, "u": USER_LOGADO}
        if change_pin:
            query += ', pin_jogador=:pin'
            params['pin'] = hash_password(pin_jogador)
        query += ' WHERE LOWER(nome)=LOWER(:na) AND usuario=:u'
        
        s.execute(text(query), params)
        if nome_antigo != novo_nome:
            s.execute(text('UPDATE historico SET nome=:nn WHERE LOWER(nome)=LOWER(:na) AND usuario=:u'), {"nn": novo_nome, "na": nome_antigo, "u": USER_LOGADO})
            s.execute(text('UPDATE trofeus SET nome=:nn WHERE LOWER(nome)=LOWER(:na) AND usuario=:u'), {"nn": novo_nome, "na": nome_antigo, "u": USER_LOGADO})
            s.execute(text('UPDATE notificacoes SET nome=:nn WHERE LOWER(nome)=LOWER(:na) AND usuario=:u'), {"nn": novo_nome, "na": nome_antigo, "u": USER_LOGADO})
        s.commit()

def delete_jogador(nome):
    with conn.session as s:
        s.execute(text('DELETE FROM status WHERE LOWER(nome) = LOWER(:n) AND usuario = :u'), {"n": nome, "u": USER_LOGADO})
        s.execute(text('DELETE FROM historico WHERE LOWER(nome) = LOWER(:n) AND usuario = :u'), {"n": nome, "u": USER_LOGADO})
        s.execute(text('DELETE FROM trofeus WHERE LOWER(nome) = LOWER(:n) AND usuario = :u'), {"n": nome, "u": USER_LOGADO})
        s.execute(text('DELETE FROM notificacoes WHERE LOWER(nome) = LOWER(:n) AND usuario = :u'), {"n": nome, "u": USER_LOGADO})
        s.commit()

def add_historico(jogador, infracao, valor, tipo='falta'):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    with conn.session as s:
        s.execute(text('INSERT INTO historico (usuario, nome, data, infracao, desconto, tipo) VALUES (:u, :n, :d, :i, :v, :t)'), 
                  {"u": USER_LOGADO, "n": str(jogador), "d": agora, "i": str(infracao), "v": float(valor), "t": str(tipo)})
        s.commit()

def get_historico(jogador):
    return conn.query('SELECT data, infracao, desconto, tipo FROM historico WHERE LOWER(nome) = LOWER(:n) AND usuario = :u ORDER BY id DESC', params={"n": jogador, "u": USER_LOGADO}, ttl=0)

def get_historico_admin(jogador):
    return conn.query('SELECT id, data, infracao, desconto, tipo FROM historico WHERE LOWER(nome) = LOWER(:n) AND usuario = :u ORDER BY id DESC', params={"n": jogador, "u": USER_LOGADO}, ttl=0)

def delete_specific_historico(jogador, id_item, valor_item, tipo_item):
    with conn.session as s:
        s.execute(text('DELETE FROM historico WHERE id = :id AND usuario = :u'), {"id": int(id_item), "u": USER_LOGADO})
        s.commit()
    dados_jogador = get_status(jogador)
    if dados_jogador:
        nivel, base, saldo, faltas, aguardando, avatar, base_ini, inc, teto, titulos, limite, pin, mdesc, mval = dados_jogador
        if tipo_item == 'falta':
            novo_saldo = saldo + float(valor_item)
            novas_faltas = max(0.0, faltas - float(valor_item))
        elif tipo_item == 'compra':
            novo_saldo = saldo + float(valor_item)
            novas_faltas = faltas
        else: 
            novo_saldo = saldo - float(valor_item)
            novas_faltas = faltas
        update_status_saldo(jogador, nivel, base, novo_saldo, novas_faltas, aguardando, avatar, titulos, teto, limite)

def clear_historico(jogador):
    with conn.session as s:
        s.execute(text('DELETE FROM historico WHERE LOWER(nome) = LOWER(:n) AND usuario = :u'), {"n": jogador, "u": USER_LOGADO})
        s.commit()

def add_trofeu(jogador, nivel, saldo):
    meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    mes_atual = meses[datetime.now().month]
    ano_atual = datetime.now().year
    with conn.session as s:
        s.execute(text('INSERT INTO trofeus (usuario, nome, data, nivel, saldo) VALUES (:u, :n, :d, :niv, :s)'), 
                  {"u": USER_LOGADO, "n": str(jogador), "d": f"{mes_atual}/{ano_atual}", "niv": str(nivel), "s": float(saldo)})
        s.commit()

def get_trofeus(jogador):
    return conn.query('SELECT data as Data, nivel as Divisão, saldo as Recompensa FROM trofeus WHERE LOWER(nome) = LOWER(:n) AND usuario = :u ORDER BY id DESC', params={"n": jogador, "u": USER_LOGADO}, ttl=0)

# ==========================================
# MOTOR MATEMÁTICO E CARD DO ATLETA
# ==========================================
def get_info_campeonato(base_inicial, incremento, teto_maximo, base_atual, nivel_atual):
    inc = max(incremento, 1.0)
    saltos_totais = int(round((teto_maximo - base_inicial) / inc))
    qtd_divisoes = saltos_totais + 1

    divisoes = []
    for i in range(qtd_divisoes):
        valor = base_inicial + (i * inc)
        num_divisao = qtd_divisoes - i
        pedra_idx = min(num_divisao - 1, len(PEDRAS) - 1)
        divisoes.append({"nome": f"{num_divisao}ª Divisão - {PEDRAS[pedra_idx]}", "valor": valor, "num_divisao": num_divisao})

    divisoes = sorted(divisoes, key=lambda x: x["valor"])
    
    if nivel_atual == "Em Avaliação 🕵️‍♂️":
        return divisoes, {"nome": "Em Avaliação 🕵️‍♂️", "valor": 0}, -1

    div_atual = divisoes[0]
    index_atual = 0
    for idx, div in enumerate(divisoes):
        if abs(div["valor"] - base_atual) < 0.1: 
            div_atual = div
            index_atual = idx
            break

    return divisoes, div_atual, index_atual

def render_carta_atleta(nome_jogador, estilo_avatar, div_nome, saldo, base, faltas, titulos):
    img_src = estilo_avatar if estilo_avatar.startswith("data:image") else f"https://api.dicebear.com/7.x/{estilo_avatar}/svg?seed={nome_jogador}&backgroundColor=e2e8f0"
    score_val = 99
    bonus_acumulado = max(0, saldo - (base - faltas))
    score_val -= int(faltas * 5)
    score_val += int(bonus_acumulado * 3)
    score_val = min(99, max(40, score_val)) 

    bg_gradient = "linear-gradient(135deg, #2b32b2 0%, #1488cc 100%)"
    if "Ouro" in div_nome: bg_gradient = "linear-gradient(135deg, #e6c27a 0%, #d4af37 50%, #997328 100%)"
    elif "Prata" in div_nome: bg_gradient = "linear-gradient(135deg, #e3e3e3 0%, #b5b5b5 50%, #8a8a8a 100%)"
    elif "Bronze" in div_nome: bg_gradient = "linear-gradient(135deg, #cd7f32 0%, #a0522d 50%, #8b4513 100%)"
    elif "Diamante" in div_nome: bg_gradient = "linear-gradient(135deg, #b9f2ff 0%, #6dd5ed 50%, #2193b0 100%)"
    elif "Alexandrita" in div_nome: bg_gradient = "linear-gradient(135deg, #8A2BE2 0%, #4B0082 100%)"
    elif "Esmeralda" in div_nome: bg_gradient = "linear-gradient(135deg, #00C9FF 0%, #92FE9D 100%)"
    elif "Rubi" in div_nome: bg_gradient = "linear-gradient(135deg, #ff0844 0%, #ffb199 100%)"
    elif "Em Avaliação" in div_nome: bg_gradient = "linear-gradient(135deg, #4b5563 0%, #1f2937 100%)"

    texto_titulos = f"<div style='font-size: 11px; color: #1a1a1a; margin-top: 5px; font-weight: 900; background: rgba(255,255,255,0.4); padding: 2px; border-radius: 5px;'>🏆 {titulos}x CAMPEÃO ELITE</div>" if titulos > 0 else "<div style='display:none;'></div>"

    st.markdown(f'''
<div style="display: flex; justify-content: center; margin-bottom: 25px;">
    <div style="background: {bg_gradient}; border-radius: 12px; width: 220px; padding: 15px; color: #1a1a1a; box-shadow: 0 8px 16px rgba(0,0,0,0.6); text-align: center; border: 2px solid #fff; position: relative; overflow: hidden;">
        <div style="position: absolute; top: 10px; left: 15px; text-align: center;">
            <div style="font-size: 32px; font-weight: 900; line-height: 1;">{score_val}</div>
            <div style="font-size: 10px; font-weight: bold; text-transform: uppercase;">SCORE</div>
        </div>
        <img src="{img_src}" style="width: 90px; height: 90px; border-radius: 50%; margin: 15px 0 5px 0; border: 3px solid #1a1a1a; background-color: #e2e8f0; object-fit: cover;">
        <div style="font-size: 18px; font-weight: 900; text-transform: uppercase; margin-bottom: 2px; letter-spacing: 0.5px;">{nome_jogador}</div>
        <div style="font-size: 12px; font-weight: 700; border-top: 1px solid rgba(0,0,0,0.2); padding-top: 4px;">{div_nome}</div>
        {texto_titulos}
    </div>
</div>
''', unsafe_allow_html=True)

# ==========================================
# POPUPS E ANIMAÇÕES
# ==========================================
def mostrar_popup(titulo, mensagem, cor, emoji):
    aviso = st.empty()
    with aviso.container():
        st.markdown(f"""
            <div style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(0,0,0,0.85); z-index: 999999; display: flex; justify-content: center; align-items: center;">
                <div style="background-color: #1e1e1e; padding: 40px 60px; border-radius: 20px; text-align: center; border: 3px solid {cor}; box-shadow: 0 10px 40px rgba(0,0,0,0.9); max-width: 80%;">
                    <div style="font-size: 80px; margin-bottom: 10px;">{emoji}</div>
                    <h1 style="color: {cor}; margin: 0; font-size: 32px; font-weight: bold;">{titulo}</h1>
                    <p style="color: #ffffff; font-size: 20px; margin-top: 15px;">{mensagem}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    time.sleep(5)
    aviso.empty()
    st.rerun()

if 'animacao_classificacao' in st.session_state and st.session_state.animacao_classificacao:
    st.session_state.animacao_classificacao = False
    st.balloons()
    mostrar_popup("CONTRATO ASSINADO!", f"Sua avaliação terminou. Você está na<br><b>{st.session_state.nome_pedra_classificacao}</b>!", "#17a2b8", "📝🤝")
if 'animacao_titulo' in st.session_state and st.session_state.animacao_titulo:
    st.session_state.animacao_titulo = False
    st.balloons()
    mostrar_popup("CAMPEÃO DA ELITE!", "Você manteve a Coroa na 1ª Divisão!", "#ffd700", "🏆👑")
if 'animacao_vitoria' in st.session_state and st.session_state.animacao_vitoria:
    st.session_state.animacao_vitoria = False
    st.balloons()
    mostrar_popup("SUBIU DE DIVISÃO!", f"Excelente! Você alcançou a<br><b>{st.session_state.nome_pedra_vitoria}</b>", "#28a745", "⬆️🚀")
if 'animacao_derrota' in st.session_state and st.session_state.animacao_derrota:
    st.session_state.animacao_derrota = False
    mostrar_popup("REBAIXADO!", f"O limite estourou. Você caiu para a<br><b>{st.session_state.nome_pedra_derrota}</b>...", "#dc3545", "⬇️🟥")
if 'animacao_manter' in st.session_state and st.session_state.animacao_manter:
    st.session_state.animacao_manter = False
    mostrar_popup("QUASE!", "Não subiu, mas escapou do rebaixamento. Foco no próximo mês!", "#fd7e14", "↪️⚠️")

# ==========================================
# TELA DE ACESSO DUPLO & LINK MÁGICO
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.tipo_conta = None 
    st.session_state.usuario = None
    st.session_state.jogador_atual = None

# Lendo o Link Mágico da URL
params = st.query_params
magic_equipe = params.get("equipe")
magic_atleta = params.get("atleta")

if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center;'>⚽ Liga de Desempenho ⚽</h1>", unsafe_allow_html=True)
    
    # Se o atleta entrou pelo Link Mágico
    if magic_equipe and magic_atleta:
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1488cc, #2b32b2); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
                <h2 style="color: white; margin:0;">Vestiário</h2>
                <h4 style="color: #e2e8f0; margin-top:5px;">Bem-vindo, {magic_atleta}!</h4>
            </div>
        """, unsafe_allow_html=True)
        
        st.info("O acesso rápido está ativado pelo seu Link Mágico.")
        
        with st.form("form_login_magico"):
            p_atleta_magic = st.text_input("Digite seu PIN de Segurança (4 dígitos):", type="password", max_chars=4)
            btn_entrar = st.form_submit_button("Entrar em Campo", use_container_width=True, type="primary")
            
            if btn_entrar:
                if verificar_login_atleta(magic_equipe, magic_atleta, p_atleta_magic):
                    st.session_state.autenticado = True
                    st.session_state.tipo_conta = 'filho'
                    st.session_state.usuario = str(magic_equipe).strip().lower()
                    st.session_state.jogador_atual = str(magic_atleta).strip()
                    st.rerun()
                else: 
                    st.error("PIN incorreto. Tente novamente.")
            
        if st.button("Acesso da Comissão Técnica (Pais)"):
            st.query_params.clear()
            st.rerun()
            
        st.stop()

    # Tela de Login Normal (Sem Link Mágico)
    menu_auth = st.tabs(["👔 Comissão Técnica", "⚽ Vestiário", "Criar Liga"])
    
    with menu_auth[0]:
        st.markdown("**Acesso Exclusivo dos Pais**")
        with st.form("form_login_pais"):
            u_login = st.text_input("E-mail do Responsável:", key="u_login_pai")
            p_login = st.text_input("Senha Principal:", type="password", key="p_login_pai")
            btn_login_pai = st.form_submit_button("Entrar no Painel", use_container_width=True, type="primary")
            if btn_login_pai:
                if verificar_login_pai(u_login, p_login):
                    st.session_state.autenticado = True
                    st.session_state.tipo_conta = 'pai'
                    st.session_state.usuario = str(u_login).strip().lower()
                    st.rerun()
                else: 
                    st.error("Usuário ou senha incorretos.")

    with menu_auth[1]:
        st.markdown("**Acesso do Atleta**")
        with st.form("form_login_atleta"):
            u_resp = st.text_input("E-mail dos seus pais:", key="u_login_filho")
            n_atleta = st.text_input("Seu Nome no Jogo:", key="n_login_filho")
            p_atleta = st.text_input("Seu PIN (4 dígitos):", type="password", key="p_login_filho", max_chars=4)
            btn_login_atleta = st.form_submit_button("Entrar em Campo", use_container_width=True, type="primary")
            if btn_login_atleta:
                if verificar_login_atleta(u_resp, n_atleta, p_atleta):
                    st.session_state.autenticado = True
                    st.session_state.tipo_conta = 'filho'
                    st.session_state.usuario = str(u_resp).strip().lower()
                    st.session_state.jogador_atual = str(n_atleta).strip()
                    st.rerun()
                else: 
                    st.error("Dados incorretos. Verifique com seu treinador.")
            
    with menu_auth[2]:
        with st.form("form_criar_conta"):
            u_new = st.text_input("E-mail Responsável:", key="u_new")
            p_new = st.text_input("Crie uma Senha:", type="password", key="p_new")
            btn_criar = st.form_submit_button("Criar Minha Liga", use_container_width=True)
            if btn_criar:
                if u_new and p_new:
                    if criar_conta(u_new, p_new): 
                        st.success("Conta criada! Logue na 'Comissão Técnica'.")
                    else: 
                        st.error("Este usuário já existe.")
                else: 
                    st.error("Preencha todos os campos.")
            
    st.stop()

# ==========================================
# ÁREA RESTRITA (SISTEMA BASE)
# ==========================================
USER_LOGADO = st.session_state.usuario
TIPO_CONTA = st.session_state.tipo_conta

if TIPO_CONTA == 'pai': st.sidebar.write(f"👔 Comissão: **{USER_LOGADO}**")
else: st.sidebar.write(f"⚽ Atleta: **{st.session_state.jogador_atual}**")

if st.sidebar.button("Sair"):
    st.session_state.autenticado = False
    st.query_params.clear()
    st.rerun()

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
jogadores_ativos = get_jogadores()
jogador_selecionado = None

if TIPO_CONTA == 'filho':
    jogador_selecionado = st.session_state.jogador_atual
else:
    if len(jogadores_ativos) > 1:
        st.markdown("<div style='text-align: center; margin-bottom: 20px;'>", unsafe_allow_html=True)
        jogador_selecionado = st.selectbox("👤 Analisando Perfil:", jogadores_ativos, label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
    elif len(jogadores_ativos) == 1:
        jogador_selecionado = jogadores_ativos[0]
    else:
        st.info("👋 **Bem-vindo à Comissão Técnica!** Vá para a aba '⚙️ Elenco' abaixo e escale seu primeiro Atleta!")

if jogador_selecionado:
    dados_jogador = get_status(jogador_selecionado)
    if dados_jogador:
        nivel_atual, base_atual, saldo_atual, faltas_atual, aguardando_resgate, estilo_avatar, base_inicial, incremento, teto_maximo, titulos, limite_faltas, pin_jog, meta_desc, meta_val = dados_jogador
        divisoes, div_atual, index_atual = get_info_campeonato(base_inicial, incremento, teto_maximo, base_atual, nivel_atual)
        
        # --- LÓGICA DO BOTÃO SURPRESA (SÓ PARA O ATLETA) ---
        if aguardando_resgate == 1 and TIPO_CONTA == 'filho':
            render_carta_atleta(jogador_selecionado, estilo_avatar, div_atual["nome"], saldo_atual, base_atual, faltas_atual, titulos)
            st.info(f"🚨 **Atenção {jogador_selecionado}!** A comissão técnica encerrou a temporada.")
            st.markdown("<h3 style='text-align: center;'>Chegou a hora de descobrir o seu destino...</h3><br>", unsafe_allow_html=True)
            
            if st.button("🎁 CLIQUE AQUI PARA VER SEU RESULTADO", type="primary", use_container_width=True):
                df_historico = get_historico(jogador_selecionado)
                teve_vermelho = False
                if not df_historico.empty: teve_vermelho = any("Cartão Vermelho" in str(inf) for inf in df_historico['infracao'])

                if nivel_atual == "Em Avaliação 🕵️‍♂️":
                    nova_divisao = divisoes[0]
                    novo_index = 0
                    for idx, div in enumerate(divisoes):
                        if saldo_atual >= div["valor"]:
                            nova_divisao = div
                            novo_index = idx
                    
                    nova_base = nova_divisao["valor"]
                    st.session_state.animacao_classificacao = True
                    st.session_state.nome_pedra_classificacao = nova_divisao["nome"]
                
                else:
                    novo_index = index_atual
                    animacao_tipo = None

                    if faltas_atual <= limite_faltas and not teve_vermelho:
                        if index_atual == len(divisoes) - 1:
                            titulos += 1
                            animacao_tipo = 'titulo'
                        else:
                            novo_index = index_atual + 1
                            animacao_tipo = 'vitoria'
                    else:
                        base_de_baixo = divisoes[index_atual - 1]["valor"] if index_atual > 0 else 0
                        if teve_vermelho or saldo_atual <= base_de_baixo:
                            if index_atual > 0: novo_index = index_atual - 1
                            animacao_tipo = 'derrota'
                        else:
                            novo_index = index_atual
                            animacao_tipo = 'manter'

                    nova_divisao = divisoes[novo_index]
                    nova_base = nova_divisao["valor"]

                    if animacao_tipo == 'titulo': st.session_state.animacao_titulo = True
                    elif animacao_tipo == 'vitoria': 
                        st.session_state.animacao_vitoria = True
                        st.session_state.nome_pedra_vitoria = nova_divisao["nome"]
                    elif animacao_tipo == 'derrota':
                        st.session_state.animacao_derrota = True
                        st.session_state.nome_pedra_derrota = nova_divisao["nome"]
                    elif animacao_tipo == 'manter': st.session_state.animacao_manter = True

                add_trofeu(jogador_selecionado, nova_divisao["nome"], saldo_atual)
                update_status_saldo(jogador_selecionado, nova_divisao["nome"], nova_base, nova_base, 0.0, aguardando=0, avatar=estilo_avatar, titulos=titulos, teto_maximo=teto_maximo, limite_faltas=limite_faltas)
                clear_historico(jogador_selecionado)
                st.rerun()
            st.stop()
            
        elif aguardando_resgate == 1 and TIPO_CONTA == 'pai':
            render_carta_atleta(jogador_selecionado, estilo_avatar, div_atual["nome"], saldo_atual, base_atual, faltas_atual, titulos)
            st.warning("⏳ **Temporada Encerrada!** O botão surpresa está esperando o atleta lá no vestiário.")
            if st.button("❌ Cancelar Fim de Temporada (Reabrir Mês)", use_container_width=True):
                update_status_saldo(jogador_selecionado, nivel_atual, base_atual, saldo_atual, faltas_atual, 0, estilo_avatar, titulos, teto_maximo, limite_faltas)
                st.rerun()
            st.stop()

        # --- EXIBIÇÃO DAS NOTIFICAÇÕES (APENAS PARA O ATLETA) ---
        if TIPO_CONTA == 'filho':
            notificacoes_ativas = get_notificacoes_nao_lidas(jogador_selecionado, USER_LOGADO)
            if not notificacoes_ativas.empty:
                st.markdown("""
                <div style="background-color: #ff4b4b; padding: 10px; border-radius: 10px; margin-bottom: 15px; border: 2px solid #fff; box-shadow: 0 4px 8px rgba(255, 75, 75, 0.3);">
                    <h4 style="color: white; margin: 0; text-align: center;">🔔 MENSAGENS DO ÁRBITRO</h4>
                </div>
                """, unsafe_allow_html=True)
                
                for _, notif in notificacoes_ativas.iterrows():
                    if "GOLAÇO" in notif['mensagem'] or "Parabéns" in notif['mensagem']:
                        st.success(f"**{notif['data']}** - {notif['mensagem']}")
                    else:
                        st.error(f"**{notif['data']}** - {notif['mensagem']}")
                
                if st.button("✅ Entendido! (Limpar Avisos)", use_container_width=True, type="primary"):
                    marcar_notificacoes_lidas(jogador_selecionado, USER_LOGADO)
                    st.rerun()
                st.markdown("---")

        # --- TELA NORMAL DO JOGADOR ---
        render_carta_atleta(jogador_selecionado, estilo_avatar, div_atual["nome"], saldo_atual, base_atual, faltas_atual, titulos)
        
        # FEATURE: META DA TEMPORADA
        if meta_val > 0 and meta_desc:
            progresso_meta = min((saldo_atual / meta_val) * 100, 100) if saldo_atual > 0 else 0
            st.markdown(f"**🎯 Grande Objetivo: {meta_desc}**")
            st.markdown(f"""
                <div style="background-color: #1a1a1a; border-radius: 10px; width: 100%; height: 22px; margin-bottom: 5px; border: 1px solid #333; position: relative;">
                    <div style="background: linear-gradient(90deg, #1488cc, #2b32b2); width: {progresso_meta}%; height: 100%; border-radius: 10px; transition: width 0.8s;"></div>
                    <div style="position: absolute; top: 0; left: 0; width: 100%; text-align: center; color: white; font-size: 12px; font-weight: bold; line-height: 22px; text-shadow: 1px 1px 2px black;">
                        {progresso_meta:.1f}% Concluído
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if progresso_meta >= 100: st.success(f"🎉 Você atingiu a meta para: **{meta_desc}**!")
            else: st.caption(f"Faltam R$ {(meta_val - saldo_atual):.2f} para alcançar a meta.".replace('.', ','))
            st.markdown("---")

        aba1, aba2 = st.tabs(["🏟️ Placar", "🏆 Sala de Troféus"])
        with aba1:
            col1, col2 = st.columns(2)
            col1.metric("Saldo Atual", f"R$ {max(0, saldo_atual):.2f}".replace('.', ','))
            col2.metric("Faltas", f"R$ {faltas_atual:.2f}".replace('.', ','), delta=f"- Limite: R$ {limite_faltas:.2f}".replace('.', ','), delta_color="inverse")

            porcentagem = min((faltas_atual / limite_faltas) * 100, 100) if limite_faltas > 0 else 100
            cor_barra = "#28a745" if porcentagem < 50 else "#fd7e14" if porcentagem < 100 else "#dc3545"
            st.markdown(f"**Tolerância de Faltas:**")
            st.markdown(f"""<div style="background-color: #2b2b2b; border-radius: 15px; width: 100%; height: 15px; margin-bottom: 10px; border: 1px solid #444;"><div style="background-color: {cor_barra}; width: {porcentagem}%; height: 100%; border-radius: 15px;"></div></div>""", unsafe_allow_html=True)

            df_hist_asc = conn.query('SELECT data, infracao, desconto, tipo FROM historico WHERE LOWER(nome) = LOWER(:n) AND usuario = :u ORDER BY id ASC', params={"n": jogador_selecionado, "u": USER_LOGADO}, ttl=0)
            timeline = [base_atual]
            curr = base_atual
            for _, row in df_hist_asc.iterrows():
                curr = curr + row['desconto'] if row['tipo'] == 'bonus' else curr - row['desconto']
                timeline.append(curr)
            if len(timeline) == 1: timeline.append(base_atual) 
            
            st.line_chart(timeline, height=150)

            df_historico = get_historico(jogador_selecionado)
            if not df_historico.empty:
                df_view = df_historico.copy()
                df_view['Lançamento'] = df_view.apply(lambda row: f"+ R$ {row['desconto']:.2f}".replace('.', ',') if row['tipo'] == 'bonus' else f"- R$ {row['desconto']:.2f}".replace('.', ','), axis=1)
                st.dataframe(df_view[['data', 'infracao', 'Lançamento']].rename(columns={'data': 'Data', 'infracao': 'Motivo'}), use_container_width=True, hide_index=True)

        with aba2:
            df_trofeus = get_trofeus(jogador_selecionado)
            if not df_trofeus.empty:
                df_trofeus.columns = ['Data', 'Divisão', 'Recompensa']
                df_trofeus['Recompensa'] = df_trofeus['Recompensa'].apply(lambda x: f"R$ {float(x):.2f}".replace('.', ','))
                st.dataframe(df_trofeus, use_container_width=True, hide_index=True)
            else: st.info(f"{jogador_selecionado} ainda não encerrou temporadas.")

# ==========================================
# PAINEL DA COMISSÃO TÉCNICA (SÓ PAIS)
# ==========================================
if TIPO_CONTA == 'pai':
    st.markdown("---")
    st.markdown("### 📋 Painel da Comissão Técnica")
    
    regras_dinamicas = get_regras()
    bonus_dinamicos = get_bonus_regras()
    
    tab_jogo, tab_configs, tab_elenco = st.tabs(["⚖️ Lançamentos", "📝 Regras e Bônus", "⚙️ Elenco"])
    
    with tab_jogo:
        if jogador_selecionado:
            st.markdown(f"**🔴 Aplicar Falta em {jogador_selecionado}**")
            with st.form("form_falta", clear_on_submit=True):
                if regras_dinamicas:
                    inf_sel = st.selectbox("Infração:", list(regras_dinamicas.keys()))
                    btn_aplicar = st.form_submit_button("Aplicar Falta", type="primary", use_container_width=True)
                    if btn_aplicar:
                        valor_falta = regras_dinamicas[inf_sel]
                        update_status_saldo(jogador_selecionado, nivel_atual, base_atual, saldo_atual - valor_falta, faltas_atual + valor_falta, 0, estilo_avatar, titulos, teto_maximo, limite_faltas)
                        add_historico(jogador_selecionado, inf_sel, valor_falta, 'falta')
                        add_notificacao(jogador_selecionado, f"🚨 Infração marcada: '{inf_sel}' (- R$ {valor_falta:.2f}).")
                        st.rerun()
                else:
                    st.warning("Crie regras na aba 'Regras e Bônus' primeiro.")
                    st.form_submit_button("Aguardando regras...")
                    
            st.markdown("---")
            st.markdown(f"**⭐ Aplicar Bônus (Golaço) para {jogador_selecionado}**")
            with st.form("form_bonus", clear_on_submit=True):
                if bonus_dinamicos:
                    m_bonus_sel = st.selectbox("Motivo do Bônus:", list(bonus_dinamicos.keys()))
                    btn_bonus = st.form_submit_button("Dar Bônus", use_container_width=True)
                    if btn_bonus:
                        v_bonus = bonus_dinamicos[m_bonus_sel]
                        update_status_saldo(jogador_selecionado, nivel_atual, base_atual, saldo_atual + v_bonus, faltas_atual, 0, estilo_avatar, titulos, teto_maximo, limite_faltas)
                        add_historico(jogador_selecionado, f"⭐ {m_bonus_sel}", v_bonus, 'bonus')
                        add_notificacao(jogador_selecionado, f"⚽ GOLAÇO! A comissão aplicou um bônus: '{m_bonus_sel}' (+ R$ {v_bonus:.2f}).")
                        st.rerun()
                else:
                    st.warning("Crie bônus na aba 'Regras e Bônus' primeiro.")
                    st.form_submit_button("Aguardando bônus...")
                
            if meta_val > 0 and meta_desc:
                st.markdown("---")
                st.markdown(f"**🛍️ Efetuar Compra do Prêmio: {meta_desc}**")
                if saldo_atual >= meta_val:
                    if st.button(f"✅ Confirmar Compra (- R$ {meta_val:.2f})", type="primary", use_container_width=True):
                        update_status_saldo(jogador_selecionado, nivel_atual, base_atual, saldo_atual - meta_val, faltas_atual, 0, estilo_avatar, titulos, teto_maximo, limite_faltas)
                        edit_jogador(jogador_selecionado, jogador_selecionado, estilo_avatar, base_inicial, incremento, teto_maximo, limite_faltas, pin_jog, "", 0.0, False)
                        add_historico(jogador_selecionado, f"🛍️ Comprou: {meta_desc}", meta_val, 'compra')
                        add_notificacao(jogador_selecionado, f"🏆 Parabéns! O prêmio '{meta_desc}' foi resgatado com sucesso pela comissão técnica.")
                        st.success("Compra efetuada! O saldo foi abatido.")
                        time.sleep(2)
                        st.rerun()
                else:
                    st.info(f"O atleta precisa de mais R$ {(meta_val - saldo_atual):.2f} para conseguir resgatar o prêmio.")
                    
            st.markdown("---")
            st.markdown("**🗑️ Excluir Lançamento Errado**")
            df_admin = get_historico_admin(jogador_selecionado)
            if not df_admin.empty:
                opcoes_falta = {f"{row['data']} | {row['infracao']}": (row['id'], row['desconto'], row['tipo']) for _, row in df_admin.iterrows()}
                with st.form("form_excluir"):
                    f_sel = st.selectbox("Selecione:", list(opcoes_falta.keys()), label_visibility="collapsed")
                    btn_excluir = st.form_submit_button("Excluir Item", use_container_width=True)
                    if btn_excluir:
                        id_f, v_item, t_item = opcoes_falta[f_sel]
                        delete_specific_historico(jogador_selecionado, id_f, v_item, t_item)
                        st.rerun()
            
            st.markdown("---")
            st.warning("🏁 **Encerrar Temporada** - Congela o saldo e libera a surpresa no app do atleta.")
            if st.button("✅ Autorizar Fim da Temporada", use_container_width=True):
                update_status_saldo(jogador_selecionado, nivel_atual, base_atual, saldo_atual, faltas_atual, 1, estilo_avatar, titulos, teto_maximo, limite_faltas)
                add_notificacao(jogador_selecionado, "⏱️ FIM DE JOGO! A temporada foi encerrada. Descubra se você subiu de divisão!")
                st.rerun()

    with tab_configs:
        sub_faltas, sub_bonus = st.tabs(["🔴 Faltas (Multas)", "⭐ Bônus (Golaços)"])
        
        with sub_faltas:
            st.markdown("**➕ Criar Nova Falta**")
            with st.form("form_criar_regra", clear_on_submit=True):
                c1, c2 = st.columns([3, 1])
                with c1: d_regra = st.text_input("Descrição da Falta:")
                with c2: v_regra = st.number_input("Valor R$:", min_value=0.50, step=0.50)
                btn_salvar_regra = st.form_submit_button("Salvar Falta", use_container_width=True)
                if btn_salvar_regra:
                    if d_regra and d_regra not in regras_dinamicas:
                        add_regra(d_regra, v_regra)
                        st.rerun()

            st.markdown("---")
            st.markdown("**✏️ Editar/Excluir Faltas**")
            if regras_dinamicas:
                r_sel = st.selectbox("Selecione a falta para editar:", list(regras_dinamicas.keys()))
                with st.form("form_editar_regra"):
                    c_ed1, c_ed2 = st.columns([3, 1])
                    with c_ed1: n_texto = st.text_input("Nova Descrição:", value=r_sel)
                    with c_ed2: n_val = st.number_input("Novo Valor R$:", value=float(regras_dinamicas[r_sel]), min_value=0.50)
                    c_btn1, c_btn2 = st.columns(2)
                    with c_btn1: btn_update_regra = st.form_submit_button("💾 Atualizar", use_container_width=True)
                    with c_btn2: btn_delete_regra = st.form_submit_button("🗑️ Excluir", use_container_width=True)
                    
                    if btn_update_regra:
                        update_regra(r_sel, n_texto, n_val)
                        st.rerun()
                    elif btn_delete_regra:
                        delete_regra(r_sel)
                        st.rerun()

        with sub_bonus:
            st.markdown("**➕ Criar Novo Bônus**")
            with st.form("form_criar_bonus", clear_on_submit=True):
                cb1, cb2 = st.columns([3, 1])
                with cb1: d_bonus = st.text_input("Descrição do Bônus:")
                with cb2: v_bonus = st.number_input("Valor R$:", min_value=0.50, step=0.50)
                btn_salvar_bonus = st.form_submit_button("Salvar Bônus", use_container_width=True)
                if btn_salvar_bonus:
                    if d_bonus and d_bonus not in bonus_dinamicos:
                        add_bonus_regra(d_bonus, v_bonus)
                        st.rerun()

            st.markdown("---")
            st.markdown("**✏️ Editar/Excluir Bônus**")
            if bonus_dinamicos:
                b_sel = st.selectbox("Selecione o bônus para editar:", list(bonus_dinamicos.keys()))
                with st.form("form_editar_bonus"):
                    cbe1, cbe2 = st.columns([3, 1])
                    with cbe1: nb_texto = st.text_input("Nova Descrição:", value=b_sel)
                    with cbe2: nb_val = st.number_input("Novo Valor R$:", value=float(bonus_dinamicos[b_sel]), min_value=0.50)
                    cbb1, cbb2 = st.columns(2)
                    with cbb1: btn_update_bonus = st.form_submit_button("💾 Atualizar", use_container_width=True)
                    with cbb2: btn_delete_bonus = st.form_submit_button("🗑️ Excluir", use_container_width=True)
                    
                    if btn_update_bonus:
                        update_bonus_regra(b_sel, nb_texto, nb_val)
                        st.rerun()
                    elif btn_delete_bonus:
                        delete_bonus_regra(b_sel)
                        st.rerun()

    with tab_elenco:
        sub_cad, sub_edit, sub_del, sub_link = st.tabs(["➕ Escalar", "✏️ Contrato", "❌ Demitir", "🔗 Convite"])
        with sub_cad:
            with st.form("form_escalar_novo", clear_on_submit=True):
                n_nome = st.text_input("Nome do Atleta:")
                n_avatar = st.selectbox("Avatar:", list(ESTILOS_AVATAR.keys()))
                c_b, c_i, c_t, c_l = st.columns(4)
                with c_b: b_ini = st.number_input("Piso Liga (R$):", value=50.0)
                with c_i: i_val = st.number_input("Aumento:", value=10.0)
                with c_t: t_val = st.number_input("Teto:", value=100.0)
                with c_l: l_val = st.number_input("Lim. Faltas:", value=5.0)
                
                st.markdown("**🔐 Acesso do Atleta e Prêmio**")
                c_pin, c_mdesc, c_mval = st.columns([1, 2, 1])
                with c_pin: pin_j = st.text_input("Crie o PIN (4 dig):", max_chars=4, placeholder="Ex: 1234")
                with c_mdesc: m_desc = st.text_input("Nome do Prêmio:", placeholder="Ex: Chuteira Nova")
                with c_mval: m_val = st.number_input("Valor do Prêmio (R$):", min_value=0.0, step=10.0)
                
                btn_cadastrar = st.form_submit_button("Cadastrar", type="primary", use_container_width=True)
                if btn_cadastrar:
                    if n_nome and pin_j and len(pin_j) == 4 and t_val > b_ini:
                        add_jogador(n_nome, ESTILOS_AVATAR[n_avatar], b_ini, i_val, t_val, l_val, pin_j, m_desc, m_val)
                        st.rerun()
                    else: st.error("Preencha o Nome, um PIN de 4 dígitos válido e confira os valores.")

        with sub_edit:
            if jogadores_ativos:
                j_edit = st.selectbox("Escolha o Atleta para ajustar o contrato:", jogadores_ativos, key="sel_edit")
                d_edit = get_status(j_edit)
                if d_edit:
                    with st.form("form_ajustar_contrato"):
                        ed_nome = st.text_input("Novo Nome:", value=j_edit)
                        st.caption("Deixe o PIN em branco caso não queira alterar.")
                        ed_pin = st.text_input("Novo PIN (opcional):", max_chars=4, placeholder="Ex: 4321")
                        
                        st.markdown("**🎯 Objetivo de Resgate (Prêmio)**")
                        ce_mdesc, ce_mval = st.columns([2, 1])
                        with ce_mdesc: ed_mdesc = st.text_input("Nome do Prêmio:", value=d_edit[12] if d_edit[12] else "")
                        with ce_mval: ed_mval = st.number_input("Valor do Prêmio (R$):", value=float(d_edit[13]), min_value=0.0)
                        
                        ce_b, ce_i, ce_t, ce_l = st.columns(4)
                        with ce_b: ed_base = st.number_input("Piso Liga R$:", value=float(d_edit[6]))
                        with ce_i: ed_inc = st.number_input("Aumento R$:", value=float(d_edit[7]))
                        with ce_t: ed_teto = st.number_input("Teto R$:", value=float(d_edit[8]))
                        with ce_l: ed_lim = st.number_input("Lim. Faltas:", value=float(d_edit[10]))
                        
                        btn_salvar_contrato = st.form_submit_button("💾 Salvar Contrato", use_container_width=True)
                        if btn_salvar_contrato:
                            edit_jogador(j_edit, ed_nome, d_edit[5], ed_base, ed_inc, ed_teto, ed_lim, ed_pin, ed_mdesc, ed_mval, bool(ed_pin))
                            st.rerun()

        with sub_del:
            if jogadores_ativos:
                j_del = st.selectbox("Demitir Atleta:", jogadores_ativos, key="sel_del")
                if st.button("Confirmar Demissão", use_container_width=True):
                    delete_jogador(j_del)
                    st.rerun()
                    
        with sub_link:
            st.markdown("**📲 Convite por WhatsApp**")
            st.caption("Gere um convite elegante. A criança não verá códigos complexos, apenas um botão para entrar no aplicativo.")
            if jogadores_ativos:
                j_link = st.selectbox("Atleta Convidado:", jogadores_ativos, key="sel_link")
                
                url_base = "https://robertoaraujo77.github.io/Liga_de_Desempenho"
                
                link_pronto = f"{url_base}/?equipe={urllib.parse.quote(USER_LOGADO)}&atleta={urllib.parse.quote(j_link)}"
                
                msg_wa = f"⚽ Olá {j_link}! A comissão técnica liberou seu acesso direto para o Vestiário da Liga de Desempenho:\n\n👉 {link_pronto}\n\nGuarde este link e use o seu PIN secreto para entrar no jogo!"
                url_wa = f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg_wa)}"
                
                st.markdown(f"""
                <a href="{url_wa}" target="_blank" style="text-decoration: none;">
                    <div style="background-color: #25D366; color: white; padding: 12px 20px; border-radius: 8px; text-align: center; font-size: 16px; font-weight: bold; margin-top: 15px; display: flex; justify-content: center; align-items: center; gap: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="currentColor" class="bi bi-whatsapp" viewBox="0 0 16 16">
                          <path d="M13.601 2.326A7.854 7.854 0 0 0 7.994 0C3.627 0 .068 3.558.064 7.926c0 1.399.366 2.76 1.057 3.965L0 16l4.204-1.102a7.933 7.933 0 0 0 3.79.965h.004c4.368 0 7.926-3.558 7.93-7.93A7.898 7.898 0 0 0 13.6 2.326zM7.994 14.521a6.573 6.573 0 0 1-3.356-.92l-.24-.144-2.49.652.666-2.433-.156-.251a6.56 6.56 0 0 1-1.007-3.505c0-3.626 2.957-6.584 6.591-6.584a6.56 6.56 0 0 1 4.66 1.931 6.557 6.557 0 0 1 1.928 4.66c-.004 3.639-2.961 6.592-6.592 6.592zm3.615-4.934c-.197-.099-1.17-.578-1.353-.646-.182-.065-.315-.099-.445.099-.133.197-.513.646-.627.775-.114.133-.232.148-.43.05-.197-.1-.836-.308-1.592-.985-.59-.525-.985-1.175-1.103-1.372-.114-.198-.011-.304.088-.403.087-.088.197-.232.296-.346.1-.114.133-.198.198-.33.065-.134.034-.248-.015-.347-.05-.099-.445-1.076-.612-1.47-.16-.389-.323-.335-.445-.34-.114-.007-.247-.007-.38-.007a.729.729 0 0 0-.529.247c-.182.198-.691.677-.691 1.654 0 .977.71 1.916.81 2.049.098.133 1.394 2.132 3.383 2.992.47.205.84.326 1.129.418.475.152.904.129 1.246.08.38-.058 1.171-.48 1.338-.943.164-.464.164-.86.114-.943-.049-.084-.182-.133-.38-.232z"/>
                        </svg>
                        Enviar convite pelo WhatsApp
                    </div>
                </a>
                """, unsafe_allow_html=True)
