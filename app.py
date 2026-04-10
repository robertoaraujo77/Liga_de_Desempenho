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

# Injeção de Manifesto para o PWABuilder
st.markdown("""
    <link rel="manifest" href="https://cdn.jsdelivr.net/gh/robertoaraujo77/Liga_de_Desempenho@main/static/manifest.json" crossorigin="anonymous">
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
# UTILITÁRIOS E SEGURANÇA (BLINDADO)
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
# CONEXÃO E BANCO DE DADOS (MULTI-USUÁRIO)
# ==========================================
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        s.execute(text('CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT)'))
        res_pin = s.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='usuarios' AND column_name='pin'")).fetchone()
        if not res_pin: s.execute(text("ALTER TABLE usuarios ADD COLUMN pin TEXT"))
        
        s.execute(text('''CREATE TABLE IF NOT EXISTS status (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, nivel TEXT, base REAL, saldo REAL, faltas REAL, aguardando_resgate INTEGER DEFAULT 0, avatar TEXT, base_inicial REAL, incremento REAL, teto_maximo REAL, titulos INTEGER, limite_faltas REAL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS historico (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, data TEXT, infracao TEXT, desconto REAL, tipo TEXT)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS trofeus (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, data TEXT, nivel TEXT, saldo REAL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS regras (id SERIAL PRIMARY KEY, usuario TEXT, descricao TEXT, valor REAL)'''))
        s.commit()

init_db()

# --- LÓGICA DE AUTENTICAÇÃO ---
def criar_conta(user, pw, pin):
    user_limpo = str(user).strip().lower()
    try:
        with conn.session as s:
            s.execute(text('INSERT INTO usuarios (username, password, pin) VALUES (:u, :p, :pin)'), 
                      {"u": user_limpo, "p": hash_password(pw), "pin": hash_password(pin)})
            regras_padrao = [
                {"u": user_limpo, "d": "🚿 Não seca o banheiro", "v": 1.0},
                {"u": user_limpo, "d": "🥱 Acordar reclamando", "v": 1.0},
                {"u": user_limpo, "d": "📚 Não fazer lição", "v": 5.0},
                {"u": user_limpo, "d": "🤬 Desobedecer (Vermelho)", "v": 20.0}
            ]
            s.execute(text('INSERT INTO regras (usuario, descricao, valor) VALUES (:u, :d, :v)'), regras_padrao)
            s.commit()
        return True
    except Exception: return False

def verificar_login(user, pw):
    user_limpo = str(user).strip().lower()
    res = conn.query('SELECT password FROM usuarios WHERE username = :u', params={"u": user_limpo}, ttl=0)
    if not res.empty and res.iloc[0]['password'] == hash_password(pw):
        return True
    return False

def verificar_pin(user, pin_digitado):
    if not pin_digitado: return False
    res = conn.query('SELECT pin FROM usuarios WHERE username = :u', params={"u": user}, ttl=0)
    if not res.empty:
        pin_banco = res.iloc[0]['pin']
        if pd.isna(pin_banco) or pin_banco is None:
            return pin_digitado == "2811"
        return pin_banco == hash_password(pin_digitado)
    return False

# ==========================================
# TELA DE ACESSO (LOGIN/CADASTRO/ONBOARDING)
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = None

if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center;'>⚽ Liga de Desempenho</h1>", unsafe_allow_html=True)
    menu_auth = st.tabs(["Acessar Liga", "Criar Nova Conta", "📖 Como Funciona?"])
    
    with menu_auth[0]:
        u_login = st.text_input("Usuário (E-mail):", key="u_login")
        p_login = st.text_input("Senha:", type="password", key="p_login")
        if st.button("Entrar em Campo", use_container_width=True):
            if verificar_login(u_login, p_login):
                st.session_state.autenticado = True
                st.session_state.usuario = str(u_login).strip().lower()
                st.rerun()
            else: st.error("Usuário ou senha incorretos.")
            
    with menu_auth[1]:
        u_new = st.text_input("Escolha um Usuário (E-mail):", key="u_new")
        p_new = st.text_input("Crie uma Senha Principal:", type="password", key="p_new")
        pin_new = st.text_input("Crie um PIN p/ Arbitragem (4 dígitos):", type="password", max_chars=4, key="pin_new", placeholder="Ex: 1234")
        if st.button("Criar Minha Liga", use_container_width=True):
            if u_new and p_new and pin_new:
                if criar_conta(u_new, p_new, pin_new):
                    st.success("Conta criada! Agora faça o login na aba 'Acessar Liga'.")
                else: st.error("Este usuário já existe.")
            else: st.error("Preencha todos os campos para criar a conta.")
            
    with menu_auth[2]:
        st.subheader("Transforme a mesada em um esporte! 🎮")
        st.write("A Liga de Desempenho é uma plataforma de gamificação familiar inspirada no clássico Modo Carreira dos esportes. Substitua as cobranças chatas por um campeonato motivador.")
        st.markdown("""
        **1️⃣ O Contrato Inicial:** Você cadastra a criança, define uma mesada base e um teto máximo que você pode pagar. O sistema cria as 'Divisões' automaticamente.

        **2️⃣ O Card e o Score 99:** O jovem ganha um Card do Atleta. Ele começa o mês em sua melhor forma (Score 99). Se ajudar em casa, o saldo sobe. Se quebrar as regras da casa, sofre Faltas, o saldo cai e o Score diminui!

        **3️⃣ Subida de Divisão:** Se o atleta terminar o mês sem estourar o limite de faltas, ele 'Sobe de Divisão' (Ex: Da Série Prata para a Série Ouro) e garante um aumento na mesada.

        **4️⃣ A Arbitragem:** Só a comissão técnica (pais) tem acesso à Área da Arbitragem via PIN, onde aplicam os bônus, faltas e fecham o mês.
        
        ---
        *Crie sua conta agora e escale seu primeiro jogador!*
        """)
        
    st.stop()

# ==========================================
# ÁREA RESTRITA (USUÁRIO LOGADO)
# ==========================================
USER_LOGADO = st.session_state.usuario

st.sidebar.write(f"Logado como:\n**{USER_LOGADO}**")

# Botão especial se o Admin estiver dentro da conta de um cliente
if st.session_state.get('is_admin_impersonating', False):
    st.sidebar.markdown("---")
    st.sidebar.warning("🕵️ Você está acessando a conta de um cliente.")
    if st.sidebar.button("🔙 Voltar ao Painel Admin", use_container_width=True):
        st.session_state.usuario = 'robertojr1990@gmail.com'
        st.session_state.is_admin_impersonating = False
        st.rerun()
else:
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

# ==========================================
# PAINEL DO DONO (GOD MODE) - EXCLUSIVO
# ==========================================
is_admin = (USER_LOGADO == 'robertojr1990@gmail.com')
modo_admin = False

if is_admin:
    st.sidebar.markdown("---")
    modo_admin = st.sidebar.toggle("👑 Painel do Dono")

if modo_admin:
    st.title("👑 Painel de Administração Global")
    st.info("Bem-vindo ao God Mode! Aqui você tem o controle total da plataforma.")
    
    tab_admin1, tab_admin2 = st.tabs(["👥 Contas e Jogadores", "⚙️ Gerenciamento"])
    
    with tab_admin1:
        st.subheader("Contas Cadastradas")
        df_users = conn.query('SELECT id, username FROM usuarios ORDER BY id DESC', ttl=0)
        if not df_users.empty:
            df_users.columns = ['ID', 'Email']
        st.dataframe(df_users, use_container_width=True, hide_index=True)
        
        st.subheader("Todos os Jogadores da Plataforma")
        df_all_players = conn.query('SELECT usuario, nome, nivel, saldo, titulos, base_inicial, incremento, teto_maximo, base FROM status ORDER BY id DESC', ttl=0)
        
        if not df_all_players.empty:
            def calc_divisao_admin(row):
                if row['nivel'] == 'Calculando...':
                    try:
                        divs, div_atual, idx = get_info_campeonato(row['base_inicial'], row['incremento'], row['teto_maximo'], row['base'])
                        return div_atual['nome']
                    except: return row['nivel']
                return row['nivel']
                
            df_all_players['Divisão Real'] = df_all_players.apply(calc_divisao_admin, axis=1)
            
            df_view = df_all_players[['usuario', 'nome', 'Divisão Real', 'saldo', 'titulos']].copy()
            df_view.columns = ['Responsável', 'Atleta', 'Divisão', 'Saldo', 'Títulos']
            df_view['Saldo'] = df_view['Saldo'].apply(lambda x: f"R$ {float(x):.2f}".replace('.', ','))
            st.dataframe(df_view, use_container_width=True, hide_index=True)
        else:
            st.write("Nenhum jogador cadastrado ainda.")
        
    with tab_admin2:
        st.markdown("**🕵️ Suporte ao Cliente (Acessar Conta)**")
        st.info("Entre na conta de uma família para corrigir fotos, nomes ou contratos usando as ferramentas deles.")
        if not df_users.empty:
            cliente_alvo = st.selectbox("Escolha a conta para acessar:", df_users['Email'].tolist())
            if st.button("🚪 Logar como este Cliente", type="primary"):
                if cliente_alvo == 'robertojr1990@gmail.com':
                    st.warning("Você já está na sua própria conta!")
                else:
                    st.session_state.usuario = cliente_alvo
                    st.session_state.is_admin_impersonating = True
                    st.rerun()

        st.markdown("---")
        st.markdown("**🚨 Excluir uma Conta Inteira**")
        st.warning("Isso apagará a conta do usuário e todos os jogadores atrelados a ele.")
        if not df_users.empty:
            usuario_del = st.selectbox("Selecione o E-mail para excluir:", df_users['Email'].tolist(), key="del_user_sel")
            if st.button("Excluir Conta Definitivamente"):
                if usuario_del == 'robertojr1990@gmail.com':
                    st.error("Você não pode excluir a sua própria conta de Dono!")
                else:
                    with conn.session as s:
                        s.execute(text("DELETE FROM usuarios WHERE username=:u"), {"u": usuario_del})
                        s.execute(text("DELETE FROM status WHERE usuario=:u"), {"u": usuario_del})
                        s.execute(text("DELETE FROM historico WHERE usuario=:u"), {"u": usuario_del})
                        s.execute(text("DELETE FROM trofeus WHERE usuario=:u"), {"u": usuario_del})
                        s.execute(text("DELETE FROM regras WHERE usuario=:u"), {"u": usuario_del})
                        s.commit()
                    st.success(f"Conta {usuario_del} excluída com sucesso.")
                    time.sleep(2)
                    st.rerun()
    st.stop()


# --- FUNÇÕES COM FILTRO DE USUÁRIO (FAMÍLIAS) ---
def get_regras():
    df = conn.query('SELECT descricao, valor FROM regras WHERE usuario = :u', params={"u": USER_LOGADO}, ttl=0)
    res = list(df.itertuples(index=False, name=None))
    def sort_key(item):
        texto = item[0]
        match = re.search(r'[a-zA-ZÀ-ÿ0-9]', texto)
        return texto[match.start():].lower() if match else texto.lower()
    res_sorted = sorted(res, key=sort_key)
    return dict(res_sorted)

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

def get_jogadores():
    df = conn.query('SELECT DISTINCT nome FROM status WHERE usuario = :u', params={"u": USER_LOGADO}, ttl=0)
    return df['nome'].tolist()

def get_status(jogador):
    df = conn.query('SELECT nivel, base, saldo, faltas, aguardando_resgate, avatar, base_inicial, incremento, teto_maximo, titulos, limite_faltas FROM status WHERE nome = :n AND usuario = :u', params={"n": jogador, "u": USER_LOGADO}, ttl=0)
    if not df.empty:
        row = df.iloc[0].to_dict()
        return (row['nivel'], row['base'], row['saldo'], row['faltas'], row['aguardando_resgate'],
                row['avatar'], row['base_inicial'], row['incremento'], float(row['teto_maximo']), int(row['titulos']), float(row['limite_faltas']))
    return None

def update_status(jogador, nivel, base, saldo, faltas, aguardando, avatar, titulos, teto_maximo, limite_faltas):
    with conn.session as s:
        s.execute(text('UPDATE status SET nivel=:n, base=:b, saldo=:s, faltas=:f, aguardando_resgate=:ag, avatar=:av, titulos=:t, teto_maximo=:tm, limite_faltas=:lf WHERE nome=:nome AND usuario=:u'), 
                  {"n": str(nivel), "b": float(base), "s": float(saldo), "f": float(faltas), "ag": int(aguardando), "av": str(avatar), "nome": str(jogador), "t": int(titulos), "tm": float(teto_maximo), "lf": float(limite_faltas), "u": USER_LOGADO})
        s.commit()

def add_jogador(nome, estilo_avatar, base_inicial, incremento, teto_maximo, limite_faltas):
    with conn.session as s:
        s.execute(text('INSERT INTO status (usuario, nome, nivel, base, saldo, faltas, aguardando_resgate, avatar, base_inicial, incremento, teto_maximo, titulos, limite_faltas) VALUES (:u, :n, :niv, :b, :s, :f, :ag, :av, :bi, :inc, :tm, 0, :lf)'), 
                  {"u": USER_LOGADO, "n": nome, "niv": "Calculando...", "b": base_inicial, "s": base_inicial, "f": 0.0, "ag": 0, "av": estilo_avatar, "bi": base_inicial, "inc": incremento, "tm": teto_maximo, "lf": limite_faltas})
        s.commit()

def edit_jogador(nome_antigo, novo_nome, estilo_avatar, base_inicial, incremento, teto_maximo, limite_faltas):
    with conn.session as s:
        s.execute(text('''
            UPDATE status 
            SET nome=:nn, avatar=:av, base_inicial=:bi, incremento=:inc, teto_maximo=:tm, limite_faltas=:lf 
            WHERE nome=:na AND usuario=:u
        '''), {"nn": novo_nome, "av": estilo_avatar, "bi": float(base_inicial), "inc": float(incremento), "tm": float(teto_maximo), "lf": float(limite_faltas), "na": nome_antigo, "u": USER_LOGADO})

        if nome_antigo != novo_nome:
            s.execute(text('UPDATE historico SET nome=:nn WHERE nome=:na AND usuario=:u'), {"nn": novo_nome, "na": nome_antigo, "u": USER_LOGADO})
            s.execute(text('UPDATE trofeus SET nome=:nn WHERE nome=:na AND usuario=:u'), {"nn": novo_nome, "na": nome_antigo, "u": USER_LOGADO})
        s.commit()

def delete_jogador(nome):
    with conn.session as s:
        s.execute(text('DELETE FROM status WHERE nome = :n AND usuario = :u'), {"n": nome, "u": USER_LOGADO})
        s.execute(text('DELETE FROM historico WHERE nome = :n AND usuario = :u'), {"n": nome, "u": USER_LOGADO})
        s.execute(text('DELETE FROM trofeus WHERE nome = :n AND usuario = :u'), {"n": nome, "u": USER_LOGADO})
        s.commit()

def add_historico(jogador, infracao, valor, tipo='falta'):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    with conn.session as s:
        s.execute(text('INSERT INTO historico (usuario, nome, data, infracao, desconto, tipo) VALUES (:u, :n, :d, :i, :v, :t)'), 
                  {"u": USER_LOGADO, "n": str(jogador), "d": agora, "i": str(infracao), "v": float(valor), "t": str(tipo)})
        s.commit()

def get_historico(jogador):
    return conn.query('SELECT data, infracao, desconto, tipo FROM historico WHERE nome = :n AND usuario = :u ORDER BY id DESC', params={"n": jogador, "u": USER_LOGADO}, ttl=0)

def get_historico_admin(jogador):
    return conn.query('SELECT id, data, infracao, desconto, tipo FROM historico WHERE nome = :n AND usuario = :u ORDER BY id DESC', params={"n": jogador, "u": USER_LOGADO}, ttl=0)

def delete_specific_historico(jogador, id_item, valor_item, tipo_item):
    with conn.session as s:
        s.execute(text('DELETE FROM historico WHERE id = :id AND usuario = :u'), {"id": int(id_item), "u": USER_LOGADO})
        s.commit()
    nivel, base, saldo, faltas, aguardando, avatar, base_ini, inc, teto, titulos, limite = get_status(jogador)
    if tipo_item == 'falta':
        novo_saldo = saldo + float(valor_item)
        novas_faltas = max(0.0, faltas - float(valor_item))
    else: 
        novo_saldo = saldo - float(valor_item)
        novas_faltas = faltas
    update_status(jogador, nivel, base, novo_saldo, novas_faltas, aguardando, avatar, titulos, teto, limite)

def clear_historico(jogador):
    with conn.session as s:
        s.execute(text('DELETE FROM historico WHERE nome = :n AND usuario = :u'), {"n": jogador, "u": USER_LOGADO})
        s.commit()

def add_trofeu(jogador, nivel, saldo):
    meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    mes_atual = meses[datetime.now().month]
    ano_atual = datetime.now().year
    data_formatada = f"{mes_atual}/{ano_atual}"
    with conn.session as s:
        s.execute(text('INSERT INTO trofeus (usuario, nome, data, nivel, saldo) VALUES (:u, :n, :d, :niv, :s)'), 
                  {"u": USER_LOGADO, "n": str(jogador), "d": data_formatada, "niv": str(nivel), "s": float(saldo)})
        s.commit()

def get_trofeus(jogador):
    return conn.query('SELECT data as Data, nivel as Divisão, saldo as Recompensa FROM trofeus WHERE nome = :n AND usuario = :u ORDER BY id DESC', params={"n": jogador, "u": USER_LOGADO}, ttl=0)

# ==========================================
# MOTOR MATEMÁTICO E CARD DO ATLETA
# ==========================================
def get_info_campeonato(base_inicial, incremento, teto_maximo, base_atual):
    inc = max(incremento, 1.0)
    saltos_totais = int(round((teto_maximo - base_inicial) / inc))
    qtd_divisoes = saltos_totais + 1

    divisoes = []
    for i in range(qtd_divisoes):
        valor = base_inicial + (i * inc)
        num_divisao = qtd_divisoes - i
        pedra_idx = min(num_divisao - 1, len(PEDRAS) - 1)
        nome = f"{num_divisao}ª Divisão - {PEDRAS[pedra_idx]}"
        divisoes.append({"nome": nome, "valor": valor, "num_divisao": num_divisao})

    divisoes = sorted(divisoes, key=lambda x: x["valor"])

    div_atual = divisoes[0]
    index_atual = 0
    for idx, div in enumerate(divisoes):
        if abs(div["valor"] - base_atual) < 0.1: 
            div_atual = div
            index_atual = idx
            break

    return divisoes, div_atual, index_atual

def render_carta_atleta(nome_jogador, estilo_avatar, div_nome, saldo, base, faltas, titulos):
    if estilo_avatar.startswith("data:image"):
        img_src = estilo_avatar
    else:
        img_src = f"https://api.dicebear.com/7.x/{estilo_avatar}/svg?seed={nome_jogador}&backgroundColor=e2e8f0"

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
# INTERFACE PRINCIPAL
# ==========================================
jogadores_ativos = get_jogadores()
jogador_selecionado = None

if len(jogadores_ativos) > 1:
    st.markdown("<div style='text-align: center; margin-bottom: 20px;'>", unsafe_allow_html=True)
    jogador_selecionado = st.selectbox("👤 Selecione o Perfil:", jogadores_ativos, label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
elif len(jogadores_ativos) == 1:
    jogador_selecionado = jogadores_ativos[0]
else:
    st.info("👋 **Bem-vindo à Liga!** Você ainda não tem jogadores. Desça até a **Área da Arbitragem**, digite seu PIN e escale seu primeiro Atleta!")

if jogador_selecionado:
    dados_jogador = get_status(jogador_selecionado)
    if dados_jogador:
        nivel_atual, base_atual, saldo_atual, faltas_atual, aguardando_resgate, estilo_avatar, base_inicial, incremento, teto_maximo, titulos, limite_faltas = dados_jogador
        
        divisoes, div_atual, index_atual = get_info_campeonato(base_inicial, incremento, teto_maximo, base_atual)
        nome_divisao_exibicao = div_atual["nome"]

        render_carta_atleta(jogador_selecionado, estilo_avatar, nome_divisao_exibicao, saldo_atual, base_atual, faltas_atual, titulos)

        if aguardando_resgate == 1:
            st.info(f"🚨 **Atenção {jogador_selecionado}!** O Árbitro encerrou a temporada. O placar está travado.")
            st.markdown("<h3 style='text-align: center;'>Chegou a hora de descobrir o seu destino...</h3>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🎁 CLIQUE AQUI PARA VER SEU RESULTADO", type="primary", use_container_width=True):
                df_historico = get_historico(jogador_selecionado)
                teve_vermelho = False
                if not df_historico.empty:
                    teve_vermelho = any("Cartão Vermelho" in str(inf) for inf in df_historico['infracao'])

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
                novo_nome_div = nova_divisao["nome"]

                if animacao_tipo == 'titulo': st.session_state.animacao_titulo = True
                elif animacao_tipo == 'vitoria': 
                    st.session_state.animacao_vitoria = True
                    st.session_state.nome_pedra_vitoria = novo_nome_div
                elif animacao_tipo == 'derrota':
                    st.session_state.animacao_derrota = True
                    st.session_state.nome_pedra_derrota = novo_nome_div
                elif animacao_tipo == 'manter': st.session_state.animacao_manter = True

                add_trofeu(jogador_selecionado, novo_nome_div, saldo_atual)
                update_status(jogador_selecionado, novo_nome_div, nova_base, nova_base, 0.0, aguardando=0, avatar=estilo_avatar, titulos=titulos, teto_maximo=teto_maximo, limite_faltas=limite_faltas)
                clear_historico(jogador_selecionado)
                st.rerun()

        else:
            aba1, aba2 = st.tabs(["🏟️ Placar do Mês", "🏆 Sala de Troféus"])
            with aba1:
                col1, col2 = st.columns(2)
                col1.metric("Saldo do Mês", f"R$ {max(0, saldo_atual):.2f}".replace('.', ','))
                col2.metric("Faltas Acumuladas", f"R$ {faltas_atual:.2f}".replace('.', ','), delta=f"- Limite: R$ {limite_faltas:.2f}".replace('.', ','), delta_color="inverse")

                st.markdown(f"**Progresso da Tolerância (Limite R$ {limite_faltas:.2f}):**".replace('.', ','))
                porcentagem = min((faltas_atual / limite_faltas) * 100, 100) if limite_faltas > 0 else 100
                if porcentagem < 50: cor_barra = "#28a745"
                elif porcentagem < 100: cor_barra = "#fd7e14"
                else: cor_barra = "#dc3545"

                st.markdown(f"""
                    <div style="background-color: #2b2b2b; border-radius: 15px; width: 100%; height: 25px; margin-bottom: 10px; border: 1px solid #444;">
                        <div style="background-color: {cor_barra}; width: {porcentagem}%; height: 100%; border-radius: 15px; transition: width 0.8s ease-in-out, background-color 0.5s;"></div>
                    </div>
                """, unsafe_allow_html=True)

                if faltas_atual <= limite_faltas: st.success("🟢 Tudo certo! Na zona de classificação.")
                else:
                    base_de_baixo = divisoes[index_atual - 1]["valor"] if index_atual > 0 else 0
                    if saldo_atual <= base_de_baixo: st.error("🔴 Perigo: Você entrou na Zona de Rebaixamento!")
                    else: st.warning("🟠 Atenção: A subida foi bloqueada, mas seu saldo garante permanência.")

                st.markdown("---")
                
                df_historico_asc = conn.query('SELECT data, infracao, desconto, tipo FROM historico WHERE nome = :n AND usuario = :u ORDER BY id ASC', params={"n": jogador_selecionado, "u": USER_LOGADO}, ttl=0)
                timeline = [base_atual]
                curr = base_atual
                for _, row in df_historico_asc.iterrows():
                    if row['tipo'] == 'bonus': curr += row['desconto']
                    else: curr -= row['desconto']
                    timeline.append(curr)
                if len(timeline) == 1: timeline.append(base_atual) 
                
                st.markdown("**📈 Desempenho no Mês:**")
                st.line_chart(timeline, height=150)

                st.markdown("---")
                st.subheader("📋 Histórico de Lançamentos")
                df_historico = get_historico(jogador_selecionado)
                if not df_historico.empty:
                    df_view = df_historico.copy()
                    df_view['Lançamento'] = df_view.apply(lambda row: f"+ R$ {row['desconto']:.2f}".replace('.', ',') if row['tipo'] == 'bonus' else f"- R$ {row['desconto']:.2f}".replace('.', ','), axis=1)
                    df_view = df_view[['data', 'infracao', 'Lançamento']]
                    df_view.columns = ['Data', 'Motivo', 'Valor']
                    st.dataframe(df_view, use_container_width=True, hide_index=True)
                else: st.info("Nenhum lançamento registrado neste mês.")

            with aba2:
                st.subheader("🌟 Histórico de Temporadas")
                df_trofeus = get_trofeus(jogador_selecionado)
                if not df_trofeus.empty:
                    df_trofeus.columns = ['Data', 'Divisão', 'Recompensa']
                    df_trofeus['Recompensa'] = df_trofeus['Recompensa'].apply(lambda x: f"R$ {float(x):.2f}".replace('.', ','))
                    st.dataframe(df_trofeus, use_container_width=True, hide_index=True)
                else: st.info(f"{jogador_selecionado} ainda não encerrou nenhuma temporada.")

# ==========================================
# ÁREA DA ARBITRAGEM
# ==========================================
st.markdown("---")
st.markdown("### 🔐 Área da Arbitragem")
if jogador_selecionado: st.markdown(f"*(Controlando o perfil: **{jogador_selecionado}**)*")

col_senha, col_btn_senha = st.columns([3, 1])
with col_senha:
    senha = st.text_input("Senha Arbitragem", type="password", label_visibility="collapsed", placeholder="Digite seu PIN...")
with col_btn_senha:
    st.button("🔓 Entrar", use_container_width=True)

if verificar_pin(USER_LOGADO, senha):
    if not jogador_selecionado:
        st.markdown("**➕ Cadastrar Primeiro Jogador**")
        novo_nome = st.text_input("Nome:", placeholder="Ex: Davi")
        tipo_foto = st.radio("Imagem do Perfil:", ["Avatar Padrão", "Fazer Upload de Foto"], horizontal=True)
        avatar_final = "notionists"
        if tipo_foto == "Avatar Padrão":
            nome_avatar = st.selectbox("Estilo do Avatar:", list(ESTILOS_AVATAR.keys()))
            avatar_final = ESTILOS_AVATAR[nome_avatar]
        else:
            foto_upload = st.file_uploader("Envie a foto (PNG/JPG):", type=["png", "jpg", "jpeg"])
            if foto_upload: 
                img_raw = Image.open(foto_upload).convert("RGB")
                st.markdown("**🖱️ Arraste e redimensione o quadrado azul para centralizar o rosto:**")
                cropped_img = st_cropper(img_raw, aspect_ratio=(1, 1), box_color='#0000FF', key="crop_cad_first")
                avatar_final = converter_para_base64(cropped_img)
            
        col_base, col_inc, col_teto, col_limite = st.columns([1, 1, 1, 1.2])
        with col_base: base_ini = st.number_input("Início (R$):", value=50.0, step=5.0)
        with col_inc: inc_val = st.number_input("Aumento (R$):", value=10.0, step=5.0)
        with col_teto: teto_val = st.number_input("Teto (R$):", value=100.0, step=5.0)
        with col_limite: limite_val = st.number_input("Lim. Faltas:", value=5.0, step=1.0)
            
        if st.button("Cadastrar e Iniciar Liga", type="primary", use_container_width=True):
            if novo_nome and teto_val > base_ini and inc_val > 0:
                qtd_divisoes = int(round((teto_val - base_ini) / inc_val)) + 1
                if qtd_divisoes > 15: st.error(f"⚠️ O campeonato ficou muito longo ({qtd_divisoes} divisões). O limite são 15.")
                else:
                    add_jogador(novo_nome, avatar_final, base_ini, inc_val, teto_val, limite_val)
                    st.success(f"O jogador {novo_nome} entrou em campo!")
                    time.sleep(1.5)
                    st.rerun()
            else: st.error("Verifique os valores. O Teto deve ser maior que o Início.")
    else:
        regras_dinamicas = get_regras()
        tab_jogo, tab_regras, tab_elenco = st.tabs(["⚖️ Lançamentos", "📝 Regras", "⚙️ Elenco"])
        
        with tab_jogo:
            if aguardando_resgate == 1:
                st.warning(f"⏳ O sistema está pausado aguardando o resgate.")
                if st.button("❌ Cancelar Autorização", use_container_width=True):
                    update_status(jogador_selecionado, nivel_atual, base_atual, saldo_atual, faltas_atual, 0, estilo_avatar, titulos, teto_maximo, limite_faltas)
                    st.rerun()
            else:
                st.markdown("**🔴 Aplicar Penalidade (Falta)**")
                col_infracao, col_btn_add = st.columns([3, 1])
                with col_infracao:
                    infracao_selecionada = st.selectbox("Selecione a infração:", list(regras_dinamicas.keys()), label_visibility="collapsed")
                with col_btn_add:
                    if st.button("Aplicar Falta", type="primary", use_container_width=True):
                        valor = regras_dinamicas[infracao_selecionada]
                        update_status(jogador_selecionado, nivel_atual, base_atual, saldo_atual - valor, faltas_atual + valor, 0, estilo_avatar, titulos, teto_maximo, limite_faltas)
                        add_historico(jogador_selecionado, infracao_selecionada, valor, 'falta')
                        st.rerun()
                        
                st.markdown("---")
                st.markdown("**⭐ Aplicar Bônus (O Golaço!)**")
                col_motivo, col_valor, col_btn_bonus = st.columns([2, 1, 1])
                with col_motivo: motivo_bonus = st.text_input("Motivo do Bônus:", placeholder="Ex: Arrumou o quarto")
                with col_valor: valor_bonus = st.number_input("Valor R$", min_value=1.00, step=1.00)
                with col_btn_bonus:
                    st.markdown("<div style='margin-top: 28px;'>", unsafe_allow_html=True)
                    if st.button("Aplicar Bônus", use_container_width=True):
                        if motivo_bonus:
                            update_status(jogador_selecionado, nivel_atual, base_atual, saldo_atual + valor_bonus, faltas_atual, 0, estilo_avatar, titulos, teto_maximo, limite_faltas)
                            add_historico(jogador_selecionado, f"⭐ {motivo_bonus}", valor_bonus, 'bonus')
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                        
                st.markdown("---")
                st.markdown("**🗑️ Remover Penalidade ou Bônus**")
                df_admin = get_historico_admin(jogador_selecionado)
                if not df_admin.empty:
                    col_remove, col_btn_remove = st.columns([3, 1])
                    opcoes_falta = {}
                    for index, row in df_admin.iterrows():
                        sinal = "+" if row['tipo'] == 'bonus' else "-"
                        texto = f"{row['data']} | {row['infracao']} ({sinal} R$ {row['desconto']:.2f})"
                        opcoes_falta[texto] = (row['id'], row['desconto'], row['tipo'])
                        
                    with col_remove: falta_selecionada = st.selectbox("Selecione o item:", list(opcoes_falta.keys()), label_visibility="collapsed")
                    with col_btn_remove:
                        if st.button("Excluir Item", use_container_width=True):
                            id_falta, valor_item, tipo_item = opcoes_falta[falta_selecionada]
                            delete_specific_historico(jogador_selecionado, id_falta, valor_item, tipo_item)
                            st.rerun()
                else: st.info("O histórico está limpo.")

                st.markdown("---")
                st.markdown("**🏁 Fechamento do Mês**")
                st.warning(f"Isto liberará o botão surpresa de virada de mês para o {jogador_selecionado}.")
                if st.button("✅ Autorizar Fim da Temporada", use_container_width=True):
                    update_status(jogador_selecionado, nivel_atual, base_atual, saldo_atual, faltas_atual, 1, estilo_avatar, titulos, teto_maximo, limite_faltas)
                    st.rerun()

        with tab_regras:
            st.markdown("**➕ Adicionar Nova Regra**")
            col_nova_regra, col_novo_val, col_btn_regra = st.columns([3, 1, 1])
            with col_nova_regra: desc_regra = st.text_input("Descrição da Regra:", placeholder="Ex: Deixar a luz acesa")
            with col_novo_val: val_regra = st.number_input("Valor (R$):", min_value=0.50, step=0.50, key="val_regra_add")
            with col_btn_regra:
                st.markdown("<div style='margin-top: 28px;'>", unsafe_allow_html=True)
                if st.button("Salvar Regra", use_container_width=True):
                    if desc_regra and desc_regra not in regras_dinamicas:
                        add_regra(desc_regra, val_regra)
                        st.success("Regra Adicionada!")
                        time.sleep(1)
                        st.rerun()
                    elif desc_regra in regras_dinamicas: st.error("Regra já existe.")
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("**✏️ Editar ou Remover Regra Existente**")
            if regras_dinamicas:
                regra_selecionada = st.selectbox("Selecione a regra para editar:", list(regras_dinamicas.keys()), key="edit_regra_sel", label_visibility="collapsed")
                col_edit_desc, col_edit_val = st.columns([3, 1])
                with col_edit_desc: novo_texto = st.text_input("Descrição:", value=regra_selecionada, key=f"edit_desc_{regra_selecionada}")
                with col_edit_val: novo_valor = st.number_input("Valor (R$):", value=float(regras_dinamicas[regra_selecionada]), min_value=0.50, step=0.50, key=f"edit_val_{regra_selecionada}")
                col_btn_save, col_btn_del = st.columns(2)
                with col_btn_save:
                    if st.button("💾 Salvar Alterações", use_container_width=True):
                        if novo_texto != regra_selecionada and novo_texto in regras_dinamicas: st.error("Já existe uma regra com esse nome!")
                        else:
                            update_regra(regra_selecionada, novo_texto, novo_valor)
                            st.success("Regra atualizada com sucesso!")
                            time.sleep(1)
                            st.rerun()
                with col_btn_del:
                    if st.button("🗑️ Excluir Regra", use_container_width=True):
                        delete_regra(regra_selecionada)
                        st.success("Regra apagada!")
                        time.sleep(1)
                        st.rerun()
            else: st.info("Nenhuma regra cadastrada.")

        with tab_elenco:
            sub_cad, sub_edit, sub_del = st.tabs(["➕ Cadastrar", "✏️ Editar", "❌ Excluir"])
            with sub_cad:
                st.markdown("**Escalar Novo Jogador**")
                novo_nome = st.text_input("Nome:", placeholder="Ex: Arthur", key="cad_nome")
                tipo_foto = st.radio("Imagem do Perfil:", ["Avatar Padrão", "Fazer Upload de Foto"], horizontal=True, key="cad_tipo_foto")
                avatar_final = "notionists"
                if tipo_foto == "Avatar Padrão":
                    nome_avatar = st.selectbox("Estilo do Avatar:", list(ESTILOS_AVATAR.keys()), key="cad_avatar")
                    avatar_final = ESTILOS_AVATAR[nome_avatar]
                else:
                    foto_upload = st.file_uploader("Envie a foto (PNG/JPG):", type=["png", "jpg", "jpeg"], key="cad_upload")
                    if foto_upload: 
                        img_raw = Image.open(foto_upload).convert("RGB")
                        st.markdown("**🖱️ Arraste e redimensione o quadrado azul para centralizar o rosto:**")
                        cropped_img = st_cropper(img_raw, aspect_ratio=(1, 1), box_color='#0000FF', key="crop_cad")
                        avatar_final = converter_para_base64(cropped_img)
                    
                col_base, col_inc, col_teto, col_limite = st.columns([1, 1, 1, 1.2])
                with col_base: base_ini = st.number_input("Início (R$):", value=50.0, step=5.0, key="cad_base")
                with col_inc: inc_val = st.number_input("Aumento (R$):", value=10.0, step=5.0, key="cad_inc")
                with col_teto: teto_val = st.number_input("Teto (R$):", value=100.0, step=5.0, key="cad_teto")
                with col_limite: lim_val = st.number_input("Lim. Faltas:", value=5.0, step=1.0, key="cad_limite")
                    
                if st.button("Cadastrar Jogador", use_container_width=True, key="btn_cadastrar"):
                    if novo_nome and novo_nome not in jogadores_ativos and teto_val > base_ini and inc_val > 0:
                        qtd_divisoes = int(round((teto_val - base_ini) / inc_val)) + 1
                        if qtd_divisoes > 15: st.error(f"⚠️ O campeonato ficou muito longo ({qtd_divisoes} divisões). O limite são 15.")
                        else:
                            add_jogador(novo_nome, avatar_final, base_ini, inc_val, teto_val, lim_val)
                            st.success(f"{novo_nome} escalado!")
                            time.sleep(1.5)
                            st.rerun()
                    elif novo_nome in jogadores_ativos: st.error("Jogador já existe!")
                    else: st.error("O Teto deve ser maior que o Início.")

            with sub_edit:
                st.markdown("**Ajustar Contrato e Perfil**")
                if jogadores_ativos:
                    jogador_editar = st.selectbox("Selecione o jogador:", jogadores_ativos, key="edit_sel_jog")
                    dados_edit = get_status(jogador_editar)
                    if dados_edit:
                        niv_e, base_e, saldo_e, faltas_e, ag_e, avatar_atual_e, base_ini_e, inc_e, teto_e, tits_e, limite_e = dados_edit
                        edit_nome = st.text_input("Nome:", value=jogador_editar, key="edit_nome")
                        tipo_foto_edit = st.radio("Imagem do Perfil:", ["Manter Atual", "Novo Avatar Padrão", "Nova Foto"], horizontal=True, key="edit_tipo_foto")
                        avatar_final_edit = avatar_atual_e
                        if tipo_foto_edit == "Novo Avatar Padrão":
                            nome_avatar_edit = st.selectbox("Estilo do Avatar:", list(ESTILOS_AVATAR.keys()), key="edit_avatar")
                            avatar_final_edit = ESTILOS_AVATAR[nome_avatar_edit]
                        elif tipo_foto_edit == "Nova Foto":
                            foto_upload_edit = st.file_uploader("Envie a nova foto:", type=["png", "jpg", "jpeg"], key="edit_upload")
                            if foto_upload_edit: 
                                img_raw_edit = Image.open(foto_upload_edit).convert("RGB")
                                st.markdown("**🖱️ Arraste e redimensione o quadrado azul:**")
                                cropped_img_edit = st_cropper(img_raw_edit, aspect_ratio=(1, 1), box_color='#0000FF', key="crop_edit")
                                avatar_final_edit = converter_para_base64(cropped_img_edit)
                        
                        col_b, col_i, col_t, col_l = st.columns([1, 1, 1, 1.2])
                        with col_b: e_base = st.number_input("Início (R$):", value=float(base_ini_e), step=5.0, key="e_base")
                        with col_i: e_inc = st.number_input("Aumento (R$):", value=float(inc_e), step=5.0, key="e_inc")
                        with col_t: e_teto = st.number_input("Teto (R$):", value=float(teto_e), step=5.0, key="e_teto")
                        with col_l: e_lim = st.number_input("Lim. Faltas:", value=float(limite_e), step=1.0, key="e_limite")
                        
                        if st.button("💾 Salvar Alterações", use_container_width=True, type="primary", key="btn_salvar_edit"):
                            if edit_nome and e_teto > e_base and e_inc > 0:
                                qtd_divisoes = int(round((e_teto - e_base) / e_inc)) + 1
                                if qtd_divisoes > 15: st.error("O campeonato ficou com mais de 15 divisões. Ajuste os valores.")
                                else:
                                    edit_jogador(jogador_editar, edit_nome, avatar_final_edit, e_base, e_inc, e_teto, e_lim)
                                    st.success("Perfil atualizado!")
                                    time.sleep(1.5)
                                    st.rerun()
                            else: st.error("Verifique os valores.")

            with sub_del:
                st.markdown("**Remover Jogador**")
                col_excluir, col_btn_excluir = st.columns([3, 1])
                with col_excluir: jogador_excluir = st.selectbox("Selecione o jogador:", jogadores_ativos, label_visibility="collapsed", key="del_sel_jog")
                with col_btn_excluir:
                    confirmar = st.checkbox("Confirmar", key="chk_excluir")
                    if st.button("Excluir", use_container_width=True, disabled=not confirmar):
                        delete_jogador(jogador_excluir)
                        st.success(f"{jogador_excluir} removido.")
                        time.sleep(1.5)
                        st.rerun()
elif senha != "": st.error("PIN Incorreto.")
