import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import io
from fpdf import FPDF
from datetime import datetime

# === CONFIGURATION DE LA PAGE ===
st.set_page_config(page_title="Analyse Météo FDF", layout="wide")

# --- NOUVEAU : CRÉATION DE COLONNES POUR LE TITRE ET LE LOGO ---
# [4, 1] signifie que la colonne titre prend 80% de la largeur, et le logo 20%
col_titre, col_logo = st.columns([4, 1])

with col_titre:
    st.title("🔥 Abaque de Départ FDF - Haute-Garonne")
    st.write("Glissez le bulletin météo (PDF) ci-dessous pour générer l'abaque de départ.")

with col_logo:
    try:
        # Remplace "logo.png" par le vrai nom de ton image (ex: "logo_amicale.jpg")
        st.image("EBM.png", width=120)
    except FileNotFoundError:
        # Ce petit message s'affichera tant que l'image ne sera pas dans le dossier
        st.info("👉 Place un fichier 'EBM.png' dans ton dossier PyCharm")

# === MENU DE CALIBRAGE INTERACTIF ===
st.sidebar.header("🎯 Calibrage des viseurs")
st.sidebar.info("Ajustez les compteurs X (gauche/droite) et Y (haut/bas) pour déplacer les points noirs sur la carte.")

# Valeurs de départ (VERROUILLÉES AVEC TES COORDONNÉES)
valeurs_depart = {
    "Frontonnais": (360, 490),
    "Lauragais": (430, 530),
    "Agglomération Toulousaine": (390, 510),
    "Muretain": (400, 550),
    "Volvestre": (350, 560),
    "Comminges": (290, 590),
    "Luchonnais": (290, 650)
}

COORDONNEES_ZONES = {}

for zone, (x_init, y_init) in valeurs_depart.items():
    st.sidebar.subheader(zone)
    col1, col2 = st.sidebar.columns(2)
    x = col1.number_input(f"X", min_value=0, max_value=1500, value=x_init, step=10, key=f"x_{zone}")
    y = col2.number_input(f"Y", min_value=0, max_value=1500, value=y_init, step=10, key=f"y_{zone}")
    COORDONNEES_ZONES[zone] = (x, y)
st.sidebar.markdown("---")


# === FONCTION D'ANALYSE DES COULEURS (TOLÉRANCE ÉLARGIE) ===
def coordonner_couleur_a_risque(rgb):
    r, g, b = rgb[:3]
    if r < 150 and g > 150 and b < 150:
        return "Léger", "#8BC34A"
    elif r > 200 and g > 180 and b < 100:
        return "Modéré", "#FFEB3B"
    elif r > 200 and 100 < g < 190 and b < 150:
        return "Sévère", "#FF9800"
    elif r > 180 and g < 100 and b < 100:
        return "Très sévère", "#F44336"
    elif r < 60 and g < 60 and b < 60:
        return "Extrême", "#212121"
    else:
        return "Indéterminé", "#FFFFFF"


# === FONCTION POUR GÉNÉRER LE DOCUMENT PDF ===
def generer_pdf_export(resultats_abaque):
    pdf = FPDF()
    pdf.add_page()

    # Titre du document
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Abaque de Depart FDF - Haute-Garonne", ln=True, align='C')

    # Date d'édition
    pdf.set_font("Arial", 'I', 12)
    date_jour = datetime.now().strftime("%d/%m/%Y")
    pdf.cell(0, 10, f"Edite le : {date_jour}", ln=True, align='C')
    pdf.ln(10)  # Saut de ligne

    # Dictionnaire des couleurs pour le PDF : (Couleur de fond RGB), (Couleur du texte RGB)
    couleurs_pdf = {
        "Léger": ((139, 195, 74), (0, 0, 0)),  # Fond Vert, texte noir
        "Modéré": ((255, 235, 59), (0, 0, 0)),  # Fond Jaune, texte noir
        "Sévère": ((255, 152, 0), (0, 0, 0)),  # Fond Orange, texte noir
        "Très sévère": ((244, 67, 54), (255, 255, 255)),  # Fond Rouge, texte blanc
        "Extrême": ((33, 33, 33), (255, 255, 255)),  # Fond Noir, texte blanc
        "Indéterminé": ((255, 255, 255), (0, 0, 0))  # Fond Blanc, texte noir
    }

    # En-tête du tableau (Gris clair)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(100, 10, "Secteur", border=1, align='C', fill=True)
    pdf.cell(90, 10, "Niveau de Risque", border=1, ln=True, align='C', fill=True)

    # Remplissage du tableau avec les résultats
    pdf.set_font("Arial", '', 12)
    for zone, niveau in resultats_abaque.items():
        fond, texte = couleurs_pdf.get(niveau, ((255, 255, 255), (0, 0, 0)))

        # Colonne Secteur (Toujours fond blanc, texte noir)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(100, 10, zone, border=1, fill=True)

        # Colonne Niveau (Fond coloré selon le risque, texte adapté)
        pdf.set_fill_color(fond[0], fond[1], fond[2])
        pdf.set_text_color(texte[0], texte[1], texte[2])

        # fill=True est la commande magique pour appliquer la couleur de fond
        pdf.cell(90, 10, niveau, border=1, ln=True, align='C', fill=True)

    # On retourne le fichier brut prêt à être téléchargé
    return pdf.output(dest="S").encode("latin-1")


