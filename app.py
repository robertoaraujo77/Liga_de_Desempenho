import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
import base64
import re
from sqlalchemy import text

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E CSS
# ==========================================
st.set_page_config(page_title="Liga de Desempenho", page_icon="⚽", layout="centered")

st.markdown("""
    <style>
    @media (max-width: 768px) {
        h1 { font-size: 1.6rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

NIVEIS = ["Nível 1 - Bronze", "Nível 2 - Prata", "Nível 3 - Ouro", "Nível 4 - Diamante"]

ESTILOS_AVATAR = {
    "🧑 Desenho Moderno": "notionists", "🤠 Aventureiro": "adventurer", "🤖 Robô": "bottts",
    "😎 Emoji Divertido": "fun-emoji", "🧑‍🎨 Retrato Elegante": "micah", "👾 Pixel Art": "pixel-art",
    "👤 Pessoas (Clássico)": "avataaars", "👂 Orelhudos": "big-ears", "😁 Sorrisão": "big-smile",
    "✏️ Rabisco": "croodles", "🎀 Meninas": "lorelei", "🖍️ Minimalista": "miniavs",
    "🧍 Corpo Inteiro": "open-peeps", "👍 Joinhas": "thumbs"
}

# ==========================================
# GATILHOS DE ANIMAÇÃO
# ==========================================
def mostrar_popup(titulo, mensagem, cor, emoji):
    aviso = st.empty()
    with aviso.container():
        st.markdown(f"""
            <div style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(0,0,0,0.85); z-index: 999999; display: flex; justify-content: center; align-items: center;">
                <div style="background-color: #1e1e1e; padding: 40px 60px; border-radius: 20px; text-align: center; border: 3px solid {cor}; box-shadow: 0 10px 40px rgba(0,0,0,0.9); max-width: 80%;">
                    <div style="font-size: 80px; margin-bottom: 10px;">{emoji}</div>
                    <h1 style="color: {cor}; margin: 0; font-size: 36px; font-weight: bold;">{titulo}</h1>
                    <p style="color: #ffffff; font-size: 22px; margin-top: 15px;">{mensagem}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    time.sleep(4)
    aviso.empty()
    st.rerun()

if 'animacao_vitoria' in st.session_state and st.session_state.animacao_vitoria:
    st.session_state.animacao_vitoria = False
    st.balloons()
    mostrar_popup("CAMPEÃO!", "Excelente trabalho! Você subiu de divisão.", "#28a745", "🏆")

if 'animacao_derrota' in st.session_state and st.session_state.animacao_derrota:
    st.session_state.animacao_derrota = False
    mostrar_popup("REBAIXADO!", "O limite estourou. Você caiu de divisão...", "#dc3545", "🟥")

if 'animacao_manter' in st.session_state and st.session_state.animacao_manter:
    st.session_state.animacao_manter = False
    mostrar_popup("QUASE!", "Não subiu, mas escapou do rebaixamento. Foco no próximo mês!", "#fd7e14", "⚠️")


# ==========================================
# CONEXÃO COM SUPABASE (POSTGRESQL)
# ==========================================
# O Streamlit usará a secret configurada na nuvem para conectar
conn = st.connection("postgresql", type="sql")

def init_db():
    with conn.session as s:
        s.execute(text('''CREATE TABLE IF NOT EXISTS status (id SERIAL PRIMARY KEY, nome TEXT, nivel TEXT, base REAL, saldo REAL, faltas REAL, aguardando_resgate INTEGER DEFAULT 0, avatar TEXT DEFAULT 'notionists', base_inicial REAL DEFAULT 60.0, incremento REAL DEFAULT 10.0)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS historico (id SERIAL PRIMARY KEY, nome TEXT, data TEXT, infracao TEXT, desconto REAL, tipo TEXT DEFAULT 'falta')'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS trofeus (id SERIAL PRIMARY KEY, nome TEXT, data TEXT, nivel TEXT, saldo REAL)'''))
        s.execute(text('''CREATE TABLE IF NOT EXISTS regras (id SERIAL PRIMARY KEY, descricao TEXT, valor REAL)'''))
        
        # Inserir regras padrão se o banco for novo
        res = s.execute(text('SELECT COUNT(*) FROM regras')).scalar()
        if res == 0:
            regras_padrao = [
                {"d": "🚿 Não seca o banheiro", "v": 1.00},
                {"d": "🥱 Acordar reclamando pra ir a escola", "v": 1.00},
                {"d": "🚽 Deixar a toalha no chão ou na privada", "v": 1.00},
                {"d": "🧼 Não ir tomar banho quando solicitado", "v": 2.00},
                {"d": "👟 Deixa roupa no chão e chuteira", "v": 2.00},
                {"d": "😒 Reclama de ir aos treinos", "v": 2.00},
                {"d": "📚 Não fazer a lição de casa quando mandar", "v": 5.00},
                {"d": "🗑️ Não levar o lixo", "v": 5.00},
                {"d": "🤬 Desobedecer aos pais (Cartão Vermelho)", "v": 20.00}
            ]
            s.execute(text('INSERT INTO regras (descricao, valor) VALUES (:d, :v)'), regras_padrao)
        s.commit()

init_db()

# --- FUNÇÕES DE REGRAS ---
def get_regras():
    df = conn.query('SELECT descricao, valor FROM regras', ttl=0)
    res = list(df.itertuples(index=False, name=None))
    def sort_key(item):
        texto = item[0]
        match = re.search(r'[a-zA-ZÀ-ÿ0-9]', texto)
        return texto[match.start():].lower() if match else texto.lower()
    res_sorted = sorted(res, key=sort_key)
    return dict(res_sorted)

def add_regra(descricao, valor):
    with conn.session as s:
        s.execute(text('INSERT INTO regras (descricao, valor) VALUES (:d, :v)'), {"d": descricao, "v": valor})
        s.commit()

def update_regra(descricao_antiga, nova_descricao, novo_valor):
    with conn.session as s:
        s.execute(text('UPDATE regras SET descricao = :nd, valor = :nv WHERE descricao = :da'), {"nd": nova_descricao, "nv": novo_valor, "da": descricao_antiga})
        s.commit()

def delete_regra(descricao):
    with conn.session as s:
        s.execute(text('DELETE FROM regras WHERE descricao = :d'), {"d": descricao})
        s.commit()

# --- FUNÇÕES DE JOGADORES ---
def get_jogadores():
    df = conn.query('SELECT DISTINCT nome FROM status', ttl=0)
    return df['nome'].tolist()

def get_status(jogador):
    df = conn.query('SELECT nivel, base, saldo, faltas, aguardando_resgate, avatar, base_inicial, incremento FROM status WHERE nome = :n', params={"n": jogador}, ttl=0)
    if not df.empty:
        return tuple(df.iloc[0])
    return None

def update_status(jogador, nivel, base, saldo, faltas, aguardando, avatar):
    with conn.session as s:
        s.execute(text('UPDATE status SET nivel=:n, base=:b, saldo=:s, faltas=:f, aguardando_resgate=:ag, avatar=:av WHERE nome=:nome'), 
                  {"n": str(nivel), "b": float(base), "s": float(saldo), "f": float(faltas), "ag": int(aguardando), "av": str(avatar), "nome": str(jogador)})
        s.commit()

def add_jogador(nome, estilo_avatar, base_inicial, incremento):
    with conn.session as s:
        s.execute(text('INSERT INTO status (nome, nivel, base, saldo, faltas, aguardando_resgate, avatar, base_inicial, incremento) VALUES (:n, :niv, :b, :s, :f, :ag, :av, :bi, :inc)'), 
                  {"n": nome, "niv": NIVEIS[0], "b": base_inicial, "s": base_inicial, "f": 0.0, "ag": 0, "av": estilo_avatar, "bi": base_inicial, "inc": incremento})
        s.commit()

def delete_jogador(nome):
    with conn.session as s:
        s.execute(text('DELETE FROM status WHERE nome = :n'), {"n": nome})
        s.execute(text('DELETE FROM historico WHERE nome = :n'), {"n": nome})
        s.execute(text('DELETE FROM trofeus WHERE nome = :n'), {"n": nome})
        s.commit()

def add_historico(jogador, infracao, valor, tipo='falta'):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    with conn.session as s:
        s.execute(text('INSERT INTO historico (nome, data, infracao, desconto, tipo) VALUES (:n, :d, :i, :v, :t)'), 
                  {"n": str(jogador), "d": agora, "i": str(infracao), "v": float(valor), "t": str(tipo)})
        s.commit()

def get_historico(jogador):
    return conn.query('SELECT data, infracao, desconto, tipo FROM historico WHERE nome = :n ORDER BY id DESC', params={"n": jogador}, ttl=0)

def get_historico_admin(jogador):
    return conn.query('SELECT id, data, infracao, desconto, tipo FROM historico WHERE nome = :n ORDER BY id DESC', params={"n": jogador}, ttl=0)

def delete_specific_historico(jogador, id_item, valor_item, tipo_item):
    with conn.session as s:
        s.execute(text('DELETE FROM historico WHERE id = :id'), {"id": int(id_item)})
        s.commit()
    nivel, base, saldo, faltas, aguardando, avatar, base_ini, inc = get_status(jogador)
    if tipo_item == 'falta':
        novo_saldo = saldo + float(valor_item)
        novas_faltas = max(0.0, faltas - float(valor_item))
    else: 
        novo_saldo = saldo - float(valor_item)
        novas_faltas = faltas
    update_status(jogador, nivel, base, novo_saldo, novas_faltas, aguardando, avatar)

def clear_historico(jogador):
    with conn.session as s:
        s.execute(text('DELETE FROM historico WHERE nome = :n'), {"n": jogador})
        s.commit()

def add_trofeu(jogador, nivel, saldo):
    meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    mes_atual = meses[datetime.now().month]
    ano_atual = datetime.now().year
    data_formatada = f"{mes_atual}/{ano_atual}"
    with conn.session as s:
        s.execute(text('INSERT INTO trofeus (nome, data, nivel, saldo) VALUES (:n, :d, :niv, :s)'), 
                  {"n": str(jogador), "d": data_formatada, "niv": str(nivel), "s": float(saldo)})
        s.commit()

def get_trofeus(jogador):
    return conn.query('SELECT data as Data, nivel as Nível, saldo as Recompensa FROM trofeus WHERE nome = :n ORDER BY id DESC', params={"n": jogador}, ttl=0)

def render_header(nome_jogador, estilo_avatar):
    arquivo_foto = f"{nome_jogador.lower()}.jpg"
    img_src = ""
    if os.path.exists(arquivo_foto):
        with open(arquivo_foto, "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()
            img_src = f"data:image/jpeg;base64,{img_b64}"
    else:
        img_src = f"https://api.dicebear.com/7.x/{estilo_avatar}/svg?seed={nome_jogador}&backgroundColor=e2e8f0"
    
    st.markdown(f'''
        <div style="display: flex; justify-content: space-between; align-items: center; background-color: #1e1e1e; padding: 15px 25px; border-radius: 15px; margin-bottom: 25px; border: 1px solid #333;">
            <h1 style="margin: 0; font-size: 1.6rem; color: #ffffff;">📊 {nome_jogador}</h1>
            <img src="{img_src}" style="width: 55px; height: 55px; border-radius: 50%; object-fit: cover; border: 2px solid #444; background-color: #e2e8f0;">
        </div>
    ''', unsafe_allow_html=True)


# ==========================================
# LÓGICA DE SELEÇÃO DE JOGADORES E SISTEMA VAZIO
# ==========================================
jogadores_ativos = get_jogadores()
jogador_selecionado = None

if len(jogadores_ativos) > 1:
    st.markdown("<div style='text-align: center; margin-bottom: 20px;'>", unsafe_allow_html=True)
    jogador_selecionado = st.selectbox("👤 Selecione o Perfil:", jogadores_ativos)
    st.markdown("</div>", unsafe_allow_html=True)
elif len(jogadores_ativos) == 1:
    jogador_selecionado = jogadores_ativos[0]
else:
    st.info("👋 **Bem-vindo à Liga de Desempenho!** O sistema está vazio. Faça o login na Área da Arbitragem abaixo para cadastrar o primeiro perfil.")

# ==========================================
# INTERFACE DO JOGADOR
# ==========================================
if jogador_selecionado:
    dados_jogador = get_status(jogador_selecionado)
    if dados_jogador:
        nivel_atual, base_atual, saldo_atual, faltas_atual, aguardando_resgate, estilo_avatar, base_inicial, incremento = dados_jogador
        
        VALORES_BASE_DINAMICO = [
            base_inicial, 
            base_inicial + incremento, 
            base_inicial + (incremento * 2), 
            base_inicial + (incremento * 3)
        ]

        render_header(jogador_selecionado, estilo_avatar)

        if aguardando_resgate == 1:
            st.info(f"🚨 **Atenção {jogador_selecionado}!** O Árbitro encerrou a temporada. O placar está travado.")
            st.markdown("<h3 style='text-align: center;'>Chegou a hora de descobrir o seu destino...</h3>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🎁 CLIQUE AQUI PARA VER SEU RESULTADO", type="primary", use_container_width=True):
                df_historico = get_historico(jogador_selecionado)
                teve_vermelho = False
                if not df_historico.empty:
                    teve_vermelho = any("Cartão Vermelho" in inf for inf in df_historico['infracao'])

                index_atual = NIVEIS.index(nivel_atual)
                novo_index = index_atual
                
                if faltas_atual <= 5.0 and not teve_vermelho:
                    if index_atual < len(NIVEIS) - 1: novo_index = index_atual + 1
                    st.session_state.animacao_vitoria = True 
                else:
                    base_de_baixo = VALORES_BASE_DINAMICO[index_atual - 1] if index_atual > 0 else 0
                    if teve_vermelho or saldo_atual <= base_de_baixo:
                        if index_atual > 0: novo_index = index_atual - 1
                        st.session_state.animacao_derrota = True 
                    else:
                        novo_index = index_atual
                        st.session_state.animacao_manter = True
                        
                novo_nivel = NIVEIS[novo_index]
                nova_base = VALORES_BASE_DINAMICO[novo_index]
                
                add_trofeu(jogador_selecionado, novo_nivel, saldo_atual)
                update_status(jogador_selecionado, novo_nivel, nova_base, nova_base, 0.0, aguardando=0, avatar=estilo_avatar)
                clear_historico(jogador_selecionado)
                st.rerun()

            st.markdown("<br><br><br><br>", unsafe_allow_html=True)

        else:
            aba1, aba2 = st.tabs(["🏟️ Placar do Mês", "🏆 Sala de Troféus"])
            
            with aba1:
                col1, col2, col3 = st.columns([1.5, 1, 1.2])
                col1.metric("Nível Atual", nivel_atual)
                col2.metric("Saldo do Mês", f"R$ {max(0, saldo_atual):.2f}".replace('.', ','))
                col3.metric("Faltas Acumuladas", f"R$ {faltas_atual:.2f}".replace('.', ','), delta="- Limite: R$ 5,00", delta_color="inverse")

                st.markdown("**Progresso da Tolerância (Limite R$ 5,00):**")
                porcentagem = min((faltas_atual / 5.0) * 100, 100)

                if porcentagem < 50: cor_barra = "#28a745"
                elif porcentagem < 100: cor_barra = "#fd7e14"
                else: cor_barra = "#dc3545"

                st.markdown(f"""
                    <div style="background-color: #2b2b2b; border-radius: 15px; width: 100%; height: 25px; margin-bottom: 10px; border: 1px solid #444;">
                        <div style="background-color: {cor_barra}; width: {porcentagem}%; height: 100%; border-radius: 15px; transition: width 0.8s ease-in-out, background-color 0.5s;"></div>
                    </div>
                """, unsafe_allow_html=True)

                index_atual = NIVEIS.index(nivel_atual)
                if faltas_atual <= 5.00:
                    st.success("🟢 Tudo certo! Na zona de classificação para o próximo nível.")
                else:
                    base_de_baixo = VALORES_BASE_DINAMICO[index_atual - 1] if index_atual > 0 else 0
                    if saldo_atual <= base_de_baixo:
                        st.error("🔴 Perigo: Você entrou na Zona de Rebaixamento!")
                    else:
                        st.warning("🟠 Atenção: A subida foi bloqueada, mas seu saldo garante permanência.")

                st.markdown("---")
                st.subheader("📋 Histórico do Mês")
                df_historico = get_historico(jogador_selecionado)
                if not df_historico.empty:
                    df_view = df_historico.copy()
                    df_view['Lançamento'] = df_view.apply(lambda row: f"+ R$ {row['desconto']:.2f}".replace('.', ',') if row['tipo'] == 'bonus' else f"- R$ {row['desconto']:.2f}".replace('.', ','), axis=1)
                    df_view = df_view[['data', 'infracao', 'Lançamento']]
                    df_view.columns = ['Data', 'Motivo', 'Valor']
                    st.dataframe(df_view, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum lançamento registrado neste mês.")

            with aba2:
                st.subheader("🌟 Histórico de Temporadas")
                df_trofeus = get_trofeus(jogador_selecionado)
                if not df_trofeus.empty:
                    df_trofeus['Recompensa'] = df_trofeus['Recompensa'].apply(lambda x: f"R$ {x:.2f}".replace('.', ','))
                    st.dataframe(df_trofeus, use_container_width=True, hide_index=True)
                else:
                    st.info(f"{jogador_selecionado} ainda não encerrou nenhuma temporada.")


# ==========================================
# ÁREA DA ARBITRAGEM (SÓ VOCÊ E A PALOMA)
# ==========================================
st.markdown("---")
st.markdown("### 🔐 Área da Arbitragem")
if jogador_selecionado:
    st.markdown(f"*(Controlando o perfil: **{jogador_selecionado}**)*")

col_senha, col_btn_senha = st.columns([3, 1])
with col_senha:
    senha = st.text_input("Senha", type="password", label_visibility="collapsed", placeholder="Digite a senha...")
with col_btn_senha:
    st.button("🔓 Entrar", use_container_width=True)

if senha == "2811":
    
    if not jogador_selecionado:
        st.markdown("**➕ Cadastrar Primeiro Jogador**")
        col_novo_nome, col_novo_avatar = st.columns([2, 2])
        with col_novo_nome:
            novo_nome = st.text_input("Nome:", placeholder="Ex: Davi", label_visibility="collapsed")
        with col_novo_avatar:
            nome_avatar = st.selectbox("Estilo do Avatar:", list(ESTILOS_AVATAR.keys()), label_visibility="collapsed")
            
        col_base, col_inc = st.columns([2, 2])
        with col_base:
            base_ini = st.number_input("Mesada Inicial (Nível 1 - R$):", value=60.0, step=5.0)
        with col_inc:
            inc_val = st.number_input("Aumento por Nível (R$):", value=10.0, step=5.0)
            
        if st.button("Cadastrar e Iniciar Liga", type="primary", use_container_width=True):
            if novo_nome:
                add_jogador(novo_nome, ESTILOS_AVATAR[nome_avatar], base_ini, inc_val)
                st.success(f"O jogador {novo_nome} entrou em campo!")
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("Digite o nome do jogador.")
    else:
        regras_dinamicas = get_regras()
        tab_jogo, tab_regras, tab_elenco = st.tabs(["⚖️ Lançamentos", "📝 Regras", "⚙️ Elenco"])
        
        with tab_jogo:
            if aguardando_resgate == 1:
                st.warning(f"⏳ O sistema está pausado aguardando o resgate.")
                if st.button("❌ Cancelar Autorização", use_container_width=True):
                    update_status(jogador_selecionado, nivel_atual, base_atual, saldo_atual, faltas_atual, aguardando=0, avatar=estilo_avatar)
                    st.rerun()
            else:
                st.markdown("**🔴 Aplicar Penalidade (Falta)**")
                col_infracao, col_btn_add = st.columns([3, 1])
                with col_infracao:
                    infracao_selecionada = st.selectbox("Selecione a infração:", list(regras_dinamicas.keys()), label_visibility="collapsed")
                with col_btn_add:
                    if st.button("Aplicar Falta", type="primary", use_container_width=True):
                        valor = regras_dinamicas[infracao_selecionada]
                        novo_saldo = saldo_atual - valor
                        novas_faltas = faltas_atual + valor
                        update_status(jogador_selecionado, nivel_atual, base_atual, novo_saldo, novas_faltas, aguardando=0, avatar=estilo_avatar)
                        add_historico(jogador_selecionado, infracao_selecionada, valor, 'falta')
                        st.rerun()
                        
                st.markdown("---")
                
                st.markdown("**⭐ Aplicar Bônus (O Golaço!)**")
                col_motivo, col_valor, col_btn_bonus = st.columns([2, 1, 1])
                with col_motivo:
                    motivo_bonus = st.text_input("Motivo do Bônus:", placeholder="Ex: Arrumou o quarto")
                with col_valor:
                    valor_bonus = st.number_input("Valor R$", min_value=1.00, step=1.00)
                with col_btn_bonus:
                    st.markdown("<div style='margin-top: 28px;'>", unsafe_allow_html=True)
                    if st.button("Aplicar Bônus", use_container_width=True):
                        if motivo_bonus:
                            novo_saldo = saldo_atual + valor_bonus
                            update_status(jogador_selecionado, nivel_atual, base_atual, novo_saldo, faltas_atual, aguardando=0, avatar=estilo_avatar)
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
                        
                    with col_remove:
                        falta_selecionada = st.selectbox("Selecione o item:", list(opcoes_falta.keys()), label_visibility="collapsed")
                        
                    with col_btn_remove:
                        if st.button("Excluir Item", use_container_width=True):
                            id_falta, valor_item, tipo_item = opcoes_falta[falta_selecionada]
                            delete_specific_historico(jogador_selecionado, id_falta, valor_item, tipo_item)
                            st.rerun()
                else:
                    st.info("O histórico está limpo.")

                st.markdown("---")
                
                st.markdown("**🏁 Fechamento do Mês**")
                st.warning(f"Isto liberará o botão surpresa de virada de mês para o {jogador_selecionado}.")
                if st.button("✅ Autorizar Fim da Temporada", use_container_width=True):
                    update_status(jogador_selecionado, nivel_atual, base_atual, saldo_atual, faltas_atual, aguardando=1, avatar=estilo_avatar)
                    st.rerun()

        with tab_regras:
            st.markdown("**➕ Adicionar Nova Regra**")
            col_nova_regra, col_novo_val, col_btn_regra = st.columns([3, 1, 1])
            with col_nova_regra:
                desc_regra = st.text_input("Descrição da Regra:", placeholder="Ex: Deixar a luz acesa")
            with col_novo_val:
                val_regra = st.number_input("Valor (R$):", min_value=0.50, step=0.50, key="val_regra_add")
            with col_btn_regra:
                st.markdown("<div style='margin-top: 28px;'>", unsafe_allow_html=True)
                if st.button("Salvar Regra", use_container_width=True):
                    if desc_regra and desc_regra not in regras_dinamicas:
                        add_regra(desc_regra, val_regra)
                        st.success("Regra Adicionada!")
                        time.sleep(1)
                        st.rerun()
                    elif desc_regra in regras_dinamicas:
                        st.error("Regra já existe.")
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("---")
            
            st.markdown("**✏️ Editar ou Remover Regra Existente**")
            if regras_dinamicas:
                regra_selecionada = st.selectbox("Selecione a regra para editar:", list(regras_dinamicas.keys()), key="edit_regra_sel", label_visibility="collapsed")
                
                col_edit_desc, col_edit_val = st.columns([3, 1])
                with col_edit_desc:
                    novo_texto = st.text_input("Descrição:", value=regra_selecionada, key="edit_regra_desc")
                with col_edit_val:
                    novo_valor = st.number_input("Valor (R$):", value=float(regras_dinamicas[regra_selecionada]), min_value=0.50, step=0.50, key="edit_regra_val")
                
                col_btn_save, col_btn_del = st.columns(2)
                with col_btn_save:
                    if st.button("💾 Salvar Alterações", use_container_width=True):
                        if novo_texto != regra_selecionada and novo_texto in regras_dinamicas:
                            st.error("Já existe uma regra com esse nome!")
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
            else:
                st.info("Nenhuma regra cadastrada.")

        with tab_elenco:
            st.markdown("**➕ Adicionar Novo Jogador ao Elenco**")
            col_novo_nome, col_novo_avatar = st.columns([2, 2])
            with col_novo_nome:
                novo_nome = st.text_input("Nome:", placeholder="Ex: Arthur", label_visibility="collapsed")
            with col_novo_avatar:
                nome_avatar = st.selectbox("Estilo do Avatar:", list(ESTILOS_AVATAR.keys()), label_visibility="collapsed")
                
            col_base, col_inc = st.columns([2, 2])
            with col_base:
                base_ini = st.number_input("Mesada Inicial (R$):", value=50.0, step=5.0)
            with col_inc:
                inc_val = st.number_input("Aumento/Nível (R$):", value=10.0, step=5.0)
                
            if st.button("Cadastrar Jogador", use_container_width=True):
                if novo_nome and novo_nome not in jogadores_ativos:
                    add_jogador(novo_nome, ESTILOS_AVATAR[nome_avatar], base_ini, inc_val)
                    st.success(f"{novo_nome} escalado para a liga!")
                    time.sleep(1.5)
                    st.rerun()
                elif novo_nome in jogadores_ativos:
                    st.error("Jogador já existe no elenco!")
                    
            st.markdown("---")
            
            st.markdown("**❌ Remover Jogador do Elenco**")
            st.warning("CUIDADO: Esta ação apagará permanentemente o perfil, o histórico e a sala de troféus.")
            col_excluir, col_btn_excluir = st.columns([3, 1])
            with col_excluir:
                jogador_excluir = st.selectbox("Selecione o jogador:", jogadores_ativos, label_visibility="collapsed")
            with col_btn_excluir:
                confirmar = st.checkbox("Confirmar exclusão", key="chk_excluir")
                if st.button("Excluir Perfil", use_container_width=True, disabled=not confirmar):
                    delete_jogador(jogador_excluir)
                    st.success(f"O jogador {jogador_excluir} foi removido.")
                    time.sleep(1.5)
                    st.rerun()

elif senha != "":
    st.error("Senha Incorreta.")
