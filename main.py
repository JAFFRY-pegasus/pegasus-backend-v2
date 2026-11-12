#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =====================================================================
# PROPRIÉTÉ INTELLECTUELLE - USAGE STRICTEMENT NON COMMERCIAL
# Copyright (c) 2024-2026 JAFFRY-pegasus. Tous droits réservés.
# =====================================================================

"""
main.py v3.29
Authentification propriétaire par COOKIE (correction bug connexion).
- Page vierge par défaut pour les visiteurs
- Connexion propriétaire par mot de passe (stocké côté serveur)
- Combinaison propriétaire accessible depuis n'importe quel appareil
"""

import sys
import os
import json
import time
import hashlib
import traceback
from datetime import datetime as _datetime
from collections import Counter
from itertools import combinations

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# =====================================================================
# 🔐 CONFIGURATION SÉCURITÉ PROPRIÉTAIRE
# =====================================================================
# ⚠️ MODIFIEZ CE MOT DE PASSE PAR LE VÔTRE !
MOT_DE_PASSE_PROPRIETAIRE = "pegasus2024"

# Token stable calculé à partir du mot de passe
TOKEN_PROPRIETAIRE = hashlib.sha256(MOT_DE_PASSE_PROPRIETAIRE.encode()).hexdigest()
NOM_COOKIE = "pegasus_proprio"

# =====================================================================
# CONFIGURATION & CHEMINS
# =====================================================================
print("=" * 60, flush=True)
print("🚀 DÉMARRAGE DE PEGASUS BACKEND V3.29 (Auth par cookie)", flush=True)
print("=" * 60, flush=True)

CHEMIN_BASE = os.path.dirname(os.path.abspath(__file__))
CHEMIN_TEMPLATES = os.path.join(CHEMIN_BASE, "templates")
CHEMIN_STATIC = os.path.join(CHEMIN_BASE, "static")
FICHIER_SAUVEGARDE = os.path.join(CHEMIN_BASE, "quinte_du_jour.json")
FICHIER_COMBINAISON = os.path.join(CHEMIN_BASE, "combinaison.json")

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
app = FastAPI(title="Pegasus Backend v3.29")

if os.path.isdir(CHEMIN_STATIC):
    app.mount("/static", StaticFiles(directory=CHEMIN_STATIC), name="static")
    print(f"✅ Dossier static monté sur /static", flush=True)

templates = Jinja2Templates(directory=CHEMIN_TEMPLATES)
DEBUG = os.environ.get("DEBUG", "0") == "1"
TTL_CACHE_SECONDS = 900

# =====================================================================
# CONSTANTES DU MOTEUR SGE (OPTIMISÉES PAR IA + SIGNATURE)
# =====================================================================
COMBINAISON_PROPRIO_DEFAUT = ["4", "5", "6", "7", "12", "13", "14", "15"]

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
COEFFICIENTS_RESONANCE = {0: 0.5, 1: 1.0, 2: 1.3, 3: 1.6, 4: 1.8, 5: 2.0}
AXES_SIGNATURE = [(6, 14), (7, 15)]
BONUS_SIGNATURE = 1.2

