# --- 1. INSTALAÇÃO ---
!pip install --upgrade gspread google-auth pandas geopy -q

# --- 2. IMPORTAÇÕES ---
from google.colab import auth
from google.auth import default
import gspread
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import re
import urllib.parse # Para criar o link do Google Maps certinho

# --- 3. AUTENTICAÇÃO ---
print("🔐 Verificando permissões...")
try:
    auth.authenticate_user()
    creds, _ = default()
    gc = gspread.authorize(creds)
except:
    pass

# --- 4. CONFIGURAÇÃO ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1X0a6gD1RkVw-p1JqRxdZx3cQTS-slWRmp6KzNyuOKGY/edit"

# --- 5. LÓGICA ---
def extrair_zap(texto_celula):
    """Limpa e valida o telefone"""
    limpo = str(texto_celula).replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
    # Procura sequencia de 10 a 13 digitos
    encontrado = re.search(r'\d{10,13}', limpo)
    
    if encontrado:
        numero = encontrado.group()
        if not numero.startswith('55'):
            return '55' + numero
        return numero
    return None

def carregar_dados():
    print("⏳ Lendo planilha...")
    sh = gc.open_by_url(URL_PLANILHA)
    worksheet = sh.sheet1
    rows = worksheet.get_all_values()
    
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df.columns = df.columns.str.strip() 
    
    geolocator = Nominatim(user_agent="life_group_fix_bairro")
    latitudes = []
    longitudes = []
    
    print(f"🌍 Validando endereços...")
    
    for index, row in df.iterrows():
        endereco = row['Endereço']
        if not endereco or str(endereco).strip() == "":
            latitudes.append(None)
            longitudes.append(None)
            continue
        try:
            # Tenta buscar
            location = geolocator.geocode(f"{endereco}, Brasil", timeout=10)
            if location:
                latitudes.append(location.latitude)
                longitudes.append(location.longitude)
            else:
                latitudes.append(None)
                longitudes.append(None)
        except:
            latitudes.append(None)
            longitudes.append(None)
            
    df['lat'] = latitudes
    df['lon'] = longitudes
    return df.dropna(subset=['lat', 'lon'])

def buscar_melhores(endereco_usuario, df_celulas):
    geolocator = Nominatim(user_agent="life_group_user_fix")
    try:
        print(f"📍 Localizando você: '{endereco_usuario}'...")
        location = geolocator.geocode(f"{endereco_usuario}, Brasil")
        if not location: return None
        
        user_loc = (location.latitude, location.longitude)
        
        # Distância em Linha Reta (Filtro)
        df_celulas['distancia_km'] = df_celulas.apply(
            lambda row: geodesic(user_loc, (row['lat'], row['lon'])).km, axis=1
        )
        return df_celulas.sort_values(by='distancia_km').head(3)
    except:
        return None

# --- 6. EXECUÇÃO ---
df = carregar_dados()

if not df.empty:
    print("\n" + "="*40)
    print("🚀 SISTEMA PRONTO (AGORA VAI!)")
    print("="*40)
    
    # DADOS PARA TESTE
    nome = input("Seu Nome: ")
    whatsapp = input("Seu WhatsApp: ")
    endereco = input("Seu Endereço: ")
    
    resultados = buscar_melhores(endereco, df)
    
    if resultados is not None and not resultados.empty:
        print(f"\n🎉 Olá {nome}, aqui estão as opções:\n")
        
        for index, row in resultados.iterrows():
            print(f"🏠 {row['Nome do Life']} ({row.get('Tipo de Life', 'Geral')})")
            
            # --- CORREÇÃO AQUI: Removemos row['Bairro'] e usamos row['Endereço'] ---
            print(f"📍 {row['Endereço']}")
            print(f"📅 {row['Dia da Semana']} às {row['Horário de Início']}")
            print(f"👤 Líderes: {row['Líderes']}")
            print(f"📏 Distância Aprox (Linha Reta): {row['distancia_km']:.2f} km")
            
            # 1. LINK WHATSAPP
            zap_lider = extrair_zap(row['Telefone'])
            if zap_lider:
                msg = f"Olá {row['Líderes']}, sou {nome}. Quero visitar seu LifeGroup! Meu zap é {whatsapp}."
                link_wa = f"https://wa.me/{zap_lider}?text={msg.replace(' ', '%20')}"
                print(f"✅ LINK WHATSAPP: {link_wa}")
            else:
                print(f"⚠️ Sem telefone cadastrado.")
            
            # 2. LINK TRAJETO (GOOGLE MAPS)
            # Cria a URL do Google Maps com Origem e Destino
            origem_codificada = urllib.parse.quote(endereco)
            destino_codificado = urllib.parse.quote(f"{row['Endereço']}, Brasil")
            link_maps = f"https://www.google.com/maps/dir/?api=1&origin={origem_codificada}&destination={destino_codificado}&travelmode=driving"
            
            print(f"🗺️ LINK TRAJETO (CARRO): {link_maps}")
            
            print("-" * 30)
    else:
        print("❌ Endereço não encontrado.")
else:
    print("⚠️ Erro ao carregar dados.")
