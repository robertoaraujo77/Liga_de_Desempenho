import streamlit as st
import pandas as pd
import re
from datetime import datetime
from sqlalchemy import text

from config import SUPER_ADMIN, PEDRAS, obter_regras_padrao, obter_bonus_padrao
from logic import hash_password

# ==========================================
# CONEXÃO E BANCO DE DADOS
# ==========================================
conn = st.connection("postgresql", type="sql")

def _usuario_ativo():
    """Descobre qual 'usuario' (conta de pai) está ativo na sessão atual,
    considerando o Modo GOD (impersonate). Substitui o antigo global USER_LOGADO
    para que essa lógica funcione corretamente estando em um módulo separado."""
    if st.session_state.get('usuario') == SUPER_ADMIN and st.session_state.get('tipo_conta') == 'pai':
        if 'impersonate' not in st.session_state:
            st.session_state.impersonate = st.session_state.usuario
        return st.session_state.impersonate
    return st.session_state.usuario

def init_db():
    with conn.session as s:
        s.execute(text('CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT)'))
        s.execute(text('''CREATE TABLE IF NOT EXISTS status (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, nivel TEXT, base REAL, saldo REAL, faltas REAL, aguardando_resgate INTEGER DEFAULT 0, avatar TEXT, base_inicial REAL, incremento REAL, teto_maximo REAL, titulos INTEGER, limite_faltas REAL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS historico (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, data TEXT, infracao TEXT, desconto REAL, tipo TEXT)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS trofeus (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, data TEXT, nivel TEXT, saldo REAL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS regras (id SERIAL PRIMARY KEY, usuario TEXT, descricao TEXT, valor REAL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS notificacoes (id SERIAL PRIMARY KEY, usuario TEXT, nome TEXT, mensagem TEXT, lida INTEGER DEFAULT 0, data TEXT)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS bonus_regras (id SERIAL PRIMARY KEY, usuario TEXT, descricao TEXT, valor REAL)'''))
        
        res_cols = s.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='status'")).fetchall()
        cols = [r[0] for r in res_cols]
        if 'pin_jogador' not in cols: s.execute(text("ALTER TABLE status ADD COLUMN pin_jogador TEXT"))
        if 'meta_descricao' not in cols: s.execute(text("ALTER TABLE status ADD COLUMN meta_descricao TEXT"))
        if 'meta_valor' not in cols: s.execute(text("ALTER TABLE status ADD COLUMN meta_valor REAL"))
        if 'poupanca' not in cols: s.execute(text("ALTER TABLE status ADD COLUMN poupanca REAL DEFAULT 0.0"))

        s.execute(text('''CREATE TABLE IF NOT EXISTS metas (id SERIAL PRIMARY KEY, usuario TEXT, jogador TEXT, descricao TEXT, valor REAL)'''))

        s.execute(text("ALTER TABLE regras ADD COLUMN IF NOT EXISTS cartao_vermelho BOOLEAN DEFAULT FALSE"))
        s.execute(text("ALTER TABLE historico ADD COLUMN IF NOT EXISTS cartao_vermelho BOOLEAN DEFAULT FALSE"))
        s.execute(text("ALTER TABLE status ADD COLUMN IF NOT EXISTS data_cadastro TEXT"))
        s.execute(text("ALTER TABLE status ADD COLUMN IF NOT EXISTS data_ultima_falta TEXT"))
        s.execute(text("ALTER TABLE status ADD COLUMN IF NOT EXISTS fechamento_automatico BOOLEAN DEFAULT FALSE"))
        s.execute(text("ALTER TABLE status ADD COLUMN IF NOT EXISTS dias_fechamento INTEGER DEFAULT 30"))
        s.execute(text("ALTER TABLE status ADD COLUMN IF NOT EXISTS data_inicio_temporada TEXT"))

        # Preenche datas em branco para registros antigos (evita erro no cálculo de streak/fechamento automático)
        s.execute(text("UPDATE status SET data_cadastro = TO_CHAR(NOW(), 'DD/MM/YYYY') WHERE data_cadastro IS NULL"))
        s.execute(text("UPDATE status SET data_inicio_temporada = TO_CHAR(NOW(), 'DD/MM/YYYY') WHERE data_inicio_temporada IS NULL"))

        # Migração única: converte a antiga "meta única" (meta_descricao/meta_valor) para a nova lista de metas
        s.execute(text('''
            INSERT INTO metas (usuario, jogador, descricao, valor)
            SELECT s.usuario, s.nome, s.meta_descricao, s.meta_valor FROM status s
            WHERE s.meta_descricao IS NOT NULL AND TRIM(s.meta_descricao) != '' AND s.meta_valor IS NOT NULL AND s.meta_valor > 0
            AND NOT EXISTS (SELECT 1 FROM metas m WHERE m.usuario = s.usuario AND m.jogador = s.nome AND m.descricao = s.meta_descricao)
        '''))

        # Realinha o contador (sequence) de cada tabela com id SERIAL para o maior ID já existente.
        # Evita "IntegrityError: duplicate key" quando a sequence fica dessincronizada dos dados
        # (ex: depois de uma migração/restauração de banco que preservou IDs antigos).
        for _tabela in ['usuarios', 'status', 'historico', 'trofeus', 'regras', 'notificacoes', 'bonus_regras', 'metas']:
            s.execute(text(f"SELECT setval(pg_get_serial_sequence('{_tabela}', 'id'), COALESCE((SELECT MAX(id) FROM {_tabela}), 1))"))

        # Faxina de Clones
        s.execute(text('''
            DELETE FROM regras WHERE id IN (
                SELECT id FROM (SELECT id, ROW_NUMBER() OVER (PARTITION BY usuario, descricao ORDER BY id DESC) as rn FROM regras) t WHERE t.rn > 1
            )
        '''))
        s.execute(text('''
            DELETE FROM bonus_regras WHERE id IN (
                SELECT id FROM (SELECT id, ROW_NUMBER() OVER (PARTITION BY usuario, descricao ORDER BY id DESC) as rn FROM bonus_regras) t WHERE t.rn > 1
            )
        '''))
        s.commit()

