import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
import io

st.set_page_config(page_title="Retenção Preditiva - Jumbo CDP", page_icon="🧠", layout="wide")
st.title("🧠 Máquina de Retenção Preditiva — Jumbo CDP")
st.markdown(
    "Gatilhos calculados a partir da **mediana real de recompra** por unidade prisional — "
    "5 meses · 15.497 pedidos · **172 unidades mapeadas** · teto de 45 dias no crítico."
)

# ─── WEBHOOKS ────────────────────────────────────────────────────────────────
WEBHOOK_ANTECIPACAO = "https://n8n.corcaqui.com.br/webhook-test/regua_antecipacao"
WEBHOOK_MEDIANA     = "https://n8n.corcaqui.com.br/webhook/regua_mediana_foco"
WEBHOOK_CRITICO     = "https://n8n.corcaqui.com.br/webhook/regua_alerta_critico"

# ─── MAPEAMENTO NOVO PURIFICADO (APENAS PEDIDOS ENVIADOS / PAGOS) ────────────
MAPEAMENTO_UNIDADES = {
    'CDP Aguaí': (9, 15, 26),
    'CDP Americana': (12, 20, 34),
    'CDP Bauru': (10, 16, 27),
    'CDP Belém 1': (13, 22, 37),
    'CDP Belém 2': (14, 23, 39),
    'CDP Caiuá': (10, 17, 29),
    'CDP Campinas': (18, 30, 45),
    'CDP Caraguatatuba': (6, 10, 17),
    'CDP Diadema': (10, 16, 27),
    'CDP Franco da Rocha': (7, 12, 20),
    'CDP Guarulhos 1': (5, 8, 14),
    'CDP Guarulhos 2': (6, 10, 17),
    'CDP Hortolândia': (8, 14, 24),
    'CDP Icém': (38, 63, 68),
    'CDP Itapecerica da Serra': (17, 28, 45),
    'CDP Jundiaí': (13, 22, 37),
    'CDP Lavínia': (13, 22, 37),
    'CDP Mauá': (13, 22, 37),
    'CDP Mogi das Cruzes': (8, 14, 24),
    'CDP Nova Independência': (23, 38, 45),
    'CDP Osasco 1': (22, 36, 45),
    'CDP Osasco 2': (19, 32, 45),
    'CDP Pacaembu 1': (28, 47, 52),
    'CDP Pacaembu 2': (22, 37, 45),
    'CDP Paulo de Faria': (13, 22, 37),
    'CDP Pinheiros 1': (11, 19, 32),
    'CDP Pinheiros 2': (11, 18, 31),
    'CDP Pinheiros 3': (7, 12, 20),
    'CDP Pinheiros 4': (11, 18, 31),
    'CDP Piracicaba': (23, 38, 45),
    'CDP Pontal': (7, 12, 20),
    'CDP Praia Grande': (13, 22, 37),
    'CDP Ribeirão Preto': (10, 16, 27),
    'CDP Riolândia': (13, 22, 37),
    'CDP Santo André': (13, 22, 37),
    'CDP Sorocaba': (17, 29, 45),
    'CDP Suzano': (17, 28, 45),
    'CDP São Bernardo do Campo': (13, 21, 36),
    'CDP São José do Rio Preto': (13, 21, 36),
    'CDP São José dos Campos': (10, 17, 29),
    'CDP São Vicente': (8, 14, 24),
    'CDP Taubaté': (10, 16, 27),
    'CDP Tijuco Preto ': (13, 22, 37),
    'CDP Vila Independência': (10, 16, 27),
    'CPP Bauru 1': (14, 23, 39),
    'CPP Bauru 2': (13, 22, 37),
    'CPP Bauru 3': (13, 22, 37),
    'CPP Butantan Feminino': (19, 32, 45),
    'CPP Castelinho': (13, 22, 37),
    'CPP Franco da Rocha - Castelinho': (6, 10, 17),
    'CPP Guariba': (17, 28, 45),
    'CPP Hortolândia': (18, 30, 45),
    'CPP Jardinópolis': (11, 18, 31),
    'CPP Mongaguá': (12, 20, 34),
    'CPP Pacaembu': (9, 15, 26),
    'CPP Porto Feliz': (13, 22, 37),
    'CPP São Vicente': (19, 31, 45),
    'CPP Tremembé': (18, 30, 45),
    'CPP de Campinas -Professor Ataliba Nogueira': (51, 85, 90),
    'CR Atibaia': (16, 26, 44),
    'CR Birigui': (13, 21, 36),
    'CR Bragança Paulista': (28, 47, 52),
    'CR Itapetininga': (14, 24, 41),
    'CR Marília': (17, 28, 45),
    'CR Mococa': (51, 85, 90),
    'CR Ourinhos': (22, 36, 45),
    'CR Piracicaba Feminino': (16, 26, 44),
    'CR São José do Rio Preto Feminino': (19, 32, 45),
    'CR de Araraquara': (20, 34, 45),
    'Détenus Français - Itaí': (14, 24, 41),
    'Détenus Français - Sant\'Ana': (14, 24, 41),
    'Hospital Franco da Rocha 1': (18, 30, 45),
    'Hospital Franco da Rocha 2': (33, 55, 60),
    'Hospital de Custódia Taubaté': (16, 26, 44),
    'International Prisoners - Sant\'Ana - Women': (19, 32, 45),
    'José Parada Neto – Semiaberto (RSA)': (20, 33, 45),
    'P5 Hortolândia ': (19, 32, 45),
    'Penitenciaria Caiuá': (12, 20, 34),
    'Penitenciaria Itatinga': (28, 46, 51),
    'Penitenciaria Pontal': (13, 21, 36),
    'Penitenciária Adriano Marrey  ': (13, 22, 37),
    'Penitenciária Andradina': (10, 17, 29),
    'Penitenciária Araraquara': (8, 14, 24),
    'Penitenciária Assis': (25, 41, 45),
    'Penitenciária Avanhandava': (34, 56, 61),
    'Penitenciária Avaré 2': (24, 40, 45),
    'Penitenciária Balbinos 1': (12, 20, 34),
    'Penitenciária Balbinos 2': (25, 42, 45),
    'Penitenciária Bernardino de Campos': (37, 62, 67),
    'Penitenciária Capela do Alto 1': (20, 34, 45),
    'Penitenciária Capela do Alto 2': (22, 36, 45),
    'Penitenciária Casa Branca': (29, 48, 53),
    'Penitenciária Cerqueira César 1': (18, 30, 45),
    'Penitenciária Cerqueira César 2': (18, 30, 45),
    'Penitenciária Dracena': (22, 37, 45),
    'Penitenciária Florínea': (20, 33, 45),
    'Penitenciária Flórida Paulista': (20, 34, 45),
    'Penitenciária Franca': (19, 31, 45),
    'Penitenciária Franco da Rocha 1': (13, 21, 36),
    'Penitenciária Franco da Rocha 2': (23, 38, 45),
    'Penitenciária Franco da Rocha 3': (8, 13, 22),
    'Penitenciária Getulina': (58, 97, 102),
    'Penitenciária Guareí 1': (27, 45, 50),
    'Penitenciária Guareí 2': (31, 51, 56),
    'Penitenciária Guarulhos 1': (16, 27, 45),
    'Penitenciária Guarulhos 2': (8, 13, 22),
    'Penitenciária Gália 1': (17, 28, 45),
    'Penitenciária Gália 2': (33, 55, 60),
    'Penitenciária Hortolândia 1': (17, 29, 45),
    'Penitenciária Hortolândia 2': (20, 33, 45),
    'Penitenciária Hortolândia 3': (43, 72, 77),
    'Penitenciária Hortolândia 4': (22, 36, 45),
    'Penitenciária Iaras': (17, 28, 45),
    'Penitenciária Iperó': (19, 31, 45),
    'Penitenciária Irapuru': (18, 30, 45),
    'Penitenciária Itapetininga 1': (4, 7, 12),
    'Penitenciária Itapetininga 2': (25, 42, 45),
    'Penitenciária Itaí': (16, 27, 45),
    'Penitenciária Itirapina 2': (14, 23, 39),
    'Penitenciária José Parada Neto ': (17, 29, 45),
    'Penitenciária Junqueirópolis': (13, 21, 36),
    'Penitenciária Lavínia 1': (34, 56, 61),
    'Penitenciária Lavínia 2': (20, 33, 45),
    'Penitenciária Lavínia 3': (29, 49, 54),
    'Penitenciária Limeira': (14, 24, 41),
    'Penitenciária Lucélia': (22, 36, 45),
    'Penitenciária Mairinque': (17, 29, 45),
    'Penitenciária Marabá Paulista': (29, 49, 54),
    'Penitenciária Martinópolis': (65, 109, 114),
    'Penitenciária Marília': (21, 35, 45),
    'Penitenciária Mirandópolis 1': (25, 42, 45),
    'Penitenciária Mogi Guaçu Feminina': (17, 29, 45),
    'Penitenciária Pacaembu': (30, 50, 55),
    'Penitenciária Paraguaçu Paulista': (18, 30, 45),
    'Penitenciária Parelheiros': (18, 30, 45),
    'Penitenciária Piracicaba': (28, 46, 51),
    'Penitenciária Pirajuí 1': (25, 42, 45),
    'Penitenciária Pirajuí 2': (46, 77, 82),
    'Penitenciária Pirajuí Feminina': (19, 32, 45),
    'Penitenciária Potim 1': (16, 27, 45),
    'Penitenciária Potim 2': (16, 26, 44),
    'Penitenciária Pracinha': (17, 29, 45),
    'Penitenciária Presidente Bernardes': (10, 16, 27),
    'Penitenciária Presidente Prudente': (11, 18, 31),
    'Penitenciária Presidente Venceslau 1': (28, 47, 52),
    'Penitenciária Presidente Venceslau 2': (30, 50, 55),
    'Penitenciária Reginópolis 1': (22, 36, 45),
    'Penitenciária Reginópolis 2': (34, 57, 62),
    'Penitenciária Registro': (23, 39, 45),
    'Penitenciária Ribeirão Preto': (49, 82, 87),
    'Penitenciária Riolândia': (20, 33, 45),
    'Penitenciária Sant\'Ana Feminina': (21, 35, 45),
    'Penitenciária Serra Azul 1': (28, 47, 52),
    'Penitenciária Serra Azul 2': (23, 38, 45),
    'Penitenciária Serra Azul 3': (19, 32, 45),
    'Penitenciária Sorocaba 1': (19, 32, 45),
    'Penitenciária Sorocaba 2': (14, 24, 41),
    'Penitenciária São Vicente 1': (31, 51, 56),
    'Penitenciária São Vicente 2': (22, 36, 45),
    'Penitenciária Taiúva': (22, 36, 45),
    'Penitenciária Taquarituba': (16, 27, 45),
    'Penitenciária Tremembé 1': (13, 22, 37),
    'Penitenciária Tremembé 1 Feminina': (14, 24, 41),
    'Penitenciária Tremembé 2': (11, 18, 31),
    'Penitenciária Tremembé 2 Feminina': (9, 15, 26),
    'Penitenciária Tupi Paulista': (58, 96, 101),
    'Penitenciária Valparaíso': (13, 22, 37),
    'Penitenciária Votorantim Feminina': (12, 20, 34),
    'Penitenciária da Capital ': (10, 16, 27),
    'Penitenciária de Itirapina 1': (18, 30, 45),
    'Penitenciária Álvaro de Carvalho': (55, 91, 96),
    'Penitenciária Álvaro de Carvalho 2': (53, 88, 93),
}

