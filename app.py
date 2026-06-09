import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import io

# Configuração da página do Streamlit
st.set_page_config(page_title="IA de Unidades - Jumbo CDP", page_icon="🧠", layout="wide")

st.title("🧠 Máquina de Retenção de Alta Personalização")
st.markdown("O sistema calcula dinamicamente a mediana real de recompra para **todas as unidades prisionais** presentes no relatório.")

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
            # 🧹 FILTRO EXCLUSIVO: Apenas clientes com histórico real de envios (>= 1)
            col_enviados = 'Quant. Pedidos Enviados' if 'Quant. Pedidos Enviados' in df.columns else 'quant. pedidos enviados'
            if col_enviados in df.columns:
                df = df[df[col_enviados] >= 1]

            # Tratamento de datas e ordenação para pegar o histórico correto
            df['Data'] = pd.to_datetime(df['Data']).dt.tz_localize(None)
            df = df.sort_values(by=['Codigo Cliente', 'Data'])

            # --- 🛠️ MOTOR DE INTELIGÊNCIA ARTIFICIAL DINÂMICA ---
            # Passo 1: Calcular os intervalos reais de compra por cliente/unidade para descobrir as medianas
            df['Intervalo_Dias'] = df.groupby('Codigo Cliente')['Data'].diff().dt.days
            
            # Agrupa por unidade para achar a mediana de recompra real de CADA UMA das 197 unidades
            medianas_unidades = df.groupby('Unidade Prisional')['Intervalo_Dias'].median().dropna().to_dict()

            # Passo 2: Preparar a base atual para o cálculo de inatividade (Days_Since)
            today = pd.to_datetime(datetime.now().date())
            
            # Consolida o último pedido de cada cliente único
            df_ultimos_pedidos = df.sort_values('Data').groupby('Codigo Cliente').last().reset_index()
            df_ultimos_pedidos['Days_Since'] = (today - df_ultimos_pedidos['Data']).dt.days

            # Captura total de unidades únicas mapeadas para a barra lateral
            todas_unidades_relatorio = df_ultimos_pedidos['Unidade Prisional'].dropna().unique()
            st.sidebar.metric(label="🏢 Unidades Personalizadas", value=f"{len(todas_unidades_relatorio)} ativas")
            unidade_selecionada = st.sidebar.selectbox("🔍 Auditar Unidade específica:", ["Ver Todas"] + sorted(list(todas_unidades_relatorio)))

            # Listas para agrupar os disparos do dia
            lote_antecipacao, lote_mediana, lote_critico = [], [], []
            
            # Mapeamento estatístico das regras de gatilho para cada linha baseado na sua própria unidade
            for idx, row in df_ultimos_pedidos.iterrows():
                unidade = row['Unidade Prisional']
                dias_inativo = row['Days_Since']
                
                # Pega a mediana real calculada para essa unidade específica. 
                # Se for uma unidade nova sem histórico de intervalo, o fallback padrão seguro do negócio é 20 dias.
                mediana_real = int(medianas_unidades.get(unidade, 20))
                
                # Se a mediana for muito curta (ex: erro de dados), força um mínimo seguro de 9 dias
                if mediana_real < 8:
                    mediana_real = 9

                # 🎯 Definição matemática e hiperpersonalizada dos gatilhos por unidade
                gatilho_mediana = mediana_real
                gatilho_antecipacao = int(mediana_real * 0.6)     # Ex: Mediana 15 -> Antecipação no dia 9
                gatilho_critico = int(mediana_real * 1.5)         # Ex: Mediana 15 -> Crítico no dia 22

                # Aloca o cliente estritamente no dia correto de sua unidade
                if dias_inativo == gatilho_antecipacao:
                    lote_antecipacao.append(row)
                elif dias_inativo == gatilho_mediana:
                    lote_mediana.append(row)
                elif dias_inativo == gatilho_critico:
                    lote_critico.append(row)

            # Transforma em DataFrames para exibição visual
            df_ant = pd.DataFrame(lote_antecipacao) if lote_antecipacao else pd.DataFrame()
            df_med = pd.DataFrame(lote_mediana) if lote_mediana else pd.DataFrame()
            df_cri = pd.DataFrame(lote_critico) if lote_critico else pd.DataFrame()
            
            # Filtro interativo da Barra Lateral para Depuração Comercial
            if unidade_selecionada != "Ver Todas":
                df_ant = df_ant[df_ant['Unidade Prisional'] == unidade_selecionada] if not df_ant.empty else df_ant
                df_med = df_med[df_med['Unidade Prisional'] == unidade_selecionada] if not df_med.empty else df_med
                df_cri = df_cri[df_cri['Unidade Prisional'] == unidade_selecionada] if not df_cri.empty else df_cri

            # 📊 Painel de Controle de Métricas na Tela
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric(label="📅 Lote 1: Antecipação Personalizada", value=f"{len(df_ant)} clientes")
            col2.metric(label="🎯 Lote 2: Mediana de Precisão Real", value=f"{len(df_med)} clientes")
            col3.metric(label="🚨 Lote 3: Alerta Crítico Proporcional", value=f"{len(df_cri)} clientes")
            st.divider()
            
            # --- RENDERIZADOR DE TABELAS ---
            def exibir_lote(df_grupo, titulo, nome_arquivo):
                st.subheader(titulo)
                if not df_grupo.empty:
                    # Limpa colunas auxiliares de cálculo para não poluir o painel do usuário
                    colunas_exibicao = [c for c in df_grupo.columns if c not in ['Intervalo_Dias']]
                    st.dataframe(df_grupo[colunas_exibicao], use_container_width=True)
                    dados_excel = converter_para_excel(df_grupo[colunas_exibicao])
                    st.download_button(
                        label=f"📥 Baixar {titulo} (.xlsx)",
                        data=dados_excel,
                        file_name=f"{nome_arquivo}_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.info(f"Nenhum cliente atingiu a régua exata de {titulo} hoje.")
                st.divider()

            exibir_lote(df_ant, "1. Lote Antecipação", "lote_antecipacao_ia")
            exibir_lote(df_med, "2. Lote Mediana de Precisão", "lote_mediana_ia")
            exibir_lote(df_cri, "3. Lote Alerta Crítico", "lote_critico_ia")
            
            # --- 🚀 BOTÃO ÚNICO DE DISPARO INTELIGENTE ---
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
                    st.success("🎉 Todas as réguas hiperpersonalizadas foram processadas e enviadas ao n8n!")

    except Exception as e:
        st.error(f"Erro crítico no algoritmo de IA Dinâmica: {e}")
