import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import io

# Configuração da página do Streamlit
st.set_page_config(page_title="IA de Unidades - Jumbo CDP", page_icon="🧠", layout="wide")

st.title("🧠 Máquina de Retenção por Comportamento de Unidade")
st.markdown("O sistema analisa a Unidade Prisional de cada cliente e calcula os dias exatos de disparo com base no ciclo real de recompra.")

# 🌐 URLs dos Webhooks do seu n8n
WEBHOOK_ANTECIPACAO = "https://n8n.corcaqui.com.br/webhook/regua_antecipacao"
WEBHOOK_MEDIANA     = "https://n8n.corcaqui.com.br/webhook/regua_mediana_foco"
WEBHOOK_CRITICO     = "https://n8n.corcaqui.com.br/webhook/regua_alerta_critico"

# 📊 PERFIS ESTRATÉGICOS MAPEADOS
PERFIL_ULTRA_RAPIDO = ['CDP Guarulhos 1', 'CDP Guarulhos 2']

PERFIL_QUINZENAL = [
    'CDP Pinheiros 3', 'CDP Hortolândia', 'CDP Diadema', 
    'CDP Mogi das Cruzes', 'CDP Franco da Rocha', 
    'CDP Caraguatatuba', 'CDP Taubaté'
]

PERFIL_TRADICIONAL = ['Penitenciária da Capital', 'CDP Pinheiros 1', 'CDP Vila Independência', 'Penitenciária Potim 2']

PERFIL_LONGO = [
    'Penitenciária Sorocaba 2', 'Penitenciária Guarulhos 1', 'Penitenciária José Parada Neto',
    'CDP São José do Rio Preto', 'CDP Mauá', 'CDP Belém 2', 'CDP Jundiaí', 
    'CDP Santo André', 'CDP Belém 1', 'Penitenciária Potim 1', 'CPP Butantan Feminino', 'CDP Sorocaba'
]

# Função para converter DataFrame para Excel (Download)
def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Lote_Disparo')
    return output.getvalue()