# ─── FUNÇÕES AUXILIARES ───────────────────────────────────────────────────────
def converter_para_excel(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Lote_Disparo')
    return output.getvalue()


def obter_gatilhos(unidade: str):
    if unidade in MAPEAMENTO_UNIDADES:
        return MAPEAMENTO_UNIDADES[unidade], True

    u_lower = unidade.lower()
    for chave, gatilhos in MAPEAMENTO_UNIDADES.items():
        if chave.lower() in u_lower or u_lower in chave.lower():
            return gatilhos, True

    return (8, 23, 39), False  # Fallback baseado na nova mediana global de 23 dias


def enviar_webhook(url: str, dados: list, nome_lote: str):
    try:
        res = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(dados, default=str),
            timeout=15,
        )
        if res.status_code in [200, 201]:
            return True, f"✅ {len(dados)} contatos enviados para {nome_lote}!"
        return False, f"❌ Erro em {nome_lote} — HTTP {res.status_code}: {res.text[:200]}"
    except requests.exceptions.Timeout:
        return False, f"❌ Timeout em {nome_lote} — n8n demorou mais de 15s."
    except Exception as e:
        return False, f"❌ Falha de conexão em {nome_lote}: {e}"


def exibir_lote(df_grupo: pd.DataFrame, titulo: str, nome_arquivo: str):
    st.subheader(titulo)
    if not df_grupo.empty:
        st.dataframe(df_grupo, use_container_width=True)
        st.download_button(
            label=f"📥 Baixar {titulo} (.xlsx)",
            data=converter_para_excel(df_grupo),
            file_name=f"{nome_arquivo}_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info(f"Nenhum cliente elegível para {titulo} hoje.")
    st.divider()


def ler_arquivo(uploaded_file) -> pd.DataFrame | None:
    try:
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file)
        if df.shape[1] > 1:
            return df
    except Exception:
        pass

    for sep, enc in [
        (';', 'utf-8-sig'), (';', 'iso-8859-1'),
        (',', 'utf-8'), (';', 'utf-8'), (',', 'iso-8859-1'),
    ]:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=sep, encoding=enc, on_bad_lines='skip')
            if df.shape[1] > 1:
                return df
        except Exception:
            continue

    return None


