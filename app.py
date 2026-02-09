import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import re
import urllib.parse

# --- CONFIGURAÇÃO ---
URL_CSV = "Cadastro dos Lifegroups.csv"

# Configuração da Página
st.set_page_config(page_title="LifeGroups | Paz São Paulo", page_icon="💙", layout="centered")

# --- ESTILOS CSS (AZUL PAZ SP) ---
st.markdown("""
<style>
    /* Botão de Buscar */
    div.stButton > button:first-child {
        width: 100%;
        background-color: #1C355E;
        color: white;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        border: none;
        font-weight: bold;
        font-size: 16px;
        text-transform: uppercase;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #162a4a;
        box-shadow: 0px 6px 8px rgba(0,0,0,0.2);
        color: white;
    }
    
    /* Textos */
    .filter-label {
        font-weight: 600;
        font-size: 14px;
        color: #1C355E;
        margin-bottom: 5px;
    }
    
    h1 { color: #1C355E; font-family: 'Helvetica', sans-serif; }
    
    /* Abas */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px;
        color: #1C355E;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1C355E;
        color: white;
    }
    
    /* Box de Confirmação de Endereço */
    .address-box {
        background-color: #e8f4fd;
        border-left: 5px solid #1C355E;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
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

def limpar_endereco_visual(location):
    try:
        end = location.raw.get('address', {})
        rua = end.get('road', '')
        numero = end.get('house_number', '')
        bairro = end.get('suburb', end.get('neighbourhood', ''))
        cidade = end.get('city', end.get('town', end.get('municipality', '')))
        
        partes = []
        if rua: partes.append(rua)
        if numero: partes.append(numero)
        if bairro: partes.append(bairro)
        
        texto_final = ", ".join(partes)
        if cidade: texto_final += f" - {cidade}"
            
        if len(texto_final) < 5:
            return location.address.split(',')[0] + ", " + location.address.split(',')[1]
        return texto_final
    except:
        return location.address.split(',')[0]

@st.cache_data(ttl=600)
def carregar_dados():
    try:
        df = pd.read_csv(URL_CSV)
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=['Nome do Life'])
        
        geolocator = Nominatim(user_agent="app_paz_v14_final")
        latitudes = []
        longitudes = []
        
        for endereco in df['Endereço']:
            if not isinstance(endereco, str) or endereco.strip() == "":
                latitudes.append(None); longitudes.append(None)
                continue
            try:
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
    geolocator = Nominatim(user_agent="app_paz_user_v14")
    try:
        query = f"{endereco}, São Paulo, Brasil"
        loc = geolocator.geocode(query)
        if not loc:
            loc = geolocator.geocode(f"{endereco}, Brasil")
        if loc:
            endereco_bonito = limpar_endereco_visual(loc)
            return loc.latitude, loc.longitude, endereco_bonito
        return None, None, None
    except:
        return None, None, None

def exibir_cartoes(dataframe, nome_usuario, is_online=False):
    for index, row in dataframe.iterrows():
        with st.container():
            st.markdown("---")
            c1, c2 = st.columns([1.5, 1])
            
            bairro = row['Bairro'] if 'Bairro' in row else "Região não informada"
            
            with c1:
                st.markdown(f"### 💙 {row['Nome do Life']}")
                
                if is_online:
                    st.write("📍 **Life Online** (Sem fronteiras 🌎)")
                else:
                    st.write(f"📍 **{bairro}** ({row['distancia']:.1f} km)")
                
                st.caption(f"{row['Tipo de Life']} | {row['Modo']}")
                st.write(f"📅 {row['Dia da Semana']} às {row['Horário de Início']}")
                
            with c2:
                tel_lider = extrair_zap(row['Telefone'])
                lider = row['Líderes']
                
                if tel_lider:
                    msg1 = f"Olá {lider}, sou {nome_usuario}. Encontrei seu LifeGroup no site da Paz e gostaria de conhecer! Quando será o próximo encontro?"
                    link1 = f"https://wa.me/{tel_lider}?text={urllib.parse.quote(msg1)}"
                    
                    msg2 = f"Olá {lider}, sou {nome_usuario}. Tenho interesse no LifeGroup, mas prefiro conversar por voz. Você pode me ligar rapidinho quando puder?"
                    link2 = f"https://wa.me/{tel_lider}?text={urllib.parse.quote(msg2)}"
                    
                    st.markdown(f"""
                    <a href="{link1}" target="_blank" style="text-decoration:none;">
                        <div style="background-color:#25D366;color:white;padding:10px;border-radius:6px;text-align:center;font-weight:bold;margin-bottom:8px;font-size:14px;box-shadow: 0px 2px 4px rgba(0,0,0,0.1);">
                            💬 Quero Participar
                        </div>
                    </a>
                    <a href="{link2}" target="_blank" style="text-decoration:none;">
                        <div style="background-color:#1C355E;color:white;padding:10px;border-radius:6px;text-align:center;font-weight:bold;font-size:14px;box-shadow: 0px 2px 4px rgba(0,0,0,0.1);">
                            📞 Peça p/ Ligar
                        </div>
                    </a>
                    """, unsafe_allow_html=True)
                else:
                    st.error("Sem contato")

# --- CARREGA DADOS ---
df_geral = carregar_dados()

# --- INTERFACE ---

# 1. LOGO (Atualizado para logo_menor.png)
# Se o arquivo não existir no GitHub ainda, o Streamlit pode mostrar um ícone de "imagem quebrada".
# Assim que você subir o arquivo 'logo_menor.png', ele aparece.
try:
    st.image("logo_menor.png", width=150) 
except:
    st.write("") # Se der erro na imagem, não quebra o site

st.title("Encontre seu LifeGroup")
st.markdown("**Paz Church São Paulo**")
st.write("Preencha seus dados abaixo para encontrar a célula mais próxima.")

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

with st.form("form_busca"):
    st.markdown("### 1. Seus Dados")
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome")
    with col2:
        whatsapp = st.text_input("WhatsApp (com DDD)")
    
    endereco_usuario = st.text_input("Endereço ou Bairro", placeholder="Ex: Rua Henrique Felipe da Costa, Vila Guilherme")
    
    st.markdown("---")
    st.markdown("### 2. Suas Preferências")
    
    c_filtro1, c_filtro2, c_filtro3 = st.columns(3)
    
    with c_filtro1:
        st.markdown('<div class="filter-label">👥 Público</div>', unsafe_allow_html=True)
        filtro_tipo = st.multiselect("Selecione:", options=opcoes_tipo, default=opcoes_tipo, label_visibility="collapsed")
        
    with c_filtro2:
        st.markdown('<div class="filter-label">📅 Dias</div>', unsafe_allow_html=True)
        filtro_dia = st.multiselect("Selecione:", options=opcoes_dia, default=opcoes_dia, label_visibility="collapsed")
        
    with c_filtro3:
        st.markdown('<div class="filter-label">💻 Modo</div>', unsafe_allow_html=True)
        filtro_modo = st.multiselect("Selecione:", options=opcoes_modo, default=opcoes_modo, label_visibility="collapsed")
    
    st.markdown("<br>", unsafe_allow_html=True)
    buscar = st.form_submit_button("🚀 BUSCAR GRUPOS")

# --- LÓGICA DE BUSCA ---
if buscar:
    if not nome or not whatsapp or not endereco_usuario:
        st.warning("⚠️ Preencha nome, whatsapp e endereço.")
    elif df_geral.empty:
        st.error("Base de dados vazia.")
    else:
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
                lat_user, lon_user, endereco_bonito = obter_lat_lon_usuario(endereco_usuario)
                
                if lat_user:
                    # FEEDBACK MELHORADO (Azul)
                    st.info(
                        f"📍 **Localização de Referência:** {endereco_bonito}\n\n"
                        "Usamos este endereço para calcular a distância. "
                        "**Não é aqui?** Edite o campo de endereço acima e busque novamente."
                    )
                    
                    df_online = df_filtrado[df_filtrado['Modo'].astype(str).str.contains("Online", case=False, na=False)]
                    df_presencial = df_filtrado[~df_filtrado['Modo'].astype(str).str.contains("Online", case=False, na=False)]
                    
                    if not df_presencial.empty and not df_online.empty:
                        tab_presencial, tab_online = st.tabs(["📍 Perto de Você", "💻 Online"])
                        
                        with tab_presencial:
                            user_loc = (lat_user, lon_user)
                            df_presencial['distancia'] = df_presencial.apply(
                                lambda row: geodesic(user_loc, (row['lat'], row['lon'])).km, axis=1
                            )
                            df_sorted = df_presencial.sort_values(by='distancia')
                            
                            exibir_cartoes(df_sorted.head(3), nome, is_online=False)
                            
                            if len(df_sorted) > 3:
                                with st.expander(f"➕ Ver mais {len(df_sorted)-3} presenciais..."):
                                    exibir_cartoes(df_sorted.iloc[3:], nome, is_online=False)

                        with tab_online:
                            st.info("💡 Lifegroups Online não dependem de distância. Mostrando todos disponíveis:")
                            exibir_cartoes(df_online, nome, is_online=True)

                    elif not df_presencial.empty:
                        st.markdown("### 👇 Melhores Opções Perto de Você:")
                        user_loc = (lat_user, lon_user)
                        df_presencial['distancia'] = df_presencial.apply(
                            lambda row: geodesic(user_loc, (row['lat'], row['lon'])).km, axis=1
                        )
                        df_sorted = df_presencial.sort_values(by='distancia')
                        exibir_cartoes(df_sorted.head(3), nome, is_online=False)
                        if len(df_sorted) > 3:
                            with st.expander(f"➕ Ver mais {len(df_sorted)-3} opções..."):
                                exibir_cartoes(df_sorted.iloc[3:], nome, is_online=False)

                    elif not df_online.empty:
                        st.markdown("### 👇 Opções Online Disponíveis:")
                        exibir_cartoes(df_online, nome, is_online=True)
                        
                else:
                    st.error("Endereço não encontrado. Tente ser mais específico.")
