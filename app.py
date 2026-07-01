import streamlit as st
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
from datetime import date

# ════════════════════════════════════════════════════════
# CONSTANTES
# ════════════════════════════════════════════════════════
CPF_AUTORIZADO = "00000000000"
MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
         "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
TIPOS_SECRETARIA = ["Educação","Saúde","Assistência Social","Obras","Agricultura",
                    "Meio Ambiente","Cultura","Esporte e Lazer","Administração",
                    "Fazenda","Planejamento","Transporte","Outra"]
PRIORIDADES  = ["Baixa","Média","Alta"]
STATUS_META  = ["Não iniciada","Em andamento","Concluída","Atrasada"]
STATUS_ACAO  = ["Pendente","Em Andamento","Concluída"]
STATUS_SEC   = ["Ativa","Inativa"]

COR_PRIO   = {"Baixa":"#16a34a","Média":"#d97706","Alta":"#dc2626"}
COR_STATUS = {
    "Não iniciada":"#6b7280","Em andamento":"#2563eb","Concluída":"#16a34a","Atrasada":"#dc2626",
    "Pendente":"#d97706","Em Andamento":"#2563eb","Ativa":"#16a34a","Inativa":"#6b7280",
}

# ════════════════════════════════════════════════════════
# BANCO DE DADOS
# ════════════════════════════════════════════════════════
def conectar_db():
    conn = sqlite3.connect("prefeitura_metas.db", check_same_thread=False)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS secretarias (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT,
            tipo TEXT, secretario TEXT, email TEXT, telefone TEXT,
            status TEXT DEFAULT 'Ativa', descricao TEXT);
        CREATE TABLE IF NOT EXISTS metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT, mes TEXT, secretaria_id INTEGER,
            objetivo TEXT, responsavel TEXT,
            prioridade TEXT DEFAULT 'Média',
            status TEXT DEFAULT 'Não iniciada',
            data_inicio TEXT, prazo_final TEXT,
            percentual INTEGER DEFAULT 0,
            indicador TEXT, observacoes TEXT,
            FOREIGN KEY(secretaria_id) REFERENCES secretarias(id));
        CREATE TABLE IF NOT EXISTS acoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT, descricao TEXT, responsavel TEXT,
            prazo TEXT, status TEXT DEFAULT 'Pendente',
            data_inicio TEXT, percentual INTEGER DEFAULT 0,
            observacoes TEXT, meta_id INTEGER,
            FOREIGN KEY(meta_id) REFERENCES metas(id));
    """)
    conn.commit()
    migrações = {
        "secretarias": {"tipo":"TEXT","secretario":"TEXT","email":"TEXT",
                        "telefone":"TEXT","status":"TEXT DEFAULT 'Ativa'","descricao":"TEXT"},
        "metas": {"objetivo":"TEXT","responsavel":"TEXT","prioridade":"TEXT DEFAULT 'Média'",
                  "status":"TEXT DEFAULT 'Não iniciada'","data_inicio":"TEXT","prazo_final":"TEXT",
                  "percentual":"INTEGER DEFAULT 0","indicador":"TEXT","observacoes":"TEXT"},
        "acoes": {"nome":"TEXT","data_inicio":"TEXT","percentual":"INTEGER DEFAULT 0","observacoes":"TEXT"},
    }
    for tabela, colunas in migrações.items():
        existentes = {r[1] for r in c.execute(f"PRAGMA table_info({tabela})")}
        for col, tipo in colunas.items():
            if col not in existentes:
                c.execute(f"ALTER TABLE {tabela} ADD COLUMN {col} {tipo}")
    conn.commit()
    return conn

# ════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════
def parse_date(s):
    try: return date.fromisoformat(str(s)[:10])
    except: return date.today()

def badge_html(texto, cor):
    return (f'<span style="display:inline-block;background:{cor};color:#fff;'
            f'padding:3px 12px;border-radius:999px;font-size:0.7rem;'
            f'font-weight:600;letter-spacing:0.3px;">{texto}</span>')

def progress_bar(pct):
    pct = max(0, min(100, int(pct or 0)))
    cor = "#16a34a" if pct >= 80 else "#d97706" if pct >= 40 else "#dc2626"
    return (f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<div style="flex:1;background:#e2e8f0;border-radius:999px;height:6px;">'
            f'<div style="background:{cor};width:{pct}%;height:6px;border-radius:999px;transition:width 0.3s;"></div>'
            f'</div><span style="font-size:0.75rem;font-weight:600;color:#374151;min-width:32px;">{pct}%</span></div>')

def kpi_card(valor, label, cor, icone):
    return f"""
    <div style="background:#fff;border-radius:16px;padding:20px 24px;
                box-shadow:0 1px 3px rgba(0,0,0,0.08),0 1px 2px rgba(0,0,0,0.06);
                border-left:4px solid {cor};height:100%;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
            <span style="font-size:1.5rem;">{icone}</span>
            <span style="font-size:0.7rem;font-weight:700;color:{cor};background:{cor}18;
                         padding:3px 10px;border-radius:999px;text-transform:uppercase;
                         letter-spacing:0.5px;">{label}</span>
        </div>
        <div style="font-size:2.4rem;font-weight:800;color:#111827;line-height:1;">{valor}</div>
    </div>"""

def section_header(titulo, subtitulo=""):
    sub = f"<p style='color:#6b7280;font-size:0.875rem;margin:4px 0 0 0;'>{subtitulo}</p>" if subtitulo else ""
    return f"""<div style="margin-bottom:24px;">
        <h2 style="color:#111827;font-size:1.5rem;font-weight:700;margin:0;">{titulo}</h2>{sub}
    </div>"""

def voltar_btn(key):
    col, _ = st.columns([1, 5])
    with col:
        if st.button("← Voltar", key=f"v_{key}", use_container_width=True):
            st.session_state.pagina = "dashboard"; st.rerun()

# ════════════════════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Metas — Prefeitura de Viçosa",
    layout="wide", page_icon="🏛️",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════
for k, v in {"autenticado":False,"pagina":"dashboard",
              "editar_meta_id":None,"editar_sec_id":None,"editar_acao_id":None,
              "del_meta_id":None,"del_acao_id":None,"del_sec_id":None}.items():
    if k not in st.session_state: st.session_state[k] = v

# ════════════════════════════════════════════════════════
# DESIGN SYSTEM — CSS
# ════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── BASE ─────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family:'Inter',sans-serif; }
.stApp { background:#f0f4f8; }
#MainMenu, footer, header { visibility:hidden; }

/* ── MAIN CONTAINER ────────────────────── */
.main .block-container {
    padding: 2rem 2rem 3rem !important;
    max-width: 1400px !important;
}

/* ── SIDEBAR ──────────────────────────── */
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #0f2a5e 0%, #1a3a72 50%, #1d6b52 100%);
    padding: 0 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: rgba(255,255,255,0.85) !important;
    border: none !important;
    border-radius: 10px !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    padding: 10px 16px !important;
    text-align: left !important;
    transition: all 0.15s ease !important;
    width: 100% !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.15) !important;
    color: #fff !important;
    transform: none !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown { color: rgba(255,255,255,0.8) !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color:#fff !important; }

/* ── CARDS ────────────────────────────── */
.card {
    background:#fff; border-radius:16px;
    padding:20px; margin-bottom:12px;
    box-shadow:0 1px 3px rgba(0,0,0,0.08);
    border:1px solid #e5e7eb;
    transition: box-shadow 0.2s;
}
.card:hover { box-shadow:0 4px 12px rgba(0,0,0,0.1); }

/* ── BUTTONS ──────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #0f2a5e 0%, #1d6b52 100%) !important;
    color: #fff !important; border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important; font-size: 0.875rem !important;
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 3px rgba(15,42,94,0.3) !important;
}
.stButton > button:hover {
    box-shadow: 0 4px 12px rgba(15,42,94,0.4) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── FORMS ────────────────────────────── */
[data-testid="stForm"] {
    background:#fff !important; border-radius:16px !important;
    padding:24px !important; border:1px solid #e5e7eb !important;
    box-shadow:0 1px 3px rgba(0,0,0,0.06) !important;
}

/* ── INPUTS ───────────────────────────── */
.stTextInput input, .stTextArea textarea,
.stSelectbox select, .stDateInput input {
    border-radius:10px !important; border:1px solid #d1d5db !important;
    background:#fff !important; color:#111827 !important;
    font-size:0.875rem !important; padding:10px 14px !important;
    transition:border-color 0.15s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color:#0f2a5e !important;
    box-shadow:0 0 0 3px rgba(15,42,94,0.1) !important;
}

/* ── TABS ─────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background:#fff; border-radius:12px;
    padding:4px; gap:4px;
    box-shadow:0 1px 3px rgba(0,0,0,0.06);
    border:1px solid #e5e7eb;
    margin-bottom:20px;
}
.stTabs [data-baseweb="tab"] {
    border-radius:8px; padding:8px 20px;
    font-weight:500; font-size:0.875rem; color:#4b5563;
    border:none !important; background:transparent;
}
.stTabs [aria-selected="true"] {
    background:linear-gradient(135deg,#0f2a5e,#1d6b52) !important;
    color:#fff !important; font-weight:600 !important;
}

/* ── DATAFRAME ────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius:12px !important; overflow:hidden !important;
    border:1px solid #e5e7eb !important;
}

/* ── DIVIDER ──────────────────────────── */
hr { border:none; border-top:1px solid #e5e7eb; margin:16px 0; }

/* ── SECTION TITLE ────────────────────── */
.sec-title {
    font-size:1rem; font-weight:700; color:#111827;
    padding-bottom:10px; margin:20px 0 14px 0;
    border-bottom:2px solid #e5e7eb;
}

/* ── KPI GRID ─────────────────────────── */
.kpi-grid {
    display:grid;
    grid-template-columns: repeat(4, 1fr);
    gap:16px; margin-bottom:20px;
}
.kpi-grid-3 {
    display:grid;
    grid-template-columns: repeat(3, 1fr);
    gap:16px; margin-bottom:20px;
}

/* ── SIDEBAR DESKTOP: sempre aberta ────── */
@media (min-width: 769px) {
    [data-testid="stSidebar"] {
        min-width:240px !important; max-width:240px !important;
        transform:translateX(0) !important;
    }
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"],
    button[data-testid="stBaseButton-headerNoPadding"] { display:none !important; }
}

/* ── MOBILE ───────────────────────────── */
@media (max-width: 768px) {
    .main .block-container { padding:1rem 0.75rem 2rem !important; }
    .kpi-grid { grid-template-columns:1fr !important; gap:10px !important; }
    .kpi-grid-3 { grid-template-columns:1fr !important; gap:10px !important; }
    [data-testid="stSidebar"] { max-width:85vw !important; }
    .stButton > button { padding:12px 16px !important; font-size:1rem !important; }
    .stTextInput input, .stTextArea textarea,
    .stSelectbox select, .stDateInput input { font-size:1rem !important; padding:12px 14px !important; }
    h1 { font-size:1.25rem !important; }
}

/* ── TABLET ───────────────────────────── */
@media (min-width:481px) and (max-width:768px) {
    .kpi-grid { grid-template-columns:repeat(2,1fr) !important; }
    .kpi-grid-3 { grid-template-columns:repeat(2,1fr) !important; }
}

/* ── ALERTS ───────────────────────────── */
[data-testid="stAlert"] { border-radius:10px !important; }

/* ── CAPTION ──────────────────────────── */
.caption-text { font-size:0.75rem; color:#6b7280; }

/* ── LOGIN ────────────────────────────── */
.login-card {
    background:#fff; border-radius:24px;
    padding:40px 36px; max-width:420px; margin:auto;
    box-shadow:0 20px 60px rgba(0,0,0,0.25);
}
</style>
""", unsafe_allow_html=True)

