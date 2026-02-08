import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import re
import urllib.parse

# --- CONFIGURAÇÃO ---
URL_CSV = "Cadastro dos Lifegroups.csv"

st.set_page_config(page_title="Encontre seu LifeGroup", page_icon="🎯", layout="centered")

# --- ESTILOS CSS (Visual Clean) ---
st.markdown("""
<style>
    /* Botão de Buscar (Verde) */
    div.stButton > button:first-child {
        width: 100%;
        background-color: #0f9d58;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: none;
    }
    /* Títulos dos filtros */
    .filter-label {
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
def extrair_zap(texto):
    if pd.isna(texto): return None
    limpo = str(texto).replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
    encontrado = re.search(r'\d{10,13}', limpo)
    if encontrado:
        num = encontrado.group()
        return '55' + num if not num.startswith('55') else num
    return None

@st.cache_data(ttl=600)
def carregar_dados():
    try:
        df = pd.read_csv(URL_CSV)
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=['Nome do Life'])
        
        geolocator = Nominatim(user_agent="app_life_v6_design")
        latitudes = []
        longitudes = []
        
        for endereco in df['Endereço']:
            if not isinstance(endereco, str) or endereco.strip() == "":
                latitudes.append(None); longitudes.append(None)
                continue
            try:
                # Otimização para SP
                query = f"{endereco}, Brasil"
                loc = geolocator.geocode(query, timeout=10)
                if loc:
                    latitudes.append(loc.latitude); longitudes.append(loc.longitude)
                else:
                    latitudes.append(None); longitudes.append(None)
            except:
                latitudes.append(None); longitudes.append(None)
        
        df['lat'] = latitudes
        df['lon'] = longitudes
        return df.dropna(subset=['lat', 'lon'])
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def obter_lat_lon_usuario(endereco):
    geolocator = Nominatim(user_agent="app_life_user_v6")
    try:
        query = f"{endereco}, São Paulo, Brasil"
        loc = geolocator.geocode(query)
        if not loc:
            loc = geolocator.geocode(f"{endereco}, Brasil")
        if loc:
            return loc.latitude, loc.longitude, loc.address
        return None, None, None
    except:
        return None, None, None

# --- CARREGA DADOS ---
df_geral = carregar_dados()

# --- INTERFACE ---
st.title("🎯 Encontre o LifeGroup ideal")
st.write("Preencha seus dados e suas preferências abaixo.")

# Verifica se o DF carregou para pegar as opções de filtro
opcoes_tipo = []
opcoes_dia = []
opcoes_modo = []

if not df_geral.empty:
    if 'Tipo de Life' in df_geral.columns:
        opcoes_tipo = sorted(df_geral['Tipo de Life'].unique().tolist())
    if 'Dia da Semana' in df_geral.columns:
        opcoes_dia = sorted(df_geral['Dia da Semana'].unique().tolist())
    if 'Modo' in df_geral.columns:
        opcoes_modo = sorted(df_geral['Modo'].unique().tolist())

# --- FORMULÁRIO ÚNICO ---
with st.form("form_busca"):
    st.subheader("1. Seus Dados")
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome")
    with col2:
        whatsapp = st.text_input("WhatsApp (com DDD)")
    
    endereco_usuario = st.text_input("Endereço ou Bairro", placeholder="Ex: Centro, Guarulhos")
    
    st.markdown("---")
    st.subheader("2. Suas Preferências")
    
    # FILTROS ORGANIZADOS EM COLUNAS (Parece células)
    c_filtro1, c_filtro2, c_filtro3 = st.columns(3)
    
    with c_filtro1:
        st.markdown('<div class="filter-label">👥 Público</div>', unsafe_allow_html=True)
        # Multiselect age como "checkboxes" compactos
        filtro_tipo = st.multiselect("Selecione:", options=opcoes_tipo, default=opcoes_tipo, label_visibility="collapsed")
        
    with c_filtro2:
        st.markdown('<div class="filter-label">📅 Dias</div>', unsafe_allow_html=True)
        filtro_dia = st.multiselect("Selecione:", options=opcoes_dia, default=opcoes_dia, label_visibility="collapsed")
        
    with c_filtro3:
        st.markdown('<div class="filter-label">💻 Modo</div>', unsafe_allow_html=True)
        filtro_modo = st.multiselect("Selecione:", options=opcoes_modo, default=opcoes_modo, label_visibility="collapsed")
    
    st.markdown("<br>", unsafe_allow_html=True)
    buscar = st.form_submit_button("🚀 BUSCAR GRUPOS AGORA")

# --- LÓGICA DE BUSCA ---
if buscar:
    if not nome or not whatsapp or not endereco_usuario:
        st.warning("⚠️ Preencha nome, whatsapp e endereço.")
    elif df_geral.empty:
        st.error("Base de dados vazia.")
    else:
        # Aplica filtros
        df_filtrado = df_geral.copy()
        if filtro_tipo:
            df_filtrado = df_filtrado[df_filtrado['Tipo de Life'].isin(filtro_tipo)]
        if filtro_dia:
            df_filtrado = df_filtrado[df_filtrado['Dia da Semana'].isin(filtro_dia)]
        if filtro_modo:
            df_filtrado = df_filtrado[df_filtrado['Modo'].isin(filtro_modo)]
            
        if df_filtrado.empty:
            st.warning("Nenhum grupo encontrado com essas combinações.")
        else:
            with st.spinner("Localizando..."):
                lat_user, lon_user, endereco_achado = obter_lat_lon_usuario(endereco_usuario)
                
                if lat_user:
                    st.success(f"📍 Base: **{endereco_achado}**")
                    
                    user_loc = (lat_user, lon_user)
                    df_filtrado['distancia'] = df_filtrado.apply(
                        lambda row: geodesic(user_loc, (row['lat'], row['lon'])).km, axis=1
                    )
                    
                    top3 = df_filtrado.sort_values(by='distancia').head(3)
                    
                    st.markdown("### 👇 Melhores Opções:")
                    
                    for index, row in top3.iterrows():
                        with st.container():
                            st.markdown("---")
                            c1, c2 = st.columns([1.5, 1])
                            
                            bairro = row['Bairro'] if 'Bairro' in row else "Região não informada"
                            
                            with c1:
                                st.subheader(f"🏠 {row['Nome do Life']}")
                                st.write(f"📍 **{bairro}** ({row['distancia']:.1f} km)")
                                st.caption(f"{row['Tipo de Life']} | {row['Modo']}")
                                st.write(f"📅 {row['Dia da Semana']} às {row['Horário de Início']}")
                                
                            with c2:
                                tel_lider = extrair_zap(row['Telefone'])
                                lider = row['Líderes']
                                
                                if tel_lider:
                                    msg1 = f"Olá {lider}, sou {nome}. Vi seu LifeGroup no site e quero visitar! Meu zap é {whatsapp}."
                                    link1 = f"https://wa.me/{tel_lider}?text={msg1.replace(' ', '%20')}"
                                    
                                    msg2 = f"Olá {lider}, sou {nome}. Tenho interesse, mas prefiro que me ligue: {whatsapp}."
                                    link2 = f"https://wa.me/{tel_lider}?text={msg2.replace(' ', '%20')}"
                                    
                                    # Botões Estilizados
                                    st.markdown(f"""
                                    <a href="{link1}" target="_blank" style="text-decoration:none;">
                                        <div style="background-color:#25D366;color:white;padding:10px;border-radius:6px;text-align:center;font-weight:bold;margin-bottom:5px;font-size:14px;">
                                            💬 Quero Visitar
                                        </div>
                                    </a>
                                    <a href="{link2}" target="_blank" style="text-decoration:none;">
                                        <div style="background-color:#007bff;color:white;padding:10px;border-radius:6px;text-align:center;font-weight:bold;font-size:14px;">
                                            📞 Peça p/ Ligar
                                        </div>
                                    </a>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.error("Sem contato")
                else:
                    st.error("Endereço não encontrado.")
