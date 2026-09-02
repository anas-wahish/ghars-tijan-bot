"""
Interface web du chatbot GHARS TIJAN TRAVEL.

Lancement :
    streamlit run app.py

Le moteur (normalisation, recherche, reponse) est celui de chatbot.py.
Ce fichier ne fait qu'ajouter l'affichage.
"""

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import os
from pathlib import Path

from chatbot import (
    charger_index,
    charger_prompt_systeme,
    normaliser,
    rechercher,
    repondre,
)

load_dotenv()

# Streamlit Cloud stocke la cle dans st.secrets, pas dans les variables
# d'environnement. On la recopie pour que chatbot.py et build_index.py,
# qui lisent os.environ, la trouvent aussi.
try:
    if "OPENAI_API_KEY" in st.secrets:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass  # En local, aucun fichier secrets.toml : le .env suffit.

st.set_page_config(page_title="GHARS TIJAN TRAVEL", page_icon="🕋", layout="centered")

# L'arabe doit s'afficher de droite a gauche.
st.markdown("""
<style>
[dir="auto"] { unicode-bidi: plaintext; }
.stChatMessage p { unicode-bidi: plaintext; text-align: start; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def demarrer():
    """Charge l'index et le prompt une seule fois, pas a chaque message.

    Si index.json est absent (cas d'un premier deploiement sur un serveur, le
    fichier n'etant pas versionne sur GitHub), il est construit automatiquement.
    """
    cle = os.environ.get("OPENAI_API_KEY")
    if not cle:
        st.error(
            "Cle API absente.\n\n"
            "- Sur Streamlit Cloud : menu (...) > Settings > Secrets, puis ajoute "
            "la ligne  OPENAI_API_KEY = \"sk-proj-...\"  (guillemets obligatoires).\n"
            "- En local : verifie ton fichier .env."
        )
        st.stop()

    if not Path("index.json").exists():
        with st.spinner("Premier demarrage : construction de l'index..."):
            import build_index
            build_index.main()

    return OpenAI(api_key=cle), charger_index(), charger_prompt_systeme()


client, index, prompt_systeme = demarrer()

st.title("🕋 GHARS TIJAN TRAVEL")
st.caption("وكالة غرس التيجان للحج والعمرة والسياحة — Omra, Hajj et tourisme")

with st.sidebar:
    st.header("Informations")
    st.write(f"**{len(index)} blocs** dans la base")
    st.divider()
    st.subheader("Contact")
    st.write("📞 0700058916\n\n📞 0700058919\n\n📞 0529153030")
    st.write("💬 [WhatsApp](https://wa.me/212700058916)")
    st.write("📧 ghars.tijan@outlook.com")
    st.divider()
    debug = st.checkbox("Mode debogage", value=False,
                        help="Affiche la question normalisee et les blocs retenus")
    if st.button("Effacer la conversation"):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("اكتب سؤالك... / Posez votre question...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("..."):
            normalisee = normaliser(client, question)
            blocs = rechercher(client, index, normalisee)
            reponse = repondre(client, prompt_systeme, blocs, question)

        st.markdown(reponse)

        if debug:
            with st.expander("Details techniques"):
                st.write(f"**Question normalisee :** {normalisee}")
                st.write("**Blocs retenus :**")
                for score, e in blocs:
                    st.write(f"- {score:.2f} — bloc {e['bloc']} : {e['titre']}")

    st.session_state.messages.append({"role": "assistant", "content": reponse})
