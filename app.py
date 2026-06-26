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
    "5 meses · 15.497 pedidos · **149 unidades mapeadas** · teto de 45 dias no crítico."
)

# ─── WEBHOOKS ────────────────────────────────────────────────────────────────
WEBHOOK_ANTECIPACAO = "https://n8n.corcaqui.com.br/webhook-test/regua_antecipacao"
WEBHOOK_MEDIANA     = "https://n8n.corcaqui.com.br/webhook/regua_mediana_foco"
WEBHOOK_CRITICO     = "https://n8n.corcaqui.com.br/webhook/regua_alerta_critico"

# ─── MAPEAMENTO REAL ─────────────────────────────────────────────────────────
# Fonte: 15.497 pedidos jan–mai 2026 | Fórmula: ant=med×0.6 | cri=min(med×1.7, 45)
# Unidades com mediana < 7 dias (ruído) e > 45 dias (churn definitivo) são excluídas.
# Formato: 'Unidade': (antecipação, mediana, crítico)
MAPEAMENTO_UNIDADES = {
    'CPP Franco da Rocha - Castelinho': (4, 7, 12),
    'Détenus Français - Sant\'Ana': (4, 7, 12),
    'Penitenciária Itapetininga 1': (4, 7, 12),
    'Penitenciária São Vicente 1': (4, 7, 12),
    'Penitenciária Gália 2': (4, 7, 13),
    'CDP Bauru': (4, 7, 13),
    'CDP Pinheiros 2': (4, 7, 13),
    'Penitenciária Guareí 1': (4, 7, 13),
    'CDP Guarulhos 2': (5, 8, 14),
    'Penitenciária Adriano Marrey': (5, 8, 14),
    'CDP Caraguatatuba': (5, 8, 14),
    'CDP Guarulhos 1': (5, 8, 14),
    'CPP Guariba': (5, 8, 14),
    'CDP Diadema': (5, 8, 14),
    'Penitenciária Votorantim Feminina': (5, 8, 14),
    'CDP Sorocaba': (5, 8, 14),
    'CPP Pacaembu': (5, 8, 14),
    'Penitenciária Iaras': (5, 8, 14),
    'Penitenciária Avaré 2': (5, 9, 15),
    'CDP Praia Grande': (5, 9, 15),
    'Penitenciária Guareí 2': (5, 9, 15),
    'Penitenciária Assis': (5, 9, 15),
    'CPP Hortolândia': (5, 9, 15),
    'CDP Taubaté': (5, 9, 15),
    'CDP Mogi das Cruzes': (5, 9, 15),
    'Penitenciária Lavínia 3': (6, 10, 17),
    'Penitenciária Dracena': (6, 10, 17),
    'Penitenciária Guarulhos 2': (6, 10, 17),
    'Penitenciária Serra Azul 3': (6, 10, 17),
    'CPP Bauru 3': (6, 10, 17),
    'CDP Suzano': (6, 10, 17),
    'CDP Pinheiros 3': (6, 10, 17),
    'CDP Pacaembu 2': (6, 10, 17),
    'CDP Jundiaí': (6, 10, 18),
    'Penitenciária Piracicaba': (6, 10, 18),
    'Penitenciária Registro': (6, 10, 18),
    'CR Atibaia': (6, 10, 18),
    'CDP Pontal': (6, 10, 18),
    'CDP Osasco 1': (6, 10, 18),
    'CDP Hortolândia': (7, 11, 19),
    'Penitenciária Franco da Rocha 3': (7, 11, 19),
    'CDP Ribeirão Preto': (7, 11, 19),
    'CDP Icém': (7, 11, 19),
    'Penitenciária Osvaldo Cruz': (7, 11, 20),
    'CDP Aguaí': (7, 11, 20),
    'CPP Mongaguá': (7, 11, 20),
    'CPP Castelinho': (7, 11, 20),
    'CDP Caiuá': (7, 11, 20),
    'CDP Tijuco Preto': (7, 12, 20),
    'CPP Tremembé': (7, 12, 20),
    'Détenus Français Penit. Guarulhos II': (7, 12, 20),
    'Penitenciária Balbinos 1': (7, 12, 20),
    'CDP São José do Rio Preto': (7, 12, 20),
    'CDP Itapecerica da Serra': (7, 12, 20),
    'Penitenciária Sorocaba 2': (7, 12, 20),
    'Penitenciária Potim 1': (7, 12, 20),
    'Penitenciária Andradina': (8, 12, 21),
    'CDP Paulo de Faria': (8, 12, 21),
    'Penitenciária Florínea': (8, 12, 21),
    'Penitenciária Hortolândia 4': (8, 13, 22),
    'Penitenciária Araraquara': (8, 13, 22),
    'Penitenciária Martinópolis': (8, 13, 22),
    'Penitenciária Tremembé 2 Feminina': (8, 13, 22),
    'Penitenciária Casa Branca': (8, 13, 22),
    'P5 Hortolândia': (8, 13, 22),
    'Penitenciária Taquarituba': (8, 13, 22),
    'CDP Santo André': (8, 13, 23),
    'CDP Piracicaba': (8, 13, 23),
    'Penitenciária da Capital': (8, 13, 23),
    'Penitenciária Lavínia 1': (8, 14, 24),
    'Penitenciária Presidente Bernardes': (8, 14, 24),
    'Penitenciária Pracinha': (8, 14, 24),
    'CDP Belém 2': (8, 14, 24),
    'CDP Franco da Rocha': (8, 14, 24),
    'CDP Mauá': (8, 14, 24),
    'Penitenciaria Pontal': (8, 14, 24),
    'Penitenciária Bernardino de Campos': (8, 14, 24),
    'Penitenciária Potim 2': (9, 14, 25),
    'Penitenciária Guarulhos 1': (9, 14, 25),
    'CDP Pinheiros 4': (9, 14, 25),
    'Penitenciária Franco da Rocha 1': (9, 15, 26),
    'CDP Pinheiros 1': (9, 15, 26),
    'CDP Belém 1': (9, 15, 26),
    'CPP Jardinópolis': (9, 15, 26),
    'Penitenciária Hortolândia 2': (9, 15, 26),
    'Penitenciária Marabá Paulista': (9, 15, 26),
    'Penitenciária Tremembé 2': (9, 15, 26),
    'CPP Butantan Feminino': (9, 15, 26),
    'CR Jaú': (10, 16, 27),
    'CDP Riolândia': (10, 16, 27),
    'Penitenciária Cerqueira César 2': (10, 16, 27),
    'CR Marília': (10, 16, 27),
    'CPP São Vicente': (10, 16, 28),
    'CPP Porto Feliz': (10, 16, 28),
    'CR Itapetininga': (10, 16, 28),
    'Penitenciária Paraguaçu Paulista': (10, 16, 28),
    'Penitenciária Pirajuí 2': (10, 17, 29),
    'Penitenciária José Parada Neto': (10, 17, 29),
    'Penitenciária Taiúva': (10, 17, 30),
    'Penitenciária Tremembé 1 Feminina': (10, 17, 30),
    'Penitenciária Presidente Prudente': (11, 18, 31),
    'CPP Bauru 1': (11, 18, 31),
    'Penitenciária Capela do Alto 1': (11, 18, 31),
    'Détenus Français - Itaí': (11, 18, 31),
    'Penitenciária Reginópolis 1': (11, 18, 31),
    'CDP São Bernardo do Campo': (11, 19, 32),
    'CDP Lavínia': (11, 19, 32),
    'Penitenciaria Itatinga': (11, 19, 32),
    'Penitenciária Mogi Guaçu Feminina': (12, 20, 34),
    'Penitenciária Mairinque': (12, 20, 34),
    'CDP Osasco 2': (12, 20, 34),
    'Penitenciária Sant\'Ana Feminina': (12, 20, 34),
    'Penitenciária Tremembé 1': (12, 20, 34),
    'Penitenciária Tupi Paulista': (13, 21, 36),
    'Penitenciária Parelheiros': (13, 21, 37),
    'Penitenciária Serra Azul 2': (14, 22, 38),
    'CDP Nova Independência': (14, 23, 39),
    'Hospital de Custódia Taubaté': (14, 23, 39),
    'Penitenciária Gália 1': (14, 23, 39),
    'Penitenciária Itapetininga 2': (14, 23, 39),
    'Penitenciária Itirapina 2': (14, 23, 39),
    'Penitenciária Hortolândia 1': (14, 23, 40),
    'Penitenciária Cerqueira César 1': (15, 25, 43),
    'Penitenciária Irapuru': (16, 26, 44),
    'Penitenciária Riolândia': (16, 26, 45),
    'CR Birigui': (16, 27, 45),
    'Penitenciária Presidente Venceslau 1': (16, 27, 45),
    'Penitenciária Franca': (17, 28, 45),
    'Penitenciária Iperó': (17, 28, 45),
    'Penitenciária Pirajuí 1': (17, 28, 45),
    'Penitenciária São Vicente 2': (17, 29, 45),
    'CDP Campinas': (17, 29, 45),
    'Penitenciária Flórida Paulista': (17, 29, 45),
    'Penitenciária Lucélia': (18, 30, 45),
    'Penitenciária de Itirapina 1': (18, 30, 45),
    'Penitenciária Pirajuí Feminina': (18, 30, 45),
    'Penitenciária Itaí': (19, 31, 45),
    'CR Bragança Paulista': (19, 32, 45),
    'Penitenciária Avanhandava': (19, 32, 45),
    'Penitenciária Lavínia 2': (19, 32, 45),
    'Penitenciária Sorocaba 1': (19, 32, 45),
    'Penitenciária Álvaro de Carvalho 2': (20, 32, 45),
    'Penitenciaria Caiuá': (20, 32, 45),
    'CR de Araraquara': (20, 33, 45),
    'Penitenciária Marília': (20, 34, 45),
    'José Parada Neto – Semiaberto (RSA)': (20, 34, 45),
    'Penitenciária Hortolândia 3': (22, 36, 45),
    'CPP Bauru 2': (23, 38, 45),
}

