import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit.components.v1 import html
import base64
from pathlib import Path

def set_page_background(image_path: str):
    """Imposta un'immagine di sfondo full-screen come background dell'app Streamlit."""
    p = Path(image_path)
    if not p.exists():
        st.warning(f"Background non trovato: {image_path}")
        return
    encoded = base64.b64encode(p.read_bytes()).decode()
    css = f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background: url("data:image/png;base64,{encoded}") center/cover no-repeat fixed;
    }}
    [data-testid="stHeader"], [data-testid="stSidebar"] {{
        background-color: rgba(255,255,255,0.0) !important;
    }}
    html, body, [data-testid="stApp"] {{
        color: #0b1320 !important;
    }}
    .stDataFrame, .stTable, .stSelectbox div[data-baseweb="select"],
    .stTextInput, .stNumberInput, .stDateInput, .stMultiSelect,
    .stRadio, .stCheckbox, .stSlider, .stFileUploader, .stTextArea {{
        background-color: rgba(255,255,255,0.88) !important;
        border-radius: 10px;
        backdrop-filter: blur(0.5px);
    }}
    .stDataFrame table, .stDataFrame th, .stDataFrame td {{
        color: #0b1320 !important;
        background-color: rgba(255,255,255,0.0) !important;
    }}
    .stButton > button, .stDownloadButton > button, .stLinkButton > a {{
        background-color: #ffffff !important;
        color: #0b1320 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

st.set_page_config(layout="wide")
set_page_background("sfondo.png")  # 👈 nome del file PNG che vuoi usare come sfondo

# --- Titolo ---
st.title("📊 Avanzamento Produzione Delivery OF - Euroirte s.r.l.")

# Intestazione con logo e bottone
# Logo in alto
st.image("LogoEuroirte.png", width=180)

# Bottone sotto il logo
st.link_button("🏠 Torna alla Home", url="https://homeeuroirte.streamlit.app/")

def pulisci_tecnici(df):
    """Rimuove righe senza tecnico e normalizza i nomi"""
    df["Tecnico"] = (
        df["Tecnico"]
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.upper()
    )
    # Esclude righe vuote o con 'NAN'
    df = df[df["Tecnico"].notna() & (df["Tecnico"] != "") & (df["Tecnico"] != "NAN")]
    return df
  
# --- Caricamento dati dal file nel repo ---
def load_data():
    df = pd.read_excel(
        "deliveryopenfiber.xlsx",
        usecols=["Data Chiusura", "Tecnico", "Stato", "Descrizione"]
    )
    df = df.rename(columns={
        "Data Chiusura": "Data",
        "Tecnico": "Tecnico"
    })
    df = df[df["Descrizione"] == "Attivazione con Appuntamento"].copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["Data"])
    df["DataStr"] = df["Data"].dt.strftime("%d/%m/%Y")
    df = pulisci_tecnici(df)  
  
    mesi_italiani = {
        1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
        5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
        9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
    }
    df["MeseNome"] = df["Data"].dt.month.map(mesi_italiani)
    return df
   

df = load_data()
if df.empty:
    st.warning("Nessuna riga valida trovata.")
    st.stop()

st.markdown(f"🗓️ **Dati aggiornati al:** {df['Data'].max().strftime('%d/%m/%Y')}")

# --- Filtri ---
ordine_mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
               "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
mesi_presenti = [m for m in ordine_mesi if m in df["MeseNome"].unique()]

r1c1, r1c2 = st.columns(2)
r2c1, = st.columns(1)

tmese = r1c1.selectbox("📆 Seleziona un mese", ["Tutti"] + mesi_presenti)
df_tmp = df if tmese == "Tutti" else df[df["MeseNome"] == tmese]

giorni = ["Tutti"] + sorted(
    df_tmp["DataStr"].dropna().unique(),
    key=lambda x: datetime.strptime(x, "%d/%m/%Y")
)
giorno_sel = r1c2.selectbox("📆 Seleziona un giorno", giorni)

tecnici = ["Tutti"] + sorted(df_tmp["Tecnico"].dropna().unique())
tecnico_sel = r2c1.selectbox("🧑‍🔧 Seleziona un tecnico", tecnici)

# --- Applica filtri ---
df_filtrato = df.copy()
if tmese != "Tutti":
    df_filtrato = df_filtrato[df_filtrato["MeseNome"] == tmese]
if giorno_sel != "Tutti":
    df_filtrato = df_filtrato[df_filtrato["DataStr"] == giorno_sel]
if tecnico_sel != "Tutti":
    df_filtrato = df_filtrato[df_filtrato["Tecnico"] == tecnico_sel]

# 👇 Base per il riepilogo mensile: applica SOLO mese e tecnico, NON il giorno
df_month_base = df.copy()
if tmese != "Tutti":
    df_month_base = df_month_base[df_month_base["MeseNome"] == tmese]
if tecnico_sel != "Tutti":
    df_month_base = df_month_base[df_month_base["Tecnico"] == tecnico_sel]

# 🆕 Normalizzazione della data (qui!)
df_filtrato["Data"] = pd.to_datetime(df_filtrato["Data"], errors="coerce", dayfirst=True)
df_filtrato["Data"] = df_filtrato["Data"].dt.normalize()

# --- Aggregazione ---
def aggrega(df_in, group_cols):
    if df_in.empty:
        return pd.DataFrame(columns=["Data", "Tecnico", "Impianti gestiti", "Impianti espletati", "Resa"])
    g = df_in.groupby(group_cols)
    def calc(grp):
        gestiti = len(grp)
        espletati = (grp["Stato"] == "Espletamento OK").sum()
        resa = (espletati / gestiti * 100) if gestiti else None
        return pd.Series({
            "Impianti gestiti": gestiti,
            "Impianti espletati": espletati,
            "Resa": resa
        })
    out = g.apply(calc).reset_index()
    if "Data" in out.columns and pd.api.types.is_datetime64_any_dtype(out["Data"]):
        out["Data"] = out["Data"].dt.strftime("%d/%m/%Y")
    out["Impianti gestiti"] = out["Impianti gestiti"].astype("Int64")
    out["Impianti espletati"] = out["Impianti espletati"].astype("Int64")
    out["Resa"] = out["Resa"].round(0)
    return out

# --- Dettaglio Giornaliero (aggregato) ---
st.subheader("📆 Dettaglio Giornaliero")

df_giornaliero = (
    df_filtrato
    .groupby(["Data", "Tecnico"], as_index=False)
    .agg(
        **{
            "Impianti gestiti": ("Descrizione", "size"),
            "Impianti espletati": ("Stato", lambda s: (s == "Espletamento OK").sum()),
        }
    )
)

df_giornaliero["Resa"] = (
    df_giornaliero["Impianti espletati"] / df_giornaliero["Impianti gestiti"] * 100
).round(0)

# formato data gg/mm/aaaa
df_giornaliero["Data"] = df_giornaliero["Data"].dt.strftime("%d/%m/%Y")

st.dataframe(
    df_giornaliero.style
    .applymap(
        lambda v: "background-color: #ccffcc" if pd.notna(v) and v >= 75
        else ("background-color: #ff9999" if pd.notna(v) and v < 75 else ""),
        subset=["Resa"]
    )
    .format({"Resa": "{:.0f}%"} )
    .hide(axis="index"),
    use_container_width=True
)

# --- Riepilogo Mensile per Tecnico (INDIPENDENTE dal giorno) ---
st.subheader("📆 Riepilogo Mensile per Tecnico")

df_mensile = (
    df_month_base
    .assign(Data=df_month_base["MeseNome"])  # Data = nome mese
    .groupby(["Data", "Tecnico"], as_index=False)
    .agg(
        **{
            "Impianti gestiti": ("Descrizione", "size"),
            "Impianti espletati": ("Stato", lambda s: (s == "Espletamento OK").sum()),
        }
    )
)

df_mensile["Resa"] = (
    df_mensile["Impianti espletati"] / df_mensile["Impianti gestiti"] * 100
).round(0)

st.dataframe(
    df_mensile.style
    .applymap(
        lambda v: "background-color: #ccffcc" if pd.notna(v) and v >= 75
        else ("background-color: #ff9999" if pd.notna(v) and v < 75 else ""),
        subset=["Resa"]
    )
    .format({"Resa": "{:.0f}%"} )
    .hide(axis="index"),
    use_container_width=True
)
