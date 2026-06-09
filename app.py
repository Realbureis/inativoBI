import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import io

# Configuração da página do Streamlit
st.set_page_config(page_title="IA de Unidades - Jumbo CDP", page_icon="🧠", layout="wide")

st.title("🧠 Máquina de Retenção de Alta Personalização")
st.markdown("O sistema analisa a Unidade Prisional de cada cliente e aplica réguas de disparo milimétricas e personalizadas.")

# 🌐 URLs dos Webhooks do seu n8n
WEBHOOK_ANTECIPACAO = "https://n8n.corcaqui.com.br/webhook/regua_antecipacao"
WEBHOOK_MEDIANA     = "https://n8n.corcaqui.com.br/webhook/regua_mediana_foco"
WEBHOOK_CRITICO     = "https://n8n.corcaqui.com.br/webhook/regua_alerta_critico"

# 📊 MATRIZ INTELIGENTE DE RECOMPRA (Mapeamento de Perfis para todas as unidades do ecossistema)
CONFIG_PERFIS = {
    "ULTRA_RAPIDO": {"antecipacao": 5, "mediana": 9, "critico": 15},
    "QUINZENAL":    {"antecipacao": 8, "mediana": 13, "critico": 21},
    "TRADICIONAL":  {"antecipacao": 12, "mediana": 17, "critico": 25},
    "LONGO_MENSAL": {"antecipacao": 18, "mediana": 25, "critico": 35},
    "PADRAO_GERAL": {"antecipacao": 14, "mediana": 23, "critico": 30}
}

# Dicionário de Rotulagem: Vincula cada unidade encontrada no seu relatório ao seu perfil de velocidade real
MAPEAMENTO_UNIDADES = {
    # --- Perfil Ultra Rápido (Mediana 9 dias) ---
    'CDP Guarulhos 1': "ULTRA_RAPIDO", 'CDP Guarulhos 2': "ULTRA_RAPIDO",
    
    # --- Perfil Quinzenal Rápido (Mediana 13 dias) ---
    'CDP Pinheiros 3': "QUINZENAL", 'CDP Hortolândia': "QUINZENAL", 'CDP Diadema': "QUINZENAL", 
    'CDP Mogi das Cruzes': "QUINZENAL", 'CDP Franco da Rocha': "QUINZENAL", 'CDP Caraguatatuba': "QUINZENAL", 
    'CDP Taubaté': "QUINZENAL", 'CDP Suzano': "QUINZENAL", 'P5 Hortolândia ': "QUINZENAL", 'CDP Americana': "QUINZENAL",
    
    # --- Perfil Tradicional (Mediana 17 dias) ---
    'Penitenciária da Capital': "TRADICIONAL", 'CDP Pinheiros 1': "TRADICIONAL", 
    'CDP Vila Independência': "TRADICIONAL", 'Penitenciária Potim 2': "TRADICIONAL",
    'Penitenciária Pracinha': "TRADICIONAL", 'Penitenciária Gália 2': "TRADICIONAL",
    'CDP São Bernardo do Campo': "TRADICIONAL", 'Penitenciária Assis': "TRADICIONAL",
    
    # --- Perfil Longo / Mensal (Mediana 25 dias) ---
    'Penitenciária Sorocaba 2': "LONGO_MENSAL", 'Penitenciária Guarulhos 1': "LONGO_MENSAL", 
    'Penitenciária José Parada Neto': "LONGO_MENSAL", 'CDP São José do Rio Preto': "LONGO_MENSAL", 
    'CDP Mauá': "LONGO_MENSAL", 'CDP Belém 2': "LONGO_MENSAL", 'CDP Jundiaí': "LONGO_MENSAL", 
    'CDP Santo André': "LONGO_MENSAL", 'CDP Belém 1': "LONGO_MENSAL", 'Penitenciária Potim 1': "LONGO_MENSAL", 
    'CPP Butantan Feminino': "LONGO_MENSAL", 'CDP Sorocaba': "LONGO_MENSAL", 'Penitenciária Iaras': "LONGO_MENSAL",
    'Penitenciária Reginópolis 1': "LONGO_MENSAL", 'Penitenciária Araraquara': "LONGO_MENSAL",
    'Penitenciária Ribeirão Preto Feminina': "LONGO_MENSAL", 'CPP Bauru 3': "LONGO_MENSAL",
    'Penitenciária Avanhandava': "LONGO_MENSAL", 'Penitenciária Registro': "LONGO_MENSAL",
    'José Parada Neto – Semiaberto (RSA)': "LONGO_MENSAL", 'CDP Lavínia': "LONGO_MENSAL",
    'Penitenciária Serra Azul 2': "LONGO_MENSAL", 'Penitenciária Lucélia': "LONGO_MENSAL",
    'Penitenciária Franca': "LONGO_MENSAL", 'Penitenciária Irapuru': "LONGO_MENSAL",
    'Penitenciária Itaí': "LONGO_MENSAL", 'CDP Paulo de Faria': "LONGO_MENSAL",
    'Penitenciária Guareí 2': "LONGO_MENSAL", 'Penitenciária Itapetininga 1': "LONGO_MENSAL",
    'Penitenciaria Itatinga': "LONGO_MENSAL", 'Penitenciária Tremembé 2 Feminina': "LONGO_MENSAL"
}

