import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide", page_title="Report Resa - Open Fiber")

# --- Stili base chiari ---
st.markdown("""
    <style>
    html, body, [data-testid="stApp"] { background-color: white !important; color: black !important; }
    .stButton > button, .stDownloadButton > button { background-color: white !important; color: black !important; border: 1px solid #ccc !important; border-radius: 6px !important; }
    .stRadio div[role="radiogroup"] label span { color: black !important; font-weight: 500 !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Report Resa - Open Fiber")

st.caption("Fonte: **deliveryopenfiber.xlsx** — filtra **solo** le attività con Descrizione = _Attivazione con Appuntamento_. Resa positiva se **Stato = Espletamento OK**, altrimenti non positiva. Target 75%.")

# --- Caricamento dati ---
DEFAULT_XLSX = "deliveryopenfiber.xlsx"

def load_data(path: str):
    df = pd.read_excel(
        path,
        usecols=["Data Chiusura", "TechnicianName", "Stato", "Descrizione"]
    )
    df = df.rename(columns={
        "Data Chiusura": "Data",
        "TechnicianName": "Tecnico"
    })
    # Considera solo "Attivazione con Appuntamento"
    df = df[df["Descrizione"] == "Attivazione con Appuntamento"].copy()

    # Pulisci date
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"])
    df["DataStr"] = df["Data"].dt.strftime("%d/%m/%Y")

    # Mesi ITA
    mesi_italiani = {
        1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
        5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
        9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
    }
    df["MeseNome"] = df["Data"].dt.month.map(mesi_italiani)

    return df

# Sorgente dati: file locale + (facoltativo) upload
colL, colR = st.columns([1,1])
with colL:
    st.write("**File di lavoro**:", DEFAULT_XLSX)
with colR:
    uploaded = st.file_uploader("Oppure carica un Excel con le stesse colonne", type=["xlsx"])

data_path = DEFAULT_XLSX
if uploaded is not None:
    data_path = uploaded
df = load_data(data_path)

if df.empty:
    st.warning("Nessuna riga valida trovata (verifica che 'Descrizione' contenga 'Attivazione con Appuntamento').")
    st.stop()

st.markdown(f"🗓️ **Dati aggiornati al:** {df['Data'].max().strftime('%d/%m/%Y')}")

# --- Filtri (senza 'Reparto') ---
ordine_mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
               "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
mesi_presenti = [m for m in ordine_mesi if m in df["MeseNome"].unique()]

r1c1, r1c2, r2c1 = st.columns(3)

tmese = r1c1.selectbox("📆 Seleziona un mese", ["Tutti"] + mesi_presenti)
df_tmp = df if tmese == "Tutti" else df[df["MeseNome"] == tmese]

giorni = ["Tutti"] + sorted(df_tmp["DataStr"].dropna().unique(), key=lambda x: datetime.strptime(x, "%d/%m/%Y"))
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

# --- Funzioni calcolo ---
def aggrega(df_in: pd.DataFrame, group_cols):
    if df_in.empty:
        return pd.DataFrame(columns=["Data", "Tecnico", "Impianti gestiti", "Resa"])
    g = df_in.groupby(group_cols)

    def calc(grp: pd.DataFrame):
        gestiti = len(grp)  # tutte le righe (già filtrate per 'Attivazione con Appuntamento')
        positivi = (grp["Stato"] == "Espletamento OK").sum()
        resa = (positivi / gestiti * 100) if gestiti else None
        return pd.Series({
            "Impianti gestiti": gestiti,
            "Resa": resa
        })

    out = g.apply(calc).reset_index()
    # Ordina e formatta
    if "Data" in out.columns and pd.api.types.is_datetime64_any_dtype(out["Data"]):
        out["Data"] = out["Data"].dt.strftime("%d/%m/%Y")
    # Tipi
    out["Impianti gestiti"] = out["Impianti gestiti"].astype("Int64")
    out["Resa"] = out["Resa"].round(0)
    return out

# --- Dettaglio Giornaliero (Data reale) ---
st.subheader("📆 Dettaglio Giornaliero")
df_giornaliero = aggrega(df_filtrato, ["Data", "Tecnico"])

styled_giornaliero = df_giornaliero.style.applymap(
    lambda v: "background-color: #ccffcc" if pd.notna(v) and v >= 75
              else ("background-color: #ff9999" if pd.notna(v) and v < 75 else ""),
    subset=["Resa"]
).format({"Resa": "{:.0f}%"}).hide(axis="index")

st.dataframe(styled_giornaliero, use_container_width=True)

# --- Riepilogo Mensile per Tecnico (Data = MeseNome) ---
st.subheader("📆 Riepilogo Mensile per Tecnico")
df_mensile = aggrega(df_filtrato, ["MeseNome", "Tecnico"]).rename(columns={"MeseNome": "Data"})

styled_mensile = df_mensile.style.applymap(
    lambda v: "background-color: #ccffcc" if pd.notna(v) and v >= 75
              else ("background-color: #ff9999" if pd.notna(v) and v < 75 else ""),
    subset=["Resa"]
).format({"Resa": "{:.0f}%"}).hide(axis="index")

st.dataframe(styled_mensile, use_container_width=True)