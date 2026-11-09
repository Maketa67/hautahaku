import streamlit as st
import openpyxl
from PIL import Image, ImageDraw
import os
import io
import qrcode

# Sivun asetukset mobiiliystävällisiksi
st.set_page_config(
    page_title="Mäntsälän Hautapaikkahaku",
    page_icon="🕊️",
    layout="centered"
)

# Piilotetaan turhat tekniset valikot seurakuntalaisilta
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stButton>button {width: 100%; border-radius: 8px; height: 3em;}
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def lataa_julkinen_data():
    """Lukee Excelistä VAIN julkiset tiedot. Yhteystiedot ohitetaan tietoturvasyistä."""
    if not os.path.exists("hautadata.xlsx"):
        return []
    
    wb = openpyxl.load_workbook("hautadata.xlsx", data_only=True)
    rows = list(wb.active.iter_rows(values_only=True))
    if len(rows) <= 1:
        return []
        
    headers = [str(h).strip() if h else "" for h in rows[0]]
    julkinen_lista = []
    
    for row in rows[1:]:
        if not row or row[0] is None:
            continue
        r = {headers[i]: row[i] for i in range(len(headers)) if i < len(row)}
        p_id = str(r.get("hautapaikka", "")).strip()
        if p_id:
            s = lambda k: str(r.get(k)).strip() if r.get(k) is not None else ""
            julkinen_lista.append({
                "paikka": p_id,
                "etunimi": s("vainaja_etunimet"),
                "sukunimi": s("vainaja_sukunimi"),
                "omasukua": s("vainaja_omasukua"),
                "syntynyt": s("syntymavuosi"),
                "kuollut": s("kuolinvuosi"),
                "x": int(float(r.get("x_koordinaatti") or 200)),
                "y": int(float(r.get("y_koordinaatti") or 200))
            })
    return julkinen_lista

def etsi_karttakuva():
    """Etsii kansiosta karttakuvan automaattisesti."""
    for tiedosto in os.listdir("."):
        if tiedosto.lower().endswith((".png", ".jpg", ".jpeg")) and "qr" not in tiedosto.lower():
            return tiedosto
    return None

def piirra_kartta_merkilla(x, y):
    """Piirtää punaisen paikannusmerkin karttakuvaan."""
    kuvapolku = etsi_karttakuva()
    if not kuvapolku:
        # Luodaan esittelypohja, jos karttakuvaa ei vielä ole kansiossa
        img = Image.new("RGB", (800, 600), color=(235, 242, 235))
        draw = ImageDraw.Draw(img)
        draw.text((250, 290), "Karttakuva (lisää kartta.png kansioon)", fill=(80, 100, 80))
    else:
        img = Image.open(kuvapolku).convert("RGB")
        draw = ImageDraw.Draw(img)

    # Piirretään selkeä kohdemerkki (punainen ympyrä ja valkoinen keskus)
    r = 22
    draw.ellipse((x - r, y - r, x + r, y + r), fill=(220, 38, 38), outline=(255, 255, 255), width=4)
    draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(255, 255, 255))
    return img

# --- KÄYTTÖLIITTYMÄ ---
st.title("🕊️ Hautapaikkahaku")
st.caption("Mäntsälän seurakunta – Esittelyversio")

data = lataa_julkinen_data()

if not data:
    st.error("Tiedostoa 'hautadata.xlsx' ei löytynyt tai se on tyhjä.")
    st.stop()

# Hakukenttä
hakusana = st.text_input("Hae vainajan nimellä tai hautapaikalla:", placeholder="Esim. Virtanen tai A1-002")

if hakusana:
    haku = hakusana.lower().strip()
    tulokset = [
        h for h in data 
        if haku in h["sukunimi"].lower() 
        or haku in h["etunimi"].lower() 
        or haku in h["omasukua"].lower() 
        or haku in h["paikka"].lower()
    ]
else:
    tulokset = data

st.write(f"Löydetty **{len(tulokset)}** hautapaikkaa:")

if tulokset:
    # Pudotusvalikko valintaa varten (toimii hyvin puhelimella)
    vaihtoehdot = {
        f"{h['sukunimi']}, {h['etunimi']} ({h['syntynyt']}–{h['kuollut']}) • Paikka: {h['paikka']}": h 
        for h in tulokset
    }
    valittu_teksti = st.selectbox("Valitse henkilö nähdäksesi sijainnin:", list(vaihtoehdot.keys()))
    valittu = vaihtoehdot[valittu_teksti]

    # Tietokortti
    with st.container(border=True):
        st.subheader(f"{valittu['etunimi']} {valittu['sukunimi']}")
        if valittu['omasukua']:
            st.write(f"**Oma sukua:** {valittu['omasukua']}")
        st.write(f"**Elinaika:** {valittu['syntynyt']} – {valittu['kuollut']}")
        st.info(f"📍 **Hautapaikan tunnus:** {valittu['paikka']}")

    # Karttanäkymä
    st.subheader("Sijainti hautausmaalla")
    kartta = piirra_kartta_merkilla(valittu["x"], valittu["y"])
    st.image(kartta, use_container_width=True, caption="Voit zoomata karttaa nipistämällä puhelimen ruutua.")

# --- QR-KOODI JA VERKKOSIVUOHJE (Ehdotus 4) ---
st.divider()
with st.expander("📲 Tulosta QR-koodi hautausmaan portille"):
    st.write("Syötä alle julkaistun sovelluksen verkko-osoite luodaksesi tulostettavan QR-koodin:")
    sovellus_url = st.text_input("Sovelluksen verkko-osoite:", value="https://streamlit.app")
    if sovellus_url:
        qr = qrcode.make(sovellus_url)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        st.image(buf.getvalue(), width=200, caption="Skannaa puhelimen kameralla")
        st.download_button(
            label="Lataa QR-koodi kuvana (PNG)",
            data=buf.getvalue(),
            file_name="hautahaku_qr.png",
            mime="image/png"
        )