# --- LÓGICA DE AUTENTICAÇÃO E REGRAS PADRÃO ---
def criar_conta(user, pw):
    user_limpo = str(user).strip().lower()
    try:
        with conn.session as s:
            s.execute(text('INSERT INTO usuarios (username, password) VALUES (:u, :p)'), {"u": user_limpo, "p": hash_password(pw)})
            s.execute(text('INSERT INTO regras (usuario, descricao, valor, cartao_vermelho) VALUES (:u, :d, :v, :cv)'), obter_regras_padrao(user_limpo))
            s.execute(text('INSERT INTO bonus_regras (usuario, descricao, valor) VALUES (:u, :d, :v)'), obter_bonus_padrao(user_limpo))
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
    df = conn.query('SELECT descricao, valor, cartao_vermelho FROM regras WHERE usuario = :u', params={"u": _usuario_ativo()}, ttl=1)
    res = [(row.descricao, {"valor": row.valor, "cartao_vermelho": bool(row.cartao_vermelho)}) for row in df.itertuples(index=False)]
    def sort_key(item):
        texto = item[0]
        match = re.search(r'[a-zA-ZÀ-ÿ0-9]', texto)
        return texto[match.start():].lower() if match else texto.lower()
    return dict(sorted(res, key=sort_key))

def add_regra(descricao, valor, cartao_vermelho=False):
    with conn.session as s:
        s.execute(text('INSERT INTO regras (usuario, descricao, valor, cartao_vermelho) VALUES (:u, :d, :v, :cv)'), {"u": _usuario_ativo(), "d": descricao, "v": valor, "cv": cartao_vermelho})
        s.commit()

def update_regra(descricao_antiga, nova_descricao, novo_valor, cartao_vermelho=False):
    with conn.session as s:
        s.execute(text('UPDATE regras SET descricao = :nd, valor = :nv, cartao_vermelho = :cv WHERE descricao = :da AND usuario = :u'), {"nd": nova_descricao, "nv": novo_valor, "cv": cartao_vermelho, "da": descricao_antiga, "u": _usuario_ativo()})
        s.commit()