# === INTERFACE UTILISATEUR PRINCIPALE ===
fichier_pdf = st.file_uploader("Charger la carte Météo-France", type=["pdf"])

if fichier_pdf is not None:
    try:
        # --- LECTURE DU PDF ---
        doc = fitz.open(stream=fichier_pdf.read(), filetype="pdf")
        page = doc.load_page(0)

        matrice = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=matrice)

        donnees_image = pix.tobytes("png")
        image_carte = Image.open(io.BytesIO(donnees_image)).convert("RGB")

        if image_carte.height > image_carte.width:
            image_carte = image_carte.rotate(-90, expand=True)

        curseur = ImageDraw.Draw(image_carte)

        # --- ANALYSE ET AFFICHAGE ---
        st.subheader("📊 Niveaux de risque par secteur")
        colonnes = st.columns(len(COORDONNEES_ZONES))

        # Dictionnaire pour stocker les résultats afin de les envoyer au PDF
        resultats_du_jour = {}

        for i, (zone, coord) in enumerate(COORDONNEES_ZONES.items()):
            try:
                pixel_color = image_carte.getpixel(coord)
                niveau, couleur_css = coordonner_couleur_a_risque(pixel_color)

                # Sauvegarde du résultat pour l'export PDF
                resultats_du_jour[zone] = niveau

                rayon = 8
                curseur.ellipse((coord[0] - rayon, coord[1] - rayon, coord[0] + rayon, coord[1] + rayon),
                                outline="black", width=4)
                curseur.ellipse((coord[0] - 2, coord[1] - 2, coord[0] + 2, coord[1] + 2), fill="white")

                with colonnes[i]:
                    st.markdown(f"""
                        <div style="background-color:{couleur_css}; padding:10px; border-radius:5px; text-align:center; color:{'white' if niveau in ['Très sévère', 'Extrême'] else 'black'}; border: 1px solid #ddd;">
                            <strong>{zone}</strong><br>
                            {niveau}<br>
                            <span style="font-size:0.8em;">RGB: {pixel_color[:3]}</span>
                        </div>
                        """, unsafe_allow_html=True)
            except IndexError:
                st.error(f"Coordonnées hors image pour {zone}")

        st.write("---")

        # --- BOUTON D'EXPORT PDF ---

        # Astuce CSS pour forcer le bouton en rouge vif, texte gras et PLUS GROS
        st.markdown("""
                    <style>
                    div[data-testid="stDownloadButton"] > button {
                        background-color: #FF0000 !important; /* Fond rouge vif */
                        color: #FFFFFF !important; /* Texte blanc */
                        border: 2px solid #CC0000 !important; /* Bordure rouge foncé */
                        padding: 15px 30px !important; /* Rend le bouton plus épais et imposant */
                    }
                    div[data-testid="stDownloadButton"] > button:hover {
                        background-color: #CC0000 !important; 
                        border-color: #990000 !important;
                        color: #FFFFFF !important;
                    }
                    /* Cible spécifiquement le texte à l'intérieur du bouton */
                    div[data-testid="stDownloadButton"] > button p {
                        font-weight: bold !important; /* Écriture grasse */
                        font-size: 24px !important; /* <--- C'EST ICI LA TAILLE DU TEXTE ! (Tu peux mettre 28px ou 30px si tu veux encore plus gros) */
                    }
                    </style>
                    """, unsafe_allow_html=True)

        col_vide, col_bouton, col_vide2 = st.columns([1, 2, 1])  # Pour centrer le bouton
        with col_bouton:
            pdf_bytes = generer_pdf_export(resultats_du_jour)
            date_fichier = datetime.now().strftime("%Y%m%d")
            st.download_button(
                label="📥 Télécharger l'Abaque en PDF",
                data=pdf_bytes,
                file_name=f"Abaque_FDF_{date_fichier}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        st.write("---")

        st.subheader("Aperçu de la carte scannée")
        st.image(image_carte, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur lors de la lecture du document : {e}")