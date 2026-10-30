#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main.py v2.7
Moteur SGE unifié avec mode manuel de secours (fallback)
Compatible Starlette récent + Gestion échec API PMU
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
from fastapi.templating import Jinja2Templates

# =====================================================================
# CONFIGURATION & IMPORTS
# =====================================================================
print("=" * 60, flush=True)
print("🚀 DÉMARRAGE DE PEGASUS BACKEND V2.7", flush=True)
print("=" * 60, flush=True)

CHEMIN_BASE = os.path.dirname(os.path.abspath(__file__))
CHEMIN_TEMPLATES = os.path.join(CHEMIN_BASE, "templates")
FICHIER_SAUVEGARDE = os.path.join(CHEMIN_BASE, "quinte_du_jour.json")

try:
    from historique import HISTORIQUE_SGE_DATA
    print(f"✅ historique.py importé — {len(HISTORIQUE_SGE_DATA)} courses", flush=True)
except Exception as e:
    print(f"❌ ERREUR historique.py: {e}", flush=True)
    sys.exit(1)

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

app = FastAPI(title="Pegasus Backend v2.7")
templates = Jinja2Templates(directory=CHEMIN_TEMPLATES)
DEBUG = os.environ.get("DEBUG", "0") == "1"
TTL_CACHE_SECONDS = 900

COMBINAISON_SELECTIONNEE = ["13", "6", "5", "12", "11"]

_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

def _date_francaise():
    d = _datetime.now()
    return f"{_JOURS[d.weekday()].capitalize()} {d.day} {_MOIS[d.month - 1]} {d.year}"

DONNEES_QUINTE_DU_JOUR = {
    "hippodrome": "EN ATTENTE",
    "discipline": "Inconnue",
    "distance": 0,
    "nb_partants": 0,
    "heure_depart": "--:--",
    "nom_course": "Chargement...",
    "date": _date_francaise(),
    "synthese_presse": "",
    "statut_robot": "Actif",
    "isQuinte": None,
    "numReunion": None,
    "numOrdre": None,
    "mode_manuel": False
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
# LOGIQUE D'ACTUALISATION & FALLBACK
# =====================================================================
def _fusionner(nouvelles_donnees):
    global DONNEES_QUINTE_DU_JOUR, FLAG_QUINTE_VALIDE
    if not isinstance(nouvelles_donnees, dict):
        return False

    flag = nouvelles_donnees.get("isQuinte")
    if flag is True:
        FLAG_QUINTE_VALIDE = True
    elif flag is False:
        FLAG_QUINTE_VALIDE = False
        return False
    else:
        FLAG_QUINTE_VALIDE = None

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
        # Si on est déjà en mode manuel, on ne réessaie pas l'API à chaque chargement
        if DONNEES_QUINTE_DU_JOUR.get("mode_manuel"):
            return DONNEES_QUINTE_DU_JOUR
        return DONNEES_QUINTE_DU_JOUR

    source = "aucune"
    
    # Tentative API
    if EXTRACTION_DISPONIBLE and not DONNEES_QUINTE_DU_JOUR.get("mode_manuel"):
        try:
            resultat = obtenir_quinte_du_jour()
            if resultat and _fusionner(resultat):
                source = "extraction.py"
                DONNEES_QUINTE_DU_JOUR["mode_manuel"] = False
        except Exception as e:
            print(f"⚠️ Extraction API échouée: {e}", flush=True)

    # Fallback Fichier JSON
    if source == "aucune":
        try:
            with open(FICHIER_SAUVEGARDE, encoding="utf-8") as f:
                secours = json.load(f)
            if secours and _fusionner(secours):
                source = "quinte_du_jour.json"
        except Exception:
            pass

    # Fallback Mode Manuel
    if source == "aucune":
        print("⚠️ Activation du MODE MANUEL (API & JSON indisponibles)", flush=True)
        DONNEES_QUINTE_DU_JOUR["statut_robot"] = "Mode Manuel"
        DONNEES_QUINTE_DU_JOUR["mode_manuel"] = True
        DONNEES_QUINTE_DU_JOUR["date"] = _date_francaise()
        source = "manuel"

    DERNIERE_VERIFICATION = maintenant
    DERNIERE_VERIFICATION_HHMM = _datetime.now().strftime("%H:%M")
    print(f"🔄 Actualisation terminée (source: {source})", flush=True)
    return DONNEES_QUINTE_DU_JOUR

# Scheduler auto
SCHEDULER_ACTIF = False
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: rafraichir_donnees_quinte(force=True), "interval", minutes=30)
    scheduler.start()
    SCHEDULER_ACTIF = True
except Exception as e:
    print(f"ℹ️ Scheduler inactif: {e}", flush=True)

# =====================================================================
# MOTEUR SGE (Inchangé)
# =====================================================================
OPPOSITIONS_VERTICALES = {
    1: 9, 2: 10, 3: 11, 4: 12, 5: 13, 6: 14, 7: 15, 8: 16,
    9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 6, 15: 7, 16: 8
}
COEFFICIENTS_RESONANCE = {0: 0.5, 1: 1.0, 2: 1.5, 3: 2.0, 4: 2.5, 5: 3.0}

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
    return [str(x) for x in valides[:5]]

# =====================================================================
# ROUTES
# =====================================================================
@app.exception_handler(Exception)
async def erreur_non_geree(request: Request, exc: Exception):
    trace = traceback.format_exc()
    if DEBUG:
        return HTMLResponse(f"<h1>Erreur 500</h1><pre>{trace}</pre>", status_code=500)
    return HTMLResponse("Internal Server Error.", status_code=500)

