import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import re
import urllib.parse

# --- CONFIGURAÇÃO ---
# Nome exato do arquivo no seu GitHub
URL_CSV = "Cadastro dos Lifegroups.csv"

st.set_page_config(page_title="Encontre seu LifeGroup", page_icon="🎯", layout="wide")

# --- ESTILOS CSS (Para deixar o botão bonito) ---
st.markdown("""
<style>
    div.stButton > button:first-child {
        width: 100%;
        background-color: #25D366;
        color: white;
        border: none;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #128C7E;
        color: white;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
def extrair_zap(texto):
    """Limpa telefone para formato 5511..."""
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
        df.columns = df.columns.str.strip() # Remove espaços extras nos nomes das colunas
        
        # Remove linhas vazias (sem nome do life)
        df = df.dropna(subset=['Nome do Life'])
        
        geolocator = Nominatim(user_agent="app_life_prod_v1")
        latitudes = []
        longitudes = []
        
        # Geocoding (Converter endereço em GPS)
        for endereco in df['Endereço']:
            if not isinstance(endereco, str) or endereco.strip() == "":
                latitudes.append(None); longitudes.append(None)
                continue
            try:
                # Força busca no Brasil para evitar erros
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
    geolocator = Nominatim(user_agent="app_life_user_prod")
    try:
        # Tenta focar em SP primeiro
        query = f"{endereco}, São Paulo, Brasil"
        loc = geolocator.geocode(query)
        # Se não achar, tenta Brasil geral
        if not loc:
            loc = geolocator.geocode(f"{endereco}, Brasil")
            
        if loc:
            return loc.latitude, loc.longitude, loc.address
        return None, None, None
    except:
        return None, None, None

# --- INTERFACE PRINCIPAL ---
st.title("🎯 Encontre o LifeGroup ideal")
st.markdown("Preencha seus dados e use os **filtros na lateral** para encontrar o grupo que combina com você.")

with st.spinner("Carregando base de células..."):
    df_geral = carregar_dados()

# --- BARRA LATERAL (FILTROS) ---
with st.sidebar:
    st.header("🔍 Filtros de Busca")
    
    # Filtro 1: Tipo de Público
    if 'Tipo de Life' in df_geral.columns:
        opcoes_tipo = df_geral['Tipo de Life'].unique().tolist()
        filtro_tipo = st.multiselect("Público Alvo", opcoes_tipo, default=opcoes_tipo)
    else:
        filtro_tipo = []

    # Filtro 2: Dia da Semana
    if 'Dia da Semana' in df_geral.columns:
        opcoes_dia = df_geral['Dia da Semana'].unique().tolist()
        filtro_dia = st.multiselect("Dia da Semana", opcoes_dia, default=opcoes_dia)
    else:
        filtro_dia = []

    # Filtro 3: Modalidade
    if 'Modo' in df_geral.columns:
        opcoes_modo = df_geral['Modo'].unique().tolist()
        filtro_modo = st.multiselect("Modalidade", opcoes_modo, default=opcoes_modo)
    else:
        filtro_modo = []
        
    st.caption("Selecione as opções acima para filtrar os resultados.")

# --- APLICAÇÃO DOS FILTROS ---
if not df_geral.empty:
    df_filtrado = df_geral.copy()
    
    if filtro_tipo:
        df_filtrado = df_filtrado[df_filtrado['Tipo de Life'].isin(filtro_tipo)]
    if filtro_dia:
        df_filtrado = df_filtrado[df_filtrado['Dia da Semana'].isin(filtro_dia)]
    if filtro_modo:
        df_filtrado = df_filtrado[df_filtrado['Modo'].isin(filtro_modo)]
else:
    df_filtrado = df_geral

st.info(f"Mostrando **{len(df_filtrado)}** grupos disponíveis com os filtros atuais.")

# --- FORMULÁRIO ---
with st.form("form_busca"):
    col_a, col_b = st.columns(2)
    with col_a:
        nome = st.text_input("Seu Nome")
        whatsapp = st.text_input("Seu WhatsApp (com DDD)")
    with col_b:
        endereco_usuario = st.text_input("Seu Endereço (Rua/Bairro e Cidade)", placeholder="Ex: Centro, Guarulhos")
    
    buscar = st.form_submit_button("🚀 Buscar LifeGroups")

if buscar:
    if not nome or not whatsapp or not endereco_usuario:
        st.warning("⚠️ Preencha todos os campos para continuarmos.")
    elif df_filtrado.empty:
        st.warning("Nenhum LifeGroup encontrado com esses filtros. Tente marcar mais opções na barra lateral.")
    else:
        with st.spinner("Calculando distâncias..."):
            lat_user, lon_user, endereco_achado = obter_lat_lon_usuario(endereco_usuario)
            
            if lat_user:
                st.success(f"📍 Localizamos você em: **{endereco_achado}**")
                
                # Cálculo de Distância
                user_loc = (lat_user, lon_user)
                df_filtrado['distancia'] = df_filtrado.apply(
                    lambda row: geodesic(user_loc, (row['lat'], row['lon'])).km, axis=1
                )
                
                # Ordena e pega os 3 mais próximos
                top3 = df_filtrado.sort_values(by='distancia').head(3)
                
                st.markdown("---")
                for index, row in top3.iterrows():
                    with st.container():
                        c1, c2, c3 = st.columns([2, 1, 1])
                        
                        # Tratamento de dados para exibição
                        bairro = row['Bairro'] if 'Bairro' in row else "Região não informada"
                        modo = row['Modo'] if 'Modo' in row else "Presencial"
                        tipo = row['Tipo de Life'] if 'Tipo de Life' in row else "Geral"
                        lider = row['Líderes']
                        dia = row['Dia da Semana']
                        horario = row['Horário de Início']
                        
                        with c1:
                            st.subheader(f"🏠 {row['Nome do Life']}")
                            st.write(f"📍 **{bairro}**")
                            st.caption(f"Distância: {row['distancia']:.1f} km")
                            st.write(f"🏷️ **{tipo}** | 💻 **{modo}**")
                        
                        with c2:
                            st.write(f"📅 **{dia}**")
                            st.write(f"⏰ **{horario}**")
                            st.write(f"👤 Líder: {lider}")
                        
                        with c3:
                            tel_lider = extrair_zap(row['Telefone'])
                            
                            if tel_lider:
                                # Mensagem personalizada
                                msg = f"Olá {lider}, sou {nome}. Vi seu LifeGroup ({tipo}) no site e gostaria de visitar! Meu zap é {whatsapp}."
                                link_wa = f"https://wa.me/{tel_lider}?text={msg.replace(' ', '%20')}"
                                
                                # Botão Visual (Link HTML)
                                st.markdown(f"""
                                <a href="{link_wa}" target="_blank" style="text-decoration:none;">
                                    <div style="
                                        background-color:#25D366;
                                        color:white;
                                        padding:15px;
                                        border-radius:10px;
                                        text-align:center;
                                        font-weight:bold;
                                        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
                                        margin-top: 10px;
                                    ">
                                        💬 Chamar no Zap
                                    </div>
                                </a>
                                """, unsafe_allow_html=True)
                            else:
                                st.error("📞 Sem telefone")
                        st.divider()
            else:
                st.error("Endereço não encontrado. Tente incluir o Bairro ou Cidade (Ex: 'Vila Galvão, Guarulhos').")
