import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import io
from datetime import date

# ═══════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════
CPF_AUTORIZADO = "00000000000"
MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
         "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
TIPOS_SECRETARIA = ["Educação","Saúde","Assistência Social","Obras","Agricultura",
                    "Meio Ambiente","Cultura","Esporte e Lazer","Administração",
                    "Fazenda","Planejamento","Transporte","Outra"]
PRIORIDADES      = ["Baixa","Média","Alta"]
STATUS_META      = ["Não iniciada","Em andamento","Concluída","Atrasada"]
STATUS_ACAO      = ["Pendente","Em Andamento","Concluída"]
STATUS_SEC       = ["Ativa","Inativa"]

COR_PRIO   = {"Baixa":"#22c55e","Média":"#f97316","Alta":"#ef4444"}
COR_STATUS = {"Não iniciada":"#94a3b8","Em andamento":"#3b82f6",
              "Concluída":"#22c55e","Atrasada":"#ef4444",
              "Pendente":"#f97316","Em Andamento":"#3b82f6",
              "Ativa":"#22c55e","Inativa":"#94a3b8"}

# ═══════════════════════════════════════
# BANCO DE DADOS
# ═══════════════════════════════════════
def conectar_db():
    conn = sqlite3.connect('prefeitura_metas.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (cpf TEXT PRIMARY KEY, nome TEXT, senha TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS secretarias (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT,
                  tipo TEXT, secretario TEXT, email TEXT, telefone TEXT,
                  status TEXT DEFAULT 'Ativa', descricao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS metas (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  titulo TEXT, mes TEXT, secretaria_id INTEGER,
                  objetivo TEXT, responsavel TEXT,
                  prioridade TEXT DEFAULT 'Média',
                  status TEXT DEFAULT 'Não iniciada',
                  data_inicio TEXT, prazo_final TEXT,
                  percentual INTEGER DEFAULT 0,
                  indicador TEXT, observacoes TEXT,
                  FOREIGN KEY(secretaria_id) REFERENCES secretarias(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS acoes (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome TEXT, descricao TEXT, responsavel TEXT,
                  prazo TEXT, status TEXT DEFAULT 'Pendente',
                  data_inicio TEXT, percentual INTEGER DEFAULT 0,
                  observacoes TEXT, meta_id INTEGER,
                  FOREIGN KEY(meta_id) REFERENCES metas(id))''')
    conn.commit()
    # Migrações
    for table, cols in [
        ("secretarias", {"tipo":"TEXT","secretario":"TEXT","email":"TEXT",
                         "telefone":"TEXT","status":"TEXT DEFAULT 'Ativa'","descricao":"TEXT"}),
        ("metas", {"objetivo":"TEXT","responsavel":"TEXT","prioridade":"TEXT DEFAULT 'Média'",
                   "status":"TEXT DEFAULT 'Não iniciada'","data_inicio":"TEXT","prazo_final":"TEXT",
                   "percentual":"INTEGER DEFAULT 0","indicador":"TEXT","observacoes":"TEXT"}),
        ("acoes", {"nome":"TEXT","data_inicio":"TEXT","percentual":"INTEGER DEFAULT 0","observacoes":"TEXT"}),
    ]:
        existentes = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
        for col, tipo in cols.items():
            if col not in existentes:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {tipo}")
    conn.commit()
    return conn

# ═══════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════
def parse_date(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return date.today()

def badge(texto, cor):
    return (f'<span style="background:{cor};color:#fff;padding:2px 10px;'
            f'border-radius:20px;font-size:0.72rem;font-weight:600;">{texto}</span>')

def barra_progresso(pct):
    pct = max(0, min(100, int(pct or 0)))
    return (f'<div style="background:#e2e8f0;border-radius:9999px;height:8px;">'
            f'<div style="background:linear-gradient(90deg,#0f2a5e,#1d6b52);'
            f'width:{pct}%;height:8px;border-radius:9999px;"></div></div>'
            f'<small style="color:#64748b">{pct}%</small>')

def kpi(col, cls, val, label):
    col.markdown(f'<div class="kpi-card {cls}"><div class="kpi-value">{val}</div>'
                 f'<div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

def btn_voltar(key):
    """Botão de seta para voltar ao Dashboard — aparece em todas as páginas internas."""
    if st.button("⬅ Voltar ao início", key=f"voltar_{key}"):
        st.session_state.pagina = "dashboard"
        st.rerun()

# ═══════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════
st.set_page_config(
    page_title="Metas — Prefeitura de Viçosa",
    layout="wide", page_icon="🏛️",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════
_def = {"autenticado":False,"pagina":"dashboard",
        "editar_meta_id":None,"editar_sec_id":None,"editar_acao_id":None,
        "del_meta_id":None,"del_acao_id":None,"del_sec_id":None}
for k,v in _def.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ═══════════════════════════════════════
# CSS
# ═══════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.stApp { background-color: #f1f5f9; }

[data-testid="stForm"] {
    background:#fff !important; border-radius:16px !important;
    padding:1.5rem !important; box-shadow:0 2px 10px rgba(0,0,0,0.06) !important;
    border:1px solid #e2e8f0 !important;
}
.kpi-card { background:#fff; border-radius:14px; padding:1.2rem 1.4rem;
            box-shadow:0 2px 10px rgba(0,0,0,0.07); border-left:5px solid; margin-bottom:0.5rem; }
.kpi-value { font-size:2.2rem; font-weight:700; line-height:1.1; }
.kpi-label { font-size:0.72rem; font-weight:600; color:#64748b;
             text-transform:uppercase; letter-spacing:0.6px; margin-top:4px; }
.kpi-blue   { border-color:#0f2a5e; } .kpi-blue   .kpi-value { color:#0f2a5e; }
.kpi-teal   { border-color:#1d6b52; } .kpi-teal   .kpi-value { color:#1d6b52; }
.kpi-sky    { border-color:#3b82f6; } .kpi-sky    .kpi-value { color:#3b82f6; }
.kpi-green  { border-color:#22c55e; } .kpi-green  .kpi-value { color:#22c55e; }
.kpi-orange { border-color:#f97316; } .kpi-orange .kpi-value { color:#f97316; }
.kpi-red    { border-color:#ef4444; } .kpi-red    .kpi-value { color:#ef4444; }
.kpi-gray   { border-color:#94a3b8; } .kpi-gray   .kpi-value { color:#94a3b8; }

.section-title { font-size:1rem; font-weight:700; color:#0f2a5e;
                 margin:1rem 0 0.75rem 0; padding-bottom:0.5rem;
                 border-bottom:2px solid #e2e8f0; }
.row-card { background:#fff; border-radius:10px; padding:0.7rem 1rem;
            margin-bottom:0.4rem; box-shadow:0 1px 4px rgba(0,0,0,0.05);
            border:1px solid #f1f5f9; }

[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(160deg,#0f2a5e 0%,#1a4a8a 60%,#1d6b52 100%);
}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,[data-testid="stSidebar"] .stMarkdown {
    color:rgba(255,255,255,0.9) !important;
}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color:#fff !important; }
[data-testid="stSidebar"] .stButton > button {
    background:rgba(255,255,255,0.12) !important; color:#fff !important;
    border:1px solid rgba(255,255,255,0.25) !important;
    border-radius:8px !important; font-weight:500 !important;
    transition:background 0.2s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background:rgba(255,255,255,0.22) !important;
}
.stButton > button {
    background:linear-gradient(135deg,#0f2a5e,#1d6b52);
    color:#fff; border:none; border-radius:8px;
    padding:0.5rem 1.4rem; font-weight:600;
    transition:box-shadow 0.2s, transform 0.15s;
}
.stButton > button:hover { box-shadow:0 4px 14px rgba(0,0,0,0.22); transform:translateY(-1px); }

.stTabs [data-baseweb="tab-list"] {
    gap:6px; background:#fff; padding:0.4rem 0.6rem;
    border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.06); margin-bottom:1rem;
}
.stTabs [data-baseweb="tab"] { border-radius:8px; padding:0.45rem 1.4rem; font-weight:500; }
.stTabs [aria-selected="true"] {
    background:linear-gradient(135deg,#0f2a5e,#1d6b52) !important; color:#fff !important;
}
.stTextInput input, .stDateInput input {
    border-radius:8px !important; border:1px solid #cbd5e1 !important;
    color:#1e293b !important; background:#fff !important;
}
/* Sidebar sempre aberta e visível */
[data-testid="stSidebar"] {
    min-width: 230px !important; max-width: 230px !important;
    transform: translateX(0) !important; visibility: visible !important;
}
[data-testid="stSidebar"][aria-expanded="false"] {
    transform: translateX(0) !important; min-width: 230px !important;
}
[data-testid="stSidebarCollapseButton"],
button[data-testid="stBaseButton-headerNoPadding"],
section[data-testid="stSidebar"] > div > button,
[data-testid="collapsedControl"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

banco = conectar_db()

# ═══════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════
if not st.session_state.autenticado:
    st.markdown("""<style>
    .stApp { background:linear-gradient(135deg,#0f2a5e 0%,#1a4a8a 55%,#1d6b52 100%) !important; }
    [data-testid="stSidebar"],[data-testid="stDecoration"] { display:none; }
    </style>""", unsafe_allow_html=True)
    _, col, _ = st.columns([1,1.05,1])
    with col:
        st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            c1,c2,c3 = st.columns([1,2,1])
            with c2:
                try:
                    st.image("logo_vicosa.jpg", use_container_width=True)
                except Exception:
                    st.markdown("<div style='text-align:center;font-size:3rem'>🏛️</div>",
                                unsafe_allow_html=True)
            st.markdown("""<div style='text-align:center;margin:0.6rem 0 1.4rem 0;'>
                <h2 style='color:#0f2a5e;font-size:1.35rem;font-weight:700;margin:0 0 6px 0;'>
                    Prefeitura de Viçosa</h2>
                <p style='color:#64748b;font-size:0.82rem;margin:0;'>
                    Sistema de Acompanhamento de Metas Municipais</p>
            </div><hr style='border:none;border-top:1px solid #e2e8f0;margin:0 0 1.4rem 0;'>
            """, unsafe_allow_html=True)
            cpf = st.text_input("CPF (somente números)", max_chars=11, placeholder="00000000000")
            if st.form_submit_button("Entrar →", use_container_width=True):
                if cpf == CPF_AUTORIZADO:
                    st.session_state.autenticado = True
                    st.rerun()
                elif cpf == "":
                    st.warning("Digite seu CPF para continuar.")
                else:
                    st.error("❌ CPF não autorizado.")
            st.markdown("<p style='text-align:center;color:#94a3b8;font-size:0.72rem;margin-top:1.2rem;'>"
                        "© 2025 Prefeitura de Viçosa — Acesso restrito</p>", unsafe_allow_html=True)
    st.stop()

# ═══════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════
with st.sidebar:
    try:
        st.image("logo_vicosa.jpg", use_container_width=True)
    except Exception:
        st.markdown("<div style='font-size:2rem;text-align:center'>🏛️</div>", unsafe_allow_html=True)
    st.markdown("## Prefeitura de Viçosa")
    st.markdown("---")
    for icon, label, key in [
        ("🏠","Dashboard","dashboard"),
        ("🏢","Secretarias","secretarias"),
        ("🎯","Metas","metas"),
        ("✅","Ações","acoes"),
        ("📊","Relatórios","relatorios"),
    ]:
        if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
            st.session_state.pagina = key
            st.rerun()
    st.markdown("---")
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()
    st.caption("Prefeitura de Viçosa © 2025")

st.markdown("<style>.stApp{background:#f1f5f9 !important;}</style>", unsafe_allow_html=True)
pagina = st.session_state.pagina

# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════
if pagina == "dashboard":
    st.markdown("<h1 style='color:#0f2a5e;font-size:1.65rem;font-weight:700;margin:0 0 4px 0;'>"
                "🏠 Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#475569;font-size:0.92rem;'>Visão geral das metas e ações municipais.</p>",
                unsafe_allow_html=True)
    st.divider()

    df_s = pd.read_sql_query("SELECT * FROM secretarias", banco)
    df_m = pd.read_sql_query("SELECT * FROM metas", banco)
    df_a = pd.read_sql_query("SELECT * FROM acoes", banco)

    tot_sec  = len(df_s)
    tot_meta = len(df_m)
    tot_acao = len(df_a)
    concl    = len(df_m[df_m["status"]=="Concluída"])    if not df_m.empty else 0
    andamen  = len(df_m[df_m["status"]=="Em andamento"]) if not df_m.empty else 0
    atras    = len(df_m[df_m["status"]=="Atrasada"])     if not df_m.empty else 0
    pct_ger  = int(df_m["percentual"].mean()) if not df_m.empty and df_m["percentual"].notna().any() else 0

    c1,c2,c3,c4 = st.columns(4)
    kpi(c1,"kpi-blue",  tot_sec,        "Total de Secretarias")
    kpi(c2,"kpi-teal",  tot_meta,       "Total de Metas")
    kpi(c3,"kpi-sky",   tot_acao,       "Total de Ações")
    kpi(c4,"kpi-gray",  f"{pct_ger}%",  "Conclusão Geral")
    st.markdown("<br>", unsafe_allow_html=True)
    c5,c6,c7 = st.columns(3)
    kpi(c5,"kpi-green",  concl,   "Metas Concluídas")
    kpi(c6,"kpi-orange", andamen, "Metas Em Andamento")
    kpi(c7,"kpi-red",    atras,   "Metas Atrasadas")

    if not df_m.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        gc1,gc2 = st.columns(2)
        CORES_S = {"Não iniciada":"#94a3b8","Em andamento":"#3b82f6","Concluída":"#22c55e","Atrasada":"#ef4444"}
        CORES_P = {"Baixa":"#22c55e","Média":"#f97316","Alta":"#ef4444"}

        with gc1:
            st.markdown('<div class="section-title">📊 Metas por Status</div>', unsafe_allow_html=True)
            sc = df_m["status"].value_counts()
            fig,ax = plt.subplots(figsize=(5,3.5)); fig.patch.set_facecolor("white"); ax.set_facecolor("#f8fafc")
            bars = ax.bar(sc.index, sc.values, color=[CORES_S.get(s,"#94a3b8") for s in sc.index],
                          width=0.5, edgecolor="white", linewidth=2)
            for bar,v in zip(bars,sc.values):
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05,
                        str(int(v)), ha="center", va="bottom", fontweight="bold", fontsize=11)
            ax.set_ylabel("Quantidade",fontsize=9,color="#475569")
            for sp in ["top","right"]: ax.spines[sp].set_visible(False)
            ax.spines["left"].set_color("#e2e8f0"); ax.spines["bottom"].set_color("#e2e8f0")
            ax.tick_params(colors="#475569",labelsize=8); ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
            plt.tight_layout(); st.pyplot(fig); plt.close(fig)

        with gc2:
            st.markdown('<div class="section-title">🎯 Metas por Prioridade</div>', unsafe_allow_html=True)
            if "prioridade" in df_m.columns:
                pc = df_m["prioridade"].value_counts()
                if not pc.empty:
                    fig2,ax2 = plt.subplots(figsize=(5,3.5)); fig2.patch.set_facecolor("white")
                    w,t,at = ax2.pie(pc.values, labels=pc.index,
                                     colors=[CORES_P.get(s,"#94a3b8") for s in pc.index],
                                     autopct="%1.0f%%", startangle=90,
                                     wedgeprops={"edgecolor":"white","linewidth":2})
                    for x in t: x.set_fontsize(9)
                    for x in at: x.set_fontsize(9); x.set_fontweight("bold"); x.set_color("white")
                    plt.tight_layout(); st.pyplot(fig2); plt.close(fig2)

# ═══════════════════════════════════════════════════════════════
# SECRETARIAS
# ═══════════════════════════════════════════════════════════════
elif pagina == "secretarias":
    btn_voltar("sec")
    st.markdown("<h1 style='color:#0f2a5e;font-size:1.65rem;font-weight:700;'>🏢 Secretarias</h1>",
                unsafe_allow_html=True)
    st.divider()

    edit_id = st.session_state.editar_sec_id
    edit_d  = None
    if edit_id:
        cur = banco.cursor(); cur.execute("SELECT * FROM secretarias WHERE id=?", (edit_id,))
        r = cur.fetchone()
        if r: edit_d = dict(zip([d[0] for d in cur.description], r))

    aba_l, aba_c = st.tabs(["📋 Listagem", "➕ Nova Secretaria"])

    with aba_l:
        df = pd.read_sql_query("SELECT * FROM secretarias ORDER BY nome", banco)
        if df.empty:
            st.info("Nenhuma secretaria cadastrada. Use a aba **➕ Nova Secretaria**.")
        else:
            f1,f2 = st.columns(2)
            with f1: ft = st.selectbox("Tipo", ["Todos"]+TIPOS_SECRETARIA, key="fs_t")
            with f2: fs = st.selectbox("Status", ["Todos"]+STATUS_SEC, key="fs_s")
            if ft != "Todos": df = df[df["tipo"]==ft]
            if fs != "Todos": df = df[df["status"]==fs]
            st.caption(f"{len(df)} secretaria(s)")
            for _,row in df.iterrows():
                st.markdown('<div class="row-card">', unsafe_allow_html=True)
                c1,c2,c3,c4,c5 = st.columns([3,2,2,1,1])
                with c1:
                    st.markdown(f"**{row['nome']}**  {badge(row.get('tipo') or '—','#0f2a5e')}",
                                unsafe_allow_html=True)
                    st.caption(f"Secretário(a): {row.get('secretario') or '—'}")
                with c2:
                    st.caption(f"📧 {row.get('email') or '—'}")
                    st.caption(f"📞 {row.get('telefone') or '—'}")
                with c3:
                    sc = row.get("status") or "Ativa"
                    st.markdown(badge(sc, COR_STATUS.get(sc,"#94a3b8")), unsafe_allow_html=True)
                    if row.get("descricao"):
                        st.caption(str(row["descricao"])[:60]+"…" if len(str(row["descricao"]))>60 else str(row["descricao"]))
                with c4:
                    if st.button("✏️", key=f"es_{row['id']}"):
                        st.session_state.editar_sec_id = int(row['id']); st.rerun()
                with c5:
                    if st.button("🗑️", key=f"ds_{row['id']}"):
                        st.session_state.del_sec_id = int(row['id'])
                st.markdown('</div>', unsafe_allow_html=True)
                if st.session_state.del_sec_id == int(row['id']):
                    st.warning(f"Excluir **{row['nome']}**?")
                    d1,d2 = st.columns(2)
                    with d1:
                        if st.button("✅ Confirmar", key=f"cds_{row['id']}"):
                            banco.cursor().execute("DELETE FROM secretarias WHERE id=?", (row['id'],))
                            banco.commit(); st.session_state.del_sec_id = None; st.rerun()
                    with d2:
                        if st.button("❌ Cancelar", key=f"cas_{row['id']}"):
                            st.session_state.del_sec_id = None; st.rerun()

    with aba_c:
        if edit_id:
            st.info(f"✏️ Editando: **{edit_d.get('nome','') if edit_d else ''}**")
        with st.form("form_sec"):
            st.markdown("**Dados da Secretaria**")
            fc1,fc2 = st.columns(2)
            with fc1:
                nome_s    = st.text_input("Nome da Secretaria *", value=edit_d.get("nome","") if edit_d else "")
                secret    = st.text_input("Nome do(a) Secretário(a)", value=edit_d.get("secretario","") if edit_d else "")
                email_s   = st.text_input("E-mail", value=edit_d.get("email","") if edit_d else "")
            with fc2:
                ti = TIPOS_SECRETARIA.index(edit_d["tipo"]) if edit_d and edit_d.get("tipo") in TIPOS_SECRETARIA else 12
                tipo_s    = st.selectbox("Tipo da Secretaria", TIPOS_SECRETARIA, index=ti)
                tel_s     = st.text_input("Telefone", value=edit_d.get("telefone","") if edit_d else "")
                si = STATUS_SEC.index(edit_d["status"]) if edit_d and edit_d.get("status") in STATUS_SEC else 0
                stat_s    = st.selectbox("Status", STATUS_SEC, index=si)
            desc_s = st.text_area("Descrição", value=edit_d.get("descricao","") if edit_d else "", height=80)
            lbl = "💾 Atualizar" if edit_id else "💾 Salvar Secretaria"
            if st.form_submit_button(lbl, use_container_width=True):
                if nome_s.strip():
                    cur = banco.cursor()
                    v = (nome_s.strip(),tipo_s,secret,email_s,tel_s,stat_s,desc_s)
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

# ═══════════════════════════════════════════════════════════════
# METAS
# ═══════════════════════════════════════════════════════════════
elif pagina == "metas":
    btn_voltar("met")
    st.markdown("<h1 style='color:#0f2a5e;font-size:1.65rem;font-weight:700;'>🎯 Metas</h1>",
                unsafe_allow_html=True)
    st.divider()

    edit_id = st.session_state.editar_meta_id
    edit_d  = None
    if edit_id:
        cur = banco.cursor(); cur.execute("SELECT * FROM metas WHERE id=?", (edit_id,))
        r = cur.fetchone()
        if r: edit_d = dict(zip([d[0] for d in cur.description], r))

    aba_l, aba_c = st.tabs(["📋 Listagem", "➕ Nova Meta"])

    with aba_l:
        df = pd.read_sql_query('''
            SELECT m.*, s.nome AS sec_nome, s.tipo AS sec_tipo
            FROM metas m LEFT JOIN secretarias s ON m.secretaria_id=s.id
            ORDER BY m.id DESC
        ''', banco)
        if df.empty:
            st.info("Nenhuma meta cadastrada. Use a aba **➕ Nova Meta**.")
        else:
            # Filtros
            mf1,mf2,mf3,mf4 = st.columns(4)
            with mf1:
                opts_sec = ["Todas"]+sorted(df["sec_nome"].dropna().unique().tolist())
                f_sec = st.selectbox("Secretaria", opts_sec, key="fm_sec")
            with mf2: f_st = st.selectbox("Status", ["Todos"]+STATUS_META, key="fm_st")
            with mf3: f_pr = st.selectbox("Prioridade", ["Todas"]+PRIORIDADES, key="fm_pr")
            with mf4: f_mes = st.selectbox("Mês", ["Todos"]+MESES, key="fm_mes")
            mf5,mf6,mf7 = st.columns([2,2,2])
            with mf5:
                opts_tipo = ["Todos"]+TIPOS_SECRETARIA
                f_tipo = st.selectbox("Tipo de Secretaria", opts_tipo, key="fm_tipo")
            with mf6: f_resp = st.text_input("Responsável contém", key="fm_resp")
            with mf7: f_busca = st.text_input("🔍 Pesquisar meta", key="fm_busca")

            if f_sec  != "Todas": df = df[df["sec_nome"]==f_sec]
            if f_st   != "Todos": df = df[df["status"]==f_st]
            if f_pr   != "Todas": df = df[df["prioridade"]==f_pr]
            if f_mes  != "Todos": df = df[df["mes"]==f_mes]
            if f_tipo != "Todos": df = df[df["sec_tipo"]==f_tipo]
            if f_resp:  df = df[df["responsavel"].str.contains(f_resp, case=False, na=False)]
            if f_busca: df = df[df["titulo"].str.contains(f_busca, case=False, na=False)]

            st.caption(f"{len(df)} meta(s) encontrada(s)")

            # Cabeçalho da tabela
            h = st.columns([3,2,1,1,2,1,0.5,0.5])
            for col,txt in zip(h,["TÍTULO","SECRETARIA","PRIORIDADE","STATUS","PROGRESSO","PRAZO","",""]):
                col.markdown(f"<small style='color:#64748b;font-weight:700;'>{txt}</small>",
                             unsafe_allow_html=True)
            st.markdown("<hr style='margin:4px 0 8px 0;border-color:#e2e8f0;'>", unsafe_allow_html=True)

            for _,row in df.iterrows():
                pct  = int(row.get("percentual") or 0)
                prio = row.get("prioridade") or "Média"
                stm  = row.get("status") or "Não iniciada"
                c1,c2,c3,c4,c5,c6,c7,c8 = st.columns([3,2,1,1,2,1,0.5,0.5])
                with c1:
                    st.markdown(f"**{row['titulo']}**")
                    if row.get("responsavel"): st.caption(f"👤 {row['responsavel']}")
                with c2: st.write(row.get("sec_nome") or "—")
                with c3: st.markdown(badge(prio, COR_PRIO.get(prio,"#94a3b8")), unsafe_allow_html=True)
                with c4: st.markdown(badge(stm,  COR_STATUS.get(stm,"#94a3b8")),  unsafe_allow_html=True)
                with c5: st.markdown(barra_progresso(pct), unsafe_allow_html=True)
                with c6: st.caption(row.get("prazo_final") or row.get("mes") or "—")
                with c7:
                    if st.button("✏️", key=f"em_{row['id']}"):
                        st.session_state.editar_meta_id = int(row['id']); st.rerun()
                with c8:
                    if st.button("🗑️", key=f"dm_{row['id']}"):
                        st.session_state.del_meta_id = int(row['id'])

                if st.session_state.del_meta_id == int(row['id']):
                    st.warning(f"Excluir **{row['titulo']}**?")
                    d1,d2 = st.columns(2)
                    with d1:
                        if st.button("✅ Confirmar", key=f"cdm_{row['id']}"):
                            banco.cursor().execute("DELETE FROM metas WHERE id=?", (row['id'],))
                            banco.commit(); st.session_state.del_meta_id = None; st.rerun()
                    with d2:
                        if st.button("❌ Cancelar", key=f"cam_{row['id']}"):
                            st.session_state.del_meta_id = None; st.rerun()
                st.markdown("<hr style='margin:4px 0;border:none;border-top:1px solid #f1f5f9;'>",
                            unsafe_allow_html=True)

    with aba_c:
        if edit_id: st.info(f"✏️ Editando: **{edit_d.get('titulo','') if edit_d else ''}**")
        df_sec2 = pd.read_sql_query("SELECT id,nome FROM secretarias", banco)
        with st.form("form_meta"):
            st.markdown("**Dados da Meta**")
            mc1,mc2 = st.columns(2)
            with mc1:
                titulo  = st.text_input("Título da Meta *", value=edit_d.get("titulo","") if edit_d else "")
                obj     = st.text_area("Objetivo da Meta", value=edit_d.get("objetivo","") if edit_d else "", height=80)
                resp    = st.text_input("Responsável pela Meta", value=edit_d.get("responsavel","") if edit_d else "")
                mes_m   = st.selectbox("Mês de Referência", MESES,
                            index=MESES.index(edit_d["mes"]) if edit_d and edit_d.get("mes") in MESES else 0,
                            key="mes_m")
            with mc2:
                sec_id_m = None
                if not df_sec2.empty:
                    nomes = df_sec2["nome"].tolist()
                    sd = 0
                    if edit_d and edit_d.get("secretaria_id"):
                        mt = df_sec2[df_sec2["id"]==edit_d["secretaria_id"]]
                        if not mt.empty: sd = nomes.index(mt.iloc[0]["nome"])
                    sel = st.selectbox("Secretaria Responsável", nomes, index=sd)
                    sec_id_m = int(df_sec2[df_sec2["nome"]==sel]["id"].values[0])
                else:
                    st.warning("⚠️ Cadastre uma secretaria antes.")
                pi = PRIORIDADES.index(edit_d["prioridade"]) if edit_d and edit_d.get("prioridade") in PRIORIDADES else 1
                prio_m = st.selectbox("Prioridade", PRIORIDADES, index=pi)
                si = STATUS_META.index(edit_d["status"]) if edit_d and edit_d.get("status") in STATUS_META else 0
                stat_m = st.selectbox("Status", STATUS_META, index=si)
                pct_m  = st.slider("Percentual de Conclusão (%)", 0, 100,
                            value=int(edit_d.get("percentual") or 0) if edit_d else 0)
            mc3,mc4 = st.columns(2)
            with mc3:
                di_m  = st.date_input("Data de Início",
                            value=parse_date(edit_d.get("data_inicio")) if edit_d else date.today())
                ind_m = st.text_input("Indicador de Sucesso", value=edit_d.get("indicador","") if edit_d else "")
            with mc4:
                pf_m  = st.date_input("Prazo Final",
                            value=parse_date(edit_d.get("prazo_final")) if edit_d else date.today())
                obs_m = st.text_area("Observações", value=edit_d.get("observacoes","") if edit_d else "", height=80)

            if st.form_submit_button("💾 Atualizar Meta" if edit_id else "💾 Salvar Meta",
                                     use_container_width=True):
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

# ═══════════════════════════════════════════════════════════════
# AÇÕES
# ═══════════════════════════════════════════════════════════════
elif pagina == "acoes":
    btn_voltar("acao")
    st.markdown("<h1 style='color:#0f2a5e;font-size:1.65rem;font-weight:700;'>✅ Ações</h1>",
                unsafe_allow_html=True)
    st.divider()

    edit_id = st.session_state.editar_acao_id
    edit_d  = None
    if edit_id:
        cur = banco.cursor(); cur.execute("SELECT * FROM acoes WHERE id=?", (edit_id,))
        r = cur.fetchone()
        if r: edit_d = dict(zip([d[0] for d in cur.description], r))

    aba_l, aba_c = st.tabs(["📋 Listagem", "➕ Nova Ação"])

    with aba_l:
        df = pd.read_sql_query('''
            SELECT a.*, m.titulo AS meta_titulo, s.nome AS sec_nome
            FROM acoes a
            LEFT JOIN metas m ON a.meta_id=m.id
            LEFT JOIN secretarias s ON m.secretaria_id=s.id
            ORDER BY a.id DESC
        ''', banco)
        if df.empty:
            st.info("Nenhuma ação cadastrada. Use a aba **➕ Nova Ação**.")
        else:
            af1,af2 = st.columns(2)
            with af1: f_sta = st.selectbox("Status", ["Todos"]+STATUS_ACAO, key="fa_st")
            with af2:
                opts_m = ["Todas"]+sorted(df["meta_titulo"].dropna().unique().tolist())
                f_meta = st.selectbox("Meta", opts_m, key="fa_meta")
            if f_sta  != "Todos": df = df[df["status"]==f_sta]
            if f_meta != "Todas": df = df[df["meta_titulo"]==f_meta]
            st.caption(f"{len(df)} ação(ões)")

            for _,row in df.iterrows():
                pct = int(row.get("percentual") or 0)
                sta = row.get("status") or "Pendente"
                nome_a = row.get("nome") or row.get("descricao") or "Ação sem nome"
                c1,c2,c3,c4,c5 = st.columns([3,2,1,0.5,0.5])
                with c1:
                    st.markdown(f"**{nome_a}**")
                    st.caption(f"Meta: {row.get('meta_titulo') or '—'}  |  👤 {row.get('responsavel') or '—'}")
                    if row.get("descricao") and row.get("nome"):
                        st.caption(row["descricao"][:80])
                with c2: st.markdown(barra_progresso(pct), unsafe_allow_html=True)
                with c3:
                    st.markdown(badge(sta, COR_STATUS.get(sta,"#94a3b8")), unsafe_allow_html=True)
                    st.caption(f"Prazo: {row.get('prazo') or '—'}")
                with c4:
                    if st.button("✏️", key=f"ea_{row['id']}"):
                        st.session_state.editar_acao_id = int(row['id']); st.rerun()
                with c5:
                    if st.button("🗑️", key=f"da_{row['id']}"):
                        st.session_state.del_acao_id = int(row['id'])

                if st.session_state.del_acao_id == int(row['id']):
                    st.warning(f"Excluir **{nome_a}**?")
                    d1,d2 = st.columns(2)
                    with d1:
                        if st.button("✅ Confirmar", key=f"cda_{row['id']}"):
                            banco.cursor().execute("DELETE FROM acoes WHERE id=?", (row['id'],))
                            banco.commit(); st.session_state.del_acao_id = None; st.rerun()
                    with d2:
                        if st.button("❌ Cancelar", key=f"caa_{row['id']}"):
                            st.session_state.del_acao_id = None; st.rerun()
                st.markdown("<hr style='margin:4px 0;border:none;border-top:1px solid #f1f5f9;'>",
                            unsafe_allow_html=True)

    with aba_c:
        if edit_id:
            n = (edit_d.get("nome") or edit_d.get("descricao","")) if edit_d else ""
            st.info(f"✏️ Editando: **{n}**")
        df_metas2 = pd.read_sql_query("SELECT id,titulo FROM metas", banco)
        with st.form("form_acao"):
            st.markdown("**Dados da Ação**")
            ac1,ac2 = st.columns(2)
            with ac1:
                nome_a  = st.text_input("Nome da Ação *",
                            value=edit_d.get("nome","") if edit_d else "")
                desc_a  = st.text_area("Descrição",
                            value=edit_d.get("descricao","") if edit_d else "", height=80)
                resp_a  = st.text_input("Responsável",
                            value=edit_d.get("responsavel","") if edit_d else "")
            with ac2:
                sai = STATUS_ACAO.index(edit_d["status"]) if edit_d and edit_d.get("status") in STATUS_ACAO else 0
                stat_a = st.selectbox("Status", STATUS_ACAO, index=sai)
                pct_a  = st.slider("Percentual de Conclusão (%)", 0, 100,
                            value=int(edit_d.get("percentual") or 0) if edit_d else 0)
                di_a   = st.date_input("Data de Início",
                            value=parse_date(edit_d.get("data_inicio")) if edit_d else date.today())
                pf_a   = st.date_input("Prazo de Conclusão",
                            value=parse_date(edit_d.get("prazo")) if edit_d else date.today())
            obs_a = st.text_area("Observações",
                        value=edit_d.get("observacoes","") if edit_d else "", height=60)
            meta_id_a = None
            if not df_metas2.empty:
                nms = df_metas2["titulo"].tolist(); md = 0
                if edit_d and edit_d.get("meta_id"):
                    mt = df_metas2[df_metas2["id"]==edit_d["meta_id"]]
                    if not mt.empty: md = nms.index(mt.iloc[0]["titulo"])
                sel_m = st.selectbox("Vincular à Meta", nms, index=md)
                meta_id_a = int(df_metas2[df_metas2["titulo"]==sel_m]["id"].values[0])
            else:
                st.warning("⚠️ Cadastre uma meta antes.")

            if st.form_submit_button("💾 Atualizar Ação" if edit_id else "💾 Salvar Ação",
                                     use_container_width=True):
                if nome_a.strip() and meta_id_a:
                    cur = banco.cursor()
                    v = (nome_a.strip(),desc_a,resp_a,str(pf_a),stat_a,str(di_a),pct_a,obs_a,meta_id_a)
                    if edit_id:
                        cur.execute("""UPDATE acoes SET nome=?,descricao=?,responsavel=?,prazo=?,
                            status=?,data_inicio=?,percentual=?,observacoes=?,meta_id=?
                            WHERE id=?""", v+(edit_id,))
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

# ═══════════════════════════════════════════════════════════════
# RELATÓRIOS
# ═══════════════════════════════════════════════════════════════
elif pagina == "relatorios":
    btn_voltar("rel")
    st.markdown("<h1 style='color:#0f2a5e;font-size:1.65rem;font-weight:700;'>📊 Relatórios</h1>",
                unsafe_allow_html=True)
    st.divider()

    df_rel = pd.read_sql_query('''
        SELECT m.titulo AS "Meta", s.nome AS "Secretaria", s.tipo AS "Tipo",
               m.responsavel AS "Responsável", m.prioridade AS "Prioridade",
               m.status AS "Status", m.percentual AS "Conclusão (%)",
               m.data_inicio AS "Início", m.prazo_final AS "Prazo Final",
               m.mes AS "Mês", m.objetivo AS "Objetivo", m.observacoes AS "Observações"
        FROM metas m LEFT JOIN secretarias s ON m.secretaria_id=s.id ORDER BY m.id DESC
    ''', banco)
    df_acoes_r = pd.read_sql_query('''
        SELECT a.nome AS "Ação", a.descricao AS "Descrição", m.titulo AS "Meta",
               s.nome AS "Secretaria", a.responsavel AS "Responsável",
               a.status AS "Status", a.percentual AS "Conclusão (%)",
               a.data_inicio AS "Início", a.prazo AS "Prazo", a.observacoes AS "Observações"
        FROM acoes a LEFT JOIN metas m ON a.meta_id=m.id
        LEFT JOIN secretarias s ON m.secretaria_id=s.id ORDER BY a.id DESC
    ''', banco)
    df_sec_r = pd.read_sql_query(
        "SELECT nome AS 'Secretaria', tipo AS 'Tipo', secretario AS 'Secretário(a)',"
        " email AS 'E-mail', telefone AS 'Telefone', status AS 'Status',"
        " descricao AS 'Descrição' FROM secretarias ORDER BY nome", banco)

    def botoes_exportar(df, base, titulo):
        e1,e2 = st.columns(2)
        with e1:
            buf = io.BytesIO()
            try:
                with pd.ExcelWriter(buf, engine='openpyxl') as w:
                    df.to_excel(w, index=False)
                buf.seek(0)
                st.download_button("📥 Exportar Excel", data=buf.getvalue(),
                    file_name=f"{base}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"xls_{base}")
            except Exception:
                st.warning("Execute `pip install openpyxl` para habilitar Excel.")
        with e2:
            hoje = date.today().strftime("%d/%m/%Y")
            html = (f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{titulo}</title>"
                    f"<style>body{{font-family:Arial;padding:24px}}h1{{color:#0f2a5e}}"
                    f"table{{border-collapse:collapse;width:100%}}"
                    f"th{{background:#0f2a5e;color:#fff;padding:8px;text-align:left}}"
                    f"td{{border:1px solid #ddd;padding:6px}}"
                    f"tr:nth-child(even){{background:#f8f9fa}}</style></head><body>"
                    f"<h1>{titulo}</h1><p>Gerado em: {hoje}</p>{df.to_html(index=False)}</body></html>")
            st.download_button("📄 Exportar PDF (HTML)", data=html.encode("utf-8"),
                file_name=f"{base}.html", mime="text/html", key=f"pdf_{base}")

    t1,t2,t3 = st.tabs(["🎯 Metas","✅ Ações","🏢 Secretarias"])
    with t1:
        st.markdown(f'<div class="section-title">🎯 Metas ({len(df_rel)} registros)</div>',
                    unsafe_allow_html=True)
        if not df_rel.empty:
            st.dataframe(df_rel, use_container_width=True, hide_index=True, height=350)
            botoes_exportar(df_rel, "metas_prefeitura", "Relatório de Metas — Prefeitura de Viçosa")
        else:
            st.info("Nenhuma meta cadastrada.")
    with t2:
        st.markdown(f'<div class="section-title">✅ Ações ({len(df_acoes_r)} registros)</div>',
                    unsafe_allow_html=True)
        if not df_acoes_r.empty:
            st.dataframe(df_acoes_r, use_container_width=True, hide_index=True, height=350)
            botoes_exportar(df_acoes_r, "acoes_prefeitura", "Relatório de Ações — Prefeitura de Viçosa")
        else:
            st.info("Nenhuma ação cadastrada.")
    with t3:
        st.markdown(f'<div class="section-title">🏢 Secretarias ({len(df_sec_r)} registros)</div>',
                    unsafe_allow_html=True)
        if not df_sec_r.empty:
            st.dataframe(df_sec_r, use_container_width=True, hide_index=True, height=350)
            botoes_exportar(df_sec_r, "secretarias_prefeitura", "Relatório de Secretarias — Prefeitura de Viçosa")
        else:
            st.info("Nenhuma secretaria cadastrada.")