@app.get("/health")
def health():
    return {"status": "ok", "debug": DEBUG, "nb_courses": len(HISTORIQUE_SGE_DATA)}

@app.get("/debug-extraction")
def debug_extraction():
    if not EXTRACTION_DISPONIBLE:
        return JSONResponse({"extraction_disponible": False, "erreur": ERREUR_EXTRACTION})
    try:
        debut = time.time()
        resultat = obtenir_quinte_du_jour()
        return JSONResponse({
            "extraction_disponible": True,
            "duree_secondes": round(time.time() - debut, 2),
            "flag_quinte_detecte": resultat.get("isQuinte") if isinstance(resultat, dict) else None,
            "contenu": resultat
        })
    except Exception as e:
        return JSONResponse({"extraction_disponible": True, "erreur": str(e)})

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    global COMBINAISON_SELECTIONNEE
    rafraichir_donnees_quinte()

    prono_pegasus = generer_prono_automatique(COMBINAISON_SELECTIONNEE)
    
    counter = Counter()
    total_courses = len(HISTORIQUE_SGE_DATA)
    for course in HISTORIQUE_SGE_DATA:
        for num in course["arrivee"][:5]:
            counter[num] += 1

    top_chevaux = [{"numero": f"{n:02d}", "occurrences": c, 
                    "pourcentage": round((c/total_courses)*100, 1)} 
                   for n, c in counter.most_common(3)]

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
    score_pegasus = calculer_score_sge([int(n) for n in prono_pegasus])
    score_combinaison = calculer_score_sge(combo_int) if len(combo_int) == 5 else 0

    stats = {
        "historique_courses": total_courses, "taux_reussite": 20,
        "nb_dernieres_courses": 5, "ponderation_pegasus": score_pegasus,
        "ponderation_combinaison": score_combinaison, "moyenne_chevaux_trouves": "0.00",
        "niveau_performance": "Faible", "top_chevaux_frequents": top_chevaux
    }

    combinaison_saisie = " - ".join(COMBINAISON_SELECTIONNEE)
    
    tag_quinte = "✅ Quinté vérifié" if FLAG_QUINTE_VALIDE is True else \
                 "⚠️ PAS un Quinté" if FLAG_QUINTE_VALIDE is False else \
                 "Quinté non vérifié"
    
    code_pmu = f"R{DONNEES_QUINTE_DU_JOUR.get('numReunion','?')}C{DONNEES_QUINTE_DU_JOUR.get('numOrdre','?')}"
    message_statut = f"{tag_quinte} • {code_pmu} • {info_quinte.get('nb_partants',0)} partants • Vérif: {DERNIERE_VERIFICATION_HHMM}"

    return templates.TemplateResponse(
        request=request, name="index.html", context={
            "statut_robot": DONNEES_QUINTE_DU_JOUR.get("statut_robot", "Actif"),
            "message_statut": message_statut,
            "info_quinte": info_quinte,
            "combinaison_saisie": combinaison_saisie,
            "jetons": jetons, "stats": stats
        }
    )

@app.post("/calculer")
def calculer(combinaison_utilisateur: str = Form(...)):
    global COMBINAISON_SELECTIONNEE
    extraits = [n.strip() for n in combinaison_utilisateur.split("-") if n.strip().isdigit()]
    if extraits: COMBINAISON_SELECTIONNEE = extraits[:8]
    return RedirectResponse(url="/", status_code=303)

@app.get("/selectionner/{numero}")
def selectionner_grille(numero: str):
    global COMBINAISON_SELECTIONNEE
    if numero in COMBINAISON_SELECTIONNEE:
        COMBINAISON_SELECTIONNEE.remove(numero)
    elif len(COMBINAISON_SELECTIONNEE) < 8:
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
    # Force la réactivation du mode auto si possible
    DONNEES_QUINTE_DU_JOUR["mode_manuel"] = False
    rafraichir_donnees_quinte(force=True)
    return RedirectResponse(url="/", status_code=303)

@app.post("/relancer")
def relancer():
    global COMBINAISON_SELECTIONNEE
    DONNEES_QUINTE_DU_JOUR["mode_manuel"] = False
    rafraichir_donnees_quinte(force=True)
    COMBINAISON_SELECTIONNEE = ["13", "6", "5", "12", "11"]
    return RedirectResponse(url="/", status_code=303)

@app.post("/saisie-manuelle")
def saisie_manuelle(
    hippodrome: str = Form(...),
    nom_course: str = Form(...),
    nb_partants: int = Form(...),
    heure_depart: str = Form(...),
    discipline: str = Form("TROT ATTELÉ"),
    distance: int = Form(0)
):
    """Route pour saisir manuellement les infos quand l'API est morte."""
    global DONNEES_QUINTE_DU_JOUR
    DONNEES_QUINTE_DU_JOUR.update({
        "hippodrome": hippodrome.upper(),
        "nom_course": nom_course,
        "nb_partants": nb_partants,
        "heure_depart": heure_depart,
        "discipline": discipline.upper(),
        "distance": distance,
        "statut_robot": "Données Manuelles",
        "mode_manuel": True,
        "isQuinte": True, # On considère que c'est le quinté puisque l'utilisateur le dit
        "numReunion": 1,
        "numOrdre": 5
    })
    # Sauvegarde pour persistance entre redémarrages
    try:
        with open(FICHIER_SAUVEGARDE, 'w', encoding='utf-8') as f:
            json.dump(DONNEES_QUINTE_DU_JOUR, f, ensure_ascii=False)
    except Exception:
        pass
        
    return RedirectResponse(url="/", status_code=303)

print("✅ Initialisation terminée", flush=True)

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host='0.0.0.0', port=port)
