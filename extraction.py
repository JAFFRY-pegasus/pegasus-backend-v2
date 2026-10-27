#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extraction.py
Module d'extraction des données brutes du Quinté PMU.
Intègre un système de cache local persistant pour la résilience de l'interface.
"""

import datetime
import json
import os
import requests

# Utilisation du dossier /tmp, seul espace autorisé en écriture sous Vercel / Render
FICHIER_DONNEES = "/tmp/quinte_du_jour.json"


def recuperer_et_sauvegarder_quinte():
    """
    Interroge l'API PMU et stocke le résultat brut dans le cache temporaire.
    """
    print("⏰ Extraction automatique du Quinté PMU lancée...")
    date_du_jour = datetime.datetime.now().strftime("%m/%d/%Y")

    try:
        response = requests.get(
            "https://vercel.app",  # Votre URL de relais ou endpoint API PMU
            params={"date": date_du_jour},
            timeout=15,
        )
        response.raise_for_status()
        courses = response.json().get("message", [])

        quinte = None
        for course in courses:
            # Recherche du flag officiel ou du libellé de l'enjeu Quinté
            if course.get("typeEnjeu") == "QUINTE" or "QUINTE" in str(course.get("libelle", "")).upper():
                quinte = course
                break

        if quinte:
            backup_data = {
                "derniere_extraction": datetime.date.today().isoformat(),
                "donnees": quinte,
            }
            # Écriture dans le dossier temporaire du serveur
            with open(FICHIER_DONNEES, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=4)
            print("✅ Données du Quinté enregistrées avec succès dans /tmp.")
            return quinte
        else:
            print("⚠️ Aucun Quinté+ actif renvoyé par l'API (Fin de journée ou course passée).")

    except Exception as e:
        print(f"❌ Échec de l'extraction automatique PMU : {e}")
        
    return None


def obtenir_quinte_du_jour():
    """
    Récupère le Quinté depuis le cache temporaire local ou force une nouvelle
    requête vers l'API si le cache est obsolète ou inexistant.
    """
    date_aujourdhui = datetime.date.today().isoformat()

    # 1. Vérification et lecture du cache existant
    if os.path.exists(FICHIER_DONNEES):
        try:
            with open(FICHIER_DONNEES, "r", encoding="utf-8") as f:
                cache = json.load(f)
                # Si le cache a été généré aujourd'hui, on l'utilise en priorité
                if cache.get("derniere_extraction") == date_aujourdhui:
                    print("📦 Données récupérées depuis le cache temporaire /tmp.")
                    return cache.get("donnees")
        except Exception as e:
            print(f"[-] Erreur de lecture du cache : {e}")

    # 2. Si pas de cache ou cache expiré, on interroge l'API PMU
    quinte_extrait = recuperer_et_sauvegarder_quinte()
    
    # 3. Sécurité Fin de journée : Si l'API renvoie du vide alors qu'on avait un cache, 
    # on renvoie quand même le cache pour ne pas laisser l'interface à blanc !
    if not quinte_extrait and os.path.exists(FICHIER_DONNEES):
        try:
            with open(FICHIER_DONNEES, "r", encoding="utf-8") as f:
                cache = json.load(f)
                print("♻️ Mode Secours : API vide. Restauration du dernier cache disponible de la journée.")
                return cache.get("donnees")
        except Exception:
            pass

    return quinte_extrait
