#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extraction.py
Module d'extraction des données brutes du Quinté PMU via l'API officielle.
"""

import datetime
import json
import os
import requests

# Cache temporaire autorisé sous Vercel / Render
FICHIER_DONNEES = "/tmp/quinte_du_jour.json"


def recuperer_et_sauvegarder_quinte():
    """
    Interroge la véritable API PMU pour récupérer le programme du jour 
    et identifier la course support du Quinté+.
    """
    print("⏰ Extraction automatique depuis l'API officielle PMU lancée...")
    
    # Le PMU demande le format jjmmaaaa (ex: 27102026)
    date_pmu = datetime.datetime.now().strftime("%d%m%Y")
    url_programme = f"https://pmu.fr"

    try:
        response = requests.get(url_programme, params={"date": date_pmu}, timeout=15)
        response.raise_for_status()
        
        # Structure PMU : programme -> reunions -> courses
        programme = response.json().get("programme", {})
        reunions = programme.get("reunions", [])

        quinte = None
        
        # On parcourt les réunions et les courses pour débusquer le Quinté
        for reunion in reunions:
            courses = reunion.get("courses", [])
            for course in courses:
                # Vérification du flag de l'enjeu Quinté+ dans la liste des paris de la course
                offres = course.get("offresParis", [])
                est_quinte = any(offre.get("typeParis") == "QUINTE_PLUS" for offre in offres)
                
                # Si le flag est trouvé ou que c'est explicitement écrit dans le libellé
                if est_quinte or "QUINTE" in str(course.get("libelle", "")).upper():
                    quinte = course
                    # On injecte les infos de la réunion parent pour que main.py y ait accès (hippodrome, etc.)
                    quinte["libelleHippodrome"] = reunion.get("libelleHippodrome")
                    break
            if quinte:
                break

        if quinte:
            backup_data = {
                "derniere_extraction": datetime.date.today().isoformat(),
                "donnees": quinte,
            }
            with open(FICHIER_DONNEES, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=4)
            print("✅ Données du Quinté officiel enregistrées dans /tmp.")
            return quinte
        else:
            print("⚠️ Aucun Quinté+ identifié dans le programme PMU de ce jour.")

    except Exception as e:
        print(f"❌ Échec de l'extraction sur l'API PMU officielle : {e}")
        
    return None


def obtenir_quinte_du_jour():
    """
    Récupère le Quinté depuis le cache temporaire local ou force une nouvelle
    requête vers l'API si le cache est obsolète ou inexistant.
    """
    date_aujourdhui = datetime.date.today().isoformat()

    if os.path.exists(FICHIER_DONNEES):
        try:
            with open(FICHIER_DONNEES, "r", encoding="utf-8") as f:
                cache = json.load(f)
                if cache.get("derniere_extraction") == date_aujourdhui:
                    print("📦 Données récupérées depuis le cache temporaire /tmp.")
                    return cache.get("donnees")
        except Exception as e:
            print(f"[-] Erreur de lecture du cache : {e}")

    quinte_extrait = recuperer_et_sauvegarder_quinte()
    
    # Secours : Si l'API renvoie du vide (ex: fin de journée), on recycle le dernier cache
    if not quinte_extrait and os.path.exists(FICHIER_DONNEES):
        try:
            with open(FICHIER_DONNEES, "r", encoding="utf-8") as f:
                cache = json.load(f)
                print("♻️ Mode Secours : API indisponible. Restauration du dernier cache valide.")
                return cache.get("donnees")
        except Exception:
            pass

    return quinte_extrait
