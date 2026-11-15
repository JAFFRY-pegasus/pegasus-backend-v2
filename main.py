import json
import os
from datetime import datetime
from collections import Counter
from itertools import combinations
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

# Import de la base historique
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

# ==============================================================================
# NOUVELLE FONCTION : COMPLÉTION INTELLIGENTE SGE
# ==============================================================================
def generer_completions_sge(fixed_horses, target_length=5, num_suggestions=3):
    """
    Génère les 'num_suggestions' meilleures combinaisons complètes 
    en partant de chevaux fixes pour atteindre 'target_length'.
    """
    # Nettoyer et valider les chevaux fixes
    fixed = []
    for h in str(fixed_horses).replace(",", " ").replace("-", " ").split():
        if h.isdigit() and 1 <= int(h) <= 16:
            fixed.append(int(h))
    
    # Supprimer les doublons
    fixed = list(dict.fromkeys(fixed))
    
    if len(fixed) >= target_length:
        return [{"combination": fixed[:target_length], "score": calculer_score_sge(fixed[:target_length]), "added": []}]

    needed = target_length - len(fixed)
    available = [h for h in range(1, 17) if h not in fixed]
    
    candidates = []
    # Générer toutes les combinaisons possibles pour compléter
    for completion in combinations(available, needed):
        full_combo = fixed + list(completion)
        score = calculer_score_sge(full_combo)
        candidates.append({
            "combination": full_combo,
            "score": score,
            "added": list(completion)
        })
    
    # Trier par score SGE décroissant
    candidates.sort(key=lambda x: x["score"], reverse=True)
    
    # Retourner les meilleures suggestions
    return candidates[:num_suggestions]

def calculer_stats_chevaux():
    counter = Counter()
    total = len(HISTORIQUE_SGE_DATA)
    for course in HISTORIQUE_SGE_DATA:
        for num in course["arrivee"][:5]:
            counter[num] += 1
    top3 = counter.most_common(3)
    return [(num, count, round(count/total*100, 1)) for num, count in top3]

# ==============================================================================
# LECTURE DES DONNÉES DU ROBOT
# ==============================================================================
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

