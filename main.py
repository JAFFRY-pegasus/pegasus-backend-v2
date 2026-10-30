#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main.py v2.6
Moteur SGE unifié — extraction PMU multi-stratégies + vérification flag Quinté
Correction finale : routes POST + TemplateResponse Starlette récent
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
# DIAGNOSTIC DE DÉMARRAGE
# =====================================================================
print("=" * 60, flush=True)
print("🚀 DÉMARRAGE DE PEGASUS BACKEND V2.6", flush=True)
print("=" * 60, flush=True)

CHEMIN_BASE = os.path.dirname(os.path.abspath(__file__))
CHEMIN_TEMPLATES = os.path.join(CHEMIN_BASE, "templates")
FICHIER_SAUVEGARDE = os.path.join(CHEMIN_BASE, "quinte_du_jour.json")

# =====================================================================
# IMPORTS
# =====================================================================
try:
    from historique import HISTORIQUE_SGE_DATA
    print(f"✅ historique.py importé — {len(HISTORIQUE_SGE_DATA)} courses", flush=True)
except Exception as e:
    print(f"❌ ERREUR historique.py: {e}", flush=True)
    traceback.print_exc()
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

# =====================================================================
# APP FASTAPI
# =====================================================================
app = FastAPI(title="Pegasus Backend v2.6")
templates = Jinja2Templates(directory=CHEMIN_TEMPLATES)
DEBUG = os.environ.get("DEBUG", "0") == "1"
TTL_CACHE_SECONDS = 900  # 15 min

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
}

DERNIERE_VERIFICATION = 0.0
DERNIERE_VERIFICATION_HHMM = "--:--"
FLAG_QUINTE_VALIDE = None

CLEFS_ATTENDUES = [
    "hippodrome", "discipline", "distance", "nb_partants",
    "heure_depart", "nom_course", "date", "synthese_presse", "statut_robot",
    "isQuinte", "numReunion", "numOrdre"
]


# =====================================================================
# ACTUALISATION
# =====================================================================
def _fusionner(nouvelles_donnees):
    """Fusionne les données + vérifie le flag Quinté."""
    global DONNEES_QUINTE_DU_JOUR, FLAG_QUINTE_VALIDE

    if not isinstance(nouvelles_donnees, dict):
        return False

    # Vérification du flag Quinté
    flag = nouvelles_donnees.get("isQuinte")
    if flag is True:
        FLAG_QUINTE_VALIDE = True
        print("✅ Flag isQuinte=True confirmé", flush=True)
    elif flag is False:
        FLAG_QUINTE_VALIDE = False
        print("⚠️ REJET: isQuinte=False", flush=True)
        return False
    else:
        FLAG_QUINTE_VALIDE = None
        print("⚠️ Pas de flag isQuinte — confiance implicite", flush=True)

    maj = False
    for clef in CLEFS_ATTENDUES:
        valeur = nouvelles_donnees.get(clef)
        if valeur is not None and valeur != "" and valeur != []:
            DONNEES_QUINTE_DU_JOUR[clef] = valeur
            maj = True
    return maj


def _lire_fichier_sauvegarde():
    try:
        with open(FICHIER_SAUVEGARDE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def rafraichir_donnees_quinte(force=False):
    global DERNIERE_VERIFICATION, DERNIERE_VERIFICATION_HHMM

    maintenant = time.time()
    if not force and (maintenant - DERNIERE_VERIFICATION) < TTL_CACHE_SECONDS:
        return DONNEES_QUINTE_DU_JOUR

    source = "aucune"
    if EXTRACTION_DISPONIBLE:
        try:
            resultat = obtenir_quinte_du_jour()
            if resultat and _fusionner(resultat):
                source = "extraction.py"
        except Exception as e:
            print(f"⚠️ obtenir_quinte_du_jour() a échoué: {e}", flush=True)

    if source == "aucune":
        secours = _lire_fichier_sauvegarde()
        if secours and _fusionner(secours):
            source = "quinte_du_jour.json"

    if not DONNEES_QUINTE_DU_JOUR.get("date"):
        DONNEES_QUINTE_DU_JOUR["date"] = _date_francaise()

    DERNIERE_VERIFICATION = maintenant
    DERNIERE_VERIFICATION_HHMM = _datetime.now().strftime("%H:%M")
    print(f"🔄 Actualisation terminée (source: {source})", flush=True)
    return DONNEES_QUINTE_DU_JOUR


# Scheduler auto (toutes les 30 min)
SCHEDULER_ACTIF = False
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: rafraichir_donnees_quinte(force=True), "interval", minutes=30)
    scheduler.start()
    SCHEDULER_ACTIF = True
    print("⏰ Scheduler actif (toutes les 30 min)", flush=True)
except Exception as e:
    print(f"ℹ️ Scheduler inactif: {e}", flush=True)


