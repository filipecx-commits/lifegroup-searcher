import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import re

# --- CONFIGURAÇÃO ---
# Link do CSV da sua planilha (Aquele público que você mandou)
URL_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTu9t9g0-lJTUulzKAXxRCjD4faGfgo79q3dgaECdQsM_1Q0riRt32mB14GXFdfxCaZ4HtJcwZ5dWlR/pub?gid=0&single=true&output=csv"

st.set_page_config(page_title="Encontre seu LifeGroup", page_icon="📍", layout="centered")

# --- FUNÇÕES ---
def limpar_telefone(texto):
    """Extrai o primeiro número válido de celular da célula"""
    # Remove tudo que não é dígito
    limpo = str(texto).replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
    # Procura sequencia de 10 a 13 digitos
    match = re.search(r'\d{10,13}', limpo)
    
    if match:
        numero = match.group()
        if not numero.startswith('55'):
            return '55' + numero
        return numero
    return None

@st.cache_data(ttl=600) # Recarrega os dados a cada 10 min
def carregar_dados():
    try:
        df = pd.read_csv(URL_CSV)
        
        # Limpa espaços nos nomes das colunas
        df.columns = df.columns.str.strip()
        
        geolocator = Nominatim(user_agent="app_lifegroup_prod_v1")
        latitudes = []
        longitudes = []
        
        # Cria as coordenadas
        for endereco in df['Endereço']:
            if not isinstance(endereco, str) or endereco.strip() == "":
                latitudes.append(None)
                longitudes.append(None)
                continue
            try:
                # Adiciona Brasil para precisão
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
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def obter_lat_lon_usuario(endereco):
    geolocator = Nominatim(user_agent="app_lifegroup_user_v1")
    try:
        loc = geolocator.geocode(f"{endereco}, Brasil")
        if loc:
            return loc.latitude, loc.longitude
        return None, None
    except:
        return None, None

# --- INTERFACE ---
st.title("📍 Encontre um LifeGroup")
st.markdown("Preencha seus dados abaixo para encontrar a célula mais próxima de você.")

with st.spinner("Atualizando base de células..."):
    df_celulas = carregar_dados()

with st.form("form_busca"):
    nome = st.text_input("Seu Nome")
    whatsapp = st.text_input("Seu WhatsApp (Ex: 11999990000)")
    endereco = st.text_input("Seu Endereço (Rua e Cidade)", placeholder="Ex: Rua Silva, Tatuapé")
    
    buscar = st.form_submit_button("🔍 Buscar Próximos")

if buscar:
    if not nome or not whatsapp or not endereco:
        st.warning("⚠️ Preencha todos os campos!")
    elif df_celulas.empty:
        st.error("Erro na base de dados. Avise a liderança.")
    else:
        with st.spinner("Calculando distâncias..."):
            lat_user, lon_user = obter_lat_lon_usuario(endereco)
            
            if lat_user:
                # Cálculo
                user_loc = (lat_user, lon_user)
                df_celulas['distancia'] = df_celulas.apply(
                    lambda row: geodesic(user_loc, (row['lat'], row['lon'])).km, axis=1
                )
                
                # Top 3
                top3 = df_celulas.sort_values(by='distancia').head(3)
                
                st.success(f"Olá {nome}, aqui estão as opções mais próximas:")
                
                for index, row in top3.iterrows():
                    with st.container():
                        st.markdown("---")
                        c1, c2 = st.columns([2,1])
                        
                        with c1:
                            st.subheader(f"🏠 {row['Nome do Life']}")
                            st.write(f"📍 **Endereço:** {row['Endereço']}")
                            st.write(f"📅 **Quando:** {row['Dia da Semana']} às {row['Horário de Início']}")
                            st.caption(f"Distância: {row['distancia']:.2f} km")
                        
                        with c2:
                            tel_lider = limpar_telefone(row['Telefone'])
                            if tel_lider:
                                msg = f"Olá {row['Líderes']}, sou {nome}. Encontrei seu LifeGroup no site e quero visitar! Meu zap é {whatsapp}."
                                link = f"https://wa.me/{tel_lider}?text={msg.replace(' ', '%20')}"
                                
                                st.markdown(f"""
                                <a href="{link}" target="_blank" style="text-decoration:none;">
                                    <div style="background-color:#25D366;color:white;padding:10px;border-radius:8px;text-align:center;font-weight:bold;">
                                        💬 Chamar Líder
                                    </div>
                                </a>
                                """, unsafe_allow_html=True)
                            else:
                                st.write("📞 Sem telefone cadastrado")
            else:
                st.error("Endereço não encontrado. Tente colocar Bairro e Cidade.")
