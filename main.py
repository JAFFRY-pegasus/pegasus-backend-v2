import json
import os
from datetime import datetime
from collections import Counter
from itertools import combinations
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
import markdown2

from historique import HISTORIQUE_SGE_DATA

app = FastAPI()
IMAGE_URL = "https://raw.githubusercontent.com/JAFFRY-pegasus/pegasus-backend-v2/main/Horse-racing-1.jpg"

# ==============================================================================
# MOTEUR SGE
# ==============================================================================
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
    valides = [n for n in combinaison_ref if 1 <= n <= 16]
    if len(valides) < 5:
        complements = [n for n in range(1, 17) if n not in valides]
        valides = (valides + complements)[:5]
    opposes = [OPPOSITIONS_VERTICALES[n] for n in valides if n in OPPOSITIONS_VERTICALES]
    candidats = list(dict.fromkeys(valides + opposes))
    scores_candidats = []
    for combo in combinations(candidats, 5):
        score = calculer_score_sge(list(combo))
        scores_candidats.append((score, list(combo)))
    scores_candidats.sort(key=lambda x: x[0], reverse=True)
    return scores_candidats[0][1] if scores_candidats else valides[:5]

def generer_completions_sge(fixed_horses, target_length=5, num_suggestions=3):
    fixed = []
    for h in str(fixed_horses).replace(",", " ").replace("-", " ").split():
        if h.isdigit() and 1 <= int(h) <= 16:
            fixed.append(int(h))
    fixed = list(dict.fromkeys(fixed))
    if len(fixed) >= target_length:
        return [{"combination": fixed[:target_length], "score": calculer_score_sge(fixed[:target_length]), "added": []}]
    needed = target_length - len(fixed)
    available = [h for h in range(1, 17) if h not in fixed]
    candidates = []
    for completion in combinations(available, needed):
        full_combo = fixed + list(completion)
        score = calculer_score_sge(full_combo)
        candidates.append({"combination": full_combo, "score": score, "added": list(completion)})
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:num_suggestions]

def calculer_stats_chevaux():
    counter = Counter()
    total = len(HISTORIQUE_SGE_DATA)
    for course in HISTORIQUE_SGE_DATA:
        for num in course["arrivee"][:5]:
            counter[num] += 1
    top3 = counter.most_common(3)
    return [(num, count, round(count/total*100, 1)) for num, count in top3]

def lire_donnees_quinte():
    file_path = "data/quinte.json"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("course_du_jour", {})
        except Exception:
            pass
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "hippodrome": "EN ATTENTE",
        "discipline": "En attente",
        "course_nom": "Le robot mettra à jour les données prochainement.",
        "distance": 0,
        "partants": "16",
        "heure": "--:--",
        "arrivee": [],
        "participants": list(range(1, 17))
    }

def lire_readme_html():
    """Lit et convertit le README.md en HTML"""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Conversion avec support des tableaux et blocs de code
        html = markdown2.markdown(content, extras=['tables', 'fenced-code-blocks'])
        return html
    except Exception as e:
        return f"<p style='color:#ef4444;'>Erreur lors du chargement de la documentation : {str(e)}</p>"

