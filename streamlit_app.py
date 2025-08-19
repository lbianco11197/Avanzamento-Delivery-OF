import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit.components.v1 import html

st.set_page_config(layout="wide")

# Imposta sfondo bianco e testo nero
st.markdown("""
<style>
/* Impone schema colore chiaro anche se il device è in dark */
:root { color-scheme: light !important; }
@media (prefers-color-scheme: dark) {
  :root { color-scheme: light !important; }
}

/* Contenitore principale, header, sidebar */
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
[data-testid="stSidebar"] {
  background: #fff !important;
  color: #000 !important;
}

/* Testi generali */
html, body, [data-testid="stApp"] { background:#fff !important; color:#000 !important; }

/* Selectbox / multiselect (BaseWeb) */
div[data-baseweb="select"] {
  background:#fff !important;
  color:#000 !important;
}
div[data-baseweb="select"] * { color:#000 !important; }

/* Input, textarea, date input */
input, textarea, select {
  background:#fff !important;
  color:#000 !important;
}

/* Pulsanti */
.stButton > button {
  background:#fff !important;
  color:#000 !important;
  border:1px solid #999 !important;
  border-radius:6px;
}

/* Tabelle: st.dataframe / st.table */
.stDataFrame [role="grid"],
.stTable,
.stDataFrame table,
.stDataFrame th, .stDataFrame td {
  background:#fff !important;
  color:#000 !important;
}

/* Nasconde lo switch tema se presente */
header [data-testid="theme-toggle"] { display:none; }
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

# Normalizza i nomi tecnici:
    df["Tecnico"] = (
        df["Tecnico"]
        .astype(str)                      # forza a stringa
        .str.strip()                      # rimuove spazi iniziali/finali
        .str.replace(r"\s+", " ", regex=True)  # rimuove spazi doppi
        .str.upper()                      # tutto maiuscolo
    )

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

# --- Riepilogo Mensile per Tecnico (aggregato) ---
st.subheader("📆 Riepilogo Mensile per Tecnico")

df_mensile = (
    df_filtrato
    .assign(Data=df_filtrato["MeseNome"])   # usa nome mese come "Data" di raggruppamento
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