# Componente de Upload de Arquivo (Arrastar e Soltar)
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

        # Validação da Coluna de Data
        if df is None or 'Data' not in df.columns:
            st.error("❌ Não foi possível ler o arquivo. Garanta que a coluna 'Data' existe.")
        else:
            # 🧹 FILTRO SOLICITADO: Isolar apenas clientes com histórico real de envios (>= 1)
            if 'Quant. Pedidos Enviados' in df.columns:
                df = df[df['Quant. Pedidos Enviados'] >= 1]
            elif 'quant. pedidos enviados' in df.columns:
                df = df[df['quant. pedidos enviados'] >= 1]

            # Tratamento de datas e cálculo de inatividade
            df['Data'] = pd.to_datetime(df['Data']).dt.tz_localize(None)
            today = pd.to_datetime(datetime.now().date())
            df['Days_Since'] = (today - df['Data']).dt.days
            
            # Listas para agrupar os disparos do dia
            lote_antecipacao = []
            lote_mediana = []
            lote_critico = []
            
            # 🧠 MOTOR DE INTELIGÊNCIA DINÂMICO: Processa TODAS as unidades presentes no relatório
            for idx, row in df.iterrows():
                dias = row['Days_Since']
                unidade = str(row['Unidade Prisional']).strip()
                
                # Executa o roteamento de réguas baseado na Unidade Real detectada
                if unidade in PERFIL_ULTRA_RAPIDO:
                    if dias == 5: lote_antecipacao.append(row)
                    elif dias == 9: lote_mediana.append(row)
                    elif dias == 15: lote_critico.append(row)
                    
                elif unidade in PERFIL_QUINZENAL:
                    if dias == 8: lote_antecipacao.append(row)
                    elif dias == 13: lote_mediana.append(row)
                    elif dias == 21: lote_critico.append(row)
                    
                elif unidade in PERFIL_TRADICIONAL:
                    if dias == 12: lote_antecipacao.append(row)
                    elif dias == 17: lote_mediana.append(row)
                    elif dias == 25: lote_critico.append(row)
                    
                elif unidade in PERFIL_LONGO:
                    if dias == 18: lote_antecipacao.append(row)
                    elif dias == 25: lote_mediana.append(row)
                    elif dias == 35: lote_critico.append(row)
                    
                else:
                    # 🚀 INTEGRAÇÃO TOTAL: Qualquer outra unidade das 197 presentes entra aqui automaticamente
                    # Mapeamento do ciclo geral do negócio: Dia 14 (Antecipação), Dia 23 (Mediana), Dia 30 (Crítico)
                    if dias == 14: lote_antecipacao.append(row)
                    elif dias == 23: lote_mediana.append(row)
                    elif dias == 30: lote_critico.append(row)

            # Transforma as listas de registros de volta em DataFrames limpos
            df_ant = pd.DataFrame(lote_antecipacao).drop(columns=['Days_Since']) if lote_antecipacao else pd.DataFrame()
            df_med = pd.DataFrame(lote_mediana).drop(columns=['Days_Since']) if lote_mediana else pd.DataFrame()
            df_cri = pd.DataFrame(lote_critico).drop(columns=['Days_Since']) if lote_critico else pd.DataFrame()
            
            # 📊 Painel de Controle de Métricas na Tela
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric(label="📅 Lote 1: Antecipação", value=f"{len(df_ant)} clientes")
            col2.metric(label="🎯 Lote 2: Mediana de Precisão", value=f"{len(df_med)} clientes")
            col3.metric(label="🚨 Lote 3: Alerta Crítico", value=f"{len(df_cri)} clientes")
            st.divider()
            
            # --- FUNÇÃO PARA RENDERIZAR CADA GRUPO COM VISUALIZAÇÃO E DOWNLOAD ---
            def exibir_lote(df_grupo, titulo, nome_arquivo):
                st.subheader(titulo)
                if not df_grupo.empty:
                    st.dataframe(df_grupo, use_container_width=True)
                    dados_excel = converter_para_excel(df_grupo)
                    st.download_button(
                        label=f"📥 Baixar {titulo} (.xlsx)",
                        data=dados_excel,
                        file_name=f"{nome_arquivo}_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.info(f"Nenhum cliente elegível para o {titulo} hoje.")
                st.divider()

            # Mostra as seções organizadas
            exibir_lote(df_ant, "1. Lote Antecipação", "lote_antecipacao_ia")
            exibir_lote(df_med, "2. Lote Mediana de Precisão", "lote_mediana_ia")
            exibir_lote(df_cri, "3. Lote Alerta Crítico", "lote_critico_ia")
            
            # --- 🚀 BOTÃO ÚNICO DE DISPARO INTELIGENTE ---
            st.subheader("🔥 Central de Disparo Automatizado")
            if st.button("Disparar Mensagens Inteligentes para o n8n", type="primary", use_container_width=True):
                sucesso = True
                
                # Envio Antecipação
                if not df_ant.empty:
                    try:
                        res = requests.post(WEBHOOK_ANTECIPACAO, headers={"Content-Type": "application/json"}, data=json.dumps(df_ant.to_dict(orient='records'), default=str))
                        if res.status_code in [200, 201]: st.success(f"✅ {len(df_ant)} contatos enviados para o fluxo de Antecipação!")
                        else: st.error(f"❌ Erro na Antecipação. Status: {res.status_code}"); sucesso = False
                    except Exception as e: st.error(f"❌ Falha de conexão no Lote 1: {e}"); sucesso = False
                
                # Envio Mediana
                if not df_med.empty:
                    try:
                        res = requests.post(WEBHOOK_MEDIANA, headers={"Content-Type": "application/json"}, data=json.dumps(df_med.to_dict(orient='records'), default=str))
                        if res.status_code in [200, 201]: st.success(f"✅ {len(df_med)} contatos enviados para o fluxo de Mediana!")
                        else: st.error(f"❌ Erro na Mediana. Status: {res.status_code}"); sucesso = False
                    except Exception as e: st.error(f"❌ Falha de conexão no Lote 2: {e}"); sucesso = False
                
                # Envio Crítico
                if not df_cri.empty:
                    try:
                        res = requests.post(WEBHOOK_CRITICO, headers={"Content-Type": "application/json"}, data=json.dumps(df_cri.to_dict(orient='records'), default=str))
                        if res.status_code in [200, 201]: st.success(f"✅ {len(df_cri)} contatos enviados para o fluxo Crítico!")
                        else: st.error(f"❌ Erro no fluxo Crítico. Status: {res.status_code}"); sucesso = False
                    except Exception as e: st.error(f"❌ Falha de conexão no Lote 3: {e}"); sucesso = False
                
                if sucesso:
                    st.balloons()
                    st.success("🎉 Todas as réguas inteligentes foram enviadas e processadas pelo n8n!")

    except Exception as e:
        st.error(f"Erro crítico no processamento de IA: {e}")
