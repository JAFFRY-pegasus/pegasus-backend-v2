#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extraction.py v2.3 — DEBUG COMPLET
Affiche la structure complète de l'API PMU pour diagnostiquer
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
    date_ddmmyyyy = today.strftime("%d%m%Y")
    
    print(f"\n{'='*60}", flush=True)
    print(f"🔍 RECHERCHE DU QUINTÉ DU {today}", flush=True)
    print(f"{'='*60}", flush=True)
    
    # Essai API offline PMU
    url = f"https://offline.pmu.fr/offline/external/api/1/courses/{date_ddmmyyyy}"
    print(f"📡 URL: {url}", flush=True)
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # AFFICHAGE COMPLET DE LA STRUCTURE JSON
        print(f"\n{'='*60}", flush=True)
        print("📋 STRUCTURE COMPLÈTE DE L'API PMU", flush=True)
        print(f"{'='*60}", flush=True)
        
        # Affiche les clés principales
        print(f"\nClés principales du JSON:", flush=True)
        for cle in data.keys():
            valeur = data[cle]
            if isinstance(valeur, list):
                print(f"  - {cle}: LISTE ({len(valeur)} éléments)", flush=True)
            elif isinstance(valeur, dict):
                print(f"  - {cle}: DICT (clés: {list(valeur.keys())[:5]})", flush=True)
            else:
                print(f"  - {cle}: {valeur}", flush=True)
        
        # Cherche les réunions
        reunions = data.get("reunions") or data.get("meetings") or []
        print(f"\n📊 Nombre de réunions trouvées: {len(reunions)}", flush=True)
        
        for idx, reunion in enumerate(reunions):
            if not isinstance(reunion, dict):
                continue
            
            code_reunion = reunion.get("numOfficiel") or reunion.get("id") or reunion.get("number") or f"R{idx+1}"
            print(f"\n  🏇 Réunion R{code_reunion}:", flush=True)
            
            courses = reunion.get("courses") or reunion.get("races") or []
            print(f"     Nombre de courses: {len(courses)}", flush=True)
            
            for c_idx, course in enumerate(courses):
                if not isinstance(course, dict):
                    continue
                
                num_course = course.get("numFormate") or course.get("number") or course.get("id") or f"C{c_idx+1}"
                libelle = course.get("libelle") or course.get("name") or "SANS NOM"
                
                print(f"\n     Course C{num_course}: {libelle}", flush=True)
                
                # Affiche TOUTES les clés de la course
                print(f"       Clés disponibles:", flush=True)
                for cle in course.keys():
                    val = course[cle]
                    if isinstance(val, list):
                        print(f"         - {cle}: LISTE ({len(val)} items)", flush=True)
                        # Affiche le contenu des listes importantes
                        if cle.lower() in ["paris", "bets", "parisdisponibles", "listeparisdisponibles", "lesparisproposes"]:
                            print(f"           Contenu: {val[:3]}", flush=True)  # Premier 3 éléments
                    elif isinstance(val, dict):
                        print(f"         - {cle}: DICT", flush=True)
                    else:
                        print(f"         - {cle}: {val}", flush=True)
                
                # Cherche le Quinté sous différentes formes
                is_quinte = False
                paris_fields = [
                    "lesParisProposes", "listeParisDisponibles", "paris", 
                    "bets", "parisDisponibles", "ParisDisponible"
                ]
                
                for field in paris_fields:
                    paris = course.get(field)
                    if isinstance(paris, list):
                        for pari in paris:
                            pari_str = str(pari).upper()
                            if "QUINTE" in pari_str:
                                print(f"       ✅ QUINTÉ TROUVÉ dans '{field}'!", flush=True)
                                is_quinte = True
                                break
                    if is_quinte:
                        break
                
                # Vérifie aussi les booléens directs
                if not is_quinte:
                    for champ in ["isQuinte", "quinte", "is_quinte", "hasQuinte", "estQuinte"]:
                        if course.get(champ) is True:
                            print(f"       ✅ QUINTÉ détecté via flag '{champ}'!", flush=True)
                            is_quinte = True
                            break
                
                if is_quinte:
                    print(f"\n{'='*60}", flush=True)
                    print(f"🎯 QUINTÉ IDENTIFIÉ : R{code_reunion}C{num_course}", flush=True)
                    print(f"   Libellé: {libelle}", flush=True)
                    print(f"{'='*60}\n", flush=True)
                    
                    # Construction du résultat
                    ts_ms = course.get("heureDepart") or course.get("startTime") or 0
                    if isinstance(ts_ms, (int, float)) and ts_ms > 1000000000000:
                        heure_depart = datetime.datetime.fromtimestamp(ts_ms / 1000).strftime("%H:%M")
                    elif isinstance(ts_ms, (int, float)) and ts_ms > 1000000000:
                        heure_depart = datetime.datetime.fromtimestamp(ts_ms).strftime("%H:%M")
                    else:
                        heure_depart = str(course.get("heureDepart") or "00:00")[:5]
                    
                    hippo = course.get("hippodrome") or {}
                    if isinstance(hippo, dict):
                        hippodrome = hippo.get("libelleCourt") or hippo.get("name") or "INCONNU"
                    else:
                        hippodrome = str(hippo)
                    
                    # Partants
                    suite_numerique = []
                    try:
                        url_part = f"https://offline.pmu.fr/offline/external/api/1/courses/{date_ddmmyyyy}/R{code_reunion}/C{num_course}/participants"
                        res_part = requests.get(url_part, headers=HEADERS, timeout=10)
                        res_part.raise_for_status()
                        donnees_part = res_part.json()
                        participants = donnees_part.get("participants") or []
                        
                        for p in participants:
                            num = p.get("numProno") or p.get("number")
                            statut = p.get("statut") or ""
                            non_partant = p.get("nonRunner") or False
                            
                            if num is not None and not non_partant:
                                suite_numerique.append(int(num))
                        
                        suite_numerique = sorted(suite_numerique)
                        print(f"   🐎 {len(suite_numerique)} partants trouvés", flush=True)
                    except Exception as e:
                        print(f"   ️ Erreur partants: {e}", flush=True)
                    
                    synthese_presse = " - ".join(str(n) for n in suite_numerique[:8]) if suite_numerique else "1 - 2 - 3 - 4 - 5 - 6 - 7 - 8"
                    
                    return {
                        "hippodrome": hippodrome.upper(),
                        "discipline": str(course.get("discipline") or "INCONNUE").replace("_", " ").upper(),
                        "distance": course.get("distance") or 0,
                        "nb_partants": len(suite_numerique) if suite_numerique else 16,
                        "heure_depart": heure_depart,
                        "nom_course": libelle,
                        "date": _date_francaise(),
                        "synthese_presse": synthese_presse,
                        "statut_robot": "Actif",
                        "isQuinte": True,
                        "numReunion": code_reunion,
                        "numOrdre": num_course,
                        "code_pmu": f"R{code_reunion}C{num_course}",
                        "suite_numerique": suite_numerique,
                    }
        
        print(f"\n❌ AUCUN QUINTÉ TROUVÉ dans {len(reunions)} réunions", flush=True)
        return None
        
    except Exception as e:
        print(f"\n❌ ERREUR CONNEXION API: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None


obtenir_quinte_du_jour = extraire_general_quinte

if __name__ == "__main__":
    resultat = extraire_general_quinte()
    if resultat:
        print("\n--- DONNÉES EXTRAITES ---")
        for cle, valeur in resultat.items():
            print(f"{cle:<20} : {valeur}")
    else:
        print("\n❌ ÉCHEC")
