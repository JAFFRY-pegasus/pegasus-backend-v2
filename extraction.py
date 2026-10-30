#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extraction.py v2.0
Extraction des données du Quinté+ du jour depuis l'API officielle PMU
Compatible avec main.py v2.4
"""

import datetime
import requests

# Configuration globale de l'API officielle PMU
date_str = datetime.date.today().strftime("%d%m%Y")
BASE_URL = "https://pmu.fr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# Traduction des codes hippodrome PMU vers noms lisibles
HIPPODROMES_PMU = {
    "VIN": "VINCENNES", "AUTEUIL": "AUTEUIL", "LONGCHAMP": "LONGCHAMP",
    "CHANT": "CHANTILLY", "DEAU": "DEAUVILLE", "SAINTCLOUD": "SAINT-CLOUD",
    "MAISONS-LAFFITTE": "MAISONS-LAFFITTE", "COMPIEGNE": "COMPIÈGNE",
    "ENGHIEN": "ENGHIEN", "CABOURG": "CABOURG", "CAEN": "CAEN",
    "LYON": "LYON", "MARSEILLE": "MARSEILLE", "CAGNES": "CAGNES-SUR-MER",
    "TOULOUSE": "TOULOUSE", "BORDEAUX": "BORDEAUX", "NANTES": "NANTES"
}

_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def _date_francaise(date_obj=None):
    """Retourne la date en français : 'Jeudi 29 octobre 2026'"""
    d = date_obj or datetime.date.today()
    txt = f"{_JOURS[d.weekday()]} {d.day} {_MOIS[d.month - 1]} {d.year}"
    return txt.capitalize()


def _traduire_hippodrome(nom_brut):
    """Tente de trouver un nom lisible pour l'hippodrome."""
    if not nom_brut:
        return "INCONNU"
    nom_upper = nom_brut.upper().replace("-", "").replace(" ", "")
    for cle, valeur in HIPPODROMES_PMU.items():
        if cle.replace("-", "").upper() in nom_upper:
            return valeur
    return nom_brut.upper()


def extraire_general_quinte():
    """
    Analyse le programme PMU, identifie le Quinté du jour et extrait
    les caractéristiques structurelles + flag isQuinte=True.
    """
    programme_url = f"{BASE_URL}/courses/{date_str}/programme"

    try:
        response = requests.get(programme_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        programme = response.json()
    except Exception as e:
        print(f"[ERREUR PEGASUS] Connexion au programme PMU impossible : {e}")
        return None

    code_reunion = None
    num_course = None
    bloc_course_pmu = {}
    is_quinte = False

    # 1. Repérage de la course Quinté dans la structure du programme
    for reunion in programme.get("reunions", []):
        for course in reunion.get("courses", []):
            paris = course.get("lesParisProposes", [])
            if "E_QUINTE_PLUS" in paris or "QUINTE_PLUS" in paris:
                code_reunion = reunion.get("numOfficiel")
                num_course = course.get("numFormate")
                bloc_course_pmu = course
                is_quinte = True  # ✅ FLAG QUINTÉ ACTIVÉ
                break
        if code_reunion:
            break

    if not code_reunion or not num_course:
        print("[INFO PEGASUS] Aucun événement Quinté+ détecté pour cette journée.")
        return None

    # 2. Conversion du timestamp horaire en format lisible HH:MM
    ts_ms = bloc_course_pmu.get("heureDepart", 0)
    heure_depart = (
        datetime.datetime.fromtimestamp(ts_ms / 1000).strftime("%H:%M")
        if ts_ms else "00:00"
    )

    # 3. Récupération des participants
    participants_url = f"{BASE_URL}/courses/{date_str}/R{code_reunion}/C{num_course}/participants"
    try:
        res_part = requests.get(participants_url, headers=HEADERS, timeout=10)
        res_part.raise_for_status()
        donnees_participants = res_part.json()
    except Exception as e:
        print(f"[ERREUR PEGASUS] Partants indisponibles R{code_reunion}C{num_course} : {e}")
        return None

    # Extraction des numéros (numProno) des chevaux confirmés partants
    suite_numerique = sorted([
        int(p.get("numProno"))
        for p in donnees_participants.get("participants", [])
        if p.get("statut") == "PARTANT" and p.get("numProno") is not None
    ])

    # 4. Extraction de l'hippodrome
    hippodrome_brut = bloc_course_pmu.get("hippodrome", {}).get("libelleCourt", "")
    hippodrome = _traduire_hippodrome(hippodrome_brut)

    # 5. Construction de la chaîne "synthese_presse" à partir de la suite numérique
    # (format attendu par le template : "13 - 8 - 10 - 4 - 16 - 6 - 5 - 12")
    synthese_presse = " - ".join(str(n) for n in suite_numerique[:8])

    # 6. ⭐ DONNÉES FINALES — noms compatibles avec main.py
    donnees_generales = {
        # Champs attendus par main.py
        "hippodrome": hippodrome,
        "discipline": bloc_course_pmu.get("discipline", "INCONNUE").replace("_", " "),
        "distance": bloc_course_pmu.get("distance", 0),
        "nb_partants": len(suite_numerique),
        "heure_depart": heure_depart,
        "nom_course": bloc_course_pmu.get("libelle", "PRIX INCONNU"),
        "date": _date_francaise(),
        "synthese_presse": synthese_presse,
        "statut_robot": "Actif",

        # ⭐ FLAG QUINTÉ — vérification défensive
        "isQuinte": is_quinte,
        "numReunion": code_reunion,
        "numOrdre": num_course,

        # Données supplémentaires utiles pour /debug-extraction
        "code_pmu": f"R{code_reunion}C{num_course}",
        "suite_numerique": suite_numerique,
        "date_iso": datetime.date.today().strftime("%Y-%m-%d"),
    }

    return donnees_generales


# Alias de compatibilité pour main.py
obtenir_quinte_du_jour = extraire_general_quinte


if __name__ == "__main__":
    resultat = extraire_general_quinte()
    if resultat:
        print("\n--- DONNÉES DU QUINTÉ EXTRAITES ---")
        for cle, valeur in resultat.items():
            print(f"{cle:<20} : {valeur}")
        print("-----------------------------------")
    else:
        print("Aucun Quinté détecté aujourd'hui.")
