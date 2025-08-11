import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide", page_title="Avanzamento Produzione Delivery - Euroirte s.r.l.")

# --- Stili base chiari ---
st.markdown("""
    <style>
    html, body, [data-testid="stApp"] { background-color: white !important; color: black !important; }
    .stButton > button, .stLinkButton > a, .stDownloadButton > button { background-color: white !important; color: black !important; border: 1px solid #ccc !important; border-radius: 6px !important; }
    .stRadio div[role="radiogroup"] label span { color: black !important; font-weight: 500 !important; }
    </style>
""", unsafe_allow_html=True)

# --- Titolo / Branding ---
st.title("📊 Avanzamento Produzione Delivery - Euroirte s.r.l.")
st.image("LogoEuroirte.jpg", width=180)
st.link_button("🏠 Torna alla Home", url="https://homeeuroirte.streamlit.app/")

st.caption(
    "Fonte: **deliveryopenfiber.xlsx** — Considera **solo** le righe con "
    "`Descrizione = Attivazione con Appuntamento`. "
    "• **Impianti gestiti** = totale attività per Tecnico • "
    "**Impianti espletati** = quante con `Stato = Espletamento OK` • "
    "Target semaforo 75%."
)

# --- Caricamento dati dal repo ---
def load_data():
    df_raw = pd.read_excel("deliveryopenfiber.xlsx")

    # Mappa nomi colonne reali -> standard
    col_map = {}

    # Data Chiusura
    for c in df_raw.columns:
        if c.strip().lower() == "data chiusura":
            col_map[c] = "Data"
            break

    # Tecnico
    for cand in ["Tecnico (TechnicianName)", "TechnicianName", "Tecnico"]:
        if cand in df_raw.columns:
            col_map[cand] = "Tecnico"
            break

    # Stato / Descrizione
    if "Stato" in df_raw.columns:
        col_map["Stato"] = "Stato"
    if "Descrizione" in df_raw.columns:
        col_map["Descrizione"] = "Descrizione"

    missing = {"Data", "Tecnico", "Stato", "Descrizione"} - set(col_map.values())
    if missing:
        st.error("Colonne mancanti nel file Excel: " + ", ".join(sorted(missing)))
        st.stop()

    df = df_raw.rename(columns=col_map)[["Data", "Tecnico", "Stato", "Descrizione"]]

    # Solo Attivazione con Appuntamento
    df = df[df["Descrizione"] == "Attivazione con Appuntamento"].copy()

    # Parse date (accetta dd/mm/yyyy hh:mm)
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["Data"])
    df["DataStr"] = df["Data"].dt.strftime("%d/%m/%Y")

    mesi_italiani = {
        1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
        5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
        9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
    }
    df["MeseNome"] = df["Data"].dt.month.map(mesi_italiani)
    return df

df = load_data()
if df.empty:
    st.warning("Nessuna riga valida trovata. Verifica che 'Descrizione' sia 'Attivazione con Appuntamento'.")
    st.stop()

st.markdown(f"🗓️ **Dati aggiornati al:** {df['Data'].max().strftime('%d/%m/%Y')}")

# --- Filtri (mese/giorno/tecnico) ---
ordine_mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
               "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
mesi_presenti = [m for m in ordine_mesi if m in df["MeseNome"].unique()]

r1c1, r1c2 = st.columns(2)
r2c1, = st.columns(1)

tmese = r1c1.selectbox("📆 Seleziona un mese", ["Tutti"] + mesi_presenti)
df_tmp = df if tmese == "Tutti" else df[df["MeseNome"] == tmese]

giorni = ["Tutti"] + sorted(
    pd.Series(df_tmp["DataStr"]).dropna().unique(),
    key=lambda x: datetime.strptime(x, "%d/%m/%Y")
)
giorno_sel = r1c2.selectbox("📆 Seleziona un giorno", giorni)

# >>> FIX qui: forziamo una Series e puliamo i NaN
tec_series = pd.Series(df_tmp["Tecnico"], dtype="object")
tecnici = ["Tutti"] + sorted(tec_series.dropna().astype(str).unique())
tecnico_sel = r2c1.selectbox("🧑‍🔧 Seleziona un tecnico", tecnici)

# --- Applica filtri ---
df_filtrato = df.copy()
if tmese != "Tutti":
    df_filtrato = df_filtrato[df_filtrato["MeseNome"] == tmese]
if giorno_sel != "Tutti":
    df_filtrato = df_filtrato[df_filtrato["DataStr"] == giorno_sel]
if tecnico_sel != "Tutti":
    df_filtrato = df_filtrato[df_filtrato["Tecnico"] == tecnico_sel]

# --- Aggregazione ---
def aggrega(df_in: pd.DataFrame, group_cols):
    if df_in.empty:
        return pd.DataFrame(columns=["Data", "Tecnico", "Impianti gestiti", "Impianti espletati", "Resa"])
    g = df_in.groupby(group_cols)

    def calc(grp: pd.DataFrame):
        gestiti = len(grp)
        espletati = (grp["Stato"] == "Espletamento OK").sum()
        resa = (espletati / gestiti * 100) if gestiti else None
        return pd.Series({
            "Impianti gestiti": gestiti,
            "Impianti espletati": espletati,
            "Resa": resa
        })

    out = g.apply(calc).reset_index()

    # Data in formato gg/mm/aaaa se datetime
    if "Data" in out.columns and pd.api.types.is_datetime64_any_dtype(out["Data"]):
        out["Data"] = out["Data"].dt.strftime("%d/%m/%Y")

    out = out[["Data", "Tecnico", "Impianti gestiti", "Impianti espletati", "Resa"]]
    out["Impianti gestiti"] = out["Impianti gestiti"].astype("Int64")
    out["Impianti espletati"] = out["Impianti espletati"].astype("Int64")
    out["Resa"] = out["Resa"].round(0)
    return out

# --- Dettaglio Giornaliero ---
st.subheader("📆 Dettaglio Giornaliero")
df_giornaliero = aggrega(df_filtrato, ["Data", "Tecnico"])
styled_giornaliero = (
    df_giornaliero.style
    .applymap(lambda v: "background-color: #ccffcc" if pd.notna(v) and v >= 75 else ("background-color: #ff9999" if pd.notna(v) and v < 75 else ""), subset=["Resa"])
    .format({"Resa": "{:.0f}%"})
    .hide(axis="index")
)
st.dataframe(styled_giornaliero, use_container_width=True)

# --- Riepilogo Mensile per Tecnico ---
st.subheader("📆 Riepilogo Mensile per Tecnico")
df_mensile_raw = df_filtrato.copy()
df_mensile_raw["Data"] = df_mensile_raw["MeseNome"]
df_mensile = aggrega(df_mensile_raw, ["Data", "Tecnico"])
styled_mensile = (
    df_mensile.style
    .applymap(lambda v: "background-color: #ccffcc" if pd.notna(v) and v >= 75 else ("background-color: #ff9999" if pd.notna(v) and v < 75 else ""), subset=["Resa"])
    .format({"Resa": "{:.0f}%"})
    .hide(axis="index")
)
st.dataframe(styled_mensile, use_container_width=True)
