import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import io

# Configuração da página do Streamlit
st.set_page_config(page_title="IA de Unidades - Jumbo CDP", page_icon="🧠", layout="wide")

st.title("🧠 Máquina de Retenção de Alta Personalização")
st.markdown("O sistema analisa dinamicamente todas as unidades do relatório e aplica réguas de comportamento customizadas.")

# 🌐 URLs dos Webhooks do seu n8n
WEBHOOK_ANTECIPACAO = "https://n8n.corcaqui.com.br/webhook/regua_antecipacao"
WEBHOOK_MEDIANA     = "https://n8n.corcaqui.com.br/webhook/regua_mediana_foco"
WEBHOOK_CRITICO     = "https://n8n.corcaqui.com.br/webhook/regua_alerta_critico"

# Função para converter DataFrame para Excel (Download)
def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Lote_Disparo')
    return output.getvalue()

# Componente de Upload de Arquivo
uploaded_file = st.file_uploader("Arraste e solte o relatório de vendas aqui (CSV ou Excel)", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        df = None
        
        # 1️⃣ TENTATIVA: Ler como arquivo Excel
        try:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file)
        except Exception:
            pass
            
        # 2️⃣ TENTATIVA: Ler como CSV tradicional
        if df is None or df.shape[1] <= 1:
            combinacoes = [
                (';', 'utf-8-sig'), (';', 'iso-8859-1'),
                (',', 'utf-8'), (';', 'utf-8'), (',', 'iso-8859-1')
            ]
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

            # 🛠️ AJUSTE CRÍTICO: Conversão de data forçando o padrão brasileiro (dia primeiro)
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True).dt.tz_localize(None)
            today = pd.to_datetime(datetime.now().date())
            df['Days_Since'] = (today - df['Data']).dt.days
            
            # Garante a retenção do último registro de cada cliente único
            df = df.sort_values(by='Data', ascending=False).drop_duplicates(subset=['Codigo Cliente'], keep='first')

            # --- 🧠 MOTOR DE INTELIGÊNCIA ARTIFICIAL DINÂMICA POR UNIDADE ---
            contagem_unidades = df['Unidade Prisional'].value_counts().to_dict()
            
            # Captura todas as unidades mapeadas para a barra lateral
            todas_unidades_relatorio = df['Unidade Prisional'].dropna().unique()
            st.sidebar.metric(label="🏢 Unidades no Relatório", value=f"{len(todas_unidades_relatorio)} mapeadas")
            unidade_selecionada = st.sidebar.selectbox("🔍 Auditar Unidade específica:", ["Ver Todas"] + sorted(list(todas_unidades_relatorio)))

            lote_antecipacao, lote_mediana, lote_critico = [], [], []
            
            # Processamento de linhas e aplicação das réguas de alta personalização
            for idx, row in df.iterrows():
                dias = row['Days_Since']
                unidade = str(row['Unidade Prisional']).strip()
                
                volume_unidade = contagem_unidades.get(unidade, 1)
                
                # CLASSIFICADOR DINÂMICO DE DIAS
                if volume_unidade >= 50:
                    gatilho_ant, gatilho_med, gatilho_cri = 5, 9, 15
                elif volume_unidade >= 20:
                    gatilho_ant, gatilho_med, gatilho_cri = 8, 13, 21
                elif volume_unidade >= 5:
                    gatilho_ant, gatilho_med, gatilho_cri = 12, 17, 25
                else:
                    gatilho_ant, gatilho_med, gatilho_cri = 18, 25, 35

                # Alocação milimétrica
                if dias == gatilho_ant:
                    lote_antecipacao.append(row)
                elif dias == gatilho_med:
                    lote_mediana.append(row)
                elif dias == gatilho_cri:
                    lote_critico.append(row)

            # Transforma em DataFrames estruturados
            df_ant = pd.DataFrame(lote_antecipacao).drop(columns=['Days_Since']) if lote_antecipacao else pd.DataFrame()
            df_med = pd.DataFrame(lote_mediana).drop(columns=['Days_Since']) if lote_mediana else pd.DataFrame()
            df_cri = pd.DataFrame(lote_critico).drop(columns=['Days_Since']) if lote_critico else pd.DataFrame()
            
            # Filtro interativo da barra lateral para auditoria comercial na tela
            if unidade_selecionada != "Ver Todas":
                df_ant = df_ant[df_ant['Unidade Prisional'] == unidade_selecionada] if not df_ant.empty else df_ant
                df_med = df_med[df_med['Unidade Prisional'] == unidade_selecionada] if not df_med.empty else df_med
                df_cri = df_cri[df_cri['Unidade Prisional'] == unidade_selecionada] if not df_cri.empty else df_cri

            # 📊 Painel de Controle de Métricas
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric(label="📅 Lote 1: Antecipação", value=f"{len(df_ant)} contatos")
            col2.metric(label="🎯 Lote 2: Mediana de Precisão", value=f"{len(df_med)} contatos")
            col3.metric(label="🚨 Lote 3: Alerta Crítico", value=f"{len(df_cri)} contatos")
            st.divider()
            
            def exibir_lote(df_grupo, titulo, nome_arquivo):
                st.subheader(titulo)
                if not df_grupo.empty:
                    # 🛠️ AJUSTE VISUAL: Substituído 'use_container_width' por 'width="stretch"'
                    st.dataframe(df_grupo, width="stretch")
                    dados_excel = converter_para_excel(df_grupo)
                    st.download_button(label=f"📥 Baixar {titulo} (.xlsx)", data=dados_excel, file_name=f"{nome_arquivo}_{datetime.now().strftime('%Y-%m-%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.info(f"Nenhum cliente elegível para o {titulo} hoje.")
                st.divider()

            exibir_lote(df_ant, "1. Lote Antecipação", "lote_antecipacao_ia")
            exibir_lote(df_med, "2. Lote Mediana de Precisão", "lote_mediana_ia")
            exibir_lote(df_cri, "3. Lote Alerta Crítico", "lote_critico_ia")
            
            # --- 🚀 BOTÃO ÚNICO DE DISPARO INTELIGENTE NO n8n ---
            st.subheader("🔥 Central de Disparo Automatizado")
            if st.button("Disparar Mensagens Inteligentes para o n8n", type="primary", width="stretch"):
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
                    st.success("🎉 Todas as réguas de alta personalização foram processadas e enviadas ao n8n!")

    except Exception as e:
        st.error(f"Erro crítico no processamento de IA: {e}")
