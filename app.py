import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

CPF_AUTORIZADO = "00000000000"
MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
         "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

# ==========================================
# BANCO DE DADOS
# ==========================================
def conectar_db():
    conn = sqlite3.connect('prefeitura_metas.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (cpf TEXT PRIMARY KEY, nome TEXT, senha TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS secretarias (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, mes TEXT, secretaria_id INTEGER, FOREIGN KEY(secretaria_id) REFERENCES secretarias(id))')
    c.execute('CREATE TABLE IF NOT EXISTS acoes (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT, responsavel TEXT, prazo TEXT, status TEXT, meta_id INTEGER, FOREIGN KEY(meta_id) REFERENCES metas(id))')
    conn.commit()
    return conn

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Metas — Prefeitura de Viçosa",
    layout="wide",
    page_icon="🏛️",
    initial_sidebar_state="collapsed"
)

# ==========================================
# SESSION STATE
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# ==========================================
# CSS GLOBAL
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }

/* ── FUNDO (painel) ──────────────────────── */
.stApp { background-color: #f1f5f9; }

/* ── CARD DE LOGIN (via st.form) ─────────── */
[data-testid="stForm"] {
    background: #ffffff !important;
    border-radius: 24px !important;
    padding: 2.5rem 2rem 2rem !important;
    box-shadow: 0 20px 60px rgba(0,0,0,0.28) !important;
    border: none !important;
}

/* ── KPI CARDS ───────────────────────────── */
.kpi-card {
    background: #ffffff; border-radius: 14px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
    border-left: 5px solid; margin-bottom: 0.5rem;
}
.kpi-value { font-size: 2.2rem; font-weight: 700; line-height: 1.1; }
.kpi-label { font-size: 0.75rem; font-weight: 600; color: #64748b;
             text-transform: uppercase; letter-spacing: 0.6px; margin-top: 4px; }

.kpi-total { border-color: #0f2a5e; } .kpi-total .kpi-value { color: #0f2a5e; }
.kpi-pend  { border-color: #f97316; } .kpi-pend  .kpi-value { color: #f97316; }
.kpi-and   { border-color: #3b82f6; } .kpi-and   .kpi-value { color: #3b82f6; }
.kpi-conc  { border-color: #22c55e; } .kpi-conc  .kpi-value { color: #22c55e; }

/* ── SEÇÃO TÍTULO ────────────────────────── */
.section-title {
    font-size: 1rem; font-weight: 700; color: #0f2a5e;
    margin: 1rem 0 0.75rem 0; padding-bottom: 0.5rem;
    border-bottom: 2px solid #e2e8f0;
}

/* ── SIDEBAR ─────────────────────────────── */
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(160deg, #0f2a5e 0%, #1a4a8a 60%, #1d6b52 100%);
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] .stMarkdown { color: rgba(255,255,255,0.9) !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #ffffff !important; }

/* ── BOTÕES ──────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #0f2a5e, #1d6b52);
    color: #fff; border: none; border-radius: 8px;
    padding: 0.5rem 1.4rem; font-weight: 600; width: 100%;
    transition: box-shadow 0.2s, transform 0.15s;
}
.stButton > button:hover {
    box-shadow: 0 4px 14px rgba(0,0,0,0.22); transform: translateY(-1px);
}

/* ── ABAS ────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px; background: #ffffff;
    padding: 0.4rem 0.6rem; border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 1rem;
}
.stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 0.45rem 1.4rem; font-weight: 500; }
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #0f2a5e, #1d6b52) !important; color: #fff !important;
}

/* ── EXPANDER ────────────────────────────── */
details summary {
    background: #ffffff; border-radius: 10px !important;
    font-weight: 600 !important; padding: 0.8rem 1rem !important;
    box-shadow: 0 1px 6px rgba(0,0,0,0.07);
}

/* ── INPUTS ──────────────────────────────── */
.stTextInput input, .stDateInput input {
    border-radius: 8px !important; border: 1px solid #cbd5e1 !important;
    color: #1e293b !important; background: #fff !important;
}
</style>
""", unsafe_allow_html=True)

banco = conectar_db()

# ==========================================
# TELA DE LOGIN
# ==========================================
if not st.session_state.autenticado:
    # Fundo gradiente + oculta sidebar
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f2a5e 0%, #1a4a8a 55%, #1d6b52 100%) !important;
    }
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stDecoration"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

    _, card_col, _ = st.columns([1, 1.05, 1])
    with card_col:
        st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)

        with st.form("login_form"):
            # Logo centralizada e menor
            lc1, lc2, lc3 = st.columns([1, 2, 1])
            with lc2:
                try:
                    st.image("logo_vicosa.jpg", use_container_width=True)
                except Exception:
                    st.markdown("<div style='text-align:center;font-size:3rem'>🏛️</div>",
                                unsafe_allow_html=True)

            # Título e subtítulo
            st.markdown("""
            <div style='text-align:center; margin:0.6rem 0 1.4rem 0;'>
                <h2 style='color:#0f2a5e;font-size:1.35rem;font-weight:700;margin:0 0 6px 0;'>
                    Prefeitura de Viçosa
                </h2>
                <p style='color:#64748b;font-size:0.82rem;margin:0;'>
                    Sistema de Acompanhamento de Metas Municipais
                </p>
            </div>
            <hr style='border:none;border-top:1px solid #e2e8f0;margin:0 0 1.4rem 0;'>
            """, unsafe_allow_html=True)

            # Campo CPF
            cpf = st.text_input(
                "CPF (somente números)",
                max_chars=11,
                placeholder="00000000000"
            )

            # Botão
            entrar = st.form_submit_button("Entrar →", use_container_width=True)

            if entrar:
                if cpf == CPF_AUTORIZADO:
                    st.session_state.autenticado = True
                    st.rerun()
                elif cpf == "":
                    st.warning("Digite seu CPF para continuar.")
                else:
                    st.error("❌ CPF não autorizado.")

            st.markdown("""
            <p style='text-align:center;color:#94a3b8;font-size:0.72rem;margin-top:1.2rem;'>
                © 2025 Prefeitura de Viçosa — Acesso restrito
            </p>
            """, unsafe_allow_html=True)

    st.stop()

# ==========================================
# SIDEBAR — PÓS LOGIN
# ==========================================
with st.sidebar:
    try:
        st.image("logo_vicosa.jpg", use_container_width=True)
    except Exception:
        st.markdown("<div style='font-size:2rem;text-align:center'>🏛️</div>", unsafe_allow_html=True)

    st.markdown("## Prefeitura de Viçosa")
    st.markdown("---")
    st.markdown("**Navegação**")
    st.markdown("📊 **Dashboard** — visão geral das metas")
    st.markdown("📝 **Cadastros** — secretarias, metas e ações")
    st.markdown("---")

    if st.button("🚪 Sair", key="btn_sair"):
        st.session_state.autenticado = False
        st.rerun()

    st.caption("Prefeitura de Viçosa © 2025")

# Garante fundo claro no painel (sobrescreve o gradiente do login)
st.markdown("""
<style>
.stApp { background: #f1f5f9 !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CABEÇALHO DO PAINEL
# ==========================================
st.markdown("""
<div style='margin-bottom:0.5rem'>
    <h1 style='color:#0f2a5e;font-size:1.65rem;margin:0 0 4px 0;font-weight:700;'>
        Painel de Acompanhamento de Metas
    </h1>
    <p style='color:#475569;font-size:0.92rem;margin:0;'>
        Acompanhe e gerencie as metas e ações das secretarias municipais.
    </p>
</div>
""", unsafe_allow_html=True)
st.divider()

aba_dash, aba_cad = st.tabs(["📊  Dashboard de Evolução", "📝  Área de Cadastros"])

# ==========================================
# ABA 1: DASHBOARD
# ==========================================
with aba_dash:

    # --- KPIs ---
    df_kpi = pd.read_sql_query("SELECT status, COUNT(id) as qt FROM acoes GROUP BY status", banco)

    def _kpi(status):
        r = df_kpi[df_kpi["status"] == status]["qt"]
        return int(r.values[0]) if not r.empty else 0

    total     = int(df_kpi["qt"].sum()) if not df_kpi.empty else 0
    pendente  = _kpi("Pendente")
    andamento = _kpi("Em Andamento")
    concluida = _kpi("Concluída")

    k1, k2, k3, k4 = st.columns(4)
    for col, cls, val, label in [
        (k1, "kpi-total", total,     "Total de Ações"),
        (k2, "kpi-pend",  pendente,  "Pendentes"),
        (k3, "kpi-and",   andamento, "Em Andamento"),
        (k4, "kpi-conc",  concluida, "Concluídas"),
    ]:
        with col:
            st.markdown(f"""
            <div class="kpi-card {cls}">
                <div class="kpi-value">{val}</div>
                <div class="kpi-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Filtros ---
    cf1, cf2, _ = st.columns([1, 1, 2])
    with cf1:
        filtro_status = st.selectbox("Filtrar por Status", ["Todos","Pendente","Em Andamento","Concluída"])
    with cf2:
        mes_grafico = st.selectbox("Mês para o Gráfico", MESES)

    # --- Tabela ---
    st.markdown('<div class="section-title">📋 Lista de Ações</div>', unsafe_allow_html=True)
    df_acoes = pd.read_sql_query('''
        SELECT s.nome AS Secretaria, m.titulo AS Meta, a.descricao AS Ação,
               a.responsavel AS Responsável, a.prazo AS Prazo, a.status AS Status
        FROM acoes a
        JOIN metas m ON a.meta_id = m.id
        JOIN secretarias s ON m.secretaria_id = s.id
    ''', banco)

    if not df_acoes.empty:
        if filtro_status != "Todos":
            df_acoes = df_acoes[df_acoes["Status"] == filtro_status]
        st.dataframe(df_acoes, use_container_width=True, hide_index=True, height=280)
    else:
        st.info("Nenhuma ação cadastrada ainda. Use a aba **Cadastros** para adicionar.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Gráficos ---
    st.markdown(f'<div class="section-title">📈 Evolução por Status — {mes_grafico}</div>', unsafe_allow_html=True)

    df_graf = pd.read_sql_query('''
        SELECT a.status, COUNT(a.id) AS quantidade
        FROM acoes a JOIN metas m ON a.meta_id = m.id
        WHERE m.mes = ? GROUP BY a.status
    ''', banco, params=(mes_grafico,))

    CORES = {"Pendente": "#f97316", "Em Andamento": "#3b82f6", "Concluída": "#22c55e"}
    gc1, gc2 = st.columns(2)

    with gc1:
        if not df_graf.empty:
            fig, ax = plt.subplots(figsize=(5, 3.8))
            fig.patch.set_facecolor("white")
            ax.set_facecolor("#f8fafc")
            bar_colors = [CORES.get(s, "#94a3b8") for s in df_graf["status"]]
            bars = ax.bar(df_graf["status"], df_graf["quantidade"],
                          color=bar_colors, width=0.45, edgecolor="white", linewidth=2)
            for bar, val in zip(bars, df_graf["quantidade"]):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                        str(int(val)), ha="center", va="bottom", fontweight="bold", fontsize=12)
            ax.set_ylabel("Qtd. de Ações", fontsize=9, color="#475569")
            ax.set_ylim(0, df_graf["quantidade"].max() + 2)
            for spine in ["top", "right"]:
                ax.spines[spine].set_visible(False)
            ax.spines["left"].set_color("#e2e8f0")
            ax.spines["bottom"].set_color("#e2e8f0")
            ax.tick_params(colors="#475569", labelsize=9)
            ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
            ax.set_title("Distribuição por Status", fontsize=10, fontweight="bold", color="#0f2a5e", pad=10)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.warning(f"Sem dados para **{mes_grafico}**.")

    with gc2:
        if not df_graf.empty:
            fig2, ax2 = plt.subplots(figsize=(5, 3.8))
            fig2.patch.set_facecolor("white")
            pie_colors = [CORES.get(s, "#94a3b8") for s in df_graf["status"]]
            wedges, texts, autos = ax2.pie(
                df_graf["quantidade"], labels=df_graf["status"],
                colors=pie_colors, autopct="%1.0f%%", startangle=90,
                wedgeprops={"edgecolor": "white", "linewidth": 2.5}
            )
            for t in texts:  t.set_fontsize(9)
            for at in autos: at.set_fontsize(9); at.set_fontweight("bold"); at.set_color("white")
            ax2.set_title("Proporção por Status", fontsize=10, fontweight="bold", color="#0f2a5e", pad=10)
            plt.tight_layout()
            st.pyplot(fig2)
            plt.close(fig2)
        else:
            st.info("O gráfico de pizza aparecerá aqui quando houver dados.")

# ==========================================
# ABA 2: CADASTROS
# ==========================================
with aba_cad:
    st.markdown('<div class="section-title">📌 Registrar Novas Informações</div>', unsafe_allow_html=True)

    with st.expander("🏢  Cadastrar Secretaria"):
        nome_sec = st.text_input("Nome da Secretaria", placeholder="Ex: Secretaria de Educação")
        if st.button("💾 Salvar Secretaria", key="btn_sec"):
            if nome_sec.strip():
                banco.cursor().execute("INSERT INTO secretarias (nome) VALUES (?)", (nome_sec.strip(),))
                banco.commit()
                st.success(f"✅ Secretaria **{nome_sec}** cadastrada!")
            else:
                st.error("Informe o nome da secretaria.")

    with st.expander("🎯  Cadastrar Meta"):
        mc1, mc2 = st.columns(2)
        with mc1:
            titulo_meta = st.text_input("Título da Meta", placeholder="Ex: Ampliar atendimento escolar")
        with mc2:
            mes_meta = st.selectbox("Mês de Referência", MESES, key="mes_meta")

        df_sec = pd.read_sql_query("SELECT id, nome FROM secretarias", banco)
        if not df_sec.empty:
            sec_sel = st.selectbox("Vincular à Secretaria", df_sec["nome"])
            sec_id  = int(df_sec[df_sec["nome"] == sec_sel]["id"].values[0])
            if st.button("💾 Salvar Meta", key="btn_meta"):
                if titulo_meta.strip():
                    banco.cursor().execute(
                        "INSERT INTO metas (titulo, mes, secretaria_id) VALUES (?, ?, ?)",
                        (titulo_meta.strip(), mes_meta, sec_id)
                    )
                    banco.commit()
                    st.success("✅ Meta cadastrada com sucesso!")
                else:
                    st.error("Informe o título da meta.")
        else:
            st.warning("⚠️ Cadastre uma secretaria antes de registrar uma meta.")

    with st.expander("✅  Cadastrar Ação"):
        ac1, ac2 = st.columns(2)
        with ac1:
            desc_acao = st.text_input("Descrição da Ação", placeholder="Ex: Contratar 10 professores")
            resp_acao = st.text_input("Responsável", placeholder="Nome do responsável")
        with ac2:
            prazo_acao  = st.date_input("Prazo de Conclusão")
            status_acao = st.selectbox("Status Atual", ["Pendente","Em Andamento","Concluída"])

        df_metas = pd.read_sql_query("SELECT id, titulo FROM metas", banco)
        if not df_metas.empty:
            meta_sel = st.selectbox("Vincular à Meta", df_metas["titulo"])
            meta_id  = int(df_metas[df_metas["titulo"] == meta_sel]["id"].values[0])
            if st.button("💾 Salvar Ação", key="btn_acao"):
                if desc_acao.strip() and resp_acao.strip():
                    banco.cursor().execute(
                        "INSERT INTO acoes (descricao, responsavel, prazo, status, meta_id) VALUES (?, ?, ?, ?, ?)",
                        (desc_acao.strip(), resp_acao.strip(), str(prazo_acao), status_acao, meta_id)
                    )
                    banco.commit()
                    st.success("✅ Ação registrada com sucesso!")
                    st.rerun()
                else:
                    st.error("Preencha todos os campos obrigatórios.")
        else:
            st.warning("⚠️ Cadastre uma meta antes de registrar uma ação.")