def delete_regra(descricao):
    with conn.session as s:
        s.execute(text('DELETE FROM regras WHERE descricao = :d AND usuario = :u'), {"d": descricao, "u": _usuario_ativo()})
        s.commit()

def get_bonus_regras():
    df = conn.query('SELECT descricao, valor FROM bonus_regras WHERE usuario = :u', params={"u": _usuario_ativo()}, ttl=1)
    if df.empty:
        with conn.session as s:
            s.execute(text('INSERT INTO bonus_regras (usuario, descricao, valor) VALUES (:u, :d, :v)'), obter_bonus_padrao(_usuario_ativo()))
            s.commit()
        df = pd.DataFrame(obter_bonus_padrao(_usuario_ativo())).rename(columns={"d": "descricao", "v": "valor"})

    res = list(df[['descricao', 'valor']].itertuples(index=False, name=None))
    def sort_key(item):
        texto = item[0]
        match = re.search(r'[a-zA-ZÀ-ÿ0-9]', texto)
        return texto[match.start():].lower() if match else texto.lower()
    return dict(sorted(res, key=sort_key))

def add_bonus_regra(descricao, valor):
    with conn.session as s:
        s.execute(text('INSERT INTO bonus_regras (usuario, descricao, valor) VALUES (:u, :d, :v)'), {"u": _usuario_ativo(), "d": descricao, "v": valor})
        s.commit()

def update_bonus_regra(descricao_antiga, nova_descricao, novo_valor):
    with conn.session as s:
        s.execute(text('UPDATE bonus_regras SET descricao = :nd, valor = :nv WHERE descricao = :da AND usuario = :u'), {"nd": nova_descricao, "nv": novo_valor, "da": descricao_antiga, "u": _usuario_ativo()})
        s.commit()

def delete_bonus_regra(descricao):
    with conn.session as s:
        s.execute(text('DELETE FROM bonus_regras WHERE descricao = :d AND usuario = :u'), {"d": descricao, "u": _usuario_ativo()})
        s.commit()

# --- FUNÇÕES DE NOTIFICAÇÃO (SININHO) ---
def add_notificacao(jogador, mensagem):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    with conn.session as s:
        s.execute(text('INSERT INTO notificacoes (usuario, nome, mensagem, lida, data) VALUES (:u, :n, :m, 0, :d)'), 
                  {"u": _usuario_ativo(), "n": str(jogador), "m": str(mensagem), "d": agora})
        s.commit()

def get_notificacoes_nao_lidas(jogador, usuario):
    return conn.query('SELECT id, mensagem, data FROM notificacoes WHERE LOWER(nome) = LOWER(:n) AND usuario = :u AND lida = 0 ORDER BY id ASC', params={"n": jogador, "u": usuario}, ttl=0)

def marcar_notificacoes_lidas(jogador, usuario):
    with conn.session as s:
        s.execute(text('UPDATE notificacoes SET lida = 1 WHERE LOWER(nome) = LOWER(:n) AND usuario = :u AND lida = 0'), {"n": jogador, "u": usuario})
        s.commit()

# --- FUNÇÕES DE STATUS E HISTÓRICO ---
def get_jogadores():
    df = conn.query('SELECT DISTINCT nome FROM status WHERE usuario = :u', params={"u": _usuario_ativo()}, ttl=0)
    return df['nome'].tolist()