def generer_interface(saisie_str, prono_list, score_prono, score_saisie, message_succes="", chevaux_base_str=""):
    infos = lire_donnees_quinte()
    date_str = infos.get("date", "")
    date_course = "Date en attente"
    if date_str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
            mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
            date_course = f"{jours[dt.weekday()]} {dt.day} {mois[dt.month-1]} {dt.year}"
        except:
            date_course = date_str

    html_prono_balls = "".join([f'<div class="circle orange">{n}</div>' for n in prono_list])
    saisie_nums = []
    for n in saisie_str.replace(",", " ").replace("-", " ").split():
        n = n.strip()
        if n.isdigit() and 1 <= int(n) <= 16:
            saisie_nums.append(int(n))
    html_saisie_balls = "".join([f'<div class="circle blue">{n}</div>' for n in saisie_nums]) if saisie_nums else '<div class="circle blue" style="opacity:0.4;">?</div>'
    synthesis_nums = [13, 8, 10, 4, 16, 6, 5, 12]
    html_synthesis_balls = "".join([f'<div class="circle turquoise">{n}</div>' for n in synthesis_nums])
    reussite = 0
    if prono_list and infos.get("arrivee") and len(infos["arrivee"]) >= 5:
        correspondances = len(set(prono_list) & set(infos["arrivee"]))
        reussite = int((correspondances / 5) * 100)
    stats = calculer_stats_chevaux()
    stats_html = "".join([f'<div class="stat-num">n°{num} <span style="font-size:0.8em;">({count} fois — {pct}%)</span></div>' for num, count, pct in stats])
    total_courses = len(HISTORIQUE_SGE_DATA)
    total_trouves = sum(1 for course in HISTORIQUE_SGE_DATA for num in course["arrivee"][:5] if num in saisie_nums)
    moyenne = round(total_trouves / total_courses, 2) if total_courses > 0 else 0
    if moyenne >= 3:
        niveau, couleur_niveau = "Très bon", "#10b981"
    elif moyenne >= 2:
        niveau, couleur_niveau = "Bon", "#f59e0b"
    else:
        niveau, couleur_niveau = "Faible", "#ef4444"

    suggestions_html = ""
    if chevaux_base_str.strip():
        base_nums = [int(h) for h in chevaux_base_str.replace(",", " ").replace("-", " ").split() if h.isdigit() and 1 <= int(h) <= 16]
        if 1 <= len(base_nums) <= 4:
            completions = generer_completions_sge(base_nums, target_length=5, num_suggestions=3)
            suggestions_html = '<div style="margin-top:20px; padding:15px; background:rgba(245, 158, 11, 0.1); border:1px solid #f59e0b; border-radius:8px;">'
            suggestions_html += f'<div class="section-label" style="color:#f59e0b; font-weight:bold;">🧠 Complétions SGE pour atteindre 5 chevaux (basées sur : {" - ".join(map(str, base_nums))})</div>'
            for i, sugg in enumerate(completions, 1):
                added_balls = "".join([f'<div class="circle turquoise">{n}</div>' for n in sugg["added"]])
                suggestions_html += f'<div style="display:flex; align-items:center; gap:15px; margin-top:10px; padding:10px; background:rgba(15, 23, 42, 0.6); border-radius:6px;"><div style="font-weight:bold; color:#f59e0b; min-width:80px;">Option {i}</div><div class="circle-group" style="margin:0;">{added_balls}</div><div style="margin-left:auto; color:#14b8a6; font-weight:bold;">Score: {sugg["score"]} pts</div></div>'
            suggestions_html += '</div>'

    grille_buttons = ""
    for i in range(1, 17):
        grille_buttons += f'<button class="grille-btn" id="btn-{i}" onclick="toggleGrille({i})">{i}</button>'

    arrivee_balls = ""
    if infos.get("arrivee") and len(infos["arrivee"]) >= 5:
        arrivee_balls = "".join([f'<div class="circle white">{n}</div>' for n in infos["arrivee"][:5]])
    else:
        arrivee_balls = '<span style="color:#94a3b8; font-style:italic;">En attente de la course</span>'

    message_html = f'<div class="success-banner">{message_succes}</div>' if message_succes else ''

    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PEGASUS QUINTÉ - Analyseur Géométrique d'Axes & Stratégie Quinté+</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-image: url('{IMAGE_URL}');
            background-size: cover; background-position: center; background-repeat: no-repeat; background-attachment: fixed;
            min-height: 100vh; color: #e0e0e0; padding: 20px; position: relative;
        }}
        body::before {{ content: ''; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.4); z-index: 0; }}
        .header {{ text-align: center; margin-bottom: 20px; position: relative; z-index: 1; }}
        .header h1 {{ color: #f59e0b; font-size: 2.5em; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); margin-bottom: 5px; }}
        .header .subtitle {{ color: #cbd5e1; font-size: 1em; margin-bottom: 15px; }}
        .header .citation {{ color: #cbd5e1; font-style: italic; font-size: 0.9em; margin: 15px auto; max-width: 700px; padding: 15px 20px; border-left: 4px solid #f59e0b; background: rgba(0,0,0,0.6); border-radius: 8px; text-align: left; line-height: 1.6; }}
        .header .base-info {{ color: #94a3b8; font-size: 0.85em; margin-top: 15px; }}
        .nav-links {{ display: flex; justify-content: center; gap: 15px; margin: 20px 0; position: relative; z-index: 1; }}
        .nav-link {{ padding: 10px 20px; background: rgba(15, 23, 42, 0.9); border: 1px solid #475569; border-radius: 20px; color: #cbd5e1; text-decoration: none; font-weight: bold; transition: all 0.3s ease; }}
        .nav-link:hover, .nav-link.active {{ background: #f59e0b; color: #0f172a; border-color: #f59e0b; }}
        .btn-group {{ display: flex; justify-content: center; gap: 15px; margin: 25px 0; position: relative; z-index: 1; flex-wrap: wrap; }}
        .btn-action {{ padding: 12px 25px; border: none; border-radius: 25px; font-weight: bold; cursor: pointer; font-size: 0.95em; text-decoration: none; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.4); color: white; transition: all 0.3s ease; }}
        .btn-action:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.5); }}
        .btn-refresh {{ background: linear-gradient(135deg, #14b8a6, #0d9488); }}
        .btn-robot {{ background: linear-gradient(135deg, #8b5cf6, #7c3aed); }}
        .section {{
            background: rgba(15, 23, 42, 0.95); border-radius: 15px; padding: 30px; margin-bottom: 30px; max-width: 900px; margin-left: auto; margin-right: auto; 
            position: relative; z-index: 1; border: 1px solid rgba(245, 158, 11, 0.3); box-shadow: 0 10px 40px rgba(0,0,0,0.6);
        }}
        .section h2 {{ color: #f59e0b; font-size: 1.3em; margin-bottom: 25px; text-transform: uppercase; border-bottom: 2px solid rgba(245, 158, 11, 0.4); padding-bottom: 12px; }}
        .alert-banner {{ background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; border-radius: 8px; padding: 12px; margin-bottom: 25px; color: #10b981; font-size: 0.9em; }}
        .success-banner {{ background: rgba(245, 158, 11, 0.2); border: 1px solid #f59e0b; border-radius: 8px; padding: 12px; margin-bottom: 25px; color: #f59e0b; font-size: 0.95em; font-weight: bold; text-align: center; }}
        .info-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 18px; }}
        .info-field {{ display: flex; flex-direction: column; }}
        .info-field.full {{ grid-column: 1 / -1; }}
        .info-field label {{ color: #94a3b8; font-size: 0.9em; margin-bottom: 6px; font-weight: 500; }}
        .info-field input {{ background: rgba(30, 41, 59, 0.9); border: 1px solid #475569; border-radius: 8px; padding: 10px; color: #e0e0e0; font-size: 1em; }}
        .info-field input[readonly] {{ background: rgba(30, 41, 59, 0.6); }}
        .info-field input.date-input {{ color: #14b8a6; font-weight: bold; }}
        .input-group {{ margin-top: 18px; }}
        .input-group label {{ color: #94a3b8; font-size: 0.9em; margin-bottom: 10px; display: block; font-weight: 500; }}
        .input-group input {{ width: 100%; background: rgba(30, 41, 59, 0.9); border: 1px solid #475569; border-radius: 8px; padding: 12px; color: #ffffff; font-size: 1.05em; }}
        .btn-submit {{ width: 100%; padding: 15px; margin-top: 25px; background: linear-gradient(135deg, #14b8a6, #0d9488); color: white; border: none; border-radius: 10px; font-size: 1.1em; font-weight: bold; cursor: pointer; text-transform: uppercase; transition: all 0.3s ease; }}
        .btn-submit:hover {{ background: linear-gradient(135deg, #0d9488, #0a7a6e); transform: translateY(-2px); }}
        .circle-group {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 12px 0; }}
        .circle {{ width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1em; }}
        .circle.turquoise {{ background: #14b8a6; color: white; }}
        .circle.orange {{ background: #d97706; color: white; }}
        .circle.white {{ background: white; color: #1e293b; }}
        .circle.blue {{ background: #475569; color: white; }}
        .reussite-box {{ background: rgba(30, 41, 59, 0.7); border: 1px solid #475569; border-radius: 10px; padding: 20px; text-align: center; margin: 20px 0; }}
        .reussite-box .label {{ color: #94a3b8; font-size: 0.9em; margin-bottom: 12px; }}
        .reussite-value {{ color: #14b8a6; font-size: 2.5em; font-weight: bold; }}
        .reussite-subtext {{ color: #64748b; font-size: 0.85em; margin-top: 8px; }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 25px; }}
        .grid-item {{ background: rgba(30, 41, 59, 0.7); border: 1px solid #475569; border-radius: 10px; padding: 18px; text-align: center; }}
        .grid-item .label {{ color: #94a3b8; font-size: 0.9em; margin-bottom: 10px; }}
        .grid-item .value {{ font-size: 1.8em; font-weight: bold; }}
        .grid-item .value.orange {{ color: #f59e0b; }}
        .grid-item .value.turquoise {{ color: #14b8a6; }}
        .grille-2x8 {{ display: grid; grid-template-columns: repeat(8, 1fr); gap: 12px; margin: 25px 0; }}
        .grille-btn {{ padding: 14px; background: rgba(30, 41, 59, 0.9); border: 1px solid #475569; border-radius: 8px; color: #ffffff; font-size: 1.1em; font-weight: bold; cursor: pointer; transition: all 0.2s ease; }}
        .grille-btn:hover {{ background: rgba(71, 85, 105, 0.9); border-color: #f59e0b; transform: scale(1.05); }}
        .grille-btn.active {{ background: #14b8a6; border-color: #14b8a6; }}
        .btn-reset {{ width: 100%; padding: 12px; background: #475569; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin-top: 18px; transition: all 0.2s ease; }}
        .btn-reset:hover {{ background: #64748b; }}
        .stat-box {{ background: rgba(30, 41, 59, 0.7); border: 1px solid #475569; border-radius: 10px; padding: 18px; text-align: center; margin: 18px 0; }}
        .stat-box .label {{ color: #94a3b8; font-size: 0.95em; }}
        .stat-badge {{ background: #ef4444; color: white; padding: 6px 18px; border-radius: 18px; display: inline-block; margin-top: 12px; font-weight: bold; font-size: 1.05em; }}
        .stat-freq {{ background: rgba(245, 158, 11, 0.15); border: 1px solid #f59e0b; border-radius: 10px; padding: 18px; margin: 18px 0; }}
        .stat-freq .label {{ color: #f59e0b; font-size: 0.95em; margin-bottom: 12px; }}
        .stat-freq .chiffres {{ display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }}
        .stat-num {{ background: #f59e0b; color: #0f172a; padding: 6px 15px; border-radius: 18px; font-size: 0.9em; font-weight: bold; }}
        .stat-note {{ color: #94a3b8; font-size: 0.85em; margin-top: 12px; text-align: center; font-style: italic; }}
        .legal-footer {{ background: rgba(15, 23, 42, 0.98); border-radius: 15px; padding: 25px; max-width: 900px; margin: 35px auto; text-align: center; position: relative; z-index: 1; border: 1px solid rgba(239, 68, 68, 0.4); }}
        .legal-footer .warning {{ color: #ef4444; font-weight: bold; margin-bottom: 12px; font-size: 0.95em; }}
        .legal-footer .help {{ color: #cbd5e1; font-size: 0.9em; margin-bottom: 12px; }}
        .legal-footer .help a {{ color: #14b8a6; text-decoration: none; }}
        .legal-footer .help a:hover {{ text-decoration: underline; }}
        .legal-footer .disclaimer {{ color: #64748b; font-size: 0.85em; font-style: italic; }}
        .section-label {{ color: #94a3b8; font-size: 0.95em; margin-bottom: 10px; display: block; font-weight: 500; }}
        
        /* Styles spécifiques pour le contenu Markdown */
        .markdown-body {{ line-height: 1.7; color: #e0e0e0; }}
        .markdown-body h1, .markdown-body h2, .markdown-body h3 {{ color: #f59e0b; margin-top: 30px; margin-bottom: 15px; border-bottom: 1px solid rgba(245, 158, 11, 0.3); padding-bottom: 8px; }}
        .markdown-body h1 {{ font-size: 2em; text-align: center; border-bottom: 2px solid #f59e0b; }}
        .markdown-body p {{ margin-bottom: 15px; }}
        .markdown-body ul, .markdown-body ol {{ margin-bottom: 15px; padding-left: 25px; }}
        .markdown-body li {{ margin-bottom: 8px; }}
        .markdown-body strong {{ color: #f59e0b; }}
        .markdown-body em {{ color: #14b8a6; font-style: italic; }}
        .markdown-body blockquote {{ border-left: 4px solid #14b8a6; padding: 15px 20px; margin: 20px 0; background: rgba(20, 184, 166, 0.1); border-radius: 0 8px 8px 0; font-style: italic; }}
        .markdown-body table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: rgba(30, 41, 59, 0.5); border-radius: 8px; overflow: hidden; }}
        .markdown-body th {{ background: rgba(245, 158, 11, 0.2); color: #f59e0b; padding: 12px 15px; text-align: left; font-weight: bold; border-bottom: 2px solid #f59e0b; }}
        .markdown-body td {{ padding: 10px 15px; border-bottom: 1px solid #475569; }}
        .markdown-body tr:last-child td {{ border-bottom: none; }}
        .markdown-body pre {{ background: rgba(15, 23, 42, 0.8); border: 1px solid #475569; border-radius: 8px; padding: 15px; overflow-x: auto; margin: 15px 0; }}
        .markdown-body code {{ font-family: 'Courier New', monospace; font-size: 0.9em; color: #14b8a6; }}
        .markdown-body pre code {{ color: #e0e0e0; background: none; padding: 0; }}
        .markdown-body a {{ color: #14b8a6; text-decoration: none; border-bottom: 1px dotted #14b8a6; }}
        .markdown-body a:hover {{ border-bottom: 1px solid #14b8a6; }}
        .markdown-body hr {{ border: none; border-top: 1px solid #475569; margin: 30px 0; }}
        .markdown-body img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; }}
        
        @media (max-width: 768px) {{
            .info-row {{ grid-template-columns: 1fr; }}
            .grille-2x8 {{ grid-template-columns: repeat(4, 1fr); }}
            .grid-2 {{ grid-template-columns: 1fr; }}
            .header h1 {{ font-size: 2em; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>PEGASUS QUINTÉ</h1>
        <div class="subtitle">Analyseur Géométrique d'Axes & Stratégie Quinté+</div>
        <div class="citation">"Le but de PEGASUS est de donner des ailes à l'intuition du parieur en transformant des données historiques brutes en une stratégie géométrique claire, automatisée et optimisée."</div>
        <div class="base-info">Base : {len(HISTORIQUE_SGE_DATA)} quintés • Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
    </div>

    <div class="nav-links">
        <a href="/" class="nav-link {'active' if request.url.path == '/' else ''}">🎯 Pronostics</a>
        <a href="/methode" class="nav-link {'active' if request.url.path == '/methode' else ''}">📖 Méthode & Licence</a>
    </div>

    <form action="/analyser" method="post">
        <div class="section">
            <h2>1. INFORMATIONS SUR LE QUINTÉ DU JOUR</h2>
            <div class="alert-banner">✅ Aucun non-partant détecté à ce stade • {infos['partants']} partants confirmés • Dernière vérification : {infos['heure']}</div>

            <div class="info-row">
                <div class="info-field full">
                    <label>Date de la course (automatique) :</label>
                    <input type="text" class="date-input" value="{date_course}" readonly>
                </div>
            </div>
            <div class="info-row">
                <div class="info-field"><label>Hippodrome :</label><input type="text" value="{infos['hippodrome']}" readonly></div>
                <div class="info-field"><label>Discipline :</label><input type="text" value="{infos['discipline']}" readonly></div>
            </div>
            <div class="info-row">
                <div class="info-field"><label>Nom de la course :</label><input type="text" value="{infos['course_nom']}" readonly></div>
                <div class="info-field"><label>Distance :</label><input type="text" value="{infos['distance']} m" readonly></div>
            </div>
            <div class="info-row">
                <div class="info-field"><label>Nombre de partants déclarés :</label><input type="text" value="{infos['partants']}" readonly></div>
                <div class="info-field"><label>Heure de départ :</label><input type="text" value="{infos['heure']}" readonly></div>
            </div>

            <div class="input-group">
                <label>Synthèse Presse / Favoris (séparés par tirets) :</label>
                <input type="text" id="synthesis-input" name="synthesis_pmu" value="13 - 8 - 10 - 4 - 16 - 6 - 5 - 12" placeholder="Ex: 13 - 8 - 10 - 4 - 16 - 6 - 5 - 12">
            </div>

            <div class="input-group">
                <label>📌 Chevaux de base fixés (1 à 4 chevaux, le moteur complétera pour vous) :</label>
                <input type="text" id="base-input" name="chevaux_base" value="{chevaux_base_str}" placeholder="Ex: 13 - 6 - 5" style="border-color: #f59e0b;">
            </div>

            <div class="input-group">
                <label>Inscrivez ici la combinaison de votre choix de 5 à 8 chevaux, elle générera automatiquement la combinaison optimisée de PEGASUS !</label>
                <input type="text" id="combinaison-input" name="combinaison" value="{saisie_str}" placeholder="Ex: 13 - 6 - 5 - 12 - 11">
            </div>

            {message_html}
            <button type="submit" class="btn-submit">METTRE À JOUR & RECALCULER</button>
        </div>
    </form>

    <div class="section">
        <h2>2. SYNTHÈSE PMU ET PRONOSTIC PEGASUS OPTIMISÉ POUR {infos['partants']} PARTANT(S) RÉEL(S) AU QUINTÉ</h2>
        <p style="color:#94a3b8; font-size:0.9em; margin-bottom:25px;">Le moteur Pegasus analyse les {len(HISTORIQUE_SGE_DATA)} dernières arrivées pour identifier les axes géométriques récurrents et optimiser votre combinaison de 5 ou 8 chevaux.</p>

        <div style="margin-bottom:25px;">
            <label class="section-label">Synthèse Presse / Favoris :</label>
            <div class="circle-group">{html_synthesis_balls}</div>
        </div>
        <div style="margin-bottom:25px;">
            <label class="section-label">Pronostic Pegasus calculé automatiquement :</label>
            <div class="circle-group">{html_prono_balls}</div>
        </div>

        {suggestions_html}

        <div style="margin-bottom:25px;">
            <label class="section-label">Arrivée officielle (1er → 5e) — Quinté du {date_course} :</label>
            <div class="circle-group" style="margin-top:12px;">
                {arrivee_balls}
            </div>
        </div>

        <div class="reussite-box">
            <div class="label">Réussite du pronostic Pegasus</div>
            <div class="reussite-value">{reussite} %</div>
            <div class="reussite-subtext">{reussite} numéro{'s' if reussite > 1 else ''} sur 5 dans les 5 premiers (entourés ci-dessus)</div>
        </div>

        <div style="margin:25px 0;">
            <label class="section-label">Combinaison active / saisie :</label>
            <div class="circle-group">{html_saisie_balls}</div>
        </div>

        <div class="grid-2">
            <div class="grid-item">
                <div class="label">Pondération Pronostic Pegasus</div>
                <div class="value orange">{score_prono} pts</div>
            </div>
            <div class="grid-item">
                <div class="label">Pondération Combinaison</div>
                <div class="value turquoise">{score_saisie} pts</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>3. TEST DE VISION GÉOMÉTRIQUE (GRILLE 1-16)</h2>
        <p style="color:#94a3b8; font-size:0.9em; text-align:center; margin-bottom:25px;">Cliquez sur les numéros de la grille pour composer instantanément votre combinaison (8 chevaux max) — outil de test indépendant</p>

        <div class="stat-box">
            <label class="label">Chevaux trouvés en moyenne dans le top 5 historique :</label>
            <div class="stat-badge" style="background:{couleur_niveau};">{moyenne} chevaux — {niveau}</div>
        </div>

        <div class="stat-freq">
            <div class="label">📊 À ce jour, la base de données des quintés nous indique que les chevaux les plus fréquemment présents dans le top 5 sont :</div>
            <div class="chiffres">{stats_html}</div>
            <div class="stat-note">(Moyenne sur {len(HISTORIQUE_SGE_DATA)} courses — 3 chevaux ou plus = Très bon, 1 cheval = Faible)</div>
        </div>

        <div class="grille-2x8" id="grille">
            {grille_buttons}
        </div>
        <button type="button" class="btn-reset" onclick="resetGrille()">RÉINITIALISER LA GRILLE</button>
    </div>

    <div class="legal-footer">
        <div class="warning">⚠️ Jouer comporte des risques : endettement, isolement, dépendance.</div>
        <div class="help">Pour être aidé, appelez le <a href="tel:0974751313">09 74 75 13 13</a> (appel non surtaxé) ou visitez <a href="https://joueurs-info-service.fr" target="_blank">joueurs-info-service.fr</a></div>
        <div class="disclaimer">PEGASUS est un outil d'analyse statistique et géométrique à titre purement indicatif. Il ne garantit aucun gain. Jouez avec modération.</div>
    </div>

    <script>
    (function() {
        function formaterAvecTirets(input) {
            var cursorPos = input.selectionStart;
            var oldLength = input.value.length;
            var chiffres = input.value.replace(/[^0-9]/g, '');
            if (chiffres.length === 0) { input.value = ''; return; }
            var nums = [];
            var i = 0;
            while (i < chiffres.length && nums.length < 8) {
                if (chiffres[i] === '1' && i + 1 < chiffres.length && '0123456'.indexOf(chiffres[i+1]) !== -1) {
                    nums.push(chiffres[i] + chiffres[i+1]); i += 2;
                } else if (chiffres[i] !== '0') {
                    nums.push(chiffres[i]); i++;
                } else { i++; }
            }
            var newValue = nums.join(' - ');
            if (input.value !== newValue) {
                input.value = newValue;
                var newLength = input.value.length;
                var diff = newLength - oldLength;
                var newPos = cursorPos + diff;
                if (newPos < 0) newPos = 0;
                if (newPos > newLength) newPos = newLength;
                input.setSelectionRange(newPos, newPos);
            }
        }
        function init() {
            var synInput = document.getElementById('synthesis-input');
            var combInput = document.getElementById('combinaison-input');
            var baseInput = document.getElementById('base-input');
            if (synInput) synInput.addEventListener('input', function() { formaterAvecTirets(this); });
            if (combInput) combInput.addEventListener('input', function() { formaterAvecTirets(this); });
            if (baseInput) baseInput.addEventListener('input', function() { formaterAvecTirets(this); });
        }
        if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); } else { init(); }
    })();

    var selectedNumbers = [];
    function toggleGrille(num) {
        var btn = document.getElementById('btn-' + num);
        var index = selectedNumbers.indexOf(num);
        if (index > -1) { selectedNumbers.splice(index, 1); btn.classList.remove('active'); }
        else {
            if (selectedNumbers.length >= 8) { alert('Maximum 8 chevaux autorisés !'); return; }
            selectedNumbers.push(num); btn.classList.add('active');
        }
        document.getElementById('combinaison-input').value = selectedNumbers.join(' - ');
    }
    function resetGrille() {
        selectedNumbers = [];
        var btns = document.querySelectorAll('.grille-btn');
        for (var i = 0; i < btns.length; i++) { btns[i].classList.remove('active'); }
        document.getElementById('combinaison-input').value = '';
    }
    </script>
</body>
</html>"""

    return HTMLResponse(content=html_content)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    saisie_defaut = "13 - 6 - 5 - 12 - 11"
    nums_saisis = [int(n) for n in saisie_defaut.replace("-", " ").split()]
    prono = generer_prono_automatique(nums_saisis)
    return HTMLResponse(content=generer_interface(
        request=request, saisie_str=saisie_defaut, prono_list=prono,
        score_prono=calculer_score_sge(prono), score_saisie=calculer_score_sge(nums_saisis)
    ))

@app.get("/methode", response_class=HTMLResponse)
async def methode(request: Request):
    readme_html = lire_readme_html()
    
    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PEGASUS QUINTÉ - Méthode & Licence</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-image: url('{IMAGE_URL}');
            background-size: cover; background-position: center; background-repeat: no-repeat; background-attachment: fixed;
            min-height: 100vh; color: #e0e0e0; padding: 20px; position: relative;
        }}
        body::before {{ content: ''; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.4); z-index: 0; }}
        .header {{ text-align: center; margin-bottom: 20px; position: relative; z-index: 1; }}
        .header h1 {{ color: #f59e0b; font-size: 2.5em; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); margin-bottom: 5px; }}
        .header .subtitle {{ color: #cbd5e1; font-size: 1em; margin-bottom: 15px; }}
        .nav-links {{ display: flex; justify-content: center; gap: 15px; margin: 20px 0; position: relative; z-index: 1; }}
        .nav-link {{ padding: 10px 20px; background: rgba(15, 23, 42, 0.9); border: 1px solid #475569; border-radius: 20px; color: #cbd5e1; text-decoration: none; font-weight: bold; transition: all 0.3s ease; }}
        .nav-link:hover, .nav-link.active {{ background: #f59e0b; color: #0f172a; border-color: #f59e0b; }}
        .section {{
            background: rgba(15, 23, 42, 0.95); border-radius: 15px; padding: 30px; margin-bottom: 30px; max-width: 900px; margin-left: auto; margin-right: auto; 
            position: relative; z-index: 1; border: 1px solid rgba(245, 158, 11, 0.3); box-shadow: 0 10px 40px rgba(0,0,0,0.6);
        }}
        .legal-footer {{ background: rgba(15, 23, 42, 0.98); border-radius: 15px; padding: 25px; max-width: 900px; margin: 35px auto; text-align: center; position: relative; z-index: 1; border: 1px solid rgba(239, 68, 68, 0.4); }}
        .legal-footer .warning {{ color: #ef4444; font-weight: bold; margin-bottom: 12px; font-size: 0.95em; }}
        .legal-footer .help {{ color: #cbd5e1; font-size: 0.9em; margin-bottom: 12px; }}
        .legal-footer .help a {{ color: #14b8a6; text-decoration: none; }}
        .legal-footer .disclaimer {{ color: #64748b; font-size: 0.85em; font-style: italic; }}
        
        /* Styles Markdown identiques à la page principale */
        .markdown-body {{ line-height: 1.7; color: #e0e0e0; }}
        .markdown-body h1, .markdown-body h2, .markdown-body h3 {{ color: #f59e0b; margin-top: 30px; margin-bottom: 15px; border-bottom: 1px solid rgba(245, 158, 11, 0.3); padding-bottom: 8px; }}
        .markdown-body h1 {{ font-size: 2em; text-align: center; border-bottom: 2px solid #f59e0b; }}
        .markdown-body p {{ margin-bottom: 15px; }}
        .markdown-body ul, .markdown-body ol {{ margin-bottom: 15px; padding-left: 25px; }}
        .markdown-body li {{ margin-bottom: 8px; }}
        .markdown-body strong {{ color: #f59e0b; }}
        .markdown-body em {{ color: #14b8a6; font-style: italic; }}
        .markdown-body blockquote {{ border-left: 4px solid #14b8a6; padding: 15px 20px; margin: 20px 0; background: rgba(20, 184, 166, 0.1); border-radius: 0 8px 8px 0; font-style: italic; }}
        .markdown-body table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: rgba(30, 41, 59, 0.5); border-radius: 8px; overflow: hidden; }}
        .markdown-body th {{ background: rgba(245, 158, 11, 0.2); color: #f59e0b; padding: 12px 15px; text-align: left; font-weight: bold; border-bottom: 2px solid #f59e0b; }}
        .markdown-body td {{ padding: 10px 15px; border-bottom: 1px solid #475569; }}
        .markdown-body tr:last-child td {{ border-bottom: none; }}
        .markdown-body pre {{ background: rgba(15, 23, 42, 0.8); border: 1px solid #475569; border-radius: 8px; padding: 15px; overflow-x: auto; margin: 15px 0; }}
        .markdown-body code {{ font-family: 'Courier New', monospace; font-size: 0.9em; color: #14b8a6; }}
        .markdown-body pre code {{ color: #e0e0e0; background: none; padding: 0; }}
        .markdown-body a {{ color: #14b8a6; text-decoration: none; border-bottom: 1px dotted #14b8a6; }}
        .markdown-body a:hover {{ border-bottom: 1px solid #14b8a6; }}
        .markdown-body hr {{ border: none; border-top: 1px solid #475569; margin: 30px 0; }}
        .markdown-body img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; }}
        
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 2em; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>PEGASUS QUINTÉ</h1>
        <div class="subtitle">Documentation Méthodologique & Licence</div>
    </div>

    <div class="nav-links">
        <a href="/" class="nav-link">🎯 Pronostics</a>
        <a href="/methode" class="nav-link active">📖 Méthode & Licence</a>
    </div>

    <div class="section">
        <div class="markdown-body">
            {readme_html}
        </div>
    </div>

    <div class="legal-footer">
        <div class="warning">⚠️ Jouer comporte des risques : endettement, isolement, dépendance.</div>
        <div class="help">Pour être aidé, appelez le <a href="tel:0974751313">09 74 75 13 13</a> (appel non surtaxé) ou visitez <a href="https://joueurs-info-service.fr" target="_blank">joueurs-info-service.fr</a></div>
        <div class="disclaimer">PEGASUS est un outil d'analyse statistique et géométrique à titre purement indicatif. Il ne garantit aucun gain. Jouez avec modération.</div>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)

@app.post("/analyser", response_class=HTMLResponse)
async def analyser(request: Request, combinaison: str = Form(...), synthesis_pmu: str = Form(...), chevaux_base: str = Form("")):
    nums_saisis = [int(n.strip()) for n in combinaison.replace(",", " ").replace("-", " ").split() if n.strip().isdigit() and 1 <= int(n.strip()) <= 16]
    prono = generer_prono_automatique(nums_saisis)
    score_prono = calculer_score_sge(prono)
    score_saisie = calculer_score_sge(nums_saisis) if len(nums_saisis) >= 5 else 0
    saisie_formatee = " - ".join(map(str, nums_saisis)) if nums_saisis else ""
    return HTMLResponse(content=generer_interface(
        request=request, saisie_str=saisie_formatee, prono_list=prono, score_prono=score_prono, score_saisie=score_saisie,
        chevaux_base_str=chevaux_base,
        message_succes="✅ Analyse SGE effectuée ! Les scores et le pronostic ont été recalculés sur 244 courses."
    ))
