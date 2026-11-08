#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main.py v3.15
Moteur SGE + Grille fixe 1-20 + Score amorti + Persistance combinaison utilisateur 
+ Combinaison propriétaire (référence) + Pronostic jusqu'à 8 chevaux
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime as _datetime
from collections import Counter
from itertools import combinations

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# =====================================================================
# CONFIGURATION & CHEMINS
# =====================================================================
print("=" * 60, flush=True)
print("🚀 DÉMARRAGE DE PEGASUS BACKEND V3.15 (Combinaison propriétaire)", flush=True)
print("=" * 60, flush=True)

CHEMIN_BASE = os.path.dirname(os.path.abspath(__file__))
CHEMIN_TEMPLATES = os.path.join(CHEMIN_BASE, "templates")
CHEMIN_STATIC = os.path.join(CHEMIN_BASE, "static")
FICHIER_SAUVEGARDE = os.path.join(CHEMIN_BASE, "quinte_du_jour.json")
FICHIER_COMBINAISON = os.path.join(CHEMIN_BASE, "combinaison.json")
FICHIER_COMBINAISON_PROPRIO = os.path.join(CHEMIN_BASE, "combinaison_proprio.json")

# =====================================================================
# IMPORTS DES MODULES
# =====================================================================
try:
    from historique import HISTORIQUE_SGE_DATA
    print(f"✅ historique.py importé — {len(HISTORIQUE_SGE_DATA)} courses", flush=True)
except Exception as e:
    print(f"❌ ERREUR historique.py: {e}", flush=True)
    HISTORIQUE_SGE_DATA = []

try:
    from extraction import obtenir_quinte_du_jour
    print("✅ extraction.py importé", flush=True)
    EXTRACTION_DISPONIBLE = True
    ERREUR_EXTRACTION = None
except Exception as e:
    print(f"⚠️ extraction.py non disponible: {e}", flush=True)
    obtenir_quinte_du_jour = None
    EXTRACTION_DISPONIBLE = False
    ERREUR_EXTRACTION = f"{type(e).__name__}: {e}"

# =====================================================================
# APPLICATION FASTAPI
# =====================================================================
app = FastAPI(title="Pegasus Backend v3.15")

if os.path.isdir(CHEMIN_STATIC):
    app.mount("/static", StaticFiles(directory=CHEMIN_STATIC), name="static")
    print(f"✅ Dossier static monté sur /static", flush=True)

templates = Jinja2Templates(directory=CHEMIN_TEMPLATES)
DEBUG = os.environ.get("DEBUG", "0") == "1"
TTL_CACHE_SECONDS = 900

# =====================================================================
# CONSTANTES DU MOTEUR SGE
# =====================================================================
COMBINAISON_SELECTIONNEE = ["13", "6", "5", "12", "11"]
COMBINAISON_PROPRIO = ["7", "1", "15", "4", "12", "8", "11", "2"]  # Valeur par défaut

_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

def _date_francaise():
    d = _datetime.now()
    return f"{_JOURS[d.weekday()].capitalize()} {d.day} {_MOIS[d.month - 1]} {d.year}"

OPPOSITIONS_VERTICALES = {
    1: 9, 2: 10, 3: 11, 4: 12, 5: 13, 6: 14, 7: 15, 8: 16,
    9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 6, 15: 7, 16: 8,
    17: 17, 18: 18, 19: 19, 20: 20
}
COEFFICIENTS_RESONANCE = {0: 0.5, 1: 1.0, 2: 1.5, 3: 2.0, 4: 2.5, 5: 3.0}