# =====================================================================
# FONCTIONS DE PERSISTANCE
# =====================================================================
def charger_combinaison_proprio():
    try:
        if os.path.exists(FICHIER_COMBINAISON):
            with open(FICHIER_COMBINAISON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'combinaison' in data and isinstance(data['combinaison'], list):
                    return data['combinaison']
    except Exception as e:
        print(f"⚠️ Erreur chargement combinaison proprio: {e}", flush=True)
    return COMBINAISON_PROPRIO_DEFAUT

def sauvegarder_combinaison_proprio(combinaison):
    try:
        with open(FICHIER_COMBINAISON, 'w', encoding='utf-8') as f:
            json.dump({'combinaison': combinaison}, f, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde combinaison proprio: {e}", flush=True)

def est_proprietaire(token: str) -> bool:
    return bool(token) and token == TOKEN_PROPRIETAIRE

def lire_token(request: Request) -> str:
    return request.cookies.get(NOM_COOKIE, "")

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
# MOTEUR SGE (OPTIMISÉ PAR IA + BONUS SIGNATURE)
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
    bonus_multiplicateur = 1.0
    axes_signature_touches = []
    for axe_sig in AXES_SIGNATURE:
        if axe_sig in axes_touches:
            bonus_multiplicateur *= BONUS_SIGNATURE
            axes_signature_touches.append(axe_sig)
    facteur_amortissement = 1.0 / (1.0 + (taille_combinaison - 5) * 0.05)
    ponderation = COEFFICIENTS_RESONANCE.get(nombre_axes, 2.0)
    score_final = int(score_brut * ponderation * facteur_amortissement * bonus_multiplicateur)
    if axes_signature_touches:
        print(f"🔍 DEBUG: Combo={combinaison} | Axes={nombre_axes} | Signature={axes_signature_touches} | Bonus x{bonus_multiplicateur:.2f} | Score={score_final}", flush=True)
    else:
        print(f"🔍 DEBUG: Combo={combinaison} | Axes={nombre_axes} | Score={score_final}", flush=True)
    return score_final

def generer_prono_automatique(combinaison_ref, nombre_max=5):
    valides = [int(n) for n in combinaison_ref if n.isdigit() and 1 <= int(n) <= 20]
    if len(valides) < nombre_max:
        liste_defaut = [11, 4, 7, 5, 9, 1, 2, 3, 6, 8, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        complements = [n for n in liste_defaut if n not in valides]
        valides = (valides + complements)[:nombre_max]
    opposes = [OPPOSITIONS_VERTICALES[n] for n in valides if n in OPPOSITIONS_VERTICALES]
    candidats = list(dict.fromkeys(valides + opposes))
    if len(candidats) > 16: candidats = candidats[:16]
    scores_candidats = []
    for combo in combinations(candidats, nombre_max):
        score = calculer_score_sge(list(combo))
        scores_candidats.append((score, list(combo)))
    scores_candidats.sort(key=lambda x: x[0], reverse=True)
    if scores_candidats:
        return [str(x) for x in scores_candidats[0][1]]
    return [str(x) for x in valides[:nombre_max]]

# =====================================================================
# 🧩 CONSTRUCTION DU CONTEXTE (factorisée)
# =====================================================================
def _construire_contexte(combinaison, proprio):
    rafraichir_donnees_quinte()

    if not combinaison or len(combinaison) == 0:
        prono_pegasus = []
        score_utilisateur = 0
    else:
        nb = len(combinaison)
        if nb < 5: nb = 5
        prono_pegasus = generer_prono_automatique(combinaison, nombre_max=nb)
        combo_int = [int(n) for n in combinaison if n.isdigit()]
        score_utilisateur = calculer_score_sge(combo_int) if 5 <= len(combo_int) <= 8 else 0

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
        "retenus": combinaison
    }

    nb_partants_brut = info_quinte.get('nb_partants', 16)
    try:
        nb_partants = max(8, min(20, int(nb_partants_brut)))
    except:
        nb_partants = 20

    stats = {
        "historique_courses": total_courses,
        "taux_reussite": 34,
        "nb_dernieres_courses": 5,
        "ponderation_pegasus": score_utilisateur,
        "ponderation_combinaison": score_utilisateur,
        "moyenne_chevaux_trouves": "0.00",
        "niveau_performance": "Excellent",
        "top_chevaux_frequents": top_chevaux
    }

    combinaison_saisie = " - ".join(combinaison) if combinaison else ""
    tag_quinte = "✅ Quinté vérifié" if FLAG_QUINTE_VALIDE is True else \
                 "⚠️ PAS un Quinté" if FLAG_QUINTE_VALIDE is False else "Quinté non vérifié"
    code_pmu = f"R{DONNEES_QUINTE_DU_JOUR.get('numReunion','?')}C{DONNEES_QUINTE_DU_JOUR.get('numOrdre','?')}"
    message_statut = f"{tag_quinte} • {code_pmu} • {nb_partants} partants • Vérif: {DERNIERE_VERIFICATION_HHMM}"

    return {
        "statut_robot": DONNEES_QUINTE_DU_JOUR.get("statut_robot", "Actif"),
        "message_statut": message_statut,
        "info_quinte": info_quinte,
        "combinaison_saisie": combinaison_saisie,
        "jetons": jetons,
        "stats": stats,
        "nb_partants": nb_partants,
        "est_proprietaire": proprio
    }

# =====================================================================
# 🔐 ROUTE DE CONNEXION PROPRIÉTAIRE (ASYNC — corrigée)
# =====================================================================
@app.post("/connexion_proprio")
async def connexion_proprio(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    mot_de_passe = body.get("mot_de_passe", "")
    if mot_de_passe == MOT_DE_PASSE_PROPRIETAIRE:
        resp = JSONResponse(content={"success": True})
        resp.set_cookie(NOM_COOKIE, TOKEN_PROPRIETAIRE,
                        max_age=30*24*3600, httponly=True, samesite="lax")
        print("🔓 Connexion propriétaire réussie", flush=True)
        return resp
    print("🔒 Tentative de connexion refusée", flush=True)
    return JSONResponse(content={"success": False, "message": "Mot de passe incorrect"},
                        status_code=401)

# =====================================================================
# ROUTES
# =====================================================================
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    proprio = est_proprietaire(lire_token(request))
    combinaison = charger_combinaison_proprio() if proprio else []
    return templates.TemplateResponse(request=request, name="index.html",
                                      context=_construire_contexte(combinaison, proprio))

@app.post("/calculer", response_class=HTMLResponse)
def calculer(request: Request, combinaison_utilisateur: str = Form(...)):
    extraits = [n.strip() for n in combinaison_utilisateur.split("-") if n.strip().isdigit()][:8]
    proprio = est_proprietaire(lire_token(request))
    if extraits and proprio:
        sauvegarder_combinaison_proprio(extraits)
    return templates.TemplateResponse(request=request, name="index.html",
                                      context=_construire_contexte(extraits, proprio))

@app.get("/selectionner/{numero}", response_class=HTMLResponse)
def selectionner_grille(numero: str, request: Request):
    proprio = est_proprietaire(lire_token(request))
    if proprio:
        combinaison = charger_combinaison_proprio()
        if numero in combinaison:
            combinaison.remove(numero)
        elif len(combinaison) < 8:
            combinaison.append(numero)
            combinaison.sort(key=lambda x: int(x))
        sauvegarder_combinaison_proprio(combinaison)
        return templates.TemplateResponse(request=request, name="index.html",
                                          context=_construire_contexte(combinaison, proprio))
    return RedirectResponse(url="/", status_code=303)

@app.post("/reinitialiser", response_class=HTMLResponse)
def reinitialiser(request: Request):
    proprio = est_proprietaire(lire_token(request))
    if proprio:
        sauvegarder_combinaison_proprio([])
    return templates.TemplateResponse(request=request, name="index.html",
                                      context=_construire_contexte([], proprio))

@app.post("/actualiser")
def actualiser():
    DONNEES_QUINTE_DU_JOUR["mode_manuel"] = False
    rafraichir_donnees_quinte(force=True)
    return RedirectResponse(url="/", status_code=303)

@app.post("/relancer")
def relancer():
    DONNEES_QUINTE_DU_JOUR["mode_manuel"] = False
    rafraichir_donnees_quinte(force=True)
    return RedirectResponse(url="/", status_code=303)

@app.post("/deconnexion")
def deconnexion():
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie(NOM_COOKIE)
    print("🔒 Déconnexion propriétaire", flush=True)
    return resp

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host='0.0.0.0', port=port)