# ─── FUNÇÕES AUXILIARES ───────────────────────────────────────────────────────
def converter_para_excel(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Lote_Disparo')
    return output.getvalue()


def obter_gatilhos(unidade: str):
    """
    Retorna ((ant, med, cri), mapeado).
    Tenta match exato → substring → fallback (mediana geral 14 dias).
    """
    if unidade in MAPEAMENTO_UNIDADES:
        return MAPEAMENTO_UNIDADES[unidade], True

    # Match por substring para variações de espaço/acento
    u_lower = unidade.lower()
    for chave, gatilhos in MAPEAMENTO_UNIDADES.items():
        if chave.lower() in u_lower or u_lower in chave.lower():
            return gatilhos, True

    # Fallback: mediana geral da operação = 14 dias → (8, 14, 24)
    return (8, 14, 24), False


def enviar_webhook(url: str, dados: list, nome_lote: str):
    """Envia para webhook com timeout e retorna (sucesso, mensagem)."""
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
    """Tenta ler Excel e múltiplos encodings de CSV. Retorna DataFrame ou None."""
    # Tentativa 1: Excel
    try:
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file)
        if df.shape[1] > 1:
            return df
    except Exception:
        pass

    # Tentativa 2: CSV com variações de separador e encoding
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

    # Filtro: apenas pedidos realmente enviados
    col_env = next(
        (c for c in df.columns if c.lower().strip() == 'quant. pedidos enviados'), None
    )
    if col_env:
        df = df[df[col_env] >= 1].copy()

    # Conversão de data (padrão brasileiro dd/mm/aaaa)
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True).dt.tz_localize(None)
    today = pd.to_datetime(datetime.now().date())
    df['Days_Since'] = (today - df['Data']).dt.days

    # Normalizar unidade e remover espaços extras
    df['Unidade Prisional'] = df['Unidade Prisional'].astype(str).str.strip()

    # Manter apenas o pedido mais recente por cliente único
    df = (
        df.sort_values('Data', ascending=False)
        .drop_duplicates(subset=['Codigo Cliente'], keep='first')
    )

    # ─── SIDEBAR ──────────────────────────────────────────────────────────────
    todas_unidades = sorted(df['Unidade Prisional'].dropna().unique())
    unidades_nao_mapeadas: set[str] = set()

    st.sidebar.metric("🏢 Unidades no relatório", len(todas_unidades))
    st.sidebar.metric("👥 Clientes únicos", f"{df['Codigo Cliente'].nunique():,}")
    unidade_selecionada = st.sidebar.selectbox(
        "🔍 Auditar unidade específica:",
        ["Ver Todas"] + todas_unidades,
    )

    # ─── MOTOR DE CLASSIFICAÇÃO ───────────────────────────────────────────────
    lote_antecipacao, lote_mediana, lote_critico = [], [], []

    for _, row in df.iterrows():
        dias = row['Days_Since']
        unidade = row['Unidade Prisional']
        (ant, med, cri), mapeado = obter_gatilhos(unidade)

        if not mapeado:
            unidades_nao_mapeadas.add(unidade)

        # Cliente entra somente no dia exato do gatilho
        # Cada cliente participa de no máximo 1 lote
        if dias == ant:
            lote_antecipacao.append(row)

        elif dias == med:
            lote_mediana.append(row)

        elif dias == cri:
            lote_critico.append(row)

    # Alertar unidades usando fallback
    if unidades_nao_mapeadas:
        st.sidebar.warning(
            f"⚠️ {len(unidades_nao_mapeadas)} unidade(s) sem mapeamento — "
            f"usando fallback (14 dias):\n\n" +
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

    # Filtro de auditoria por unidade (sidebar)
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
    c1.metric("📋 Clientes processed", f"{len(df):,}")
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