def get_status(jogador):
    df = conn.query('SELECT nivel, base, saldo, faltas, aguardando_resgate, avatar, base_inicial, incremento, teto_maximo, titulos, limite_faltas, pin_jogador, meta_descricao, meta_valor, poupanca, data_cadastro, data_ultima_falta, fechamento_automatico, dias_fechamento, data_inicio_temporada FROM status WHERE LOWER(nome) = LOWER(:n) AND usuario = :u', params={"n": jogador, "u": _usuario_ativo()}, ttl=0)
    if not df.empty:
        row = df.iloc[0].to_dict()
        return (row['nivel'], row['base'], row['saldo'], row['faltas'], row['aguardando_resgate'],
                row['avatar'], row['base_inicial'], row['incremento'], float(row['teto_maximo']), int(row['titulos']), float(row['limite_faltas']), row['pin_jogador'], row['meta_descricao'], float(row['meta_valor'] if row['meta_valor'] else 0), float(row['poupanca'] if row['poupanca'] else 0.0),
                row['data_cadastro'], row['data_ultima_falta'], bool(row['fechamento_automatico']), int(row['dias_fechamento']) if row['dias_fechamento'] else 30, row['data_inicio_temporada'])
    return None

def update_status_saldo(jogador, nivel, base, saldo, faltas, aguardando, avatar, titulos, teto_maximo, limite_faltas, poupanca):
    with conn.session as s:
        s.execute(text('UPDATE status SET nivel=:n, base=:b, saldo=:s, faltas=:f, aguardando_resgate=:ag, avatar=:av, titulos=:t, teto_maximo=:tm, limite_faltas=:lf, poupanca=:p WHERE LOWER(nome)=LOWER(:nome) AND usuario=:u'), 
                  {"n": str(nivel), "b": float(base), "s": float(saldo), "f": float(faltas), "ag": int(aguardando), "av": str(avatar), "nome": str(jogador), "t": int(titulos), "tm": float(teto_maximo), "lf": float(limite_faltas), "p": float(poupanca), "u": _usuario_ativo()})
        s.commit()

def add_jogador(nome, estilo_avatar, base_inicial, incremento, teto_maximo, limite_faltas, pin_jogador, is_temporada_zero, fechamento_automatico=False, dias_fechamento=30):
    inc = max(incremento, 1.0)
    saltos_totais = int(round((teto_maximo - base_inicial) / inc))
    qtd_divisoes = saltos_totais + 1
    pedra_idx = min(qtd_divisoes - 1, len(PEDRAS) - 1)
    divisao_piso = f"{qtd_divisoes}ª Divisão - {PEDRAS[pedra_idx]}"

    niv_inicial = "Em Avaliação 🕵️‍♂️" if is_temporada_zero else divisao_piso
    b_inicial = 0.0 if is_temporada_zero else float(base_inicial)
    hoje = datetime.now().strftime("%d/%m/%Y")

    with conn.session as s:
        s.execute(text('INSERT INTO status (usuario, nome, nivel, base, saldo, faltas, aguardando_resgate, avatar, base_inicial, incremento, teto_maximo, titulos, limite_faltas, pin_jogador, poupanca, data_cadastro, data_inicio_temporada, fechamento_automatico, dias_fechamento) VALUES (:u, :n, :niv, :b, :s, :f, :ag, :av, :bi, :inc, :tm, 0, :lf, :pin, 0.0, :dc, :dit, :fa, :df)'), 
                  {"u": _usuario_ativo(), "n": nome, "niv": niv_inicial, "b": b_inicial, "s": b_inicial, "f": 0.0, "ag": 0, "av": estilo_avatar, "bi": base_inicial, "inc": incremento, "tm": teto_maximo, "lf": limite_faltas, "pin": hash_password(pin_jogador), "dc": hoje, "dit": hoje, "fa": bool(fechamento_automatico), "df": int(dias_fechamento)})
        s.commit()

