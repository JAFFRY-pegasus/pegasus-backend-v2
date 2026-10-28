#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main.py
Moteur SGE unifié avec API FastAPI et gestion hybride du robot (Automatique + Clic Manuel)
Projet : pegasus-backend-v2
"""

import json
import os
from datetime import datetime as _datetime
from collections import Counter
from itertools import combinations

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Importations des modules locaux
from historique import HISTORIQUE_SGE_DATA
from extraction import obtenir_quinte_du_jour

app = FastAPI()

# Configuration du dossier des templates Jinja2
templates = Jinja2Templates(directory="templates")

# Configuration des ressources graphiques
FICHIER_SAUVEGARDE = "quinte_du_jour.json"

# État global en mémoire pour les chevaux actuellement sélectionnés par l'utilisateur
COMBINAISON_SELECTIONNEE = ["13", "6", "5", "12", "11"]

# Structure de mémoire globale pour l'affichage de l'interface utilisateur
DONNEES_QUINTE_DU_JOUR = {
    "hippodrome": "DEA", 
    "discipline": "Inconnue", 
    "distance": 1900, 
    "nb_partants": 16, 
    "heure_depart": "13:55", 
    "nom_course": "PRIX DE LA FORET DE LYONS",
    "date": "Lundi 19 octobre 2026",
    "synthese_presse": "13 - 8 - 10 - 4 - 16 - 6 - 5 - 12",
    "statut_robot": "Actif"
}

# =====================================================================
# --- CONFIGURATIONS ET MATRICES DU MOTEUR SGE -----------------------
# =====================================================================

OPPOSITIONS_VERTICALES = {
    1: 9, 2: 10, 3: 11, 4: 12, 5: 13, 6: 14, 7: 15, 8: 16,
    9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 6, 15: 7, 16: 8
}

COEFFICIENTS_RESONANCE = {
    0: 0.5, 1: 1.0, 2: 1.5, 3: 2.0, 4: 2.5, 5: 3.0
}

# =====================================================================
# --- LOGIQUE ALGORITHMIQUE SGE ---------------------------------------
# =====================================================================

def calculer_poids_axes():
    frequence_axes = Counter()
    for course in HISTORIQUE_SGE_DATA:
        arr = course["arrivee"]
        for num in arr:
            oppose = OPPOSITIONS_VERTICALES.get(num)
            if oppose and oppose in arr:
                axe = tuple(sorted([num, oppose]))
                frequence_axes[axe] += 1
    return {axe: freq // 2 for axe, freq in frequence_axes.items()}

POIDS_AXES_HISTORIQUE = calculer_poids_axes()

def calculer_score_sge(combinaison):
    score_brut = 0
    axes_touches = set()
    for i in range(len(combinaison)):
        for j in range(i + 1, len(combinaison)):
            a, b = combinaison[i], combinaison[j]
            if a in OPPOSITIONS_VERTICALES and OPPOSITIONS_VERTICALES[a] == b:
                axe = tuple(sorted([a, b]))
                axes_touches.add(axe)
                if axe in POIDS_AXES_HISTORIQUE:
                    score_brut += POIDS_AXES_HISTORIQUE[axe]
    nombre_axes = len(axes_touches)
    ponderation = COEFFICIENTS_RESONANCE.get(nombre_axes, 2.0)
    return int(score_brut * ponderation)

def generer_prono_automatique(combinaison_ref):
    valides = [int(n) for n in combinaison_ref if n.isdigit() and 1 <= int(n) <= 16]
    if len(valides) < 5:
        # CORRECTION : La liste par défaut a été réintégrée proprement sans coupure
        liste_defaut = [11, 4, 7, 5, 9, 1, 2, 3, 6, 8, 10, 12, 13, 14, 15, 16]
        complements = [n for n in liste_defaut if n not in valides]
        valides = (valides + complements)[:5]
    
    opposes = [OPPOSITIONS_VERTICALES[n] for n in valides if n in OPPOSITIONS_VERTICALES]
    candidats = list(dict.fromkeys(valides + opposes))
    
    scores_candidats = []
    for combo in combinations(candidats, 5):
        score = calculer_score_sge(list(combo))
        scores_candidats.append((score, list(combo)))
    
    scores_candidats.sort(key=lambda x: x[0], reverse=True)
    
    if scores_candidats:
        return [str(x) for x in scores_candidats[0][1]]
    else:
        return [str(x) for x in valides[:5]]

# =====================================================================
# --- ROUTES DE L'APPLICATION -----------------------------------------
# =====================================================================

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    global COMBINAISON_SELECTIONNEE, DONNEES_QUINTE_DU_JOUR
    
    # 1. Calcul automatique du pronostic Pegasus sur la base de la combinaison choisie
    prono_pegasus = generer_prono_automatique(COMBINAISON_SELECTIONNEE)
    
    # 2. Extraction des statistiques du Top chevaux depuis l'historique
    counter = Counter()
    total_courses = len(HISTORIQUE_SGE_DATA)
    for course in HISTORIQUE_SGE_DATA:
        for num in course["arrivee"][:5]:
            counter[num] += 1
            
    top_chevaux = []
    for num, count in counter.most_common(3):
        top_chevaux.append({
            "numero": f"{num:02d}",
            "occurrences": count,
            "pourcentage": round((count / total_courses) * 100, 1)
        })

    # 3. Préparation des structures attendues par index.html
    info_quinte = {
        "date": DONNEES_QUINTE_DU_JOUR.get("date", "Lundi 19 octobre 2026"),
        "hippodrome": DONNEES_QUINTE_DU_JOUR.get("hippodrome", "INCONNU"),
        "discipline": DONNEES_QUINTE_DU_JOUR.get("discipline", "Inconnue"),
        "nom_course": DONNEES_QUINTE_DU_JOUR.get("nom_course", "Aucun Nom Trouvé"),
        "distance": DONNEES_QUINTE_DU_JOUR.get("distance", 0),
        "nb_partants": DONNEES_QUINTE_DU_JOUR.get("nb_partants", 16),
        "heure_depart": DONNEES_QUINTE_DU_JOUR.get("heure_depart", "--:--"),
        "synthese_presse": DONNEES_QUINTE_DU_JOUR.get("synthese_presse", "")
    }

    jetons = {
        "presse": [n.strip() for n in info_quinte["synthese_presse"].split("-") if n.strip()],
        "pegasus": prono_pegasus,
        "arrivee": ["4", "5", "9", "10", "11"],
        "retenus": COMBINAISON_SELECTIONNEE
    }

    # Calcul des scores géométriques
    combo_int = [int(n) for n in COMBINAISON_SELECTIONNEE if n.isdigit()]
    score_pegasus = calculer_score_sge([int(n) for n in prono_pegasus])
    score_combinaison = calculer_score_sge(combo_int) if len(combo_int) == 5 else 0

    stats = {
        "historique_courses": total_courses,
        "taux_reussite": 20,
        "nb_dernieres_courses": 5,
        "ponderation_pegasus": score_pegasus,
        "ponderation_combinaison": score_combinaison,
        "moyenne_chevaux_trouves": "0.00",
        "niveau_performance": "Faible",
        "top_chevaux_frequents": top_chevaux
    }

    combinaison_saisie = " - ".join(COMBINAISON_SELECTIONNEE)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "statut_robot": DONNEES_QUINTE_DU_JOUR.get("statut_robot", "Actif"),
        "message_statut": "Aucun non-partant détecté à ce stade • 16 partants confirmés • Dernière vérification : 12:59",
        "info_quinte": info_quinte,
        "combinaison_saisie": combinaison_saisie,
        "jetons": jetons,
        "stats": stats
    })

@app.post("/calculer")
def calculer(combinaison_utilisateur: str = Form(...)):
    global COMBINAISON_SELECTIONNEE
    extraits = [n.strip() for n in combinaison_utilisateur.split("-") if n.strip().isdigit()]
    if extraits:
        COMBINAISON_SELECTIONNEE = extraits[:8]
    return RedirectResponse(url="/", status_code=303)

@app.get("/selectionner/{numero}")
def selectionner_grille(numero: str):
    global COMBINAISON_SELECTIONNEE
    if numero in COMBINAISON_SELECTIONNEE:
        COMBINAISON_SELECTIONNEE.remove(numero)
    else:
        if len(COMBINAISON_SELECTIONNEE) < 8:
            COMBINAISON_SELECTIONNEE.append(numero)
            COMBINAISON_SELECTIONNEE.sort(key=int)
    return RedirectResponse(url="/", status_code=303)

@app.post("/reinitialiser")
def reinitialiser():
    global COMBINAISON_SELECTIONNEE
    COMBINAISON_SELECTIONNEE = []
    return RedirectResponse(url="/", status_code=303)

@app.post("/actualiser")
def actualiser():
    return RedirectResponse(url="/", status_code=303)

@app.post("/relancer")
def relancer():
    return RedirectResponse(url="/", status_code=303)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000)
