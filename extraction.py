#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extraction.py v2.1 — MODE DEBUG
Affiche la structure brute de l'API PMU pour diagnostiquer
"""

import datetime
import requests
import json

date_str = datetime.date.today().strftime("%d%m%Y")
BASE_URL = "https://pmu.fr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

def extraire_general_quinte():
    programme_url = f"{BASE_URL}/courses/{date_str}/programme"
    
    try:
        response = requests.get(programme_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        programme = response.json()
    except Exception as e:
        print(f"[ERREUR] Connexion PMU impossible : {e}")
        return None

    #  MODE DEBUG : Affiche la structure complète
    print("\n" + "="*60, flush=True)
    print(" STRUCTURE BRUTE DE L'API PMU", flush=True)
    print("="*60, flush=True)
    print(json.dumps(programme, indent=2, ensure_ascii=False)[:3000], flush=True)  # Premier 3000 caractères
    print("="*60 + "\n", flush=True)

    # Recherche du Quinté
    code_reunion = None
    num_course = None
    bloc_course_pmu = {}

    for reunion in programme.get("reunions", []):
        print(f"\n Réunion R{reunion.get('numOfficiel')}", flush=True)
        for course in reunion.get("courses", []):
            paris = course.get("lesParisProposes", [])
            libelle = course.get("libelle", "SANS NOM")
            print(f"   C{course.get('numFormate')} : {libelle}", flush=True)
            print(f"      Paris proposés : {paris}", flush=True)
            
            if "E_QUINTE_PLUS" in paris or "QUINTE_PLUS" in paris:
                print(f"      ✅ QUINTÉ TROUVÉ !", flush=True)
                code_reunion = reunion.get("numOfficiel")
                num_course = course.get("numFormate")
                bloc_course_pmu = course

    if not code_reunion or not num_course:
        print("\n❌ AUCUN QUINTÉ DÉTECTÉ dans les paris proposés", flush=True)
        print("Les noms de champs ont peut-être changé dans l'API PMU", flush=True)
        return None

    # Si on arrive ici, on a trouvé le Quinté
    print(f"\n✅ Quinté trouvé : R{code_reunion}C{num_course}", flush=True)
    
    # Extraction des données
    ts_ms = bloc_course_pmu.get("heureDepart", 0)
    heure_depart = datetime.datetime.fromtimestamp(ts_ms / 1000).strftime("%H:%M") if ts_ms else "00:00"

    participants_url = f"{BASE_URL}/courses/{date_str}/R{code_reunion}/C{num_course}/participants"
    try:
        res_part = requests.get(participants_url, headers=HEADERS, timeout=10)
        res_part.raise_for_status()
        donnees_participants = res_part.json()
    except Exception as e:
        print(f"[ERREUR] Partants indisponibles : {e}")
        return None

    suite_numerique = sorted([
        int(p.get("numProno"))
        for p in donnees_participants.get("participants", [])
        if p.get("statut") == "PARTANT" and p.get("numProno") is not None
    ])

    hippodrome_brut = bloc_course_pmu.get("hippodrome", {}).get("libelleCourt", "")
    
    _JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    _MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
             "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    d = datetime.date.today()
    date_fr = f"{_JOURS[d.weekday()].capitalize()} {d.day} {_MOIS[d.month - 1]} {d.year}"

    synthese_presse = " - ".join(str(n) for n in suite_numerique[:8])

    return {
        "hippodrome": hippodrome_brut.upper() if hippodrome_brut else "INCONNU",
        "discipline": bloc_course_pmu.get("discipline", "INCONNUE").replace("_", " "),
        "distance": bloc_course_pmu.get("distance", 0),
        "nb_partants": len(suite_numerique),
        "heure_depart": heure_depart,
        "nom_course": bloc_course_pmu.get("libelle", "PRIX INCONNU"),
        "date": date_fr,
        "synthese_presse": synthese_presse,
        "statut_robot": "Actif",
        "isQuinte": True,
        "numReunion": code_reunion,
        "numOrdre": num_course,
        "code_pmu": f"R{code_reunion}C{num_course}",
        "suite_numerique": suite_numerique,
    }

obtenir_quinte_du_jour = extraire_general_quinte

if __name__ == "__main__":
    resultat = extraire_general_quinte()
    if resultat:
        print("\n--- DONNÉES EXTRAITES ---")
        for cle, valeur in resultat.items():
            print(f"{cle:<20} : {valeur}")