def edit_jogador(nome_antigo, novo_nome, estilo_avatar, base_inicial, incremento, teto_maximo, limite_faltas, pin_jogador, change_pin, nova_poupanca, fechamento_automatico, dias_fechamento):
    with conn.session as s:
        query = 'UPDATE status SET nome=:nn, avatar=:av, base_inicial=:bi, incremento=:inc, teto_maximo=:tm, limite_faltas=:lf, poupanca=:np, fechamento_automatico=:fa, dias_fechamento=:df'
        params = {"nn": novo_nome, "av": estilo_avatar, "bi": float(base_inicial), "inc": float(incremento), "tm": float(teto_maximo), "lf": float(limite_faltas), "np": float(nova_poupanca), "fa": bool(fechamento_automatico), "df": int(dias_fechamento), "na": nome_antigo, "u": _usuario_ativo()}
        if change_pin:
            query += ', pin_jogador=:pin'
            params['pin'] = hash_password(pin_jogador)
        query += ' WHERE LOWER(nome)=LOWER(:na) AND usuario=:u'
        
        s.execute(text(query), params)
        if nome_antigo != novo_nome:
            s.execute(text('UPDATE historico SET nome=:nn WHERE LOWER(nome)=LOWER(:na) AND usuario=:u'), {"nn": novo_nome, "na": nome_antigo, "u": _usuario_ativo()})
            s.execute(text('UPDATE trofeus SET nome=:nn WHERE LOWER(nome)=LOWER(:na) AND usuario=:u'), {"nn": novo_nome, "na": nome_antigo, "u": _usuario_ativo()})
            s.execute(text('UPDATE notificacoes SET nome=:nn WHERE LOWER(nome)=LOWER(:na) AND usuario=:u'), {"nn": novo_nome, "na": nome_antigo, "u": _usuario_ativo()})
            s.execute(text('UPDATE metas SET jogador=:nn WHERE LOWER(jogador)=LOWER(:na) AND usuario=:u'), {"nn": novo_nome, "na": nome_antigo, "u": _usuario_ativo()})
        s.commit()

def delete_jogador(nome):
    with conn.session as s:
        s.execute(text('DELETE FROM status WHERE LOWER(nome) = LOWER(:n) AND usuario = :u'), {"n": nome, "u": _usuario_ativo()})
        s.execute(text('DELETE FROM historico WHERE LOWER(nome) = LOWER(:n) AND usuario = :u'), {"n": nome, "u": _usuario_ativo()})
        s.execute(text('DELETE FROM trofeus WHERE LOWER(nome) = LOWER(:n) AND usuario = :u'), {"n": nome, "u": _usuario_ativo()})
        s.execute(text('DELETE FROM notificacoes WHERE LOWER(nome) = LOWER(:n) AND usuario = :u'), {"n": nome, "u": _usuario_ativo()})
        s.execute(text('DELETE FROM metas WHERE LOWER(jogador) = LOWER(:n) AND usuario = :u'), {"n": nome, "u": _usuario_ativo()})
        s.commit()

# --- FUNÇÕES DE METAS (LISTA DE DESEJOS) ---
def get_metas(jogador):
    return conn.query('SELECT id, descricao, valor FROM metas WHERE LOWER(jogador) = LOWER(:j) AND usuario = :u ORDER BY id ASC', params={"j": jogador, "u": _usuario_ativo()}, ttl=0)

def add_meta(jogador, descricao, valor):
    with conn.session as s:
        s.execute(text('INSERT INTO metas (usuario, jogador, descricao, valor) VALUES (:u, :j, :d, :v)'), {"u": _usuario_ativo(), "j": jogador, "d": descricao, "v": float(valor)})
        s.commit()

def delete_meta(meta_id):
    with conn.session as s:
        s.execute(text('DELETE FROM metas WHERE id = :id AND usuario = :u'), {"id": int(meta_id), "u": _usuario_ativo()})
        s.commit()

# --- FUNÇÕES DE STREAK (SEQUÊNCIA SEM FALTAS) ---
def registrar_data_ultima_falta(jogador):
    hoje = datetime.now().strftime("%d/%m/%Y")
    with conn.session as s:
        s.execute(text('UPDATE status SET data_ultima_falta = :d WHERE LOWER(nome) = LOWER(:n) AND usuario = :u'), {"d": hoje, "n": jogador, "u": _usuario_ativo()})
        s.commit()

def calcular_dias_sem_falta(data_ultima_falta, data_cadastro):
    referencia = data_ultima_falta if data_ultima_falta else data_cadastro
    if not referencia:
        return 0
    try:
        data_ref = datetime.strptime(referencia, "%d/%m/%Y")
        return max(0, (datetime.now().date() - data_ref.date()).days)
    except Exception:
        return 0

