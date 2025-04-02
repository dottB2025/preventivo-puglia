import streamlit as st
import pandas as pd
import re
from datetime import datetime
from fpdf import FPDF
import base64

# Carica il font localmente
def carica_font():
    return "DejaVuSans.ttf"

# Caricamento del file Excel con caching
@st.cache_data
def carica_tariffario(percorso="TariffarioRegionePuglia.xlsx"):
    return pd.read_excel(percorso)

# Funzione per generare il preventivo
def genera_preventivo_da_dettato(testo: str, df: pd.DataFrame, aggiungi_prelievo: bool = False) -> str:
    testo = testo.upper().replace("PAI", "")
    testo = testo.replace("-", ",")  # Consente separazione anche con trattino
    codici_input = re.split(r"[,]+", testo)

    codici_validi = [c for c in codici_input if len(c) == 5 and c.isdigit()]
    codici_non_validi = [c for c in codici_input if len(c) != 5 or not c.isdigit()]

    df_codici = df[df["Regionale-Puglia"].astype(str).isin(codici_validi)]
    totale = df_codici["Tariffa-Puglia"].sum()

    righe_dettaglio = [
        f"- {row['Descrizione'].capitalize()} € {row['Tariffa-Puglia']}"
        for _, row in df_codici.iterrows()
    ]

    if aggiungi_prelievo:
        totale += 3.8
        righe_dettaglio.append("- Prelievo ematico € 3.8")

    codici_trovati = df_codici["Regionale-Puglia"].astype(str).tolist()
    codici_non_trovati = [c for c in codici_validi if c not in codici_trovati]
    codici_errati = codici_non_trovati + codici_non_validi
    if codici_errati:
        for c in codici_errati:
            righe_dettaglio.append(f"- codice non trovato: {c}")

    dettaglio = "\n".join(righe_dettaglio)
    data_oggi = datetime.today().strftime('%d/%m/%Y')
    intestazione = "Laboratorio di analisi cliniche MONTEMURRO - Matera"
    intestazione += f"\nPreventivo - data di generazione: {data_oggi}"
    contenuto = f"{intestazione}\n\n1) Preventivo: € {round(totale, 2)}\n2) Dettaglio:\n{dettaglio}"
    return contenuto

# Classe PDF migliorata
class PDF(FPDF):
    def header(self):
        self.set_font("DejaVu", size=14)
        self.set_text_color(0)
        self.cell(0, 10, "Laboratorio di analisi cliniche MONTEMURRO - Matera", ln=True, align="C")
        self.ln(5)

# Funzione per creare PDF con formattazione migliorata

def crea_pdf_unicode(contenuto: str) -> bytes:
    pdf = PDF()
    font_path = carica_font()
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.add_font("DejaVu", "B", font_path, uni=True)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("DejaVu", size=12)

    larghezza_pagina = pdf.w - 2 * pdf.l_margin

    righe = contenuto.split("\n")
    for i, linea in enumerate(righe):
        if i == 1:
            pdf.set_font("DejaVu", style="B", size=11)
            pdf.cell(0, 8, linea, ln=True)
            pdf.ln(3)
        elif i == 3 and "1)" in linea:
            pdf.set_font("DejaVu", style="B", size=12)
            pdf.set_text_color(0, 0, 128)
            pdf.cell(0, 10, linea, ln=True)
            pdf.set_text_color(0)
        elif i == 4 and "2)" in linea:
            pdf.set_font("DejaVu", style="B", size=12)
            pdf.cell(0, 10, linea, ln=True)
        elif linea.strip() == "":
            pdf.ln(4)
        else:
            pdf.set_font("DejaVu", size=11)
            if "€" in linea:
                descrizione, prezzo = linea.rsplit("€", 1)
                pdf.cell(larghezza_pagina * 0.75, 8, descrizione.strip())
                pdf.cell(larghezza_pagina * 0.25, 8, f"€ {prezzo.strip()}", align="R", ln=True)
            else:
                pdf.multi_cell(0, 8, linea)

    return pdf.output(dest='S').encode('latin1')

# Layout Streamlit
st.set_page_config(page_title="Preventivo Sanitario Puglia", layout="centered")
st.title("Preventivo Sanitario - Regione Puglia")

st.markdown("Inserisci i codici regionali separati da virgola o trattino.\n" 
            "Esempio: 12345,23456 - 34567")

# Input manuale
input_codici = st.text_input("Scrivi qui i codici regionali:")
aggiungi_prelievo = st.checkbox("Aggiungi prelievo")

if st.button("Genera Preventivo") or input_codici:
    try:
        risultato_testo = genera_preventivo_da_dettato(input_codici, carica_tariffario(), aggiungi_prelievo)
        st.text_area("Risultato del Preventivo:", risultato_testo, height=300, key="output_area")

        # Pulsante copia testo
        st.download_button(
            label="📋 Copia preventivo (testo)",
            data=risultato_testo,
            file_name="preventivo.txt",
            mime="text/plain"
        )

        # Pulsante esporta PDF
        pdf_bytes = crea_pdf_unicode(risultato_testo)
        b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="preventivo.pdf">⬇️ Esporta come PDF</a>'
        st.markdown(href, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Errore durante la generazione del preventivo: {e}")
