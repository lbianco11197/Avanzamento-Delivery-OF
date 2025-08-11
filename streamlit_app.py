import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(layout="wide")

#imposta sfondo sempre bianco e testi neri
st.markdown("""
<style>
/* Sfondo generale bianco e testo nero */
html, body, [data-testid="stApp"] {
    background-color: white !important;
    color: black !important;
}

/* Titoli, markdown e testi */
h1, h2, h3, h4, h5, h6, p, span, div, label {
    color: black !important;
}

/* Radio button etichette */
div[data-baseweb="radio"] label {
    color: black !important;
    font-weight: 600 !important;
}

/* Input e selezioni */
input, textarea, select {
    background-color: white !important;
    color: black !important;
}

/* Pulsanti */
button[kind="primary"], button[kind="secondary"], .stButton > button {
    background-color: white !important;
    color: black !important;
    border: 1px solid #999 !important;
    border-radius: 6px;
}

/* Pulsanti al passaggio del mouse */
button[kind="primary"]:hover, button[kind="secondary"]:hover, .stButton > button:hover {
    background-color: #f0f0f0 !important;
    color: black !important;
}

/* Dataframe */
.css-1d391kg, .stDataFrame, .css-1m3z7sd {
    color: black !important;
    background-color: white !important;
}

/* Riduzione padding su mobile */
@media only screen and (max-width: 768px) {
    .stRadio > div {
        flex-direction: row !important;
        gap: 1rem;
        justify-content: space-around;
    }
    .stRadio label {
        font-size: 14px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# --- Titolo ---
st.title("📊 Avanzamento Produzione Delivery OF - Euroirte s.r.l.")

# Intestazione con logo e bottone
# Logo in alto
st.image("LogoEuroirte.jpg", width=180)

# Bottone sotto il logo
st.link_button("🏠 Torna alla Home", url="https://homeeuroirte.streamlit.app/")


# --- Caricamento dati dal file nel repo ---
def load_data():
    df = pd.read_excel(
        "deliveryopenfiber.xlsx",
        usecols=["Data Chiusura", "Tecnico (TechnicianName)", "Stato", "Descrizione"]
    )
    df = df.rename(columns={
        "Data Chiusura": "Data",
        "Tecnico (TechnicianName)": "Tecnico"
    })
    df = df[df["Descrizione"] == "Attivazione con Appuntamento"].copy()
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
