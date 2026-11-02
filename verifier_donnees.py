#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de vérification et de nettoyage de la base de données historique Pegasus.
"""

import json
from historique import HISTORIQUE_SGE_DATA

def verifier_base_de_donnees():
    print("=" * 60)
    print("🔍 DIAGNOSTIC DE LA BASE DE DONNÉES PEGASUS")
    print("=" * 60)
    
    total_courses = len(HISTORIQUE_SGE_DATA)
    print(f"📊 Total des courses analysées : {total_courses}\n")

    erreurs_doublons = []
    erreurs_numeros = []
    erreurs_manquantes = []
    
    signatures_vues = set()

    for index, course in enumerate(HISTORIQUE_SGE_DATA):
        date = course.get("date", "")
        hippodrome = course.get("hippodrome", "")
        arrivee = course.get("arrivee", [])
        nb_partants = course.get("nb_partants", 0)

        # 1. Vérification des données manquantes
        if not date or not hippodrome or not arrivee:
            erreurs_manquantes.append(f"Ligne {index}: Données manquantes (Date: {date}, Hippo: {hippodrome}, Arrivée: {arrivee})")

        # 2. Vérification des doublons (Signature unique : Date + Hippodrome + Arrivée)
        signature = (str(date), str(hippodrome), tuple(arrivee))
        if signature in signatures_vues:
            erreurs_doublons.append(f"Ligne {index}: Doublon détecté ({date} à {hippodrome})")
        else:
            signatures_vues.add(signature)

        # 3. Vérification des numéros de chevaux (Doivent être entre 1 et 20)
        if isinstance(arrivee, list):
            for num in arrivee:
                if not isinstance(num, int) or num < 1 or num > 20:
                    erreurs_numeros.append(f"Ligne {index}: Numéro invalide '{num}' dans l'arrivée {arrivee}")
                
                # Vérification logique : un cheval ne peut pas avoir un numéro > nb_partants
                if isinstance(nb_partants, int) and nb_partants > 0 and num > nb_partants:
                    erreurs_numeros.append(f"Ligne {index}: Cheval n°{num} mais seulement {nb_partants} partants déclarés.")

    # === AFFICHAGE DES RÉSULTATS ===
    print("✅ VÉRIFICATION TERMINÉE\n")
    
    if not erreurs_doublons and not erreurs_numeros and not erreurs_manquantes:
        print("🎉 EXCELLENT ! Aucune erreur, doublon ou incohérence détectée dans la base.")
    else:
        if erreurs_doublons:
            print(f"⚠️ DOUBLONS DÉTECTÉS ({len(erreurs_doublons)}) :")
            for err in erreurs_doublons[:5]: # Affiche les 5 premiers
                print(f"   - {err}")
            if len(erreurs_doublons) > 5:
                print(f"   ... et {len(erreurs_doublons) - 5} autres.")
            print()
            
        if erreurs_numeros:
            print(f"⚠️ NUMÉROS INVALIDES DÉTECTÉS ({len(erreurs_numeros)}) :")
            for err in erreurs_numeros[:5]:
                print(f"   - {err}")
            if len(erreurs_numeros) > 5:
                print(f"   ... et {len(erreurs_numeros) - 5} autres.")
            print()
            
        if erreurs_manquantes:
            print(f"⚠️ DONNÉES MANQUANTES DÉTECTÉES ({len(erreurs_manquantes)}) :")
            for err in erreurs_manquantes[:5]:
                print(f"   - {err}")
            print()

    print("=" * 60)

if __name__ == "__main__":
    verifier_base_de_donnees()