# =====================================================================
# MOTEUR SGE
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
# GESTION DES ERREURS
# =====================================================================
@app.exception_handler(Exception)
async def erreur_non_geree(request: Request, exc: Exception):
    trace = traceback.format_exc()
    if DEBUG:
        return HTMLResponse(
            f"<h1>Erreur 500 — Mode DEBUG</h1><pre style='white-space:pre-wrap'>{trace}</pre>",
            status_code=500
        )
    return HTMLResponse(
        "Internal Server Error. Activez DEBUG=1 sur Render pour voir le traceback.",
        status_code=500
    )


@app.get("/health")
def health():
    return {"status": "ok", "debug": DEBUG, "nb_courses": len(HISTORIQUE_SGE_DATA)}


@app.get("/debug")
def debug():
    dossier_ok = os.path.isdir(CHEMIN_TEMPLATES)
    return JSONResponse({
        "cwd_serveur": os.getcwd(),
        "chemin_base": CHEMIN_BASE,
        "dossier_templates_existe": dossier_ok,
        "contenu_templates": os.listdir(CHEMIN_TEMPLATES) if dossier_ok else "DOSSIER INTROUVABLE",
        "racine_projet": os.listdir(CHEMIN_BASE),
        "nb_courses_historique": len(HISTORIQUE_SGE_DATA),
        "extraction_disponible": EXTRACTION_DISPONIBLE,
        "erreur_extraction": ERREUR_EXTRACTION,
        "scheduler_actif": SCHEDULER_ACTIF,
        "derniere_verification": DERNIERE_VERIFICATION_HHMM,
        "flag_quinte_valide": FLAG_QUINTE_VALIDE,
        "debug_active": DEBUG,
    })


@app.get("/debug-extraction")
def debug_extraction():
    if not EXTRACTION_DISPONIBLE:
        return JSONResponse({
            "extraction_disponible": False,
            "erreur": ERREUR_EXTRACTION,
        })
    try:
        debut = time.time()
        resultat = obtenir_quinte_du_jour()
        duree = round(time.time() - debut, 2)
        return JSONResponse({
            "extraction_disponible": True,
            "duree_secondes": duree,
            "flag_quinte_detecte": resultat.get("isQuinte") if isinstance(resultat, dict) else None,
            "contenu": resultat
        })
    except Exception as e:
        return JSONResponse({
            "extraction_disponible": True,
            "erreur": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc()
        })


# =====================================================================
# ROUTES PRINCIPALES
# =====================================================================
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

    top_chevaux = []
    for num, count in counter.most_common(3):
        top_chevaux.append({
            "numero": f"{num:02d}",
            "occurrences": count,
            "pourcentage": round((count / total_courses) * 100, 1) if total_courses else 0.0
        })

    info_quinte = {clef: DONNEES_QUINTE_DU_JOUR.get(clef, "") for clef in CLEFS_ATTENDUES}

    # Construction sécurisée des jetons
    synthese_brute = str(DONNEES_QUINTE_DU_JOUR.get("synthese_presse", ""))
    jetons_presse = []
    for item in synthese_brute.split("-"):
        cleaned = item.strip()
        if cleaned.isdigit():
            jetons_presse.append(cleaned)
    if not jetons_presse:
        jetons_presse = ["?", "?", "?", "?", "?"]

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

    # Message de statut
    if FLAG_QUINTE_VALIDE is True:
        tag_quinte = "✅ Quinté vérifié"
    elif FLAG_QUINTE_VALIDE is False:
        tag_quinte = "⚠️ PAS un Quinté"
    else:
        tag_quinte = "Quinté non vérifié"

    code_pmu = f"R{DONNEES_QUINTE_DU_JOUR.get('numReunion', '?')}C{DONNEES_QUINTE_DU_JOUR.get('numOrdre', '?')}"
    message_statut = (
        f"{tag_quinte} • {code_pmu} • "
        f"{info_quinte.get('nb_partants', 0)} partants • "
        f"Dernière vérif : {DERNIERE_VERIFICATION_HHMM}"
    )

    # ⭐ NOUVELLE SYNTAXE STARBLETTE (corrige le TypeError)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "statut_robot": DONNEES_QUINTE_DU_JOUR.get("statut_robot", "Actif"),
            "message_statut": message_statut,
            "info_quinte": info_quinte,
            "combinaison_saisie": combinaison_saisie,
            "jetons": jetons,
            "stats": stats
        }
    )


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
    print("🔄 Bouton Actualiser cliqué", flush=True)
    rafraichir_donnees_quinte(force=True)
    return RedirectResponse(url="/", status_code=303)


@app.post("/relancer")
def relancer():
    global COMBINAISON_SELECTIONNEE
    print("🤖 Bouton Relancer cliqué", flush=True)
    rafraichir_donnees_quinte(force=True)
    COMBINAISON_SELECTIONNEE = ["13", "6", "5", "12", "11"]
    return RedirectResponse(url="/", status_code=303)


print("✅ Initialisation terminée", flush=True)

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host='0.0.0.0', port=port)
