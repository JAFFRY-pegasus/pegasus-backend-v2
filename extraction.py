#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extraction.py v2.2 — Multi-stratégies PMU
Essaie plusieurs endpoints API PMU pour trouver le Quinté du jour
S'adapte automatiquement à la date du jour
"""

import datetime
import requests

BASE_URLS = [
    "https://offline.pmu.fr/offline/external/api/1",
    "https://www.pmu.fr/rest/opera/v1",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def _date_francaise():
    """Retourne la date en français : 'Jeudi 30 octobre 2026'"""
    d = datetime.date.today()
    return f"{_JOURS[d.weekday()].capitalize()} {d.day} {_MOIS[d.month - 1]} {d.year}"


def _try_api_offline(date_ddmmyyyy):
    """Stratégie 1 : API offline PMU"""
    url = f"https://offline.pmu.fr/offline/external/api/1/courses/{date_ddmmyyyy}"
    try:
        print(f"🔍 Tentative API offline: {url}", flush=True)
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ API offline répond ({len(str(data))} octets)", flush=True)
        return data
    except Exception as e:
        print(f"❌ API offline échoue: {e}", flush=True)
        return None


def _try_api_opera(date_yyyymmdd):
    """Stratégie 2 : API Opera PMU"""
    url = f"https://www.pmu.fr/rest/opera/v1/courses?date={date_yyyymmdd}"
    try:
        print(f"🔍 Tentative API Opera: {url}", flush=True)
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ API Opera répond ({len(str(data))} octets)", flush=True)
        return data
    except Exception as e:
        print(f"❌ API Opera échoue: {e}", flush=True)
        return None


def _chercher_quinte(data):
    """
    Cherche le Quinté dans différentes structures JSON possibles.
    Retourne un dict avec reunion/course/code_reunion/num_course ou None.
    """
    if not isinstance(data, dict):
        return None

    # Parcourt les réunions
    reunions = data.get("reunions") or data.get("meetings") or []
    
    for reunion in reunions:
        if not isinstance(reunion, dict):
            continue
        
        courses = reunion.get("courses") or reunion.get("races") or []
        code_reunion = reunion.get("numOfficiel") or reunion.get("id") or reunion.get("number")
        
        for course in courses:
            if not isinstance(course, dict):
                continue
            
            # Cherche le flag Quinté sous différentes formes
            paris = course.get("lesParisProposes") or course.get("bets") or course.get("paris") or []
            is_quinte = False
            
            if isinstance(paris, list):
                for pari in paris:
                    pari_str = str(pari).upper()
                    if "QUINTE" in pari_str:
                        is_quinte = True
                        break
            
            # Vérifie aussi les champs booléens directs
            if not is_quinte:
                for champ in ["isQuinte", "quinte", "is_quinte", "hasQuinte"]:
                    if course.get(champ) is True:
                        is_quinte = True
                        break
            
            if is_quinte:
                num_course = course.get("numFormate") or course.get("number") or course.get("id")
                print(f"   ✅ Quinté détecté : R{code_reunion}C{num_course}", flush=True)
                return {
                    "reunion": reunion,
                    "course": course,
                    "code_reunion": code_reunion,
                    "num_course": num_course
                }
    
    return None


def _construire_resultat(quinte_info, date_ddmmyyyy):
    """Construit le dict final compatible avec main.py"""
    course = quinte_info["course"]
    code_reunion = quinte_info["code_reunion"]
    num_course = quinte_info["num_course"]
    
    # Heure de départ
    ts_ms = course.get("heureDepart") or course.get("startTime") or course.get("time") or 0
    if isinstance(ts_ms, (int, float)) and ts_ms > 1000000000000:
        heure_depart = datetime.datetime.fromtimestamp(ts_ms / 1000).strftime("%H:%M")
    elif isinstance(ts_ms, (int, float)) and ts_ms > 1000000000:
        heure_depart = datetime.datetime.fromtimestamp(ts_ms).strftime("%H:%M")
    else:
        heure_depart = str(course.get("heureDepart") or course.get("time") or "00:00")[:5]
    
    # Hippodrome
    hippo = course.get("hippodrome") or course.get("meeting") or {}
    if isinstance(hippo, dict):
        hippodrome = hippo.get("libelleCourt") or hippo.get("name") or hippo.get("shortName") or "INCONNU"
    else:
        hippodrome = str(hippo) if hippo else "INCONNU"
    
    # Récupération des partants
    suite_numerique = []
    try:
        url_part = f"https://offline.pmu.fr/offline/external/api/1/courses/{date_ddmmyyyy}/R{code_reunion}/C{num_course}/participants"
        res_part = requests.get(url_part, headers=HEADERS, timeout=10)
        res_part.raise_for_status()
        donnees_part = res_part.json()
        participants = donnees_part.get("participants") or donnees_part.get("runners") or []
        
        for p in participants:
            num = p.get("numProno") or p.get("number") or p.get("saddleCloth")
            statut = p.get("statut") or p.get("status") or ""
            non_partant = p.get("nonRunner") or p.get("nonPartant") or False
            
            if num is not None and not non_partant and statut.upper() in ["PARTANT", "RUNNER", "", "CONFIRME"]:
                suite_numerique.append(int(num))
        
        suite_numerique = sorted(suite_numerique)
        print(f"   🐎 {len(suite_numerique)} partants confirmés", flush=True)
    except Exception as e:
        print(f"⚠️ Impossible de récupérer les partants: {e}", flush=True)
    
    # Synthèse presse (premiers numéros)
    synthese_presse = " - ".join(str(n) for n in suite_numerique[:8]) if suite_numerique else "1 - 2 - 3 - 4 - 5 - 6 - 7 - 8"
    
    return {
        "hippodrome": hippodrome.upper(),
        "discipline": str(course.get("discipline") or course.get("type") or "INCONNUE").replace("_", " ").upper(),
        "distance": course.get("distance") or course.get("length") or 0,
        "nb_partants": len(suite_numerique) if suite_numerique else 16,
        "heure_depart": heure_depart,
        "nom_course": course.get("libelle") or course.get("name") or "PRIX INCONNU",
        "date": _date_francaise(),
        "synthese_presse": synthese_presse,
        "statut_robot": "Actif",
        "isQuinte": True,
        "numReunion": code_reunion,
        "numOrdre": num_course,
        "code_pmu": f"R{code_reunion}C{num_course}",
        "suite_numerique": suite_numerique,
    }


def extraire_general_quinte():
    """
    Fonction principale : essaie toutes les stratégies pour trouver le Quinté du jour.
    S'adapte automatiquement à la date du jour.
    """
    today = datetime.date.today()
    date_ddmmyyyy = today.strftime("%d%m%Y")
    date_yyyymmdd = today.strftime("%Y-%m-%d")
    
    print(f"\n{'='*60}", flush=True)
    print(f"🔍 RECHERCHE DU QUINTÉ DU {today}", flush=True)
    print(f"{'='*60}", flush=True)
    
    # Stratégie 1 : API offline
    data = _try_api_offline(date_ddmmyyyy)
    if data:
        quinte_info = _chercher_quinte(data)
        if quinte_info:
            return _construire_resultat(quinte_info, date_ddmmyyyy)
    
    # Stratégie 2 : API Opera
    data = _try_api_opera(date_yyyymmdd)
    if data:
        quinte_info = _chercher_quinte(data)
        if quinte_info:
            return _construire_resultat(quinte_info, date_ddmmyyyy)
    
    print("\n❌ AUCUNE STRATÉGIE N'A TROUVÉ LE QUINTÉ", flush=True)
    return None


# Alias de compatibilité pour main.py
obtenir_quinte_du_jour = extraire_general_quinte


if __name__ == "__main__":
    resultat = extraire_general_quinte()
    if resultat:
        print("\n--- DONNÉES EXTRAITES ---")
        for cle, valeur in resultat.items():
            print(f"{cle:<20} : {valeur}")
    else:
        print("\n❌ ÉCHEC DE L'EXTRACTION")
