#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main.py
Moteur SGE unifié avec API FastAPI et gestion hybride du robot (Automatique + Clic Manuel)
Projet : pegasus-backend-v2
Version : 2.2 — Diagnostic de démarrage Render
"""

import sys
import os
import traceback

# =====================================================================
# DIAGNOSTIC DE DÉMARRAGE IMMÉDIAT
# =====================================================================
print("=" * 60, flush=True)
print("🚀 DÉMARRAGE DE PEGASUS BACKEND V2", flush=True)
print("=" * 60, flush=True)
print(f"Python version: {sys.version}", flush=True)
print(f"Current Working Directory: {os.getcwd()}", flush=True)
print(f"Fichier courant: {__file__}", flush=True)
print("=" * 60, flush=True)

# Vérification des fichiers critiques
CHEMIN_BASE = os.path.dirname(os.path.abspath(__file__))
print(f"\n📂 Contenu de {CHEMIN_BASE}:", flush=True)
try:
    fichiers = os.listdir(CHEMIN_BASE)
    for f in sorted(fichiers):
        chemin_complet = os.path.join(CHEMIN_BASE, f)
        if os.path.isdir(chemin_complet):
            print(f"  📁 [DIR]  {f}/", flush=True)
        else:
            taille = os.path.getsize(chemin_complet)
            print(f"  📄 [FILE] {f} ({taille} bytes)", flush=True)
except Exception as e:
    print(f"  ❌ Erreur listage: {e}", flush=True)

print("\n🔍 Vérification des fichiers critiques...", flush=True)

fichiers_critiques = {
    "main.py": os.path.join(CHEMIN_BASE, "main.py"),
    "historique.py": os.path.join(CHEMIN_BASE, "historique.py"),
    "extraction.py": os.path.join(CHEMIN_BASE, "extraction.py"),
    "templates/": os.path.join(CHEMIN_BASE, "templates"),
    "templates/index.html": os.path.join(CHEMIN_BASE, "templates", "index.html"),
}

for nom, chemin in fichiers_critiques.items():
    existe = os.path.exists(chemin)
    statut = "✅" if existe else "❌ MANQUANT"
    print(f"  {statut} {nom} -> {chemin}", flush=True)
    if not existe:
        print(f"    ⚠️  Le fichier {nom} est ABSENT du serveur !", flush=True)

print("\n" + "=" * 60, flush=True)
print("📦 IMPORT DES DÉPENDANCES EXTERNES...", flush=True)
print("=" * 60, flush=True)

try:
    from fastapi import FastAPI, Form, Request
    from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
    from fastapi.templating import Jinja2Templates
    print("✅ FastAPI importé avec succès", flush=True)
except Exception as e:
    print(f"❌ ERREUR import FastAPI: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60, flush=True)
print("📦 IMPORT DES MODULES LOCAUX...", flush=True)
print("=" * 60, flush=True)

# Import historique.py
print("\n1️⃣  Import de historique.py...", flush=True)
try:
    from historique import HISTORIQUE_SGE_DATA
    print(f"   ✅ historique.py importé - {len(HISTORIQUE_SGE_DATA)} courses", flush=True)
except Exception as e:
    print(f"   ❌ ERREUR import historique.py: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

# Import extraction.py (optionnel mais utile)
print("\n2️⃣  Import de extraction.py...", flush=True)
try:
    from extraction import obtenir_quinte_du_jour
    print("   ✅ extraction.py importé", flush=True)
    EXTRACTION_DISPONIBLE = True
    ERREUR_EXTRACTION = None
except Exception as e:
    print(f"   ⚠️  extraction.py non disponible: {e}", flush=True)
    print("   ℹ️  Ce n'est pas bloquant, l'app continue sans extraction dynamique", flush=True)
    obtenir_quinte_du_jour = None
    EXTRACTION_DISPONIBLE = False
    ERREUR_EXTRACTION = f"{type(e).__name__}: {e}"

print("\n" + "=" * 60, flush=True)
print("⚙️  CONFIGURATION DU SERVEUR...", flush=True)
print("=" * 60, flush=True)

# Configuration des chemins
CHEMIN_TEMPLATES = os.path.join(CHEMIN_BASE, "templates")
print(f"📁 Dossier templates: {CHEMIN_TEMPLATES}", flush=True)
print(f"   Existe: {os.path.isdir(CHEMIN_TEMPLATES)}", flush=True)

if os.path.isdir(CHEMIN_TEMPLATES):
    contenu = os.listdir(CHEMIN_TEMPLATES)
    print(f"   Contenu: {contenu}", flush=True)

# Initialisation FastAPI
print("\n🚀 Initialisation de l'application FastAPI...", flush=True)
app = FastAPI(title="Pegasus Backend v2")

# Configuration Jinja2
print("🎨 Configuration Jinja2...", flush=True)
templates = Jinja2Templates(directory=CHEMIN_TEMPLATES)
print("   ✅ Templates configurés", flush=True)

# Mode debug
DEBUG = os.environ.get("DEBUG", "1") == "1"
print(f"🐛 Mode DEBUG: {'ACTIVÉ' if DEBUG else 'désactivé'}", flush=True)

# Configuration des ressources
FICHIER_SAUVEGARDE = os.path.join(CHEMIN_BASE, "quinte_du_jour.json")
COMBINAISON_SELECTIONNEE = ["13", "6", "5", "12", "11"]

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

print("\n" + "=" * 60, flush=True)
print("🧮 INITIALISATION DU MOTEUR SGE...", flush=True)
print("=" * 60, flush=True)

OPPOSITIONS_VERTICALES = {
    1: 9, 2: 10, 3: 11, 4: 12, 5: 13, 6: 14, 7: 15, 8: 16,
    9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 6, 15: 7, 16: 8
}

COEFFICIENTS_RESONANCE = {
    0: 0.5, 1: 1.0, 2: 1.5, 3: 2.0, 4: 2.5, 5: 3.0
}

print("✅ Matrices SGE configurées", flush=True)

# Calcul des poids historiques
print("\n📊 Calcul des poids historiques...", flush=True)
try:
    from collections import Counter
    from itertools import combinations
    
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
    print(f"   ✅ {len(POIDS_AXES_HISTORIQUE)} axes historiques calculés", flush=True)
except Exception as e:
    print(f"   ❌ ERREUR calcul poids: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

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
    else:
        return [str(x) for x in valides[:5]]

print("\n" + "=" * 60, flush=True)
print("🌐 DÉFINITION DES ROUTES...", flush=True)
print("=" * 60, flush=True)

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
        "chemin_templates": CHEMIN_TEMPLATES,
        "dossier_templates_existe": dossier_ok,
        "contenu_templates": os.listdir(CHEMIN_TEMPLATES) if dossier_ok else "DOSSIER INTROUVABLE",
        "racine_projet": os.listdir(CHEMIN_BASE),
        "nb_courses_historique": len(HISTORIQUE_SGE_DATA),
        "extraction_disponible": EXTRACTION_DISPONIBLE,
        "erreur_extraction": ERREUR_EXTRACTION,
        "debug_active": DEBUG,
    })

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    global COMBINAISON_SELECTIONNEE, DONNEES_QUINTE_DU_JOUR

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

print("\n" + "=" * 60, flush=True)
print("✅ INITIALISATION TERMINÉE AVEC SUCCÈS", flush=True)
print("=" * 60, flush=True)

print("\n🚀 Démarrage du serveur uvicorn...", flush=True)
print(f"   Port: {os.environ.get('PORT', '5000')}", flush=True)
print(f"   Host: 0.0.0.0", flush=True)
print("=" * 60, flush=True)

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host='0.0.0.0', port=port)
