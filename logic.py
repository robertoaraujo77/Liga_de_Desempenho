import streamlit as st
import re
import time
import base64
import io
import hashlib
from PIL import Image
from config import PEDRAS

# ==========================================
# UTILITÁRIOS E SEGURANÇA E AUTO-CROP
# ==========================================
def hash_password(password):
    senha_limpa = str(password).strip()
    return hashlib.sha256(str.encode(senha_limpa)).hexdigest()

def converter_para_base64(image):
    width, height = image.size
    min_dim = min(width, height)
    left = (width - min_dim)/2
    top = (height - min_dim)/2
    right = (width + min_dim)/2
    bottom = (height + min_dim)/2
    image = image.crop((left, top, right, bottom))
    image = image.resize((150, 150), Image.Resampling.LANCZOS)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode()}"

def extrair_numero_divisao(nivel_str):
    match = re.match(r'(\d+)ª', str(nivel_str))
    return int(match.group(1)) if match else None

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
        divisao_nome = f"{num_divisao}ª Divisão - {PEDRAS[pedra_idx]}"
        divisoes.append({"nome": divisao_nome, "valor": valor, "num_divisao": num_divisao})

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

def calcular_badges(df_hist, faltas_atual):
    badges = []
    if df_hist.empty: return badges
    
    infracoes_str = df_hist['infracao'].astype(str).str.lower()
    
    gols = infracoes_str.str.contains('gol').sum()
    ajudas = infracoes_str.str.contains('louça|limpeza|cama|lixo|casa').sum()
    estudos = infracoes_str.str.contains('livro|escola|lição|dever').sum()
    treinos = infracoes_str.str.contains('trein|quadra|desafio').sum()
    
    if gols >= 1: badges.append("⚽ Artilheiro")
    if ajudas >= 3: badges.append("🧹 Ajudante")
    if estudos >= 2: badges.append("📚 Estudioso")
    if treinos >= 2: badges.append("🔥 Atleta Focado")
    if faltas_atual == 0.0 and len(df_hist) >= 3: badges.append("🛡️ Intacto")
    
    return badges

def render_carta_atleta(nome_jogador, estilo_avatar, div_nome, saldo, base, faltas, titulos, badges=[]):
    img_src = estilo_avatar if estilo_avatar.startswith("data:image") else f"https://api.dicebear.com/7.x/{estilo_avatar}/svg?seed={nome_jogador}&backgroundColor=e2e8f0"
    
    # Cálculo do Score
    score_val = 99
    bonus_acumulado = max(0, saldo - (base - faltas))
    score_val -= int(faltas * 5)
    score_val += int(bonus_acumulado * 3)
    score_val = min(99, max(40, score_val)) 

    # Cor do anel do Score (verde = ótimo, laranja = mediano, vermelho = crítico)
    cor_score = "#28a745" if score_val >= 80 else "#fd7e14" if score_val >= 60 else "#dc3545"

    # Cores dinâmicas baseadas na divisão
    bg_gradient = "linear-gradient(135deg, #2b32b2 0%, #1488cc 100%)"
    if "Ouro" in div_nome: bg_gradient = "linear-gradient(135deg, #e6c27a 0%, #d4af37 50%, #997328 100%)"
    elif "Prata" in div_nome: bg_gradient = "linear-gradient(135deg, #e3e3e3 0%, #b5b5b5 50%, #8a8a8a 100%)"
    elif "Bronze" in div_nome: bg_gradient = "linear-gradient(135deg, #cd7f32 0%, #a0522d 50%, #8b4513 100%)"
    elif "Diamante" in div_nome: bg_gradient = "linear-gradient(135deg, #b9f2ff 0%, #6dd5ed 50%, #2193b0 100%)"
    elif "Alexandrita" in div_nome: bg_gradient = "linear-gradient(135deg, #8A2BE2 0%, #4B0082 100%)"
    elif "Esmeralda" in div_nome: bg_gradient = "linear-gradient(135deg, #00C9FF 0%, #92FE9D 100%)"
    elif "Rubi" in div_nome: bg_gradient = "linear-gradient(135deg, #ff0844 0%, #ffb199 100%)"
    elif "Em Avaliação" in div_nome: bg_gradient = "linear-gradient(135deg, #4b5563 0%, #1f2937 100%)"

    texto_titulos = f"<div style='font-size: 10px; color: #1a1a1a; margin-bottom: 5px; font-weight: 900; background: rgba(255,255,255,0.4); padding: 2px 8px; border-radius: 4px; display: inline-block;'>🏆 {titulos}x CAMPEÃO</div>" if titulos > 0 else ""
    
    # Design das Badges em faixas horizontais pequenas
    html_badges = ""
    if badges:
        badges_tags = "".join([f"<div style='background: rgba(255,255,255,0.8); color: #1a1a1a; padding: 2px 6px; border-radius: 3px; margin: 2px 0; font-size: 9px; font-weight: 900; text-transform: uppercase; width: fit-content; border: 1px solid rgba(0,0,0,0.1);'>{b}</div>" for b in badges])
        html_badges = f"<div style='margin-top: 5px; display: flex; flex-direction: column; gap: 2px;'>{badges_tags}</div>"

    # Layout Horizontal alinhado à esquerda para evitar o bug do Markdown
    card_html = f'''
<div style="background: {bg_gradient}; border-radius: 15px; padding: 15px; color: #1a1a1a; box-shadow: 0 6px 12px rgba(0,0,0,0.4); border: 2px solid #fff; display: flex; align-items: center; gap: 20px; position: relative; overflow: hidden; margin-bottom: 20px;">
<div style="text-align: center; min-width: 90px;">
<div style="background: #1a1a1a; color: white; border-radius: 8px; padding: 2px 5px; position: absolute; top: 10px; left: 10px; z-index: 10; border: 2px solid {cor_score};">
<div style="font-size: 18px; font-weight: 900; line-height: 1;">{score_val}</div>
<div style="font-size: 7px; font-weight: bold; text-transform: uppercase;">SCORE</div>
</div>
<img src="{img_src}" style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid {cor_score}; background-color: #e2e8f0; object-fit: cover;">
</div>
<div style="flex-grow: 1;">
<div style="font-size: 20px; font-weight: 900; text-transform: uppercase; letter-spacing: -0.5px; line-height: 1;">{nome_jogador}</div>
<div style="font-size: 12px; font-weight: 700; color: rgba(0,0,0,0.7); margin-bottom: 8px;">{div_nome}</div>
{texto_titulos}
{html_badges}
</div>
</div>
'''
    st.markdown(card_html, unsafe_allow_html=True)

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