# =====================================================================
# FONCTIONS DE PERSISTANCE
# =====================================================================
def charger_combinaison():
    global COMBINAISON_SELECTIONNEE
    try:
        if os.path.exists(FICHIER_COMBINAISON):
            with open(FICHIER_COMBINAISON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'combinaison' in data and isinstance(data['combinaison'], list):
                    COMBINAISON_SELECTIONNEE = data['combinaison']
                    print(f"✅ Combinaison utilisateur chargée: {COMBINAISON_SELECTIONNEE}", flush=True)
    except Exception as e:
        print(f"⚠️ Erreur chargement combinaison: {e}", flush=True)

def sauvegarder_combinaison():
    try:
        with open(FICHIER_COMBINAISON, 'w', encoding='utf-8') as f:
            json.dump({'combinaison': COMBINAISON_SELECTIONNEE}, f, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde combinaison: {e}", flush=True)

def charger_combinaison_proprio():
    global COMBINAISON_PROPRIO
    try:
        if os.path.exists(FICHIER_COMBINAISON_PROPRIO):
            with open(FICHIER_COMBINAISON_PROPRIO, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'combinaison' in data and isinstance(data['combinaison'], list):
                    COMBINAISON_PROPRIO = data['combinaison']
                    print(f"✅ Combinaison propriétaire chargée: {COMBINAISON_PROPRIO}", flush=True)
    except Exception as e:
        print(f"⚠️ Erreur chargement combinaison proprio: {e}. Valeur par défaut utilisée.", flush=True)

charger_combinaison()
charger_combinaison_proprio()

# =====================================================================
# DONNÉES GLOBALES
# =====================================================================
DONNEES_QUINTE_DU_JOUR = {
    "hippodrome": "EN ATTENTE", "discipline": "Inconnue", "distance": 0,
    "nb_partants": 16, "heure_depart": "--:--", "nom_course": "Chargement...",
    "date": _date_francaise(), "synthese_presse": "", "statut_robot": "Actif",
    "isQuinte": None, "numReunion": None, "numOrdre": None, "mode_manuel": False
}

DERNIERE_VERIFICATION = 0.0
DERNIERE_VERIFICATION_HHMM = "--:--"
FLAG_QUINTE_VALIDE = None

CLEFS_ATTENDUES = [
    "hippodrome", "discipline", "distance", "nb_partants",
    "heure_depart", "nom_course", "date", "synthese_presse", "statut_robot",
    "isQuinte", "numReunion", "numOrdre", "mode_manuel"
]

# =====================================================================
# LOGIQUE D'ACTUALISATION
# =====================================================================
def _fusionner(nouvelles_donnees):
    global DONNEES_QUINTE_DU_JOUR, FLAG_QUINTE_VALIDE
    if not isinstance(nouvelles_donnees, dict): return False
    flag = nouvelles_donnees.get("isQuinte")
    if flag is True: FLAG_QUINTE_VALIDE = True
    elif flag is False: FLAG_QUINTE_VALIDE = False; return False
    else: FLAG_QUINTE_VALIDE = None
    
    maj = False
    for clef in CLEFS_ATTENDUES:
        valeur = nouvelles_donnees.get(clef)
        if valeur is not None and valeur != "" and valeur != []:
            DONNEES_QUINTE_DU_JOUR[clef] = valeur
            maj = True
    return maj

def rafraichir_donnees_quinte(force=False):
    global DERNIERE_VERIFICATION, DERNIERE_VERIFICATION_HHMM
    maintenant = time.time()
    if not force and (maintenant - DERNIERE_VERIFICATION) < TTL_CACHE_SECONDS:
        if DONNEES_QUINTE_DU_JOUR.get("mode_manuel"): return DONNEES_QUINTE_DU_JOUR
        return DONNEES_QUINTE_DU_JOUR

    source = "aucune"
    if EXTRACTION_DISPONIBLE and not DONNEES_QUINTE_DU_JOUR.get("mode_manuel"):
        try:
            resultat = obtenir_quinte_du_jour()
            if resultat and _fusionner(resultat):
                source = "extraction.py"
                DONNEES_QUINTE_DU_JOUR["mode_manuel"] = False
        except Exception as e: print(f"⚠️ Extraction API échouée: {e}", flush=True)

    if source == "aucune":
        try:
            with open(FICHIER_SAUVEGARDE, encoding="utf-8") as f:
                secours = json.load(f)
            if secours and _fusionner(secours): source = "quinte_du_jour.json"
        except Exception: pass

    if source == "aucune":
        print("⚠️ Activation du MODE MANUEL", flush=True)
        DONNEES_QUINTE_DU_JOUR["statut_robot"] = "Mode Manuel"
        DONNEES_QUINTE_DU_JOUR["mode_manuel"] = True
        DONNEES_QUINTE_DU_JOUR["date"] = _date_francaise()
        source = "manuel"

    DERNIERE_VERIFICATION = maintenant
    DERNIERE_VERIFICATION_HHMM = _datetime.now().strftime("%H:%M")
    print(f"🔄 Actualisation terminée (source: {source})", flush=True)
    return DONNEES_QUINTE_DU_JOUR

# =====================================================================
# SCHEDULER
# =====================================================================
SCHEDULER_ACTIF = False
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: rafraichir_donnees_quinte(force=True), "interval", minutes=30)
    scheduler.start()
    SCHEDULER_ACTIF = True
except Exception as e: print(f"ℹ️ Scheduler inactif: {e}", flush=True)

# =====================================================================
# MOTEUR SGE (AVEC AMORTISSEMENT PHYSIQUE)
# =====================================================================
def calculer_poids_axes():
    frequence_axes = Counter()
    for course in HISTORIQUE_SGE_DATA:
        arr = course.get("arrivee", [])
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
    taille_combinaison = len(combinaison)
    
    # Frottement / Amortissement physique
    facteur_amortissement = 1.0 / (1.0 + (taille_combinaison - 5) * 0.15) 
    ponderation = COEFFICIENTS_RESONANCE.get(nombre_axes, 2.0)
    score_final = int(score_brut * ponderation * facteur_amortissement)
    
    print(f"🔍 DEBUG SCORE: Combo={combinaison} | Taille={taille_combinaison} | Axes={nombre_axes} | Score Final={score_final}", flush=True)
    return score_final

def generer_prono_automatique(combinaison_ref, nombre_max=5):
    """Génère un pronostic basé sur la combinaison de référence.
    nombre_max permet de retourner entre 5 et 8 chevaux."""
    valides = [int(n) for n in combinaison_ref if n.isdigit() and 1 <= int(n) <= 20]
    
    # Si pas assez de chevaux valides, on complète avec une liste par défaut
    if len(valides) < nombre_max:
        liste_defaut = [11, 4, 7, 5, 9, 1, 2, 3, 6, 8, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        complements = [n for n in liste_defaut if n not in valides]
        valides = (valides + complements)[:nombre_max]
    
    # On ajoute les opposés des chevaux valides pour enrichir les candidats
    opposes = [OPPOSITIONS_VERTICALES[n] for n in valides if n in OPPOSITIONS_VERTICALES]
    candidats = list(dict.fromkeys(valides + opposes))
    
    # Si trop de candidats, on limite pour éviter un calcul trop long
    if len(candidats) > 16:
        candidats = candidats[:16]
    
    scores_candidats = []
    for combo in combinations(candidats, nombre_max):
        score = calculer_score_sge(list(combo))
        scores_candidats.append((score, list(combo)))
    
    scores_candidats.sort(key=lambda x: x[0], reverse=True)
    
    if scores_candidats:
        return [str(x) for x in scores_candidats[0][1]]
    return [str(x) for x in valides[:nombre_max]]

# =====================================================================
# ROUTES
# =====================================================================
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    global COMBINAISON_SELECTIONNEE, COMBINAISON_PROPRIO
    rafraichir_donnees_quinte()

    # ✅ PRONOSTIC PEGASUS CALCULÉ À PARTIR DE LA COMBINAISON PROPRIÉTAIRE
    # Le nombre de chevaux du pronostic = nombre de chevaux de la combinaison proprio (5 à 8)
    nb_chevaux_proprio = len(COMBINAISON_PROPRIO)
    prono_pegasus = generer_prono_automatique(COMBINAISON_PROPRIO, nombre_max=nb_chevaux_proprio)
    
    # ✅ SCORE DE LA COMBINAISON PROPRIÉTAIRE
    combo_proprio_int = [int(n) for n in COMBINAISON_PROPRIO if n.isdigit()]
    if 5 <= len(combo_proprio_int) <= 8:
        score_proprio = calculer_score_sge(combo_proprio_int)
    else:
        score_proprio = 0
    
    # Stats classiques
    counter = Counter()
    total_courses = len(HISTORIQUE_SGE_DATA)
    for course in HISTORIQUE_SGE_DATA:
        for num in course.get("arrivee", [])[:5]:
            counter[num] += 1

    top_chevaux = [
        {"numero": f"{n:02d}", "occurrences": c, 
         "pourcentage": round((c/total_courses)*100, 1) if total_courses > 0 else 0} 
        for n, c in counter.most_common(3)
    ]

    info_quinte = {k: DONNEES_QUINTE_DU_JOUR.get(k, "") for k in CLEFS_ATTENDUES}
    
    synthese_brute = str(DONNEES_QUINTE_DU_JOUR.get("synthese_presse", ""))
    jetons_presse = [x.strip() for x in synthese_brute.split("-") if x.strip().isdigit()]
    if not jetons_presse: jetons_presse = ["?", "?", "?", "?", "?"]

    jetons = {
        "presse": jetons_presse,
        "pegasus": prono_pegasus,
        "arrivee": ["4", "5", "9", "10", "11"],
        "retenus": COMBINAISON_SELECTIONNEE
    }

    combo_int = [int(n) for n in COMBINAISON_SELECTIONNEE if n.isdigit()]
    if 5 <= len(combo_int) <= 8:
        score_utilisateur = calculer_score_sge(combo_int)
    else:
        score_utilisateur = 0

    nb_partants_brut = info_quinte.get('nb_partants', 16)
    try:
        nb_partants = max(8, min(20, int(nb_partants_brut)))
    except:
        nb_partants = 20

    stats = {
        "historique_courses": total_courses, 
        "taux_reussite": 20,
        "nb_dernieres_courses": 5, 
        "ponderation_pegasus": score_utilisateur,
        "ponderation_combinaison": score_utilisateur, 
        "moyenne_chevaux_trouves": "0.00",
        "niveau_performance": "Faible", 
        "top_chevaux_frequents": top_chevaux
    }

    combinaison_saisie = " - ".join(COMBINAISON_SELECTIONNEE)
    tag_quinte = "✅ Quinté vérifié" if FLAG_QUINTE_VALIDE is True else \
                 "⚠️ PAS un Quinté" if FLAG_QUINTE_VALIDE is False else "Quinté non vérifié"
    code_pmu = f"R{DONNEES_QUINTE_DU_JOUR.get('numReunion','?')}C{DONNEES_QUINTE_DU_JOUR.get('numOrdre','?')}"
    message_statut = f"{tag_quinte} • {code_pmu} • {nb_partants} partants • Vérif: {DERNIERE_VERIFICATION_HHMM}"

    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "statut_robot": DONNEES_QUINTE_DU_JOUR.get("statut_robot", "Actif"),
            "message_statut": message_statut,
            "info_quinte": info_quinte,
            "combinaison_saisie": combinaison_saisie,
            "jetons": jetons, 
            "stats": stats,
            "nb_partants": nb_partants,
            # ✅ NOUVELLES VARIABLES POUR LA COMBINAISON PROPRIÉTAIRE
            "combinaison_proprio": COMBINAISON_PROPRIO,
            "prono_proprio": prono_pegasus,
            "score_proprio": score_proprio
        }
    )

# =====================================================================
# ROUTES SÉCURISÉES (GET + POST)
# =====================================================================

@app.get("/calculer")
def calculer_get():
    return RedirectResponse(url="/", status_code=302)

@app.post("/calculer")
def calculer(combinaison_utilisateur: str = Form(...)):
    global COMBINAISON_SELECTIONNEE
    extraits = [n.strip() for n in combinaison_utilisateur.split("-") if n.strip().isdigit()]
    if extraits: 
        COMBINAISON_SELECTIONNEE = extraits[:8]
        sauvegarder_combinaison()
    return RedirectResponse(url="/", status_code=303)

@app.get("/selectionner/{numero}")
def selectionner_grille(numero: str):
    global COMBINAISON_SELECTIONNEE
    if numero in COMBINAISON_SELECTIONNEE:
        COMBINAISON_SELECTIONNEE.remove(numero)
    elif len(COMBINAISON_SELECTIONNEE) < 8:
        COMBINAISON_SELECTIONNEE.append(numero)
        COMBINAISON_SELECTIONNEE.sort(key=lambda x: int(x))
    sauvegarder_combinaison()
    return RedirectResponse(url="/", status_code=303)

@app.get("/reinitialiser")
def reinitialiser_get():
    return RedirectResponse(url="/", status_code=302)

@app.post("/reinitialiser")
def reinitialiser():
    global COMBINAISON_SELECTIONNEE
    COMBINAISON_SELECTIONNEE = []
    sauvegarder_combinaison()
    return RedirectResponse(url="/", status_code=303)

@app.get("/actualiser")
def actualiser_get():
    return RedirectResponse(url="/", status_code=302)

@app.post("/actualiser")
def actualiser():
    DONNEES_QUINTE_DU_JOUR["mode_manuel"] = False
    rafraichir_donnees_quinte(force=True)
    return RedirectResponse(url="/", status_code=303)

@app.get("/relancer")
def relancer_get():
    return RedirectResponse(url="/", status_code=302)

@app.post("/relancer")
def relancer():
    global COMBINAISON_SELECTIONNEE
    DONNEES_QUINTE_DU_JOUR["mode_manuel"] = False
    rafraichir_donnees_quinte(force=True)
    COMBINAISON_SELECTIONNEE = ["13", "6", "5", "12", "11"]
    sauvegarder_combinaison()
    return RedirectResponse(url="/", status_code=303)

@app.get("/saisie-manuelle")
def saisie_manuelle_get():
    return RedirectResponse(url="/", status_code=302)

@app.post("/saisie-manuelle")
def saisie_manuelle(
    hippodrome: str = Form(...), nom_course: str = Form(...),
    nb_partants: int = Form(...), heure_depart: str = Form(...),
    discipline: str = Form("TROT ATTELÉ"), distance: int = Form(0)
):
    global DONNEES_QUINTE_DU_JOUR
    DONNEES_QUINTE_DU_JOUR.update({
        "hippodrome": hippodrome.upper(), "nom_course": nom_course,
        "nb_partants": nb_partants, "heure_depart": heure_depart,
        "discipline": discipline.upper(), "distance": distance,
        "statut_robot": "Données Manuelles", "mode_manuel": True,
        "isQuinte": True, "numReunion": 1, "numOrdre": 5
    })
    try:
        with open(FICHIER_SAUVEGARDE, 'w', encoding='utf-8') as f:
            json.dump(DONNEES_QUINTE_DU_JOUR, f, ensure_ascii=False)
    except Exception: pass
    return RedirectResponse(url="/", status_code=303)

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host='0.0.0.0', port=port)
