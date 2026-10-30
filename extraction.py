#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extraction.py v2.4 — Endpoint PMU fonctionnel uniquement
Utilise www.pmu.fr/rest/opera/v1 (le seul endpoint qui résout encore)
"""

import datetime
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def _date_francaise():
    d = datetime.date.today()
    return f"{_JOURS[d.weekday()].capitalize()} {d.day} {_MOIS[d.month - 1]} {d.year}"


def extraire_general_quinte():
    today = datetime.date.today()
    date_iso = today.strftime("%Y-%m-%d")
    
    print(f"\n{'='*60}", flush=True)
    print(f"🔍 RECHERCHE DU QUINTÉ DU {today}", flush=True)
    print(f"{'='*60}", flush=True)
    
    # SEUL ENDPOINT QUI FONCTIONNE ENCORE
    url = f"https://www.pmu.fr/rest/opera/v1/courses?date={date_iso}"
    print(f"📡 URL: {url}", flush=True)
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ API répond ({len(str(data))} octets)", flush=True)
        
        # Affiche la structure pour diagnostic
        print(f"\nClés principales:", flush=True)
        for cle in list(data.keys())[:10]:
            val = data[cle]
            if isinstance(val, list):
                print(f"  - {cle}: LISTE ({len(val)} éléments)", flush=True)
            else:
                print(f"  - {cle}: {type(val).__name__}", flush=True)
        
        # Cherche le Quinté
        reunions = data.get("reunions") or data.get("meetings") or []
        print(f"\n📊 {len(reunions)} réunions trouvées", flush=True)
        
        for reunion in reunions:
            if not isinstance(reunion, dict):
                continue
            
            code_reunion = reunion.get("numOfficiel") or reunion.get("id") or reunion.get("number")
            courses = reunion.get("courses") or reunion.get("races") or []
            
            print(f"\n  Réunion R{code_reunion}: {len(courses)} courses", flush=True)
            
            for course in courses:
                if not isinstance(course, dict):
                    continue
                
                num_course = course.get("numFormate") or course.get("number") or course.get("id")
                libelle = course.get("libelle") or course.get("name") or "SANS NOM"
                
                # Cherche le Quinté sous toutes les formes possibles
                is_quinte = False
                paris_fields = [
                    "lesParisProposes", "listeParisDisponibles", "paris",
                    "bets", "parisDisponibles", "ParisDisponible",
                    "typesParis", "availableBets"
                ]
                
                for field in paris_fields:
                    paris = course.get(field)
                    if isinstance(paris, list):
                        for pari in paris:
                            pari_str = str(pari).upper()
                            if "QUINTE" in pari_str:
                                print(f"     ✅ QUINTÉ trouvé dans '{field}'!", flush=True)
                                is_quinte = True
                                break
                    if is_quinte:
                        break
                
                # Vérifie les booléens
                if not is_quinte:
                    for champ in ["isQuinte", "quinte", "is_quinte", "hasQuinte"]:
                        if course.get(champ) is True:
                            print(f"     ✅ QUINTÉ via flag '{champ}'", flush=True)
                            is_quinte = True
                            break
                
                if is_quinte:
                    print(f"\n{'='*60}", flush=True)
                    print(f"🎯 QUINTÉ : R{code_reunion}C{num_course}", flush=True)
                    print(f"   Course: {libelle}", flush=True)
                    
                    # Heure
                    ts = course.get("heureDepart") or course.get("startTime") or 0
                    if isinstance(ts, (int, float)) and ts > 1e12:
                        heure = datetime.datetime.fromtimestamp(ts / 1000).strftime("%H:%M")
                    elif isinstance(ts, (int, float)) and ts > 1e9:
                        heure = datetime.datetime.fromtimestamp(ts).strftime("%H:%M")
                    else:
                        heure = str(course.get("heureDepart") or "00:00")[:5]
                    
                    # Hippodrome
                    hippo = course.get("hippodrome") or {}
                    if isinstance(hippo, dict):
                        nom_hippo = hippo.get("libelleCourt") or hippo.get("name") or "INCONNU"
                    else:
                        nom_hippo = str(hippo)
                    
                    # Partants (essai avec nouvel endpoint)
                    suite_numerique = []
                    try:
                        date_ddmm = today.strftime("%d%m%Y")
                        url_part = f"https://www.pmu.fr/rest/opera/v1/courses/{date_ddmm}/R{code_reunion}/C{num_course}/participants"
                        res = requests.get(url_part, headers=HEADERS, timeout=10)
                        if res.status_code == 200:
                            part_data = res.json()
                            participants = part_data.get("participants") or part_data.get("runners") or []
                            for p in participants:
                                num = p.get("numProno") or p.get("number")
                                non_partant = p.get("nonRunner") or p.get("nonPartant") or False
                                if num is not None and not non_partant:
                                    suite_numerique.append(int(num))
                            suite_numerique = sorted(suite_numerique)
                            print(f"   🐎 {len(suite_numerique)} partants", flush=True)
                    except Exception as e:
                        print(f"   ⚠️ Partants: {e}", flush=True)
                    
                    synthese = " - ".join(str(n) for n in suite_numerique[:8]) if suite_numerique else "1 - 2 - 3 - 4 - 5 - 6 - 7 - 8"
                    
                    return {
                        "hippodrome": nom_hippo.upper(),
                        "discipline": str(course.get("discipline") or "INCONNUE").replace("_", " ").upper(),
                        "distance": course.get("distance") or 0,
                        "nb_partants": len(suite_numerique) if suite_numerique else 16,
                        "heure_depart": heure,
                        "nom_course": libelle,
                        "date": _date_francaise(),
                        "synthese_presse": synthese,
                        "statut_robot": "Actif",
                        "isQuinte": True,
                        "numReunion": code_reunion,
                        "numOrdre": num_course,
                        "code_pmu": f"R{code_reunion}C{num_course}",
                        "suite_numerique": suite_numerique,
                    }
        
        print("\n❌ Aucun Quinté trouvé", flush=True)
        return None
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None


obtenir_quinte_du_jour = extraire_general_quinte

if __name__ == "__main__":
    resultat = extraire_general_quinte()
    if resultat:
        print("\n--- DONNÉES ---")
        for k, v in resultat.items():
            print(f"{k:<20}: {v}")
    else:
        print("\n❌ ÉCHEC")