# ─── UPLOAD ───────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Arraste o relatório de vendas aqui (CSV ou Excel)",
    type=["csv", "xlsx"],
)

if uploaded_file is None:
    st.stop()

try:
    df = ler_arquivo(uploaded_file)

    if df is None:
        st.error("❌ Não foi possível ler o arquivo. Verifique o formato e tente novamente.")
        st.stop()

    # ─── LIMPEZA ──────────────────────────────────────────────────────────────
    df.columns = df.columns.str.strip()

    if 'Data' not in df.columns:
        st.error("❌ Coluna 'Data' não encontrada. Verifique o arquivo.")
        st.stop()

    if 'Unidade Prisional' not in df.columns:
        st.error("❌ Coluna 'Unidade Prisional' não encontrada. Verifique o arquivo.")
        st.stop()

    # Filtra o relatório para conter apenas registros com status de faturamento real
    if 'Status' in df.columns:
        df['Status'] = df['Status'].astype(str).str.strip()
        df = df[df['Status'].str.lower().isin(['enviado', 'pagamento efetuado'])].copy()
    else:
        col_status_alt = next(
            (c for c in df.columns if 'status' in c.lower() or 'situação' in c.lower()), None
        )
        if col_status_alt:
            df[col_status_alt] = df[col_status_alt].astype(str).str.strip()
            df = df[df[col_status_alt].str.lower().isin(['enviado', 'pagamento efetuado'])].copy()

    col_env = next(
        (c for c in df.columns if c.lower().strip() == 'quant. pedidos enviados'), None
    )
    if col_env:
        df = df[df[col_env] >= 1].copy()

    # Normalização segura das datas
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True).dt.tz_localize(None).dt.normalize()
    today = pd.to_datetime(datetime.now().date()).normalize()
    df['Days_Since'] = (today - df['Data']).dt.days

    df['Unidade Prisional'] = df['Unidade Prisional'].astype(str).str.strip()

    df = (
        df.sort_values('Data', ascending=False)
        .drop_duplicates(subset=['Codigo Cliente'], keep='first')
    )
    
    # Preenche campos vazios/nulos antes de enviar para evitar erros de parser JSON no n8n (HTTP 422)
    df = df.fillna("")

    # ─── SIDEBAR ──────────────────────────────────────────────────────────────
    todas_unidades = sorted(df['Unidade Prisional'].dropna().unique())
    unidades_nao_mapeadas: set[str] = set()

    st.sidebar.metric("🏢 Unidades no relatório", len(todas_unidades))
    st.sidebar.metric("👥 Clientes únicos", f"{df['Codigo Cliente'].nunique():,}")
    unidade_selecionada = st.sidebar.selectbox(
        "🔍 Auditar unidade específica:",
        ["Ver Todas"] + todas_unidades,
    )

    # ─── MOTOR DE CLASSIFICAÇÃO (DIA EXATO COM LOGÍSTICA DE 3 DIAS ÚTEIS DE ENTREGA) ───
    lote_antecipacao, lote_mediana, lote_critico = [], [], []

    for _, row in df.iterrows():
        unidade = row['Unidade Prisional']
        (ant, med, cri), mapeado = obter_gatilhos(unidade)

        if not mapeado:
            unidades_nao_mapeadas.add(unidade)

        data_pedido = row['Data']
        dia_semana = data_pedido.dayofweek  # 0=Seg, 1=Ter, 2=Qua, 3=Qui, 4=Sex, 5=Sáb, 6=Dom
        
        # --- NOVO MOTOR LOGÍSTICO (3 DIAS ÚTEIS COM REAPROVEITAMENTO DE FINAL DE SEMANA) ---
        if dia_semana in [0, 1, 2]:  # Segunda, Terça ou Quarta -> Despacha no dia seguinte + 3 dias úteis
            dias_logistica = 4       # Ex: Compra na Seg (0) -> Sai na Ter -> Entrega na Sex (4 dias depois)
        elif dia_semana == 3:        # Quinta-feira -> Despacha na Sexta -> Entrega na Quarta da outra semana
            dias_logistica = 6
        elif dia_semana == 4:        # Sexta-feira -> Despacha na Segunda -> Entrega na Quinta da outra semana
            dias_logistica = 6
        elif dia_semana == 5:        # Sábado -> Despacha na Segunda -> Entrega na Quinta da outra semana
            dias_logistica = 5
        elif dia_semana == 6:        # Domingo -> Despacha na Segunda -> Entrega na Quinta da outra semana
            dias_logistica = 4
            
        data_entrega_real = data_pedido + pd.Timedelta(days=dias_logistica)
        # ───────────────────────────────────────────────────────────────────────────────────

        # Datas exatas calculadas de disparo
        data_antecipacao = (data_entrega_real + pd.Timedelta(days=ant)).normalize()
        data_mediana     = (data_entrega_real + pd.Timedelta(days=med)).normalize()
        data_critico     = (data_entrega_real + pd.Timedelta(days=cri)).normalize()

        # COMPARAÇÃO DIA EXATO
        if today == data_antecipacao:
            lote_antecipacao.append(row)

        elif today == data_mediana:
            lote_mediana.append(row)

        elif today == data_critico:
            lote_critico.append(row)

    if unidades_nao_mapeadas:
        st.sidebar.warning(
            f"⚠️ {len(unidades_nao_mapeadas)} unidade(s) sem mapeamento — "
            f"usando fallback (23 dias):\n\n" +
            "\n".join(f"• {u}" for u in sorted(unidades_nao_mapeadas))
        )

    # ─── MONTAR DATAFRAMES ────────────────────────────────────────────────────
    def para_df(lista):
        return (
            pd.DataFrame(lista).drop(columns=['Days_Since'], errors='ignore')
            if lista else pd.DataFrame()
        )

    df_ant = para_df(lote_antecipacao)
    df_med = para_df(lote_mediana)
    df_cri = para_df(lote_critico)

    if unidade_selecionada != "Ver Todas":
        filtro = lambda d: (
            d[d['Unidade Prisional'] == unidade_selecionada] if not d.empty else d
        )
        df_ant = filtro(df_ant)
        df_med = filtro(df_med)
        df_cri = filtro(df_cri)

    # ─── MÉTRICAS ─────────────────────────────────────────────────────────────
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Clientes processados", f"{len(df):,}")
    c2.metric("📅 Lote 1 — Antecipação", f"{len(df_ant)}")
    c3.metric("🎯 Lote 2 — Mediana", f"{len(df_med)}")
    c4.metric("🚨 Lote 3 — Crítico", f"{len(df_cri)}")
    st.divider()

    # ─── EXIBIÇÃO DOS LOTES ───────────────────────────────────────────────────
    exibir_lote(df_ant, "1. Lote Antecipação", "lote_antecipacao")
    exibir_lote(df_med, "2. Lote Mediana de Precisão", "lote_mediana")
    exibir_lote(df_cri, "3. Lote Alerta Crítico", "lote_critico")

    # ─── DISPARO PARA O n8n ───────────────────────────────────────────────────
    st.subheader("🔥 Central de Disparo Automatizado")

    total = len(df_ant) + len(df_med) + len(df_cri)

    if total == 0:
        st.info(
            "Nenhum cliente elegível para disparo hoje. "
            "Verifique se o relatório cobre o período correto."
        )
    else:
        st.info(f"**{total} contatos** prontos para disparo nos 3 fluxos do n8n.")

        if st.button("🚀 Disparar Mensagens para o n8n", type="primary", use_container_width=True):
            sucesso_geral = True
            disparos = [
                (df_ant, WEBHOOK_ANTECIPACAO, "Antecipação"),
                (df_med, WEBHOOK_MEDIANA, "Mediana"),
                (df_cri, WEBHOOK_CRITICO, "Crítico"),
            ]

            for df_lote, url, nome in disparos:
                if df_lote.empty:
                    continue
                ok, msg = enviar_webhook(url, df_lote.to_dict(orient='records'), nome)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
                    sucesso_geral = False

            if sucesso_geral:
                st.balloons()
                st.success("🎉 Todos os fluxos enviados com sucesso ao n8n!")

except Exception as e:
    st.error(f"Erro crítico no processamento: {e}")
    st.exception(e)
