#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extraction.py v2.5 — TOUS les endpoints PMU testés + affichage complet
"""

import datetime
import requests
import json

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
    date_ddmm = today.strftime("%d%m%Y")
    
    print(f"\n{'='*60}", flush=True)
    print(f"🔍 RECHERCHE QUINTÉ DU {today}", flush=True)
    print(f"{'='*60}", flush=True)
    
    # Liste de TOUS les endpoints possibles
    urls_to_try = [
        f"https://www.pmu.fr/rest/opera/v1/courses?date={date_iso}",
        f"https://www.pmu.fr/rest/opera/v1/programme?date={date_iso}",
        f"https://www.pmu.fr/rest/opera/v1/reunions?date={date_iso}",
        f"https://offline.pmu.fr/offline/external/api/1/courses/{date_ddmm}",
        f"https://api.pmu.fr/v1/courses?date={date_iso}",
    ]
    
    data = None
    working_url = None
    
    for url in urls_to_try:
        print(f"\n📡 Test: {url}", flush=True)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                working_url = url
                print(f"   ✅ RÉPOND ({len(str(data))} octets)", flush=True)
                
                # Affiche les clés principales
                print(f"   Clés: {list(data.keys())[:15]}", flush=True)
                break
            else:
                print(f"   ❌ HTTP {resp.status_code}", flush=True)
        except Exception as e:
            print(f"   ❌ {e}", flush=True)
    
    if not data:
        print("\n❌ AUCUN ENDPOINT NE FONCTIONNE", flush=True)
        return None
    
    print(f"\n✅ Endpoint fonctionnel: {working_url}", flush=True)
    
    # Cherche le Quinté dans toutes les structures possibles
    # Structure 1: liste directe de courses
    courses_list = data.get("courses") or data.get("races") or []
    
    # Structure 2: réunions contenant des courses
    reunions = data.get("reunions") or data.get("meetings") or data.get("events") or []
    
    all_courses = []
    
    if isinstance(courses_list, list) and len(courses_list) > 0:
        all_courses = [(None, c) for c in courses_list if isinstance(c, dict)]
    
    if isinstance(reunions, list):
        for reunion in reunions:
            if not isinstance(reunion, dict):
                continue
            code_r = reunion.get("numOfficiel") or reunion.get("id") or reunion.get("number") or reunion.get("code")
            cs = reunion.get("courses") or reunion.get("races") or reunion.get("events") or []
            if isinstance(cs, list):
                for c in cs:
                    if isinstance(c, dict):
                        all_courses.append((code_r, c))
    
    print(f"\n📊 {len(all_courses)} courses trouvées au total", flush=True)
    
    # Cherche le Quinté
    quinte_found = None
    
    for code_r, course in all_courses:
        num_c = course.get("numFormate") or course.get("number") or course.get("id") or course.get("raceNumber")
        libelle = course.get("libelle") or course.get("name") or course.get("title") or "SANS NOM"
        
        # Vérifie tous les champs possibles pour le Quinté
        is_quinte = False
        
        # Méthode 1: chercher dans les paris/bets
        paris_fields = [
            "lesParisProposes", "listeParisDisponibles", "paris", "bets",
            "parisDisponibles", "typesParis", "availableBets", "betTypes",
            "parisDisponible", "Paris", "PARIS"
        ]
        
        for field in paris_fields:
            paris = course.get(field)
            if isinstance(paris, list):
                for pari in paris:
                    if "QUINTE" in str(pari).upper():
                        print(f"   ✅ QUINTÉ dans '{field}' → R{code_r}C{num_c}: {libelle}", flush=True)
                        is_quinte = True
                        break
            if is_quinte:
                break
        
        # Méthode 2: booléen direct
        if not is_quinte:
            for champ in ["isQuinte", "quinte", "is_quinte", "hasQuinte", "estQuinte", "isQuintePlus"]:
                if course.get(champ) is True:
                    print(f"   ✅ QUINTÉ via flag '{champ}' → R{code_r}C{num_c}", flush=True)
                    is_quinte = True
                    break
        
        # Méthode 3: nom de course contient "QUINTE"
        if not is_quinte:
            nom_upper = str(libelle).upper()
            if "QUINTE" in nom_upper or "QUINTE+" in nom_upper:
                print(f"   ✅ QUINTÉ via nom → R{code_r}C{num_c}: {libelle}", flush=True)
                is_quinte = True
        
        if is_quinte:
            quinte_found = (code_r, num_c, course, libelle)
            break
    
    if not quinte_found:
        print("\n❌ Aucun Quinté trouvé. Affichage des 3 premières courses:", flush=True)
        for i, (cr, c) in enumerate(all_courses[:3]):
            print(f"   Course {i+1}: R{cr}C{c.get('numFormate') or c.get('number')} - {c.get('libelle') or c.get('name')}", flush=True)
            print(f"      Clés: {list(c.keys())[:20]}", flush=True)
            # Affiche les valeurs de paris
            for pf in ["lesParisProposes", "paris", "bets", "typesParis"]:
                val = c.get(pf)
                if val is not None:
                    print(f"      {pf}: {val[:5] if isinstance(val, list) else val}", flush=True)
        return None
    
    code_r, num_c, course, libelle = quinte_found
    
    # Construction du résultat
    ts = course.get("heureDepart") or course.get("startTime") or course.get("time") or 0
    if isinstance(ts, (int, float)) and ts > 1e12:
        heure = datetime.datetime.fromtimestamp(ts / 1000).strftime("%H:%M")
    elif isinstance(ts, (int, float)) and ts > 1e9:
        heure = datetime.datetime.fromtimestamp(ts).strftime("%H:%M")
    else:
        heure = str(course.get("heureDepart") or course.get("time") or "00:00")[:5]
    
    hippo = course.get("hippodrome") or course.get("meeting") or {}
    if isinstance(hippo, dict):
        nom_hippo = hippo.get("libelleCourt") or hippo.get("name") or hippo.get("shortName") or "INCONNU"
    else:
        nom_hippo = str(hippo)
    
    # Partants
    suite_numerique = []
    try:
        url_part = f"https://www.pmu.fr/rest/opera/v1/courses/{date_ddmm}/R{code_r}/C{num_c}/participants"
        res = requests.get(url_part, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            part_data = res.json()
            participants = part_data.get("participants") or part_data.get("runners") or []
            for p in participants:
                num = p.get("numProno") or p.get("number") or p.get("saddleCloth")
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
        "discipline": str(course.get("discipline") or course.get("type") or "INCONNUE").replace("_", " ").upper(),
        "distance": course.get("distance") or course.get("length") or 0,
        "nb_partants": len(suite_numerique) if suite_numerique else 16,
        "heure_depart": heure,
        "nom_course": libelle,
        "date": _date_francaise(),
        "synthese_presse": synthese,
        "statut_robot": "Actif",
        "isQuinte": True,
        "numReunion": code_r,
        "numOrdre": num_c,
        "code_pmu": f"R{code_r}C{num_c}",
        "suite_numerique": suite_numerique,
    }


obtenir_quinte_du_jour = extraire_general_quinte

if __name__ == "__main__":
    resultat = extraire_general_quinte()
    if resultat:
        print("\n--- DONNÉES ---")
        for k, v in resultat.items():
            print(f"{k:<20}: {v}")
    else:
        print("\n❌ ÉCHEC")