# ==============================================================================
# INTERFACE UTILISATEUR
# ==============================================================================
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

    # --- NOUVEAU : Logique de complétion SGE ---
    suggestions_html = ""
    if chevaux_base_str.strip():
        base_nums = [int(h) for h in chevaux_base_str.replace(",", " ").replace("-", " ").split() if h.isdigit() and 1 <= int(h) <= 16]
        if 1 <= len(base_nums) <= 4:
            completions = generer_completions_sge(base_nums, target_length=5, num_suggestions=3)
            
            suggestions_html = '<div style="margin-top:20px; padding:15px; background:rgba(245, 158, 11, 0.1); border:1px solid #f59e0b; border-radius:8px;">'
            suggestions_html += f'<div class="section-label" style="color:#f59e0b; font-weight:bold;">🧠 Complétions SGE pour atteindre 5 chevaux (basées sur : {" - ".join(map(str, base_nums))})</div>'
            
            for i, sugg in enumerate(completions, 1):
                added_balls = "".join([f'<div class="circle turquoise">{n}</div>' for n in sugg["added"]])
                suggestions_html += f'''
                <div style="display:flex; align-items:center; gap:15px; margin-top:10px; padding:10px; background:rgba(15, 23, 42, 0.6); border-radius:6px;">
                    <div style="font-weight:bold; color:#f59e0b; min-width:80px;">Option {i}</div>
                    <div class="circle-group" style="margin:0;">{added_balls}</div>
                    <div style="margin-left:auto; color:#14b8a6; font-weight:bold;">Score: {sugg["score"]} pts</div>
                </div>
                '''
            suggestions_html += '</div>'

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PEGASUS QUINTÉ</title>
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
        .header h1 {{ color: #f59e0b; font-size: 2.2em; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); margin-bottom: 5px; }}
        .header .subtitle {{ color: #cbd5e1; font-size: 0.95em; margin-bottom: 15px; }}
        .header .citation {{ color: #cbd5e1; font-style: italic; font-size: 0.85em; margin: 10px auto; max-width: 600px; padding: 10px 15px; border-left: 3px solid #f59e0b; background: rgba(0,0,0,0.5); border-radius: 6px; text-align: left; }}
        .header .base-info {{ color: #94a3b8; font-size: 0.8em; margin-top: 10px; }}
        .btn-group {{ display: flex; justify-content: center; gap: 15px; margin: 20px 0; position: relative; z-index: 1; flex-wrap: wrap; }}
        .btn-action {{ padding: 10px 20px; border: none; border-radius: 20px; font-weight: bold; cursor: pointer; font-size: 0.9em; text-decoration: none; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); color: white; }}
        .btn-refresh {{ background: #14b8a6; }}
        .section {{ 
            background: rgba(15, 23, 42, 0.95);
            border-radius: 12px; padding: 25px; margin-bottom: 25px; max-width: 850px; margin-left: auto; margin-right: auto; 
            position: relative; z-index: 1; border: 1px solid rgba(245, 158, 11, 0.2); box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        }}
        .section h2 {{ color: #f59e0b; font-size: 1.1em; margin-bottom: 20px; text-transform: uppercase; border-bottom: 2px solid rgba(245, 158, 11, 0.3); padding-bottom: 10px; }}
        .alert-banner {{ background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; border-radius: 6px; padding: 10px; margin-bottom: 20px; color: #10b981; font-size: 0.85em; }}
        .success-banner {{ background: rgba(245, 158, 11, 0.2); border: 1px solid #f59e0b; border-radius: 6px; padding: 10px; margin-bottom: 20px; color: #f59e0b; font-size: 0.9em; font-weight: bold; text-align: center; }}
        .info-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px; }}
        .info-field {{ display: flex; flex-direction: column; }}
        .info-field.full {{ grid-column: 1 / -1; }}
        .info-field label {{ color: #94a3b8; font-size: 0.85em; margin-bottom: 5px; }}
        .info-field input {{ background: rgba(30, 41, 59, 0.8); border: 1px solid #475569; border-radius: 6px; padding: 8px; color: #e0e0e0; font-size: 0.95em; }}
        .info-field input[readonly] {{ background: rgba(30, 41, 59, 0.5); }}
        .info-field input.date-input {{ color: #14b8a6; font-weight: bold; }}
        .input-group {{ margin-top: 15px; }}
        .input-group label {{ color: #94a3b8; font-size: 0.85em; margin-bottom: 8px; display: block; }}
        .input-group input {{ width: 100%; background: rgba(30, 41, 59, 0.8); border: 1px solid #475569; border-radius: 6px; padding: 10px; color: #ffffff; font-size: 1em; }}
        .btn-submit {{ width: 100%; padding: 12px; margin-top: 20px; background: #14b8a6; color: white; border: none; border-radius: 8px; font-size: 1em; font-weight: bold; cursor: pointer; text-transform: uppercase; }}
        .btn-submit:hover {{ background: #0d9488; }}
        .circle-group {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0; }}
        .circle {{ width: 35px; height: 35px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 0.95em; }}
        .circle.turquoise {{ background: #14b8a6; color: white; }}
        .circle.orange {{ background: #d97706; color: white; }}
        .circle.white {{ background: white; color: #1e293b; }}
        .circle.blue {{ background: #475569; color: white; }}
        .reussite-box {{ background: rgba(30, 41, 59, 0.6); border: 1px solid #475569; border-radius: 8px; padding: 15px; text-align: center; margin: 15px 0; }}
        .reussite-box .label {{ color: #94a3b8; font-size: 0.85em; margin-bottom: 10px; }}
        .reussite-value {{ color: #14b8a6; font-size: 2em; font-weight: bold; }}
        .reussite-subtext {{ color: #64748b; font-size: 0.8em; margin-top: 5px; }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 20px; }}
        .grid-item {{ background: rgba(30, 41, 59, 0.6); border: 1px solid #475569; border-radius: 8px; padding: 15px; text-align: center; }}
        .grid-item .label {{ color: #94a3b8; font-size: 0.85em; margin-bottom: 8px; }}
        .grid-item .value {{ font-size: 1.5em; font-weight: bold; }}
        .grid-item .value.orange {{ color: #f59e0b; }}
        .grid-item .value.turquoise {{ color: #14b8a6; }}
        .grille-2x8 {{ display: grid; grid-template-columns: repeat(8, 1fr); gap: 10px; margin: 20px 0; }}
        .grille-btn {{ padding: 12px; background: rgba(30, 41, 59, 0.8); border: 1px solid #475569; border-radius: 6px; color: #ffffff; font-size: 1em; font-weight: bold; cursor: pointer; }}
        .grille-btn:hover {{ background: rgba(71, 85, 105, 0.8); border-color: #f59e0b; }}
        .grille-btn.active {{ background: #14b8a6; border-color: #14b8a6; }}
        .btn-reset {{ width: 100%; padding: 10px; background: #475569; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 15px; }}
        .stat-box {{ background: rgba(30, 41, 59, 0.6); border: 1px solid #475569; border-radius: 8px; padding: 15px; text-align: center; margin: 15px 0; }}
        .stat-box .label {{ color: #94a3b8; font-size: 0.9em; }}
        .stat-badge {{ background: #ef4444; color: white; padding: 5px 15px; border-radius: 15px; display: inline-block; margin-top: 10px; font-weight: bold; }}
        .stat-freq {{ background: rgba(245, 158, 11, 0.1); border: 1px solid #f59e0b; border-radius: 8px; padding: 15px; margin: 15px 0; }}
        .stat-freq .label {{ color: #f59e0b; font-size: 0.9em; margin-bottom: 10px; }}
        .stat-freq .chiffres {{ display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }}
        .stat-num {{ background: #f59e0b; color: #0f172a; padding: 5px 12px; border-radius: 15px; font-size: 0.85em; font-weight: bold; }}
        .stat-note {{ color: #94a3b8; font-size: 0.8em; margin-top: 10px; text-align: center; font-style: italic; }}
        .legal-footer {{ background: rgba(15, 23, 42, 0.95); border-radius: 12px; padding: 20px; max-width: 850px; margin: 30px auto; text-align: center; position: relative; z-index: 1; border: 1px solid rgba(239, 68, 68, 0.3); }}
        .legal-footer .warning {{ color: #ef4444; font-weight: bold; margin-bottom: 10px; font-size: 0.9em; }}
        .legal-footer .help {{ color: #cbd5e1; font-size: 0.85em; margin-bottom: 10px; }}
        .legal-footer .help a {{ color: #14b8a6; text-decoration: none; }}
        .legal-footer .disclaimer {{ color: #64748b; font-size: 0.8em; font-style: italic; }}
        .section-label {{ color: #94a3b8; font-size: 0.9em; margin-bottom: 8px; display: block; }}
        @media (max-width: 768px) {{
            .info-row {{ grid-template-columns: 1fr; }}
            .grille-2x8 {{ grid-template-columns: repeat(4, 1fr); }}
            .grid-2 {{ grid-template-columns: 1fr; }}
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
    
    <div class="btn-group">
        <a href="/" class="btn-action btn-refresh">🔄 Actualiser la page</a>
    </div>

    <form action="/analyser" method="post">
        <div class="section">
            <h2>1. INFORMATIONS SUR LE QUINTÉ DU JOUR</h2>
            <div class="alert-banner">✅ Course détectée : {infos['course_nom']} • {infos['partants']} partants • Départ : {infos['heure']}</div>
            
            <div class="info-row">
                <div class="info-field full">
                    <label>Date de la course :</label>
                    <input type="text" class="date-input" value="{date_course}" readonly>
                </div>
            </div>
            <div class="info-row">
                <div class="info-field"><label>Hippodrome :</label><input type="text" value="{infos['hippodrome']}" readonly></div>
                <div class="info-field"><label>Discipline :</label><input type="text" value="{infos['discipline']}" readonly></div>
            </div>
            <div class="info-row">
                <div class="info-field"><label>Distance :</label><input type="text" value="{infos['distance']} m" readonly></div>
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
            
            {f'<div class="success-banner">{message_succes}</div>' if message_succes else ''}
            <button type="submit" class="btn-submit">METTRE À JOUR & RECALCULER</button>
        </div>
    </form>
    
    <div class="section">
        <h2>2. SYNTHÈSE PMU ET PRONOSTIC PEGASUS OPTIMISÉ</h2>
        <p style="color:#94a3b8; font-size:0.85em; margin-bottom:20px;">Le moteur Pegasus analyse les {len(HISTORIQUE_SGE_DATA)} dernières arrivées pour identifier les axes géométriques récurrents.</p>
        
        <div style="margin-bottom:20px;">
            <label class="section-label">Synthèse Presse / Favoris :</label>
            <div class="circle-group">{html_synthesis_balls}</div>
        </div>
        <div style="margin-bottom:20px;">
            <label class="section-label">Pronostic Pegasus calculé automatiquement :</label>
            <div class="circle-group">{html_prono_balls}</div>
        </div>
        
        {suggestions_html}
        
        <div style="margin-bottom:20px;">
            <label class="section-label">Arrivée officielle (1er → 5e) :</label>
            <div class="circle-group" style="margin-top:10px;">
                {"".join([f'<div class="circle white">{{n}}</div>' for n in infos.get('arrivee', [])]) or '<span style="color:#94a3b8; font-style:italic;">En attente de la course</span>'}
            </div>
        </div>
        
        <div class="reussite-box">
            <div class="label">Réussite du pronostic Pegasus</div>
            <div class="reussite-value">{reussite} %</div>
            <div class="reussite-subtext">Numéros trouvés dans les 5 premiers (entourés ci-dessus)</div>
        </div>
        
        <div style="margin:20px 0;">
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
        <p style="color:#94a3b8; font-size:0.85em; text-align:center; margin-bottom:20px;">Cliquez sur les numéros de la grille pour composer instantanément votre combinaison (8 chevaux max)</p>
        
        <div class="stat-box">
            <label class="label">Chevaux trouvés en moyenne dans le top 5 historique :</label>
            <div class="stat-badge" style="background:{couleur_niveau};">{moyenne} chevaux — {niveau}</div>
        </div>
        
        <div class="stat-freq">
            <div class="label">📊 Les chevaux les plus fréquemment présents dans le top 5 sont :</div>
            <div class="chiffres">{stats_html}</div>
            <div class="stat-note">(Moyenne sur {len(HISTORIQUE_SGE_DATA)} courses)</div>
        </div>
        
        <div class="grille-2x8" id="grille">
            {"".join([f'<button class="grille-btn" id="btn-{i}" onclick="toggleGrille({i})">{{i}}</button>' for i in range(1, 17)])}
        </div>
        <button type="button" class="btn-reset" onclick="resetGrille()">RÉINITIALISER LA GRILLE</button>
    </div>

    <div class="legal-footer">
        <div class="warning">⚠️ Jouer comporte des risques : endettement, isolement, dépendance.</div>
        <div class="help">Pour être aidé, appelez le <a href="tel:0974751313">09 74 75 13 13</a> (appel non surtaxé) ou visitez <a href="https://joueurs-info-service.fr" target="_blank">joueurs-info-service.fr</a></div>
        <div class="disclaimer">PEGASUS est un outil d'analyse statistique et géométrique à titre purement indicatif. Il ne garantit aucun gain. Jouez avec modération.</div>
    </div>

    <script>
    (function() {{
        function formaterAvecTirets(input) {{
            var cursorPos = input.selectionStart;
            var oldLength = input.value.length;
            var chiffres = input.value.replace(/[^0-9]/g, '');
            if (chiffres.length === 0) {{ input.value = ''; return; }}
            var nums = [];
            var i = 0;
            while (i < chiffres.length && nums.length < 8) {{
                if (chiffres[i] === '1' && i + 1 < chiffres.length && '0123456'.indexOf(chiffres[i+1]) !== -1) {{
                    nums.push(chiffres[i] + chiffres[i+1]); i += 2;
                }} else if (chiffres[i] !== '0') {{
                    nums.push(chiffres[i]); i++;
                }} else {{ i++; }}
            }}
            var newValue = nums.join(' - ');
            if (input.value !== newValue) {{
                input.value = newValue;
                var newLength = input.value.length;
                var diff = newLength - oldLength;
                var newPos = cursorPos + diff;
                if (newPos < 0) newPos = 0;
                if (newPos > newLength) newPos = newLength;
                input.setSelectionRange(newPos, newPos);
            }}
        }}
        function init() {{
            var synInput = document.getElementById('synthesis-input');
            var combInput = document.getElementById('combinaison-input');
            var baseInput = document.getElementById('base-input');
            if (synInput) synInput.addEventListener('input', function() {{ formaterAvecTirets(this); }});
            if (combInput) combInput.addEventListener('input', function() {{ formaterAvecTirets(this); }});
            if (baseInput) baseInput.addEventListener('input', function() {{ formaterAvecTirets(this); }});
        }}
        if (document.readyState === 'loading') {{ document.addEventListener('DOMContentLoaded', init); }} else {{ init(); }}
    }})();
    
    var selectedNumbers = [];
    function toggleGrille(num) {{
        var btn = document.getElementById('btn-' + num);
        var index = selectedNumbers.indexOf(num);
        if (index > -1) {{ selectedNumbers.splice(index, 1); btn.classList.remove('active'); }} 
        else {{
            if (selectedNumbers.length >= 8) {{ alert('Maximum 8 chevaux autorisés !'); return; }}
            selectedNumbers.push(num); btn.classList.add('active');
        }}
        document.getElementById('combinaison-input').value = selectedNumbers.join(' - ');
    }}
    function resetGrille() {{
        selectedNumbers = [];
        var btns = document.querySelectorAll('.grille-btn');
        for (var i = 0; i < btns.length; i++) {{ btns[i].classList.remove('active'); }}
        document.getElementById('combinaison-input').value = '';
    }}
    </script>
</body>
</html>"""

# ==============================================================================
# ROUTES FASTAPI
# ==============================================================================
@app.get("/", response_class=HTMLResponse)
async def index():
    saisie_defaut = "13 - 6 - 5 - 12 - 11"
    nums_saisis = [int(n) for n in saisie_defaut.replace("-", " ").split()]
    prono = generer_prono_automatique(nums_saisis)
    return HTMLResponse(content=generer_interface(
        saisie_str=saisie_defaut, prono_list=prono,
        score_prono=calculer_score_sge(prono), score_saisie=calculer_score_sge(nums_saisis)
    ))

@app.post("/analyser", response_class=HTMLResponse)
async def analyser(combinaison: str = Form(...), synthesis_pmu: str = Form(...), chevaux_base: str = Form("")):
    nums_saisis = [int(n.strip()) for n in combinaison.replace(",", " ").replace("-", " ").split() if n.strip().isdigit() and 1 <= int(n.strip()) <= 16]
    prono = generer_prono_automatique(nums_saisis)
    score_prono = calculer_score_sge(prono)
    score_saisie = calculer_score_sge(nums_saisis) if len(nums_saisis) >= 5 else 0
    saisie_formatee = " - ".join(map(str, nums_saisis)) if nums_saisis else ""
    return HTMLResponse(content=generer_interface(
        saisie_str=saisie_formatee, prono_list=prono, score_prono=score_prono, score_saisie=score_saisie,
        chevaux_base_str=chevaux_base,
        message_succes="✅ Analyse SGE effectuée ! Les scores et le pronostic ont été recalculés."
    ))
