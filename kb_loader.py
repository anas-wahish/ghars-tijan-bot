"""
Chargement de la base de connaissances GHARS TIJAN TRAVEL.

Ce module ne fait AUCUN appel reseau. Il prepare simplement les donnees :
  - il charge kb_v2.json
  - il ecarte les blocs internes (audience = "interne")
  - il construit, pour chaque bloc, le texte qui servira a calculer l'embedding
  - il construit le texte complet qui sera envoye au modele (texte + donnees structurees)

Distinction importante :
  texte_embedding  -> uniquement les 3 langues, sert a la RECHERCHE
  texte_contexte   -> texte + objet `structured`, sert a la REPONSE

Sans cette distinction, le modele verrait la description d'un programme mais pas les
champs `vol` / `transport` / `prix`, et ne pourrait pas appliquer les regles R4, R5 et R7.
"""

import json
from pathlib import Path

LANGUES = ("ar", "fr", "en")


def charger_kb(chemin="kb_v2.json"):
    """Charge la base et retourne la liste des blocs destines aux clients."""
    donnees = json.loads(Path(chemin).read_text(encoding="utf-8"))
    blocs = donnees["chunks"]

    publics = [b for b in blocs if b.get("audience") != "interne"]
    internes = len(blocs) - len(publics)
    print(f"Base chargee : {len(blocs)} blocs, dont {internes} interne(s) ecarte(s).")
    return publics


def texte_embedding(bloc):
    """Texte utilise pour la recherche. Les 3 langues, pour que la question du client
    trouve le bloc quelle que soit la langue employee."""
    morceaux = []
    for lang in LANGUES:
        if lang in bloc:
            morceaux.append(bloc[lang]["title"])
            morceaux.append(bloc[lang]["content"])
    return "\n".join(morceaux)


def texte_contexte(bloc):
    """Texte envoye au modele quand ce bloc est retenu. Contient les donnees
    structurees, sans lesquelles le bot ne peut pas savoir ce qui est connu ou non."""
    lignes = [f"### BLOC {bloc['bloc']} — {bloc['fr']['title']} (id: {bloc['id']})"]

    if "statut" in bloc:
        lignes.append(f"STATUT DU PROGRAMME : {bloc['statut']}")

    for lang in LANGUES:
        if lang in bloc:
            lignes.append(f"\n[{lang.upper()}] {bloc[lang]['title']}")
            lignes.append(bloc[lang]["content"])

    if "structured" in bloc:
        lignes.append("\nDONNEES STRUCTUREES (null = information inconnue, "
                      "le bot doit renvoyer vers l'agence) :")
        lignes.append(json.dumps(bloc["structured"], ensure_ascii=False, indent=2))

    return "\n".join(lignes)


def preparer(chemin="kb_v2.json"):
    """Retourne les blocs enrichis des deux textes."""
    blocs = charger_kb(chemin)
    for b in blocs:
        b["_texte_embedding"] = texte_embedding(b)
        b["_texte_contexte"] = texte_contexte(b)
    return blocs


if __name__ == "__main__":
    blocs = preparer()
    print(f"\nBlocs prepares : {len(blocs)}")
    exemple = next(b for b in blocs if b["bloc"] == 10)
    print("\n--- Exemple de contexte (bloc 10) ---")
    print(exemple["_texte_contexte"][:900])
