import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import re
import urllib.parse

# --- CONFIGURAÇÃO ---
# AQUI ESTÁ A MÁGICA: Peguei seu link de compartilhamento e mudei o final para /export?format=csv
# Isso força o Google a entregar os dados puros para o site.
URL_CSV = "https://docs.google.com/spreadsheets/d/1X0a6gD1RkVw-p1JqRxdZx3cQTS-slWRmp6KzNyuOKGY/export?format=csv"

st.set_page_config(page_title="Encontre seu LifeGroup", page_icon="📍", layout="centered")

# --- FUNÇÕES ---
def extrair_zap(texto_celula):
    """Limpa e valida o telefone para garantir que o link do WhatsApp funcione"""
    # Remove tudo que não é número
    limpo = str(texto_celula).replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
    # Procura sequencia de 10 a 13 digitos
    encontrado = re.search(r'\d{10,13}', limpo)
    
    if encontrado:
        numero = encontrado.group()
        # Se não tiver 55 (Brasil), adiciona
        if not numero.startswith('55'):
            return '55' + numero
        return numero
    return None

@st.cache_data(ttl=600) # Guarda os dados na memória por 10 min para o site ficar rápido
def carregar_dados():
    try:
        df = pd.read_csv(URL_CSV)
        df.columns = df.columns.str.strip() # Remove espaços dos nomes das colunas
        
        geolocator = Nominatim(user_agent="app_lifegroup_prod_final")
        latitudes = []
        longitudes = []
        
        # Converte endereços em GPS
        for endereco in df['Endereço']:
            if not isinstance(endereco, str) or endereco.strip() == "":
                latitudes.append(None)
                longitudes.append(None)
                continue
            try:
                # Adiciona Brasil para não cair em outro país
                loc = geolocator.geocode(f"{endereco}, Brasil", timeout=10)
                if loc:
                    latitudes.append(loc.latitude)
                    longitudes.append(loc.longitude)
                else:
                    latitudes.append(None)
                    longitudes.append(None)
            except:
                latitudes.append(None)
                longitudes.append(None)
        
        df['lat'] = latitudes
        df['lon'] = longitudes
        return df.dropna(subset=['lat', 'lon'])
    except Exception as e:
        st.error(f"Erro ao carregar dados. Verifique se a planilha está compartilhada como 'Qualquer pessoa com o link'. Detalhe: {e}")
        return pd.DataFrame()

def obter_lat_lon_usuario(endereco):
    geolocator = Nominatim(user_agent="app_lifegroup_user_final")
    try:
        loc = geolocator.geocode(f"{endereco}, Brasil")
        if loc:
            return loc.latitude, loc.longitude
        return None, None
    except:
        return None, None

# --- INTERFACE DO SITE ---
st.title("📍 Encontre um LifeGroup")
st.markdown("Preencha seus dados abaixo para encontrar a célula mais próxima de você.")

with st.spinner("Atualizando base de células..."):
    df_celulas = carregar_dados()

with st.form("form_busca"):
    nome = st.text_input("Seu Nome")
    whatsapp = st.text_input("Seu WhatsApp", placeholder="Ex: 11999990000")
    endereco_usuario = st.text_input("Seu Endereço (Rua e Cidade)", placeholder="Ex: Rua Silva, Tatuapé")
    
    buscar = st.form_submit_button("🔍 Buscar Próximos")

if buscar:
    if not nome or not whatsapp or not endereco_usuario:
        st.warning("⚠️ Por favor, preencha todos os campos!")
    elif df_celulas.empty:
        st.error("Erro na base de dados. Tente novamente mais tarde.")
    else:
        with st.spinner("Calculando distâncias..."):
            lat_user, lon_user = obter_lat_lon_usuario(endereco_usuario)
            
            if lat_user:
                # 1. Filtro Matemático (Linha Reta) para achar os mais pertos
                user_loc = (lat_user, lon_user)
                df_celulas['distancia'] = df_celulas.apply(
                    lambda row: geodesic(user_loc, (row['lat'], row['lon'])).km, axis=1
                )
                
                # Pega os 3 primeiros
                top3 = df_celulas.sort_values(by='distancia').head(3)
                
                st.success(f"Olá {nome}, aqui estão as opções mais próximas:")
                
                for index, row in top3.iterrows():
                    with st.container():
                        st.markdown("---")
                        c1, c2 = st.columns([2,1])
                        
                        with c1:
                            st.subheader(f"🏠 {row['Nome do Life']}")
                            st.write(f"📍 **Local:** {row['Endereço']}")
                            st.write(f"📅 **Quando:** {row['Dia da Semana']} às {row['Horário de Início']}")
                            st.caption(f"Distância aprox: {row['distancia']:.1f} km (linha reta)")
                            
                            # --- BOTÃO DE ROTA (Google Maps) ---
                            origem_enc = urllib.parse.quote(endereco_usuario)
                            destino_enc = urllib.parse.quote(f"{row['Endereço']}, Brasil")
                            link_maps = f"https://www.google.com/maps/dir/?api=1&origin={origem_enc}&destination={destino_enc}&travelmode=driving"
                            
                            st.markdown(f"🗺️ [**Ver trajeto no Mapa**]({link_maps})")
                        
                        with c2:
                            # --- BOTÃO DE WHATSAPP ---
                            tel_lider = extrair_zap(row['Telefone'])
                            if tel_lider:
                                msg = f"Olá {row['Líderes']}, sou {nome}. Vi seu LifeGroup no site e quero visitar! Meu zap é {whatsapp}."
                                link_wa = f"https://wa.me/{tel_lider}?text={msg.replace(' ', '%20')}"
                                
                                st.markdown(f"""
                                <a href="{link_wa}" target="_blank" style="text-decoration:none;">
                                    <div style="
                                        background-color:#25D366;
                                        color:white;
                                        padding:12px;
                                        border-radius:8px;
                                        text-align:center;
                                        font-weight:bold;
                                        margin-top: 10px;
                                        box-shadow: 0px 2px 5px rgba(0,0,0,0.2);
                                    ">
                                        💬 Chamar Líder
                                    </div>
                                </a>
                                """, unsafe_allow_html=True)
                            else:
                                st.write("📞 (Sem telefone cadastrado)")
            else:
                st.error("Endereço não encontrado. Tente colocar 'Rua X, Cidade Y'.")
