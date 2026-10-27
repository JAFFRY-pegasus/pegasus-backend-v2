#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main.py
Moteur SGE unifié avec API FastAPI (Projet pegasus-backend-v2)
"""

import html
import json
import os
import re
from datetime import datetime as _datetime
from collections import Counter
from itertools import combinations

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

# 1. IMPORTATIONS DES MODULES LOCAUX
from historique import HISTORIQUE_SGE_DATA
from extraction import obtenir_quinte_du_jour

# Initialisation de l'API
app = FastAPI()

# ✅ URL de l'image de fond (à la racine du dépôt GitHub)
IMAGE_URL = "https://raw.githubusercontent.com/JAFFRY-pegasus/pegasus-backend-v2/main/Horse-racing-1.jpg"


# --- CONFIGURATIONS ET MATRICES DU MOTEUR SGE ---

OPPOSITIONS_VERTICALES = {
    1: 9, 2: 10, 3: 11, 4: 12, 5: 13, 6: 14, 7: 15, 8: 16,
    9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 6, 15: 7, 16: 8
}

COEFFICIENTS_RESONANCE = {
    0: 0.5, 
    1: 1.0, 
    2: 1.5, 
    3: 2.0, 
    4: 2.5, 
    5: 3.0
}


# --- LOGIQUE ALGORITHMIQUE SGE ---

def calculer_poids_axes():
    """
    Analyse l'historique complet pour calculer le poids de chaque axe vertical.
    """
    frequence_axes = Counter()
    for course in HISTORIQUE_SGE_DATA:
        arr = course["arrivee"]
        for num in arr:
            oppose = OPPOSITIONS_VERTICALES.get(num)
            if oppose and oppose in arr:
                axe = tuple(sorted([num, oppose]))
                frequence_axes[axe] += 1
    # Division par 2 car chaque paire d'axe est comptée deux fois (a->b et b->a)
    return {axe: freq // 2 for axe, freq in frequence_axes.items()}


# Initialisation des poids d'axes dès le chargement du serveur FastAPI
POIDS_AXES_HISTORIQUE = calculer_poids_axes()


def calculer_score_sge(combinaison):
    """
    Calcule le score SGE d'une combinaison de 5 chevaux selon les résonances d'axes.
    """
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
    """
    Génère la combinaison à plus fort potentiel à partir d'une ligne de référence.
    """
    valides = [n for n in combinaison_ref if 1 <= n <= 16]
    if len(valides) < 5:
        complements = [n for n in [11, 4, 7, 5, 9, 1, 2, 3, 6, 8, 10, 12, 13, 14, 15, 16] if n not in valides]
        valides = (valides + complements)[:5]
    opposes = [OPPOSITIONS_VERTICALES[n] for n in valides if n in OPPOSITIONS_VERTICALES]
    candidats = list(dict.fromkeys(valides + opposes))
    
    scores_candidats = []
    for combo in combinations(candidats, 5):
        score = calculer_score_sge(list(combo))
        scores_candidats.append((score, list(combo)))
    
    scores_candidats.sort(key=lambda x: x[0], reverse=True)
    return scores_candidats[0][1] if scores_candidats else valides[:5]


def calculer_stats_chevaux():
    """
    Extrait le TOP 3 des chevaux les plus fréquents de l'historique global.
    """
    counter = Counter()
    total = len(HISTORIQUE_SGE_DATA)
    for course in HISTORIQUE_SGE_DATA:
        for num in course["arrivee"][:5]:
            counter[num] += 1
    top3 = counter.most_common(3)
    return [(num, count, round(count / total * 100, 1)) for num, count in top3]


# --- ROUTES ENDPOINTS FASTAPI (WEB INTERFACE) ---

@app.get("/", response_class=HTMLResponse)
async def page_accueil():
    """
    Route principale servant l'interface utilisateur.
    Exemple basique d'intégration de l'image de fond et des statistiques.
    """
    stats = calculer_stats_chevaux()
    stats_html = "".join([f"<li>Cheval N°{n} : {occ} fois ({p}%)</li>" for n, occ, p in stats])
    
    content = f"""
    <html>
        <head>
            <title>Moteur Pegasus SGE</title>
            <style>
                body {{
                    background-image: url('{IMAGE_URL}');
                    background-size: cover;
                    font-family: Arial, sans-serif;
                    color: white;
                    text-shadow: 2px 2px 4px #000000;
                    padding: 50px;
                }}
                .container {{
                    background: rgba(0, 0, 0, 0.7);
                    padding: 20px;
                    border-radius: 10px;
                    max-width: 600px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Moteur SGE - Pegasus Backend v2</h1>
                <p>Base historique connectée : {len(HISTORIQUE_SGE_DATA)} quintés.</p>
                <h3>TOP 3 Historique des chevaux :</h3>
                <ul>{stats_html}</ul>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=content)
