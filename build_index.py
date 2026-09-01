"""
Calcule les embeddings de la base et les enregistre dans index.json.

A relancer UNIQUEMENT quand kb_v2.json change (nouveau programme, prix modifie...).
Les embeddings coutent tres peu : 17 blocs = une fraction de centime.

Usage :
    python build_index.py
"""

import json
import os
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

from kb_loader import preparer

MODELE_EMBEDDING = "text-embedding-3-small"
SORTIE = "index.json"


def main():
    cle = os.environ.get("OPENAI_API_KEY")
    if not cle:
        raise SystemExit(
            "Cle API absente.\n"
            "Sous Linux/Mac : export OPENAI_API_KEY='sk-...'\n"
            "Sous Windows   : set OPENAI_API_KEY=sk-..."
        )

    client = OpenAI(api_key=cle)
    blocs = preparer()

    textes = [b["_texte_embedding"] for b in blocs]
    print(f"Calcul des embeddings pour {len(textes)} blocs...")

    reponse = client.embeddings.create(model=MODELE_EMBEDDING, input=textes)

    index = []
    for bloc, item in zip(blocs, reponse.data):
        index.append({
            "id": bloc["id"],
            "bloc": bloc["bloc"],
            "titre": bloc["fr"]["title"],
            "contexte": bloc["_texte_contexte"],
            "embedding": item.embedding,
        })

    Path(SORTIE).write_text(
        json.dumps({"modele": MODELE_EMBEDDING, "entrees": index}, ensure_ascii=False),
        encoding="utf-8",
    )

    taille = Path(SORTIE).stat().st_size / 1024
    print(f"Index enregistre dans {SORTIE} ({taille:.0f} Ko, "
          f"{len(index)} blocs, {len(index[0]['embedding'])} dimensions).")


if __name__ == "__main__":
    main()
