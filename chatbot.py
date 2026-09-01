"""
Chatbot GHARS TIJAN TRAVEL — prototype en ligne de commande.

Enchainement pour chaque question :

    1. NORMALISATION  la question du client (darija, arabizi, francais, anglais)
                      est reformulee en arabe standard, uniquement pour la recherche.
    2. RECHERCHE      on compare la question normalisee aux blocs de l'index et on
                      garde les plus proches.
    3. REPONSE        prompt systeme + blocs retenus + question ORIGINALE envoyes au
                      modele. Le bot repond dans la langue du client.

Point important : la reponse est generee a partir de la question ORIGINALE, pas de la
version normalisee. La normalisation ne sert qu'a retrouver les bons blocs ; si on
repondait a la version reformulee, on perdrait le ton et la langue du client.

Usage :
    python chatbot.py
"""

import json
import math
import os
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

MODELE_REPONSE = "gpt-4o-mini"
MODELE_NORMALISATION = "gpt-4.1-nano"
MODELE_EMBEDDING = "text-embedding-3-small"
NB_BLOCS = 4  # nombre de blocs injectes dans le contexte

PROMPT_NORMALISATION = """Tu reformules la question d'un client marocain en arabe standard (fusha).
Le client peut ecrire en darija marocaine, en arabizi (lettres latines et chiffres,
ex: "ch7al", "bghit"), en francais ou en anglais.
Reponds UNIQUEMENT par la question reformulee en arabe standard, sans aucun commentaire.
Si la question est deja en arabe standard, renvoie-la telle quelle."""


def charger_index(chemin="index.json"):
    if not Path(chemin).exists():
        raise SystemExit("index.json introuvable. Lance d'abord : python build_index.py")
    return json.loads(Path(chemin).read_text(encoding="utf-8"))["entrees"]


def charger_prompt_systeme(chemin="prompt_systeme.md"):
    return Path(chemin).read_text(encoding="utf-8")


def cosinus(a, b):
    produit = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return produit / (na * nb) if na and nb else 0.0


def normaliser(client, question):
    """Reformule la question en arabe standard pour ameliorer la recherche."""
    reponse = client.chat.completions.create(
        model=MODELE_NORMALISATION,
        messages=[
            {"role": "system", "content": PROMPT_NORMALISATION},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    return reponse.choices[0].message.content.strip()


def rechercher(client, index, requete, k=NB_BLOCS):
    """Retourne les k blocs les plus proches de la requete."""
    vecteur = client.embeddings.create(
        model=MODELE_EMBEDDING, input=[requete]
    ).data[0].embedding

    scores = [(cosinus(vecteur, e["embedding"]), e) for e in index]
    scores.sort(key=lambda x: x[0], reverse=True)
    return scores[:k]


def repondre(client, prompt_systeme, blocs, question):
    contexte = "\n\n".join(e["contexte"] for _, e in blocs)

    systeme = (
        prompt_systeme
        + "\n\n---\n\n"
        + "INFORMATIONS DISPONIBLES POUR CETTE QUESTION :\n\n"
        + contexte
        + "\n\n---\n\n"
        + "CONSIGNES DE REPONSE :\n"
        "- Reponds dans la MEME langue que le client (arabe, darija, francais ou anglais).\n"
        "- Utilise UNIQUEMENT les informations ci-dessus. N'invente jamais un prix, une\n"
        "  date, une compagnie aerienne, un hotel ou un horaire.\n"
        "- Si une donnee vaut null ou est absente, dis que l'information n'est pas\n"
        "  disponible et donne les numeros de l'agence.\n"
        "- Applique strictement les regles R1 a R12 ci-dessus.\n"
        "- Sois concis."
    )

    reponse = client.chat.completions.create(
        model=MODELE_REPONSE,
        messages=[
            {"role": "system", "content": systeme},
            {"role": "user", "content": question},
        ],
        temperature=0.3,
    )
    return reponse.choices[0].message.content


def main():
    cle = os.environ.get("OPENAI_API_KEY")
    if not cle:
        raise SystemExit("Cle API absente. Fais : export OPENAI_API_KEY='sk-...'")

    client = OpenAI(api_key=cle)
    index = charger_index()
    prompt_systeme = charger_prompt_systeme()

    print(f"Chatbot GHARS TIJAN TRAVEL — {len(index)} blocs charges.")
    print("Ecris ta question (ou 'quit' pour sortir).\n")

    while True:
        question = input("Client > ").strip()
        if question.lower() in ("quit", "exit", "q"):
            break
        if not question:
            continue

        normalisee = normaliser(client, question)
        blocs = rechercher(client, index, normalisee)

        # Traces de debogage : a retirer en production
        print(f"  [normalisee] {normalisee}")
        print("  [blocs] " + ", ".join(
            f"{e['bloc']}:{e['titre']} ({s:.2f})" for s, e in blocs))

        print("\nBot > " + repondre(client, prompt_systeme, blocs, question) + "\n")


if __name__ == "__main__":
    main()