def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Lote_Disparo')
    return output.getvalue()

uploaded_file = st.file_uploader("Arraste e solte o relatório de vendas aqui (CSV ou Excel)", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        df = None
        try:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file)
        except Exception:
            pass
            
        if df is None or df.shape[1] <= 1:
            combinacoes = [(';', 'utf-8-sig'), (';', 'iso-8859-1'), (',', 'utf-8'), (';', 'utf-8'), (',', 'iso-8859-1')]
            for sep, enc in combinacoes:
                try:
                    uploaded_file.seek(0)
                    temp_df = pd.read_csv(uploaded_file, sep=sep, encoding=enc, on_bad_lines='skip')
                    if temp_df.shape[1] > 1:
                        df = temp_df
                        break
                except Exception:
                    continue

        if df is None or 'Data' not in df.columns:
            st.error("❌ Não foi possível ler o arquivo. Garanta que a coluna 'Data' existe.")
        else:
            # 🧹 FILTRO OBRIGATÓRIO: Apenas quem já comprou de verdade (>= 1 pedido enviado)
            col_enviados = 'Quant. Pedidos Enviados' if 'Quant. Pedidos Enviados' in df.columns else 'quant. pedidos enviados'
            if col_enviados in df.columns:
                df = df[df[col_enviados] >= 1]

            # Tratamento de datas e cálculo de dias desde o último pedido (Days_Since)
            df['Data'] = pd.to_datetime(df['Data']).dt.tz_localize(None)
            today = pd.to_datetime(datetime.now().date())
            df['Days_Since'] = (today - df['Data']).dt.days
            
            # Garante que pegamos apenas a última atividade real do cliente único
            df = df.sort_values(by='Data', ascending=False).drop_duplicates(subset=['Codigo Cliente'], keep='first')

            # Captura todas as unidades mapeadas para controle visual da barra lateral
            todas_unidades_relatorio = df['Unidade Prisional'].dropna().unique()
            st.sidebar.metric(label="🏢 Unidades no Relatório", value=f"{len(todas_unidades_relatorio)} mapeadas")
            unidade_selecionada = st.sidebar.selectbox("🔍 Auditar Unidade específica:", ["Ver Todas"] + sorted(list(todas_unidades_relatorio)))

            lote_antecipacao, lote_mediana, lote_critico = [], [], []
            
            # 🧠 MOTOR DE DIRECIONAMENTO MILIMÉTRICO
            for idx, row in df.iterrows():
                dias = row['Days_Since']
                unidade = str(row['Unidade Prisional']).strip()
                
                # Identifica o perfil da unidade. Se for uma nova unidade das 197, assume o PADRAO_GERAL hiperpersonalizável
                perfil_nome = MAPEAMENTO_UNIDADES.get(unidade, "PADRAO_GERAL")
                config = CONFIG_PERFIS[perfil_nome]
                
                # Alocação precisa nos lotes do dia
                if dias == config['antecipacao']:
                    lote_antecipacao.append(row)
                elif dias == config['mediana']:
                    lote_mediana.append(row)
                elif dias == config['critico']:
                    lote_critico.append(row)

            # Transforma em DataFrames limpos
            df_ant = pd.DataFrame(lote_antecipacao).drop(columns=['Days_Since']) if lote_antecipacao else pd.DataFrame()
            df_med = pd.DataFrame(lote_mediana).drop(columns=['Days_Since']) if lote_mediana else pd.DataFrame()
            df_cri = pd.DataFrame(lote_critico).drop(columns=['Days_Since']) if lote_critico else pd.DataFrame()
            
            # Filtro da barra lateral para depuração comercial
            if unidade_selecionada != "Ver Todas":
                df_ant = df_ant[df_ant['Unidade Prisional'] == unidade_selecionada] if not df_ant.empty else df_ant
                df_med = df_med[df_med['Unidade Prisional'] == unidade_selecionada] if not df_med.empty else df_med
                df_cri = df_cri[df_cri['Unidade Prisional'] == unidade_selecionada] if not df_cri.empty else df_cri

            # 📊 Exibição das Métricas
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric(label="📅 Lote 1: Antecipação", value=f"{len(df_ant)} contatos")
            col2.metric(label="🎯 Lote 2: Mediana de Precisão", value=f"{len(df_med)} contatos")
            col3.metric(label="🚨 Lote 3: Alerta Crítico", value=f"{len(df_cri)} contatos")
            st.divider()
            
            def exibir_lote(df_grupo, titulo, nome_arquivo):
                st.subheader(titulo)
                if not df_grupo.empty:
                    st.dataframe(df_grupo, use_container_width=True)
                    dados_excel = converter_para_excel(df_grupo)
                    st.download_button(label=f"📥 Baixar {titulo} (.xlsx)", data=dados_excel, file_name=f"{nome_arquivo}_{datetime.now().strftime('%Y-%m-%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.info(f"Nenhum cliente elegível para o {titulo} hoje.")
                st.divider()

            exibir_lote(df_ant, "1. Lote Antecipação", "lote_antecipacao_ia")
            exibir_lote(df_med, "2. Lote Mediana de Precisão", "lote_mediana_ia")
            exibir_lote(df_cri, "3. Lote Alerta Crítico", "lote_critico_ia")
            
            # --- 🚀 BOTÃO DE DISPARO AUTOMATIZADO ---
            st.subheader("🔥 Central de Disparo Automatizado")
            if st.button("Disparar Mensagens Inteligentes para o n8n", type="primary", use_container_width=True):
                sucesso = True
                
                if not df_ant.empty:
                    try:
                        res = requests.post(WEBHOOK_ANTECIPACAO, headers={"Content-Type": "application/json"}, data=json.dumps(df_ant.to_dict(orient='records'), default=str))
                        if res.status_code in [200, 201]: st.success(f"✅ {len(df_ant)} contatos enviados para Antecipação!")
                        else: sucesso = False
                    except Exception: sucesso = False
                
                if not df_med.empty:
                    try:
                        res = requests.post(WEBHOOK_MEDIANA, headers={"Content-Type": "application/json"}, data=json.dumps(df_med.to_dict(orient='records'), default=str))
                        if res.status_code in [200, 201]: st.success(f"✅ {len(df_med)} contatos enviados para Mediana!")
                        else: sucesso = False
                    except Exception: sucesso = False
                
                if not df_cri.empty:
                    try:
                        res = requests.post(WEBHOOK_CRITICO, headers={"Content-Type": "application/json"}, data=json.dumps(df_cri.to_dict(orient='records'), default=str))
                        if res.status_code in [200, 201]: st.success(f"✅ {len(df_cri)} contatos enviados para o fluxo Crítico!")
                        else: sucesso = False
                    except Exception: sucesso = False
                
                if sucesso and (not df_ant.empty or not df_med.empty or not df_cri.empty):
                    st.balloons()
                    st.success("🎉 Todas as réguas inteligentes foram enviadas e processadas pelo n8n!")

    except Exception as e:
        st.error(f"Erro crítico no processamento de IA: {e}")