banco = conectar_db()

# ════════════════════════════════════════════════════════
# LOGIN
# ════════════════════════════════════════════════════════
if not st.session_state.autenticado:
    st.markdown("""<style>
        .stApp { background:linear-gradient(135deg,#0f2a5e 0%,#1a3a72 50%,#1d6b52 100%) !important; }
        [data-testid="stSidebar"],[data-testid="stDecoration"] { display:none !important; }
        .main .block-container { max-width:100% !important; padding:0 !important; }
    </style>""", unsafe_allow_html=True)

    st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with st.form("login_form"):
            try: st.image("logo_vicosa.jpg", use_container_width=True)
            except: st.markdown("<div style='text-align:center;font-size:4rem'>🏛️</div>", unsafe_allow_html=True)

            st.markdown("""
            <div style='text-align:center;margin:16px 0 24px;'>
                <h2 style='color:#0f2a5e;font-size:1.4rem;font-weight:800;margin:0 0 6px;'>
                    Prefeitura de Viçosa</h2>
                <p style='color:#6b7280;font-size:0.85rem;margin:0;'>
                    Sistema de Acompanhamento de Metas Municipais</p>
            </div>
            <hr style='border:none;border-top:1px solid #e5e7eb;margin:0 0 20px;'>
            """, unsafe_allow_html=True)

            cpf = st.text_input("CPF (somente números)", max_chars=11, placeholder="00000000000")
            entrar = st.form_submit_button("Entrar no Sistema →", use_container_width=True)

            if entrar:
                if cpf == CPF_AUTORIZADO:
                    st.session_state.autenticado = True; st.rerun()
                elif not cpf:
                    st.warning("Digite seu CPF para continuar.")
                else:
                    st.error("CPF não autorizado.")

            st.markdown("<p style='text-align:center;color:#9ca3af;font-size:0.72rem;margin-top:16px;'>"
                        "© 2025 Prefeitura de Viçosa · Acesso restrito</p>", unsafe_allow_html=True)
    st.stop()

