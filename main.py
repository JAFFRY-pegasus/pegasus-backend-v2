#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main.py
Moteur SGE unifié avec API FastAPI et gestion hybride du robot (Automatique + Clic Manuel)
Projet : pegasus-backend-v2
"""

import html
import json
import os
import re
from datetime import datetime as _datetime
from collections import Counter
from itertools import combinations

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from apscheduler.schedulers.background import BackgroundScheduler

# Importations des modules locaux
from historique import HISTORIQUE_SGE_DATA
from extraction import obtenir_quinte_du_jour

app = FastAPI()

# Configuration des ressources graphiques
IMAGE_URL = "https://githubusercontent.com"
FICHIER_SAUVEGARDE = "quinte_du_jour.json"

# Structure de mémoire globale pour l'affichage de l'interface utilisateur
DONNEES_QUINTE_DU_JOUR = {
    "hippodrome": "INCONNU", 
    "discipline": "Inconnue", 
    "distance": 0, 
    "partants": 0, 
    "heure": "--:--", 
    "nom_course": "Aucune Course Trouvée",
    "derniere_maj": "--:--",
    "statut_robot": "En attente du cycle"
}


# =====================================================================
# --- CONFIGURATIONS ET MATRICES DU MOTEUR SGE -----------------------
# =====================================================================

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


# =====================================================================
# --- LOGIQUE ALGORITHMIQUE SGE ---------------------------------------
# =====================================================================

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
    # Division par 2 car chaque paire d'axe est lue deux fois (num puis oppose)
    return {axe: freq // 2 for axe, freq in frequence_axes.items()}


# Initialisation dynamique du poids des axes par rapport à l'historique global
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


# =====================================================================
# --- SYNCHRONISATION DES DONNÉES & AUTOMATISATION DU ROBOT -----------
# =====================================================================

def charger_donnees_locales():
    """
    Charge les données du fichier JSON local au démarrage du serveur si disponible.
    """
    global DONNEES_QUINTE_DU_JOUR
    if os.path.exists(FICHIER_SAUVEGARDE):
        try:
            with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as f:
                DONNEES_QUINTE_DU_JOUR = json.load(f)
            print("[*] Données du quinté restaurées depuis le fichier local.")
        except Exception as e:
            print(f"[!] Impossible de lire le fichier de sauvegarde : {e}")


def executer_scraping_quotidien(mode=""):
    """
    Pilote l'extraction de l'API PMU via extraction.py, applique les calculs 
    et enregistre le résultat dans la mémoire globale et le fichier local.
    """
    global DONNEES_QUINTE_DU_JOUR
    horodatage = _datetime.now().strftime("%H:%M")
    print(f"[{_datetime.now().strftime('%H:%M:%S')}] [{mode}] Le robot interroge l'API PMU...")
    
    try:
        # Appel de la fonction d'extraction externe
        nouvelles_donnees = obtenir_quinte_du_jour()
        
        # Injection des indicateurs système de suivi temporels
        nouvelles_donnees["derniere_maj"] = horodatage
        nouvelles_donnees["statut_robot"] = f"Actif ({mode})"
        
        DONNEES_QUINTE_DU_JOUR = nouvelles_donnees
        
        # Écriture physique sur le disque pour prévenir les crashs
        with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as f:
            json.dump(DONNEES_QUINTE_DU_JOUR, f, ensure_ascii=False, indent=4)
            
        print(f"[{_datetime.now().strftime('%H:%M:%S')}] [{mode}] Données SGE synchronisées et figées avec succès.")
    except Exception as e:
        print(f"[!] Échec de la récupération des données ({mode}) : {e}")
        DONNEES_QUINTE_DU_JOUR["statut_robot"] = f"Erreur de flux à {horodatage}"


# --- PLANIFICATEUR DE TÂCHES EN ARRIÈRE-PLAN (CRON) ---

scheduler = BackgroundScheduler()

# 1. À 05h00 : Injection massive initiale (Données de base figées depuis l'API PMU)
scheduler.add_job(executer_scraping_quotidien, 'cron', hour=5, minute=0, args=["INJECTION_05H00"], id="pmu_massive")

# 2. À 08h30 : Ouverture officielle des terminaux de paris
scheduler.add_job(executer_scraping_quotidien, 'cron', hour=8, minute=30, args=["OUVERTURE_PARIS"], id="pmu_ouverture")

# 3. De 08h30 à 20h00 : Flux dynamique tendu toutes les 15 minutes (Variations de cotes & non-partants)
scheduler.add_job(executer_scraping_quotidien, 'cron', hour='8-19', minute='0,15,30,45', args=["FLUX_15MIN"], id="pmu_tendu")

scheduler.start()

# =====================================================================
# --- ENDPOINTS FASTAPI (INTERFACE WEB GRAPHIQUE) --------------------
# =====================================================================

@app.get("/", response_class=HTMLResponse)
async def page_accueil():
    """
    Route principale servant l'interface utilisateur enrichie avec 
    les données dynamiques de la variable globale.
    """
    global DONNEES_QUINTE_DU_JOUR
    date_formatee = _datetime.now().strftime("%A %d %B %Y")
    
    # Récupération et formatage des statistiques historiques SGE
    stats = calculer_stats_chevaux()
    stats_html = "".join([f"<li>Cheval N°{num:02d} : {count} fois ({pct}%)</li>" for num, count, pct in stats])
    
    content = f"""
    <html>
        <head>
            <title>PEGASUS - Moteur SGE</title>
            <style>
                body {{ 
                    background-image: url('{IMAGE_URL}'); 
                    background-size: cover; 
                    background-attachment: fixed;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    color: white; 
                    margin: 0;
                    padding: 20px;
                }}
                .top-bar {{ 
                    display: flex; 
                    gap: 15px; 
                    justify-content: center; 
                    margin-bottom: 25px; 
                }}
                .btn {{ 
                    padding: 12px 24px; 
                    border-radius: 20px; 
                    border: none; 
                    font-weight: bold; 
                    cursor: pointer; 
                    color: white; 
                    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                    transition: transform 0.2s;
                }}
                .btn:hover {{ transform: scale(1.05); }}
                .btn-green {{ background-color: #06d6a0; }}
                .btn-purple {{ background-color: #7209b7; }}
                .btn-orange {{ background-color: #ff9f1c; margin-top: 10px; width: 100%; border-radius: 6px; }}
                .block {{ 
                    background: rgba(16, 24, 48, 0.95); 
                    padding: 30px; 
                    border-radius: 12px; 
                    max-width: 850px; 
                    margin: 0 auto 30px auto; 
                    border: 1px solid #233554;
                    box-shadow: 0 8px 16px rgba(0,0,0,0.5);
                }}
                .alert {{ 
                    background: rgba(6, 214, 160, 0.15); 
                    border: 1px solid #06d6a0; 
                    color: #06d6a0; 
                    padding: 12px; 
                    border-radius: 6px; 
                    font-size: 13.5px;
                    margin-bottom: 20px;
                    font-weight: 500;
                }}
                .row {{ display: flex; gap: 20px; margin-bottom: 15px; }}
                .col {{ flex: 1; display: flex; flex-direction: column; }}
                label {{ color: #ff9f1c; font-size: 12px; margin-bottom: 6px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }}
                input {{
                    background: #0f172a;
                    border: 1px solid #334155;
                    color: #38bdf8;
                    padding: 12px;
                    border-radius: 6px;
                    font-size: 14.5px;
                    font-weight: 500;
                }}
                input[readonly] {{ color: #94a3b8; background: #1e293b; }}
                .input-combo {{ text-align: center; font-size: 18px; font-weight: bold; color: #64ffda; }}
                ul {{ padding-left: 20px; color: #cbd5e1; }}
                li {{ margin-bottom: 6px; }}
            </style>
        </head>
        <body>
            <div class="top-bar">
                <form action="/actualiser" method="post"><button type="submit" class="btn btn-green">🔄 Actualiser les données</button></form>
                <form action="/actualiser" method="post"><button type="submit" class="btn btn-purple">🤖 Relancer le robot</button></form>
            </div>

            <!-- 1. INFORMATIONS SUR LE QUINTÉ DU JOUR -->
            <div class="block">
                <h2 style="color: #ff9f1c; margin-top: 0; border-bottom: 2px solid #ff9f1c; padding-bottom: 8px;">1. INFORMATIONS SUR LE QUINTÉ DU JOUR</h2>
                
                <div class="alert">
                    ✅ Aucun non-partant détecté à ce stade • {DONNEES_QUINTE_DU_JOUR.get('partants', 0)} partants confirmés • Dernière vérification : {DONNEES_QUINTE_DU_JOUR.get('derniere_maj')} — [Statut : {DONNEES_QUINTE_DU_JOUR.get('statut_robot')}]
                </div>

                <div class="row">
                    <div class="col">
                        <label>Date de la course (automatique) :</label>
                        <input type="text" value="{date_formatee}" readonly>
                    </div>
                </div>

                <div class="row">
                    <div class="col">
                        <label>Hippodrome :</label>
                        <input type="text" value="{DONNEES_QUINTE_DU_JOUR.get('hippodrome')}" readonly>
                    </div>
                    <div class="col">
                        <label>Discipline :</label>
                        <input type="text" value="{DONNEES_QUINTE_DU_JOUR.get('discipline')}" readonly>
                    </div>
                </div>

                <div class="row">
                    <div class="col">
                        <label>Nom de la course :</label>
                        <input type="text" value="{DONNEES_QUINTE_DU_JOUR.get('nom_course')}" readonly>
                    </div>
                    <div class="col">
                        <label>Distance :</label>
                        <input type="text" value="{DONNEES_QUINTE_DU_JOUR.get('distance')}" readonly>
                    </div>
                </div>

                <div class="row">
                    <div class="col">
                        <label>Nombre de partants déclarés :</label>
                        <input type="text" value="{DONNEES_QUINTE_DU_JOUR.get('partants')}" readonly>
                    </div>
                    <div class="col">
                        <label>Heure de départ :</label>
                        <input type="text" value="{DONNEES_QUINTE_DU_JOUR.get('heure')}" readonly>
                    </div>
                </div>
            </div>

            <!-- 2. INDICATEURS DE CONTRÔLE -->
            <div class="block">
                <h3 style="color: #38bdf8; margin-top: 0; border-bottom: 2px solid #38bdf8; padding-bottom: 8px;">2. INDICATEURS DE CONTRÔLE DE LA BASE GLOBALE</h3>
                <p>Analyse effectuée sur un historique de <strong>{len(HISTORIQUE_SGE_DATA)}</strong> courses.</p>
                <h4>TOP 3 des chevaux les plus fréquents :</h4>
                <ul>{stats_html}</ul>
            </div>

            <!-- 3. SIMULATEUR MATHÉMATIQUE SGE -->
            <div class="block">
                <h3 style="color: #64ffda; margin-top: 0; border-bottom: 2px solid #64ffda; padding-bottom: 8px;">3. SIMULATEUR MATHÉMATIQUE SGE</h3>
                <p>Saisissez une combinaison de référence (5 chevaux entre 1 et 16) pour évaluer sa résonance d'axes.</p>
                
                <form action="/calculer-sge" method="post">
                    <div class="row">
                        <div class="col"><label>Ch 1</label><input type="number" name="c1" class="input-combo" min="1" max="16" required></div>
                        <div class="col"><label>Ch 2</label><input type="number" name="c2" class="input-combo" min="1" max="16" required></div>
                        <div class="col"><label>Ch 3</label><input type="number" name="c3" class="input-combo" min="1" max="16" required></div>
                        <div class="col"><label>Ch 4</label><input type="number" name="c4" class="input-combo" min="1" max="16" required></div>
                        <div class="col"><label>Ch 5</label><input type="number" name="c5" class="input-combo" min="1" max="16" required></div>
                    </div>
                    <button type="submit" class="btn btn-orange">🧮 Lancer l'analyse SGE</button>
                </form>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=content)


@app.post("/calculer-sge", response_class=HTMLResponse)
async def traiter_simulation_sge(
    c1: int = Form(...),
    c2: int = Form(...),
    c3: int = Form(...),
    c4: int = Form(...),
    c5: int = Form(...),
):
    """
    Intercepte les 5 chevaux saisis dans le simulateur, calcule le score SGE
    et génère le pronostic automatique optimal associé.
    """
    combinaison_saisie = [c1, c2, c3, c4, c5]
    
    # Calculs algorithmiques via vos fonctions SGE existantes
    score_combinaison = calculer_score_sge(combinaison_saisie)
    pronostic_optimal = generer_prono_automatique(combinaison_saisie)
    score_optimal = calculer_score_sge(pronostic_optimal)
    
    content = f"""
    <html>
        <head>
            <title>Résultats Analyse SGE</title>
            <style>
                body {{ 
                    background-image: url('{IMAGE_URL}'); 
                    background-size: cover; 
                    background-attachment: fixed;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    color: white; 
                    margin: 0;
                    padding: 40px;
                    text-align: center;
                }}
                .box {{ 
                    background: rgba(16, 24, 48, 0.95); 
                    padding: 40px; 
                    border-radius: 12px; 
                    border: 1px solid #233554; 

max-width: 650px;
margin: 40px auto;
box-shadow: 0 8px 16px rgba(0,0,0,0.5);
}}
.highlight {{ color: #64ffda; font-size: 26px; font-weight: bold; }}
.orange {{ color: #ff9f1c; font-size: 26px; font-weight: bold; }}
.btn-back {{
display: inline-block;
padding: 12px 24px;
background: #38bdf8;
color: white;
border-radius: 20px;
text-decoration: none;
margin-top: 25px;
font-weight: bold;
box-shadow: 0 4px 6px rgba(0,0,0,0.3);
}}

            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=content)


@app.post("/actualiser")
async def clic_robot_manuel():
    """
    Intercepte l'appel POST déclenché par l'un des boutons de l'interface.
    Force le scraping immédiat des API PMU puis redirige vers la page d'accueil.
    """
    executer_scraping_quotidien(mode="CLIC_MANUEL_INTERFACE")
    return RedirectResponse(url="/", status_code=303)


# =====================================================================
# --- INITIALISATION AU LANCEMENT DE L'APPLICATION --------------------
# =====================================================================

@app.on_event("startup")
async def startup_event():
    """
    S'exécute automatiquement lors de l'initialisation du serveur Uvicorn.
    Restaure la session précédente ou force un rafraîchissement.
    """
    charger_donnees_locales()
    if DONNEES_QUINTE_DU_JOUR["partants"] == 0:
        executer_scraping_quotidien(mode="INITIALISATION_SERVEUR")