# --- FECHAMENTO AUTOMÁTICO DE TEMPORADA ---
def set_data_inicio_temporada(jogador, data):
    with conn.session as s:
        s.execute(text('UPDATE status SET data_inicio_temporada = :d WHERE LOWER(nome) = LOWER(:n) AND usuario = :u'), {"d": data, "n": jogador, "u": _usuario_ativo()})
        s.commit()

def add_historico(jogador, infracao, valor, tipo='falta', cartao_vermelho=False):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    with conn.session as s:
        s.execute(text('INSERT INTO historico (usuario, nome, data, infracao, desconto, tipo, cartao_vermelho) VALUES (:u, :n, :d, :i, :v, :t, :cv)'), 
                  {"u": _usuario_ativo(), "n": str(jogador), "d": agora, "i": str(infracao), "v": float(valor), "t": str(tipo), "cv": bool(cartao_vermelho)})
        s.commit()

def get_historico(jogador):
    return conn.query('SELECT data, infracao, desconto, tipo FROM historico WHERE LOWER(nome) = LOWER(:n) AND usuario = :u ORDER BY id DESC', params={"n": jogador, "u": _usuario_ativo()}, ttl=0)

def get_historico_admin(jogador):
    # O Ponto Central de Carregamento para o Banco de Dados!
    return conn.query('SELECT id, data, infracao, desconto, tipo, cartao_vermelho FROM historico WHERE LOWER(nome) = LOWER(:n) AND usuario = :u ORDER BY id DESC', params={"n": jogador, "u": _usuario_ativo()}, ttl=1)

def delete_specific_historico(jogador, id_item, valor_item, tipo_item):
    with conn.session as s:
        s.execute(text('DELETE FROM historico WHERE id = :id AND usuario = :u'), {"id": int(id_item), "u": _usuario_ativo()})
        s.commit()
    dados_jogador = get_status(jogador)
    if dados_jogador:
        nivel, base, saldo, faltas, aguardando, avatar, base_ini, inc, teto, titulos, limite, pin, mdesc, mval, poupanca, *_resto = dados_jogador
        
        novo_saldo = saldo
        novas_faltas = faltas
        nova_poupanca = poupanca
        
        if tipo_item == 'falta':
            novo_saldo = saldo + float(valor_item)
            novas_faltas = max(0.0, faltas - float(valor_item))
        elif tipo_item == 'bonus':
            novo_saldo = saldo - float(valor_item)
            # Reverte também o "perdão" que o bônus deu na barra de faltas (mecânica do perdão)
            novas_faltas = faltas + float(valor_item)
        elif tipo_item == 'compra':
            nova_poupanca = poupanca + float(valor_item)
        elif tipo_item == 'deposito':
            nova_poupanca = max(0.0, poupanca - float(valor_item))
            
        update_status_saldo(jogador, nivel, base, novo_saldo, novas_faltas, aguardando, avatar, titulos, teto, limite, nova_poupanca)

def clear_historico(jogador):
    with conn.session as s:
        s.execute(text("DELETE FROM historico WHERE LOWER(nome) = LOWER(:n) AND usuario = :u AND tipo IN ('falta', 'bonus')"), {"n": jogador, "u": _usuario_ativo()})
        s.commit()

def add_trofeu(jogador, nivel, saldo):
    meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    mes_atual = meses[datetime.now().month]
    ano_atual = datetime.now().year
    with conn.session as s:
        s.execute(text('INSERT INTO trofeus (usuario, nome, data, nivel, saldo) VALUES (:u, :n, :d, :niv, :s)'), 
                  {"u": _usuario_ativo(), "n": str(jogador), "d": f"{mes_atual}/{ano_atual}", "niv": str(nivel), "s": float(saldo)})
        s.commit()

def get_trofeus(jogador):
    return conn.query('SELECT data as Data, nivel as Divisão, saldo as Recompensa FROM trofeus WHERE LOWER(nome) = LOWER(:n) AND usuario = :u ORDER BY id DESC', params={"n": jogador, "u": _usuario_ativo()}, ttl=0)