# ════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("<div style='padding:24px 16px 8px;'>", unsafe_allow_html=True)
    try: st.image("logo_vicosa.jpg", use_container_width=True)
    except: st.markdown("<div style='text-align:center;font-size:3rem;padding:16px;'>🏛️</div>",
                        unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:center;padding:12px 0 20px;'>
        <h3 style='color:#fff;font-size:1rem;font-weight:700;margin:0;'>Prefeitura de Viçosa</h3>
        <p style='color:rgba(255,255,255,0.55);font-size:0.75rem;margin:4px 0 0;'>
            Sistema de Metas</p>
    </div>
    <div style='border-top:1px solid rgba(255,255,255,0.15);margin:0 16px 16px;'></div>
    """, unsafe_allow_html=True)

    pag_atual = st.session_state.pagina
    for icon, label, key in [
        ("🏠","Dashboard","dashboard"),
        ("🏢","Secretarias","secretarias"),
        ("🎯","Metas","metas"),
        ("✅","Ações","acoes"),
        ("📊","Relatórios","relatorios"),
    ]:
        ativo = pag_atual == key
        if ativo:
            st.markdown(f"""<div style='background:rgba(255,255,255,0.18);border-radius:10px;
                padding:10px 16px;margin:2px 0;color:#fff;font-weight:600;font-size:0.875rem;
                border-left:3px solid rgba(255,255,255,0.8);'>
                {icon}  {label}</div>""", unsafe_allow_html=True)
        else:
            if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
                st.session_state.pagina = key; st.rerun()

    st.markdown("<div style='border-top:1px solid rgba(255,255,255,0.15);margin:16px 16px;'></div>",
                unsafe_allow_html=True)
    if st.button("🚪  Sair", key="sair", use_container_width=True):
        st.session_state.autenticado = False; st.rerun()
    st.markdown(f"<p style='text-align:center;color:rgba(255,255,255,0.35);font-size:0.7rem;"
                f"padding-bottom:16px;'>v2.0 · © 2025</p>", unsafe_allow_html=True)

st.markdown("<style>.stApp{background:#f0f4f8 !important;}</style>", unsafe_allow_html=True)

# Botão flutuante de menu — visível só no mobile
st.markdown("""
<div id="m-menu"
     onclick="(window.parent.document.querySelector('[data-testid=collapsedControl] button')||window.parent.document.querySelector('section[data-testid=stSidebar] button')||window.parent.document.querySelector('button[data-testid=stBaseButton-headerNoPadding]'))?.click()"
     style="display:none;position:fixed;top:14px;left:14px;z-index:99999;cursor:pointer;">
  <div style="background:#0f2a5e;color:#fff;border-radius:12px;width:44px;height:44px;
              display:flex;align-items:center;justify-content:center;
              font-size:1.4rem;box-shadow:0 4px 16px rgba(15,42,94,0.5);">☰</div>
</div>
<style>@media(max-width:768px){#m-menu{display:block!important;}
.main .block-container{padding-top:4rem!important;}}</style>
""", unsafe_allow_html=True)

pagina = st.session_state.pagina

# ════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════
if pagina == "dashboard":
    st.markdown(section_header("🏠 Dashboard",
                "Visão geral das metas e ações municipais"), unsafe_allow_html=True)
    st.divider()

    df_s = pd.read_sql_query("SELECT * FROM secretarias", banco)
    df_m = pd.read_sql_query("SELECT * FROM metas", banco)
    df_a = pd.read_sql_query("SELECT * FROM acoes", banco)

    tot_sec  = len(df_s)
    tot_meta = len(df_m)
    tot_acao = len(df_a)
    concl    = len(df_m[df_m.status=="Concluída"])    if not df_m.empty else 0
    andamen  = len(df_m[df_m.status=="Em andamento"]) if not df_m.empty else 0
    atras    = len(df_m[df_m.status=="Atrasada"])     if not df_m.empty else 0
    pct_ger  = int(df_m.percentual.mean()) if not df_m.empty and df_m.percentual.notna().any() else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(kpi_card(tot_sec,       "Secretarias",     "#0f2a5e", "🏢"), unsafe_allow_html=True)
    k2.markdown(kpi_card(tot_meta,      "Total de Metas",  "#1d6b52", "🎯"), unsafe_allow_html=True)
    k3.markdown(kpi_card(tot_acao,      "Total de Ações",  "#2563eb", "✅"), unsafe_allow_html=True)
    k4.markdown(kpi_card(f"{pct_ger}%", "Conclusão Geral", "#6b7280", "📈"), unsafe_allow_html=True)

    k5, k6, k7 = st.columns(3)
    k5.markdown(kpi_card(concl,   "Metas Concluídas", "#16a34a", "🏆"), unsafe_allow_html=True)
    k6.markdown(kpi_card(andamen, "Em Andamento",      "#d97706", "⏳"), unsafe_allow_html=True)
    k7.markdown(kpi_card(atras,   "Metas Atrasadas",   "#dc2626", "⚠️"), unsafe_allow_html=True)

    if not df_m.empty:
        st.markdown('<div class="sec-title">📊 Análise Visual</div>', unsafe_allow_html=True)
        gc1, gc2 = st.columns(2)
        CORES_S = {"Não iniciada":"#9ca3af","Em andamento":"#3b82f6",
                   "Concluída":"#22c55e","Atrasada":"#ef4444"}
        CORES_P = {"Baixa":"#22c55e","Média":"#f59e0b","Alta":"#ef4444"}

        with gc1:
            st.markdown("**Status das Metas**")
            sc = df_m.status.value_counts()
            fig, ax = plt.subplots(figsize=(5, 3.2))
            fig.patch.set_facecolor("white"); ax.set_facecolor("#fafafa")
            bars = ax.barh(sc.index, sc.values,
                           color=[CORES_S.get(s,"#9ca3af") for s in sc.index],
                           height=0.5, edgecolor="white", linewidth=1.5)
            for bar, v in zip(bars, sc.values):
                ax.text(v + 0.05, bar.get_y() + bar.get_height()/2,
                        str(int(v)), va="center", fontweight="bold", fontsize=10, color="#374151")
            ax.set_xlabel("Quantidade", fontsize=9, color="#6b7280")
            for sp in ["top","right","left"]: ax.spines[sp].set_visible(False)
            ax.spines["bottom"].set_color("#e5e7eb")
            ax.tick_params(colors="#6b7280", labelsize=8)
            ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
            plt.tight_layout(); st.pyplot(fig, use_container_width=True); plt.close(fig)

        with gc2:
            st.markdown("**Metas por Prioridade**")
            if "prioridade" in df_m.columns:
                pc = df_m.prioridade.value_counts()
                if not pc.empty:
                    fig2, ax2 = plt.subplots(figsize=(5, 3.2))
                    fig2.patch.set_facecolor("white")
                    wedges, texts, autos = ax2.pie(
                        pc.values, labels=pc.index,
                        colors=[CORES_P.get(s,"#9ca3af") for s in pc.index],
                        autopct="%1.0f%%", startangle=90,
                        wedgeprops={"edgecolor":"white","linewidth":2.5},
                        pctdistance=0.75)
                    for t in texts: t.set_fontsize(9); t.set_color("#374151")
                    for a in autos: a.set_fontsize(9); a.set_fontweight("bold"); a.set_color("white")
                    plt.tight_layout(); st.pyplot(fig2, use_container_width=True); plt.close(fig2)

        # Últimas metas
        st.markdown('<div class="sec-title">🎯 Últimas Metas</div>', unsafe_allow_html=True)
        df_ult = pd.read_sql_query("""
            SELECT m.titulo, s.nome AS secretaria, m.prioridade, m.status, m.percentual, m.prazo_final
            FROM metas m LEFT JOIN secretarias s ON m.secretaria_id=s.id
            ORDER BY m.id DESC LIMIT 5""", banco)
        if not df_ult.empty:
            for _, r in df_ult.iterrows():
                pct = int(r.get("percentual") or 0)
                prio = r.get("prioridade") or "Média"
                stm  = r.get("status") or "Não iniciada"
                st.markdown(f"""
                <div class="card" style="padding:14px 18px;margin-bottom:8px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                        <div>
                            <strong style="color:#111827;font-size:0.9rem;">{r['titulo']}</strong>
                            <span style="color:#6b7280;font-size:0.8rem;margin-left:8px;">{r.get('secretaria') or '—'}</span>
                        </div>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
                            {badge_html(prio, COR_PRIO.get(prio,"#6b7280"))}
                            {badge_html(stm, COR_STATUS.get(stm,"#6b7280"))}
                        </div>
                    </div>
                    <div style="margin-top:10px;">{progress_bar(pct)}</div>
                </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# SECRETARIAS
# ════════════════════════════════════════════════════════
elif pagina == "secretarias":
    voltar_btn("sec")
    st.markdown(section_header("🏢 Secretarias", "Gerencie as secretarias municipais"),
                unsafe_allow_html=True)

    edit_id = st.session_state.editar_sec_id
    edit_d  = None
    if edit_id:
        cur = banco.cursor(); cur.execute("SELECT * FROM secretarias WHERE id=?", (edit_id,))
        r = cur.fetchone()
        if r: edit_d = dict(zip([d[0] for d in cur.description], r))

    aba_l, aba_c = st.tabs(["📋  Listagem", "➕  Nova Secretaria"])

    with aba_l:
        df = pd.read_sql_query("SELECT * FROM secretarias ORDER BY nome", banco)
        if df.empty:
            st.info("Nenhuma secretaria cadastrada. Use a aba **Nova Secretaria**.")
        else:
            c1, c2 = st.columns(2)
            with c1: ft = st.selectbox("Filtrar por Tipo", ["Todos"] + TIPOS_SECRETARIA, key="fs_t")
            with c2: fs = st.selectbox("Filtrar por Status", ["Todos"] + STATUS_SEC, key="fs_s")
            if ft != "Todos": df = df[df.tipo == ft]
            if fs != "Todos": df = df[df.status == fs]

            st.markdown(f"<p class='caption-text'>{len(df)} secretaria(s) encontrada(s)</p>",
                        unsafe_allow_html=True)

            for _, row in df.iterrows():
                tipo_b = badge_html(row.get("tipo") or "—", "#0f2a5e")
                stat_v = row.get("status") or "Ativa"
                stat_b = badge_html(stat_v, COR_STATUS.get(stat_v, "#6b7280"))
                st.markdown(f"""
                <div class="card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
                        <div style="flex:1;min-width:200px;">
                            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px;">
                                <strong style="color:#111827;font-size:1rem;">{row['nome']}</strong>
                                {tipo_b} {stat_b}
                            </div>
                            <p style="color:#6b7280;font-size:0.8rem;margin:2px 0;">
                                👤 {row.get('secretario') or '—'} &nbsp;|&nbsp;
                                📧 {row.get('email') or '—'} &nbsp;|&nbsp;
                                📞 {row.get('telefone') or '—'}
                            </p>
                            {f"<p style='color:#9ca3af;font-size:0.78rem;margin:4px 0 0;'>{str(row['descricao'])[:80]}…</p>" if row.get('descricao') else ""}
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)

                b1, b2, _ = st.columns([1, 1, 8])
                with b1:
                    if st.button("✏️ Editar", key=f"es_{row['id']}", use_container_width=True):
                        st.session_state.editar_sec_id = int(row['id']); st.rerun()
                with b2:
                    if st.button("🗑️ Excluir", key=f"ds_{row['id']}", use_container_width=True):
                        st.session_state.del_sec_id = int(row['id'])

                if st.session_state.del_sec_id == int(row['id']):
                    st.warning(f"Confirmar exclusão de **{row['nome']}**?")
                    d1, d2 = st.columns(2)
                    with d1:
                        if st.button("✅ Confirmar", key=f"cds_{row['id']}", use_container_width=True):
                            banco.cursor().execute("DELETE FROM secretarias WHERE id=?", (row['id'],))
                            banco.commit(); st.session_state.del_sec_id = None; st.rerun()
                    with d2:
                        if st.button("❌ Cancelar", key=f"cas_{row['id']}", use_container_width=True):
                            st.session_state.del_sec_id = None; st.rerun()

    with aba_c:
        if edit_id:
            st.info(f"✏️ Editando: **{edit_d.get('nome','') if edit_d else ''}**")
        with st.form("form_sec"):
            st.markdown("**Informações da Secretaria**")
            c1, c2 = st.columns(2)
            with c1:
                nome_s  = st.text_input("Nome da Secretaria *", value=edit_d.get("nome","") if edit_d else "")
                secret  = st.text_input("Secretário(a)", value=edit_d.get("secretario","") if edit_d else "")
                email_s = st.text_input("E-mail", value=edit_d.get("email","") if edit_d else "")
            with c2:
                ti     = TIPOS_SECRETARIA.index(edit_d["tipo"]) if edit_d and edit_d.get("tipo") in TIPOS_SECRETARIA else 12
                tipo_s = st.selectbox("Tipo", TIPOS_SECRETARIA, index=ti)
                tel_s  = st.text_input("Telefone", value=edit_d.get("telefone","") if edit_d else "")
                si     = STATUS_SEC.index(edit_d["status"]) if edit_d and edit_d.get("status") in STATUS_SEC else 0
                stat_s = st.selectbox("Status", STATUS_SEC, index=si)
            desc_s = st.text_area("Descrição", value=edit_d.get("descricao","") if edit_d else "", height=80)

            if st.form_submit_button("💾 Salvar Secretaria", use_container_width=True):
                if nome_s.strip():
                    cur = banco.cursor()
                    v = (nome_s.strip(), tipo_s, secret, email_s, tel_s, stat_s, desc_s)
                    if edit_id:
                        cur.execute("UPDATE secretarias SET nome=?,tipo=?,secretario=?,email=?,telefone=?,status=?,descricao=? WHERE id=?", v+(edit_id,))
                        st.success("✅ Secretaria atualizada!"); st.session_state.editar_sec_id = None
                    else:
                        cur.execute("INSERT INTO secretarias (nome,tipo,secretario,email,telefone,status,descricao) VALUES (?,?,?,?,?,?,?)", v)
                        st.success(f"✅ Secretaria **{nome_s}** cadastrada!")
                    banco.commit(); st.rerun()
                else:
                    st.error("Informe o nome da secretaria.")
        if edit_id:
            if st.button("❌ Cancelar edição", key="canc_sec"):
                st.session_state.editar_sec_id = None; st.rerun()

# ════════════════════════════════════════════════════════
# METAS
# ════════════════════════════════════════════════════════
elif pagina == "metas":
    voltar_btn("met")
    st.markdown(section_header("🎯 Metas", "Cadastre e acompanhe as metas municipais"),
                unsafe_allow_html=True)

    edit_id = st.session_state.editar_meta_id
    edit_d  = None
    if edit_id:
        cur = banco.cursor(); cur.execute("SELECT * FROM metas WHERE id=?", (edit_id,))
        r = cur.fetchone()
        if r: edit_d = dict(zip([d[0] for d in cur.description], r))

    aba_l, aba_c = st.tabs(["📋  Listagem", "➕  Nova Meta"])

    with aba_l:
        df = pd.read_sql_query("""
            SELECT m.*, s.nome AS sec_nome, s.tipo AS sec_tipo
            FROM metas m LEFT JOIN secretarias s ON m.secretaria_id=s.id
            ORDER BY m.id DESC""", banco)
        if df.empty:
            st.info("Nenhuma meta cadastrada. Use a aba **Nova Meta**.")
        else:
            with st.expander("🔍 Filtros e Pesquisa", expanded=False):
                f1, f2, f3, f4 = st.columns(4)
                with f1:
                    opts_sec = ["Todas"] + sorted(df.sec_nome.dropna().unique().tolist())
                    f_sec = st.selectbox("Secretaria", opts_sec, key="fm_sec")
                with f2: f_st = st.selectbox("Status", ["Todos"] + STATUS_META, key="fm_st")
                with f3: f_pr = st.selectbox("Prioridade", ["Todas"] + PRIORIDADES, key="fm_pr")
                with f4: f_mes = st.selectbox("Mês", ["Todos"] + MESES, key="fm_mes")
                f5, f6 = st.columns(2)
                with f5: f_resp = st.text_input("Responsável", key="fm_resp")
                with f6: f_busca = st.text_input("🔍 Pesquisar pelo título", key="fm_busca")

            if f_sec  != "Todas": df = df[df.sec_nome == f_sec]
            if f_st   != "Todos": df = df[df.status == f_st]
            if f_pr   != "Todas": df = df[df.prioridade == f_pr]
            if f_mes  != "Todos": df = df[df.mes == f_mes]
            if f_resp:  df = df[df.responsavel.str.contains(f_resp, case=False, na=False)]
            if f_busca: df = df[df.titulo.str.contains(f_busca, case=False, na=False)]

            st.markdown(f"<p class='caption-text'>{len(df)} meta(s) encontrada(s)</p>",
                        unsafe_allow_html=True)

            for _, row in df.iterrows():
                pct  = int(row.get("percentual") or 0)
                prio = row.get("prioridade") or "Média"
                stm  = row.get("status") or "Não iniciada"
                st.markdown(f"""
                <div class="card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
                        <div style="flex:1;min-width:200px;">
                            <strong style="color:#111827;font-size:0.95rem;">{row['titulo']}</strong>
                            <p style="color:#6b7280;font-size:0.8rem;margin:4px 0 10px;">
                                🏢 {row.get('sec_nome') or '—'} &nbsp;|&nbsp;
                                👤 {row.get('responsavel') or '—'} &nbsp;|&nbsp;
                                📅 {row.get('prazo_final') or row.get('mes') or '—'}
                            </p>
                            {progress_bar(pct)}
                        </div>
                        <div style="display:flex;flex-direction:column;gap:6px;align-items:flex-end;">
                            {badge_html(prio, COR_PRIO.get(prio,'#6b7280'))}
                            {badge_html(stm, COR_STATUS.get(stm,'#6b7280'))}
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)

                b1, b2, _ = st.columns([1, 1, 8])
                with b1:
                    if st.button("✏️ Editar", key=f"em_{row['id']}", use_container_width=True):
                        st.session_state.editar_meta_id = int(row['id']); st.rerun()
                with b2:
                    if st.button("🗑️ Excluir", key=f"dm_{row['id']}", use_container_width=True):
                        st.session_state.del_meta_id = int(row['id'])

                if st.session_state.del_meta_id == int(row['id']):
                    st.warning(f"Confirmar exclusão de **{row['titulo']}**?")
                    d1, d2 = st.columns(2)
                    with d1:
                        if st.button("✅ Confirmar", key=f"cdm_{row['id']}", use_container_width=True):
                            banco.cursor().execute("DELETE FROM metas WHERE id=?", (row['id'],)); banco.commit()
                            st.session_state.del_meta_id = None; st.rerun()
                    with d2:
                        if st.button("❌ Cancelar", key=f"cam_{row['id']}", use_container_width=True):
                            st.session_state.del_meta_id = None; st.rerun()

    with aba_c:
        if edit_id: st.info(f"✏️ Editando: **{edit_d.get('titulo','') if edit_d else ''}**")
        df_sec2 = pd.read_sql_query("SELECT id,nome FROM secretarias", banco)
        with st.form("form_meta"):
            st.markdown("**Informações da Meta**")
            c1, c2 = st.columns(2)
            with c1:
                titulo = st.text_input("Título *", value=edit_d.get("titulo","") if edit_d else "")
                obj    = st.text_area("Objetivo", value=edit_d.get("objetivo","") if edit_d else "", height=80)
                resp   = st.text_input("Responsável", value=edit_d.get("responsavel","") if edit_d else "")
                mes_m  = st.selectbox("Mês", MESES,
                           index=MESES.index(edit_d["mes"]) if edit_d and edit_d.get("mes") in MESES else 0,
                           key="mes_m")
            with c2:
                sec_id_m = None
                if not df_sec2.empty:
                    nomes = df_sec2.nome.tolist(); sd = 0
                    if edit_d and edit_d.get("secretaria_id"):
                        mt = df_sec2[df_sec2.id == edit_d["secretaria_id"]]
                        if not mt.empty: sd = nomes.index(mt.iloc[0]["nome"])
                    sel = st.selectbox("Secretaria *", nomes, index=sd)
                    sec_id_m = int(df_sec2[df_sec2.nome == sel]["id"].values[0])
                else:
                    st.warning("⚠️ Cadastre uma secretaria antes.")
                pi     = PRIORIDADES.index(edit_d["prioridade"]) if edit_d and edit_d.get("prioridade") in PRIORIDADES else 1
                prio_m = st.selectbox("Prioridade", PRIORIDADES, index=pi)
                si     = STATUS_META.index(edit_d["status"]) if edit_d and edit_d.get("status") in STATUS_META else 0
                stat_m = st.selectbox("Status", STATUS_META, index=si)
                pct_m  = st.slider("Conclusão (%)", 0, 100,
                           value=int(edit_d.get("percentual") or 0) if edit_d else 0)

            c3, c4 = st.columns(2)
            with c3:
                di_m  = st.date_input("Data de Início",
                          value=parse_date(edit_d.get("data_inicio")) if edit_d else date.today())
                ind_m = st.text_input("Indicador de Sucesso",
                          value=edit_d.get("indicador","") if edit_d else "")
            with c4:
                pf_m  = st.date_input("Prazo Final",
                          value=parse_date(edit_d.get("prazo_final")) if edit_d else date.today())
                obs_m = st.text_area("Observações",
                          value=edit_d.get("observacoes","") if edit_d else "", height=80)

            if st.form_submit_button("💾 Salvar Meta", use_container_width=True):
                if titulo.strip() and sec_id_m:
                    cur = banco.cursor()
                    v = (titulo.strip(),mes_m,sec_id_m,obj,resp,prio_m,stat_m,
                         str(di_m),str(pf_m),pct_m,ind_m,obs_m)
                    if edit_id:
                        cur.execute("""UPDATE metas SET titulo=?,mes=?,secretaria_id=?,objetivo=?,
                            responsavel=?,prioridade=?,status=?,data_inicio=?,prazo_final=?,
                            percentual=?,indicador=?,observacoes=? WHERE id=?""", v+(edit_id,))
                        st.success("✅ Meta atualizada!"); st.session_state.editar_meta_id = None
                    else:
                        cur.execute("""INSERT INTO metas (titulo,mes,secretaria_id,objetivo,responsavel,
                            prioridade,status,data_inicio,prazo_final,percentual,indicador,observacoes)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", v)
                        st.success("✅ Meta cadastrada!")
                    banco.commit(); st.rerun()
                else:
                    st.error("Preencha o título e selecione a secretaria.")
        if edit_id:
            if st.button("❌ Cancelar edição", key="canc_meta"):
                st.session_state.editar_meta_id = None; st.rerun()

# ════════════════════════════════════════════════════════
# AÇÕES
# ════════════════════════════════════════════════════════
elif pagina == "acoes":
    voltar_btn("acao")
    st.markdown(section_header("✅ Ações", "Registre e acompanhe as ações vinculadas às metas"),
                unsafe_allow_html=True)

    edit_id = st.session_state.editar_acao_id
    edit_d  = None
    if edit_id:
        cur = banco.cursor(); cur.execute("SELECT * FROM acoes WHERE id=?", (edit_id,))
        r = cur.fetchone()
        if r: edit_d = dict(zip([d[0] for d in cur.description], r))

    aba_l, aba_c = st.tabs(["📋  Listagem", "➕  Nova Ação"])

    with aba_l:
        df = pd.read_sql_query("""
            SELECT a.*, m.titulo AS meta_titulo, s.nome AS sec_nome
            FROM acoes a
            LEFT JOIN metas m ON a.meta_id=m.id
            LEFT JOIN secretarias s ON m.secretaria_id=s.id
            ORDER BY a.id DESC""", banco)
        if df.empty:
            st.info("Nenhuma ação cadastrada. Use a aba **Nova Ação**.")
        else:
            c1, c2 = st.columns(2)
            with c1: f_sta  = st.selectbox("Status", ["Todos"] + STATUS_ACAO, key="fa_st")
            with c2:
                opts_m = ["Todas"] + sorted(df.meta_titulo.dropna().unique().tolist())
                f_meta = st.selectbox("Meta", opts_m, key="fa_meta")
            if f_sta  != "Todos": df = df[df.status == f_sta]
            if f_meta != "Todas": df = df[df.meta_titulo == f_meta]

            st.markdown(f"<p class='caption-text'>{len(df)} ação(ões)</p>", unsafe_allow_html=True)

            for _, row in df.iterrows():
                pct    = int(row.get("percentual") or 0)
                sta    = row.get("status") or "Pendente"
                nome_a = row.get("nome") or row.get("descricao") or "Ação sem nome"
                st.markdown(f"""
                <div class="card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
                        <div style="flex:1;min-width:200px;">
                            <strong style="color:#111827;">{nome_a}</strong>
                            <p style="color:#6b7280;font-size:0.8rem;margin:4px 0 10px;">
                                🎯 {row.get('meta_titulo') or '—'} &nbsp;|&nbsp;
                                👤 {row.get('responsavel') or '—'} &nbsp;|&nbsp;
                                📅 {row.get('prazo') or '—'}
                            </p>
                            {progress_bar(pct)}
                        </div>
                        <div>{badge_html(sta, COR_STATUS.get(sta,'#6b7280'))}</div>
                    </div>
                </div>""", unsafe_allow_html=True)

                b1, b2, _ = st.columns([1, 1, 8])
                with b1:
                    if st.button("✏️ Editar", key=f"ea_{row['id']}", use_container_width=True):
                        st.session_state.editar_acao_id = int(row['id']); st.rerun()
                with b2:
                    if st.button("🗑️ Excluir", key=f"da_{row['id']}", use_container_width=True):
                        st.session_state.del_acao_id = int(row['id'])

                if st.session_state.del_acao_id == int(row['id']):
                    st.warning(f"Confirmar exclusão de **{nome_a}**?")
                    d1, d2 = st.columns(2)
                    with d1:
                        if st.button("✅ Confirmar", key=f"cda_{row['id']}", use_container_width=True):
                            banco.cursor().execute("DELETE FROM acoes WHERE id=?", (row['id'],)); banco.commit()
                            st.session_state.del_acao_id = None; st.rerun()
                    with d2:
                        if st.button("❌ Cancelar", key=f"caa_{row['id']}", use_container_width=True):
                            st.session_state.del_acao_id = None; st.rerun()

    with aba_c:
        if edit_id:
            n = (edit_d.get("nome") or edit_d.get("descricao","")) if edit_d else ""
            st.info(f"✏️ Editando: **{n}**")
        df_metas2 = pd.read_sql_query("SELECT id,titulo FROM metas", banco)
        with st.form("form_acao"):
            st.markdown("**Informações da Ação**")
            c1, c2 = st.columns(2)
            with c1:
                nome_a = st.text_input("Nome da Ação *", value=edit_d.get("nome","") if edit_d else "")
                desc_a = st.text_area("Descrição", value=edit_d.get("descricao","") if edit_d else "", height=80)
                resp_a = st.text_input("Responsável", value=edit_d.get("responsavel","") if edit_d else "")
            with c2:
                sai    = STATUS_ACAO.index(edit_d["status"]) if edit_d and edit_d.get("status") in STATUS_ACAO else 0
                stat_a = st.selectbox("Status", STATUS_ACAO, index=sai)
                pct_a  = st.slider("Conclusão (%)", 0, 100,
                           value=int(edit_d.get("percentual") or 0) if edit_d else 0)
                di_a   = st.date_input("Data de Início",
                           value=parse_date(edit_d.get("data_inicio")) if edit_d else date.today())
                pf_a   = st.date_input("Prazo",
                           value=parse_date(edit_d.get("prazo")) if edit_d else date.today())
            obs_a = st.text_area("Observações", value=edit_d.get("observacoes","") if edit_d else "", height=60)

            meta_id_a = None
            if not df_metas2.empty:
                nms = df_metas2.titulo.tolist(); md = 0
                if edit_d and edit_d.get("meta_id"):
                    mt = df_metas2[df_metas2.id == edit_d["meta_id"]]
                    if not mt.empty: md = nms.index(mt.iloc[0]["titulo"])
                sel_m     = st.selectbox("Vincular à Meta *", nms, index=md)
                meta_id_a = int(df_metas2[df_metas2.titulo == sel_m]["id"].values[0])
            else:
                st.warning("⚠️ Cadastre uma meta antes.")

            if st.form_submit_button("💾 Salvar Ação", use_container_width=True):
                if nome_a.strip() and meta_id_a:
                    cur = banco.cursor()
                    v = (nome_a.strip(),desc_a,resp_a,str(pf_a),stat_a,str(di_a),pct_a,obs_a,meta_id_a)
                    if edit_id:
                        cur.execute("""UPDATE acoes SET nome=?,descricao=?,responsavel=?,prazo=?,
                            status=?,data_inicio=?,percentual=?,observacoes=?,meta_id=? WHERE id=?""",
                            v+(edit_id,))
                        st.success("✅ Ação atualizada!"); st.session_state.editar_acao_id = None
                    else:
                        cur.execute("""INSERT INTO acoes (nome,descricao,responsavel,prazo,status,
                            data_inicio,percentual,observacoes,meta_id) VALUES (?,?,?,?,?,?,?,?,?)""", v)
                        st.success("✅ Ação cadastrada!")
                    banco.commit(); st.rerun()
                else:
                    st.error("Preencha o nome e selecione a meta.")
        if edit_id:
            if st.button("❌ Cancelar edição", key="canc_acao"):
                st.session_state.editar_acao_id = None; st.rerun()

# ════════════════════════════════════════════════════════
# RELATÓRIOS
# ════════════════════════════════════════════════════════
elif pagina == "relatorios":
    voltar_btn("rel")
    st.markdown(section_header("📊 Relatórios", "Exporte os dados do sistema"),
                unsafe_allow_html=True)

    df_rel = pd.read_sql_query("""
        SELECT m.titulo AS "Meta", s.nome AS "Secretaria", s.tipo AS "Tipo",
               m.responsavel AS "Responsável", m.prioridade AS "Prioridade",
               m.status AS "Status", m.percentual AS "Conclusão (%)",
               m.data_inicio AS "Início", m.prazo_final AS "Prazo Final",
               m.mes AS "Mês", m.objetivo AS "Objetivo", m.observacoes AS "Observações"
        FROM metas m LEFT JOIN secretarias s ON m.secretaria_id=s.id ORDER BY m.id DESC""", banco)

    df_acoes_r = pd.read_sql_query("""
        SELECT a.nome AS "Ação", a.descricao AS "Descrição", m.titulo AS "Meta",
               s.nome AS "Secretaria", a.responsavel AS "Responsável",
               a.status AS "Status", a.percentual AS "Conclusão (%)",
               a.data_inicio AS "Início", a.prazo AS "Prazo", a.observacoes AS "Observações"
        FROM acoes a LEFT JOIN metas m ON a.meta_id=m.id
        LEFT JOIN secretarias s ON m.secretaria_id=s.id ORDER BY a.id DESC""", banco)

    df_sec_r = pd.read_sql_query("""
        SELECT nome AS "Secretaria", tipo AS "Tipo", secretario AS "Secretário(a)",
               email AS "E-mail", telefone AS "Telefone", status AS "Status",
               descricao AS "Descrição" FROM secretarias ORDER BY nome""", banco)

    def exportar(df, base, titulo):
        c1, c2 = st.columns(2)
        with c1:
            buf = io.BytesIO()
            try:
                with pd.ExcelWriter(buf, engine="openpyxl") as w:
                    df.to_excel(w, index=False)
                buf.seek(0)
                st.download_button("📥 Exportar Excel", data=buf.getvalue(),
                    file_name=f"{base}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"xls_{base}", use_container_width=True)
            except:
                st.warning("Instale `openpyxl` para exportar Excel.")
        with c2:
            hoje = date.today().strftime("%d/%m/%Y")
            html = (f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{titulo}</title>"
                    f"<style>body{{font-family:Arial,sans-serif;padding:32px;color:#111}}"
                    f"h1{{color:#0f2a5e;border-bottom:2px solid #0f2a5e;padding-bottom:8px}}"
                    f"table{{border-collapse:collapse;width:100%;margin-top:16px}}"
                    f"th{{background:#0f2a5e;color:#fff;padding:10px;text-align:left;font-size:13px}}"
                    f"td{{border:1px solid #e5e7eb;padding:8px;font-size:12px}}"
                    f"tr:nth-child(even){{background:#f9fafb}}"
                    f"p{{color:#6b7280;font-size:13px}}</style></head><body>"
                    f"<h1>🏛️ {titulo}</h1><p>Gerado em: {hoje}</p>"
                    f"{df.to_html(index=False)}</body></html>")
            st.download_button("📄 Exportar HTML/PDF", data=html.encode("utf-8"),
                file_name=f"{base}.html", mime="text/html",
                key=f"pdf_{base}", use_container_width=True)

    t1, t2, t3 = st.tabs(["🎯  Metas", "✅  Ações", "🏢  Secretarias"])
    with t1:
        st.markdown(f'<div class="sec-title">🎯 Metas — {len(df_rel)} registros</div>', unsafe_allow_html=True)
        if not df_rel.empty:
            st.dataframe(df_rel, use_container_width=True, hide_index=True, height=340)
            exportar(df_rel, "metas_prefeitura", "Relatório de Metas — Prefeitura de Viçosa")
        else: st.info("Nenhuma meta cadastrada.")

    with t2:
        st.markdown(f'<div class="sec-title">✅ Ações — {len(df_acoes_r)} registros</div>', unsafe_allow_html=True)
        if not df_acoes_r.empty:
            st.dataframe(df_acoes_r, use_container_width=True, hide_index=True, height=340)
            exportar(df_acoes_r, "acoes_prefeitura", "Relatório de Ações — Prefeitura de Viçosa")
        else: st.info("Nenhuma ação cadastrada.")

    with t3:
        st.markdown(f'<div class="sec-title">🏢 Secretarias — {len(df_sec_r)} registros</div>', unsafe_allow_html=True)
        if not df_sec_r.empty:
            st.dataframe(df_sec_r, use_container_width=True, hide_index=True, height=340)
            exportar(df_sec_r, "secretarias_prefeitura", "Relatório de Secretarias — Prefeitura de Viçosa")
        else: st.info("Nenhuma secretaria cadastrada.")
