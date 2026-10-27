import html
import json
import os
import re
from collections import Counter
from itertools import combinations
from datetime import datetime as _datetime
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from extraction import obtenir_quinte_du_jour

app = FastAPI()

# ✅ URL de l'image de fond (à la racine du dépôt GitHub)
IMAGE_URL = "https://raw.githubusercontent.com/JAFFRY-pegasus/pegasus-backend-v2/main/Horse-racing-1.jpg"

# ==============================================================================
# 1. MOTEUR SGE - LE CUR DE PEGASUS
# ==============================================================================

HISTORIQUE_SGE_DATA = [
  {"id": "1", "arrivee": [11, 4, 15, 6, 12]}, {"id": "2", "arrivee": [8, 14, 5, 13, 2]},
  {"id": "3", "arrivee": [9, 3, 16, 7, 10]}, {"id": "4", "arrivee": [1, 12, 6, 14, 8]},
  {"id": "5", "arrivee": [15, 7, 2, 11, 13]}, {"id": "6", "arrivee": [4, 10, 8, 5, 9]},
  {"id": "7", "arrivee": [13, 6, 14, 3, 1]}, {"id": "8", "arrivee": [2, 11, 7, 12, 16]},
  {"id": "9", "arrivee": [12, 5, 9, 15, 4]}, {"id": "10", "arrivee": [6, 14, 3, 8, 11]},
  {"id": "11", "arrivee": [10, 2, 13, 7, 5]}, {"id": "12", "arrivee": [7, 15, 1, 12, 9]},
  {"id": "13", "arrivee": [3, 8, 11, 14, 6]}, {"id": "14", "arrivee": [16, 4, 12, 9, 2]},
  {"id": "15", "arrivee": [5, 13, 6, 10, 8]}, {"id": "16", "arrivee": [14, 9, 2, 7, 15]},
  {"id": "17", "arrivee": [8, 1, 10, 13, 4]}, {"id": "18", "arrivee": [11, 6, 15, 3, 12]},
  {"id": "19", "arrivee": [2, 12, 5, 14, 7]}, {"id": "20", "arrivee": [9, 7, 4, 8, 11]},
  {"id": "21", "arrivee": [13, 3, 8, 16, 5]}, {"id": "22", "arrivee": [6, 10, 14, 2, 12]},
  {"id": "23", "arrivee": [1, 15, 7, 11, 9]}, {"id": "24", "arrivee": [12, 4, 9, 13, 6]},
  {"id": "25", "arrivee": [8, 11, 2, 5, 14]}, {"id": "26", "arrivee": [15, 6, 13, 10, 3]},
  {"id": "27", "arrivee": [4, 14, 8, 12, 7]}, {"id": "28", "arrivee": [7, 2, 11, 9, 16]},
  {"id": "29", "arrivee": [10, 8, 5, 15, 1]}, {"id": "30", "arrivee": [3, 13, 12, 6, 14]},
  {"id": "31", "arrivee": [16, 5, 9, 4, 11]}, {"id": "32", "arrivee": [11, 9, 3, 7, 2]},
  {"id": "33", "arrivee": [6, 14, 8, 12, 15]}, {"id": "34", "arrivee": [2, 10, 13, 5, 4]},
  {"id": "35", "arrivee": [12, 7, 1, 16, 9]}, {"id": "36", "arrivee": [5, 13, 14, 8, 6]},
  {"id": "37", "arrivee": [9, 3, 6, 11, 10]}, {"id": "38", "arrivee": [14, 8, 10, 2, 7]},
  {"id": "39", "arrivee": [7, 12, 15, 4, 13]}, {"id": "40", "arrivee": [4, 1, 9, 14, 5]},
  {"id": "41", "arrivee": [13, 11, 2, 8, 12]}, {"id": "42", "arrivee": [8, 6, 16, 3, 10]},
  {"id": "43", "arrivee": [10, 15, 5, 7, 14]}, {"id": "44", "arrivee": [1, 4, 12, 9, 6]},
  {"id": "45", "arrivee": [15, 9, 7, 13, 2]}, {"id": "46", "arrivee": [3, 12, 14, 6, 11]},
  {"id": "47", "arrivee": [11, 2, 8, 10, 15]}, {"id": "48", "arrivee": [6, 13, 4, 16, 9]},
  {"id": "49", "arrivee": [14, 5, 10, 1, 7]}, {"id": "50", "arrivee": [9, 8, 3, 12, 13]},
  {"id": "51", "arrivee": [2, 14, 11, 5, 6]}, {"id": "52", "arrivee": [7, 10, 6, 15, 8]},
  {"id": "53", "arrivee": [12, 3, 13, 9, 4]}, {"id": "54", "arrivee": [5, 16, 2, 11, 14]},
  {"id": "55", "arrivee": [13, 7, 9, 4, 10]}, {"id": "56", "arrivee": [8, 12, 15, 6, 1]},
  {"id": "57", "arrivee": [4, 9, 1, 14, 11]}, {"id": "58", "arrivee": [10, 2, 7, 13, 5]},
  {"id": "59", "arrivee": [15, 6, 12, 8, 3]}, {"id": "60", "arrivee": [3, 11, 14, 10, 16]},
  {"id": "61", "arrivee": [11, 4, 8, 5, 12]}, {"id": "62", "arrivee": [6, 13, 2, 9, 7]},
  {"id": "63", "arrivee": [14, 8, 10, 15, 3]}, {"id": "64", "arrivee": [9, 1, 12, 6, 13]},
  {"id": "65", "arrivee": [2, 15, 5, 11, 8]}, {"id": "66", "arrivee": [7, 10, 14, 4, 16]},
  {"id": "67", "arrivee": [12, 3, 9, 13, 6]}, {"id": "68", "arrivee": [5, 11, 7, 2, 10]},
  {"id": "69", "arrivee": [13, 6, 4, 12, 15]}, {"id": "70", "arrivee": [8, 14, 16, 9, 1]},
  {"id": "71", "arrivee": [4, 2, 11, 8, 5]}, {"id": "72", "arrivee": [10, 9, 3, 14, 12]},
  {"id": "73", "arrivee": [15, 7, 12, 6, 2]}, {"id": "74", "arrivee": [1, 13, 8, 10, 4]},
  {"id": "75", "arrivee": [6, 5, 15, 11, 9]}, {"id": "76", "arrivee": [12, 14, 2, 3, 7]},
  {"id": "77", "arrivee": [3, 8, 10, 13, 16]}, {"id": "78", "arrivee": [14, 11, 6, 5, 1]},
  {"id": "79", "arrivee": [9, 4, 13, 7, 12]}, {"id": "80", "arrivee": [2, 16, 9, 8, 15]},
  {"id": "81", "arrivee": [7, 3, 11, 14, 10]}, {"id": "82", "arrivee": [13, 12, 5, 2, 6]},
  {"id": "83", "arrivee": [8, 6, 14, 10, 4]}, {"id": "84", "arrivee": [10, 15, 1, 9, 11]},
  {"id": "85", "arrivee": [5, 2, 8, 12, 13]}, {"id": "86", "arrivee": [16, 9, 4, 7, 3]},
  {"id": "87", "arrivee": [11, 7, 13, 15, 14]}, {"id": "88", "arrivee": [4, 14, 6, 3, 8]},
  {"id": "89", "arrivee": [12, 8, 10, 11, 2]}, {"id": "90", "arrivee": [6, 1, 3, 5, 9]},
  {"id": "91", "arrivee": [15, 10, 12, 13, 7]}, {"id": "92", "arrivee": [3, 5, 9, 2, 16]},
  {"id": "93", "arrivee": [9, 13, 7, 8, 12]}, {"id": "94", "arrivee": [14, 2, 11, 4, 15]},
  {"id": "95", "arrivee": [7, 16, 4, 10, 6]}, {"id": "96", "arrivee": [2, 6, 15, 14, 11]},
  {"id": "97", "arrivee": [10, 11, 8, 1, 5]}, {"id": "98", "arrivee": [1, 4, 13, 9, 12]},
  {"id": "99", "arrivee": [8, 12, 2, 6, 10]}, {"id": "100", "arrivee": [13, 9, 5, 15, 3]},
  {"id": "101", "arrivee": [5, 7, 14, 11, 8]}, {"id": "102", "arrivee": [12, 3, 10, 4, 16]},
  {"id": "103", "arrivee": [6, 15, 1, 8, 13]}, {"id": "104", "arrivee": [11, 2, 9, 12, 7]},
  {"id": "105", "arrivee": [4, 8, 6, 13, 10]}, {"id": "106", "arrivee": [16, 14, 11, 3, 2]},
  {"id": "107", "arrivee": [9, 5, 12, 7, 15]}, {"id": "108", "arrivee": [3, 10, 4, 14, 6]},
  {"id": "109", "arrivee": [7, 13, 8, 2, 11]}, {"id": "110", "arrivee": [14, 1, 15, 9, 5]},
  {"id": "111", "arrivee": [6, 13, 8, 11, 4]}, {"id": "112", "arrivee": [12, 5, 14, 7, 2]},
  {"id": "113", "arrivee": [9, 15, 3, 12, 6]}, {"id": "114", "arrivee": [4, 10, 16, 8, 13]},
  {"id": "115", "arrivee": [15, 7, 11, 2, 9]}, {"id": "116", "arrivee": [3, 14, 6, 10, 15]},
  {"id": "117", "arrivee": [11, 8, 13, 4, 1]}, {"id": "118", "arrivee": [7, 12, 5, 14, 10]},
  {"id": "119", "arrivee": [13, 2, 9, 15, 6]}, {"id": "121", "arrivee": [5, 13, 8, 2, 11]},
  {"id": "122", "arrivee": [12, 4, 15, 7, 3]}, {"id": "123", "arrivee": [9, 16, 5, 14, 6]},
  {"id": "124", "arrivee": [3, 11, 14, 8, 12]}, {"id": "125", "arrivee": [15, 6, 10, 13, 4]},
  {"id": "126", "arrivee": [8, 2, 7, 16, 11]}, {"id": "127", "arrivee": [14, 9, 3, 12, 5]},
  {"id": "128", "arrivee": [1, 13, 6, 10, 15]}, {"id": "130", "arrivee": [6, 4, 3, 13, 9]},
  {"id": "131", "arrivee": [13, 5, 11, 12, 8]}, {"id": "132", "arrivee": [14, 6, 12, 4, 8]},
  {"id": "134", "arrivee": [13, 6, 2, 10, 7]}, {"id": "135", "arrivee": [8, 14, 11, 3, 15]},
  {"id": "136", "arrivee": [12, 4, 7, 9, 16]}, {"id": "137", "arrivee": [5, 13, 8, 2, 11]},
  {"id": "138", "arrivee": [10, 6, 14, 4, 9]}, {"id": "139", "arrivee": [3, 15, 12, 7, 1]},
  {"id": "140", "arrivee": [14, 8, 6, 11, 2]}, {"id": "141", "arrivee": [7, 12, 15, 5, 10]},
  {"id": "142", "arrivee": [11, 3, 9, 14, 6]}, {"id": "144", "arrivee": [14, 9, 7, 3, 12]},
  {"id": "145", "arrivee": [6, 11, 2, 15, 8]}, {"id": "146", "arrivee": [12, 5, 14, 9, 4]},
  {"id": "147", "arrivee": [3, 16, 8, 13, 6]}, {"id": "148", "arrivee": [8, 2, 11, 15, 7]},
  {"id": "149", "arrivee": [5, 13, 10, 4, 14]}, {"id": "150", "arrivee": [9, 15, 6, 12, 3]},
  {"id": "151", "arrivee": [11, 7, 4, 16, 2]}, {"id": "152", "arrivee": [2, 14, 9, 5, 13]},
  {"id": "154", "arrivee": [5, 11, 14, 8, 3]}, {"id": "155", "arrivee": [12, 7, 16, 4, 9]},
  {"id": "156", "arrivee": [10, 3, 13, 6, 15]}, {"id": "157", "arrivee": [4, 14, 8, 11, 2]},
  {"id": "158", "arrivee": [7, 12, 5, 15, 10]}, {"id": "159", "arrivee": [13, 6, 9, 3, 14]},
  {"id": "160", "arrivee": [2, 15, 11, 7, 8]}, {"id": "161", "arrivee": [14, 5, 12, 1, 9]},
  {"id": "162", "arrivee": [8, 13, 4, 10, 15]}, {"id": "163", "arrivee": [11, 9, 2, 14, 6]},
  {"id": "176", "arrivee": [13, 7, 4, 12, 9]}, {"id": "177", "arrivee": [6, 15, 10, 2, 14]},
  {"id": "178", "arrivee": [9, 11, 3, 16, 5]}, {"id": "179", "arrivee": [4, 13, 8, 7, 15]},
  {"id": "180", "arrivee": [11, 5, 14, 6, 2]}, {"id": "181", "arrivee": [3, 12, 9, 10, 16]},
  {"id": "182", "arrivee": [14, 8, 6, 11, 7]}, {"id": "183", "arrivee": [10, 16, 12, 4, 13]},
  {"id": "184", "arrivee": [7, 2, 15, 9, 11]}, {"id": "185", "arrivee": [5, 14, 1, 8, 12]},
  {"id": "187", "arrivee": [9, 6, 14, 3, 11]}, {"id": "188", "arrivee": [5, 13, 8, 10, 2]},
  {"id": "189", "arrivee": [12, 4, 15, 7, 6]}, {"id": "190", "arrivee": [3, 11, 9, 14, 5]},
  {"id": "191", "arrivee": [14, 8, 2, 12, 7]}, {"id": "192", "arrivee": [6, 15, 4, 10, 13]},
  {"id": "193", "arrivee": [11, 5, 16, 8, 3]}, {"id": "194", "arrivee": [7, 12, 1, 15, 9]},
  {"id": "195", "arrivee": [13, 10, 6, 2, 14]}, {"id": "197", "arrivee": [6, 14, 3, 11, 8]},
  {"id": "198", "arrivee": [12, 5, 10, 2, 15]}, {"id": "199", "arrivee": [9, 7, 13, 4, 6]},
  {"id": "200", "arrivee": [4, 16, 8, 14, 11]}, {"id": "201", "arrivee": [15, 3, 12, 6, 9]},
  {"id": "202", "arrivee": [8, 11, 5, 13, 2]}, {"id": "203", "arrivee": [10, 14, 7, 1, 12]},
  {"id": "204", "arrivee": [13, 9, 4, 15, 5]}, {"id": "206", "arrivee": [11, 7, 14, 3, 9]},
  {"id": "207", "arrivee": [5, 12, 8, 15, 6]}, {"id": "208", "arrivee": [13, 4, 10, 2, 16]},
  {"id": "209", "arrivee": [6, 15, 11, 7, 1]}, {"id": "210", "arrivee": [9, 3, 14, 12, 5]},
  {"id": "211", "arrivee": [2, 16, 7, 13, 10]}, {"id": "212", "arrivee": [14, 8, 5, 12, 4]},
  {"id": "213", "arrivee": [7, 13, 2, 10, 15]}, {"id": "214", "arrivee": [12, 6, 9, 14, 8]},
  {"id": "216", "arrivee": [8, 12, 5, 14, 3]}, {"id": "217", "arrivee": [13, 6, 10, 2, 15]},
  {"id": "218", "arrivee": [4, 11, 16, 7, 9]}, {"id": "219", "arrivee": [15, 3, 8, 12, 6]},
  {"id": "220", "arrivee": [10, 14, 2, 5, 13]}, {"id": "221", "arrivee": [7, 9, 15, 4, 11]},
  {"id": "222", "arrivee": [12, 1, 6, 14, 8]}, {"id": "223", "arrivee": [6, 13, 9, 16, 5]},
  {"id": "225", "arrivee": [12, 7, 3, 14, 9]}, {"id": "226", "arrivee": [5, 13, 8, 11, 2]},
  {"id": "227", "arrivee": [14, 6, 10, 4, 15]}, {"id": "228", "arrivee": [9, 16, 5, 12, 7]},
  {"id": "229", "arrivee": [3, 11, 14, 8, 6]}, {"id": "230", "arrivee": [15, 4, 9, 13, 10]},
  {"id": "231", "arrivee": [8, 2, 12, 16, 11]}, {"id": "232", "arrivee": [6, 14, 3, 10, 1]},
  {"id": "233", "arrivee": [11, 5, 7, 15, 13]}, {"id": "236", "arrivee": [8, 13, 6, 11, 4]},
  {"id": "237", "arrivee": [12, 5, 14, 7, 9]}, {"id": "238", "arrivee": [3, 15, 8, 10, 6]},
  {"id": "239", "arrivee": [14, 2, 11, 16, 5]}, {"id": "240", "arrivee": [9, 13, 4, 12, 7]},
  {"id": "241", "arrivee": [6, 10, 15, 3, 14]}, {"id": "242", "arrivee": [11, 7, 2, 13, 8]},
  {"id": "243", "arrivee": [5, 16, 9, 12, 10]}, {"id": "244", "arrivee": [13, 4, 14, 6, 11]}
]

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
    counter = Counter()
    total = len(HISTORIQUE_SGE_DATA)
    for course in HISTORIQUE_SGE_DATA:
        for num in course["arrivee"][:5]:
            counter[num] += 1
    top3 = counter.most_common(3)
    return [(num, count, round(count/total*100, 1)) for num, count in top3]

# ==============================================================================
# 2. INTERFACE UTILISATEUR
# ==============================================================================

def generer_interface(saisie_str, prono_list, score_prono, score_saisie, message_succes=""):
    infos = {
        "hippodrome": "DEAUVILLE",
        "discipline": "Plat",
        "nom_course": "PRIX DE LA FORÊT DE LYONS",
        "distance": "1900",
        "partants": "16",
        "heure": "13:55",
        "date_course": "lundi 19 octobre 2026",
        "arrivee": [4, 5, 9, 10, 11]
    }
    
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
    if prono_list and infos["arrivee"]:
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
        .btn-robot {{ background: #8b5cf6; }}
        
        .section {{ 
            background: rgba(15, 23, 42, 0.95);
            border-radius: 12px; 
            padding: 25px; 
            margin-bottom: 25px; 
            max-width: 850px; 
            margin-left: auto; 
            margin-right: auto; 
            position: relative; 
            z-index: 1;
            border: 1px solid rgba(245, 158, 11, 0.2);
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
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
        <div class="base-info">Base : 220 quintés (dont 0 ajoutés automatiquement) • Dernière mise à jour PMU : 2026-10-19 10:02</div>
    </div>
    
    <div class="btn-group">
        <button class="btn-action btn-refresh">🔄 Actualiser les données</button>
        <button class="btn-action btn-robot">🤖 Relancer le robot</button>
    </div>

    <form action="/analyser" method="post">
        <div class="section">
            <h2>1. INFORMATIONS SUR LE QUINTÉ DU JOUR</h2>
            <div class="alert-banner">✅ Aucun non-partant détecté à ce stade • {infos['partants']} partants confirmés • Dernière vérification : {infos['heure']}</div>
            
            <div class="info-row">
                <div class="info-field full">
                    <label>Date de la course (automatique) :</label>
                    <input type="text" class="date-input" value="{infos['date_course']}" readonly>
                </div>
            </div>
            
            <div class="info-row">
                <div class="info-field"><label>Hippodrome :</label><input type="text" value="{infos['hippodrome']}" readonly></div>
                <div class="info-field"><label>Discipline :</label><input type="text" value="{infos['discipline']}" readonly></div>
            </div>
            
            <div class="info-row">
                <div class="info-field"><label>Nom de la course :</label><input type="text" value="{infos['nom_course']}" readonly></div>
                <div class="info-field"><label>Distance :</label><input type="text" value="{infos['distance']}" readonly></div>
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
                <label>Inscrivez ici la combinaison de votre choix de 5 à 8 chevaux, elle générera automatiquement la combinaison optimisée de PEGASUS !</label>
                <input type="text" id="combinaison-input" name="combinaison" value="{saisie_str}" placeholder="Ex: 13 - 6 - 5 - 12 - 11">
            </div>
            
            {f'<div class="success-banner">{message_succes}</div>' if message_succes else ''}
            
            <button type="submit" class="btn-submit">METTRE À JOUR & RECALCULER</button>
        </div>
    </form>
    
    <div class="section">
        <h2>2. SYNTHÈSE PMU ET PRONOSTIC PEGASUS OPTIMISÉ POUR {infos['partants']} PARTANT(S) RÉEL(S) AU QUINTÉ</h2>
        <p style="color:#94a3b8; font-size:0.85em; margin-bottom:20px;">Le moteur Pegasus analyse les 220 dernières arrivées pour identifier les axes géométriques récurrents et optimiser votre combinaison de 5 ou 8 chevaux.</p>
        
        <div style="margin-bottom:20px;">
            <label class="section-label">Synthèse Presse / Favoris :</label>
            <div class="circle-group">{html_synthesis_balls}</div>
        </div>
        
        <div style="margin-bottom:20px;">
            <label class="section-label">Pronostic Pegasus calculé automatiquement :</label>
            <div class="circle-group">{html_prono_balls}</div>
        </div>
        
        <div style="margin-bottom:20px;">
            <label class="section-label">Arrivée officielle (1er → 5e) — Quinté du {infos['date_course']} :</label>
            <div class="circle-group" style="margin-top:10px;">{"".join([f'<div class="circle white">{{n}}</div>' for n in infos['arrivee']])}</div>
        </div>
        
        <div class="reussite-box">
            <div class="label">Réussite du pronostic Pegasus</div>
            <div class="reussite-value">{reussite} %</div>
            <div class="reussite-subtext">1 numéro sur 5 dans les 5 premiers (entourés ci-dessus)</div>
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
        <p style="color:#94a3b8; font-size:0.85em; text-align:center; margin-bottom:20px;">Cliquez sur les numéros de la grille pour composer instantanément votre combinaison (8 chevaux max) — outil de test indépendant</p>
        
        <div class="stat-box">
            <label class="label">Chevaux trouvés en moyenne dans le top 5 historique :</label>
            <div class="stat-badge" style="background:{couleur_niveau};">{moyenne} chevaux — {niveau}</div>
        </div>
        
        <div class="stat-freq">
            <div class="label"> À ce jour, la base de données des quintés nous indique que les chevaux les plus fréquemment présents dans le top 5 sont :</div>
            <div class="chiffres">{stats_html}</div>
            <div class="stat-note">(Moyenne sur 220 courses — 3 chevaux ou plus = Très bon, 1 cheval = Faible)</div>
        </div>
        
        <div class="grille-2x8" id="grille">
            {"".join([f'<button class="grille-btn" id="btn-{i}" onclick="toggleGrille({i})">{{i}}</button>' for i in range(1, 17)])}
        </div>
        <button type="button" class="btn-reset" onclick="resetGrille()">RÉINITIALISER LA GRILLE</button>
    </div>

    <div class="legal-footer">
        <div class="warning">️ Jouer comporte des risques : endettement, isolement, dépendance.</div>
        <div class="help">Pour être aidé, appelez le <a href="tel:0974751313">09 74 75 13 13</a> (appel non surtaxé) ou visitez <a href="https://joueurs-info-service.fr" target="_blank">joueurs-info-service.fr</a></div>
        <div class="disclaimer">PEGASUS est un outil d'analyse statistique et géométrique à titre purement indicatif. Il ne garantit aucun gain. Jouez avec modération.</div>
    </div>

    <script>
    (function() {{
        function formaterAvecTirets(input) {{
            var cursorPos = input.selectionStart;
            var oldLength = input.value.length;
            var chiffres = input.value.replace(/[^0-9]/g, '');
            if (chiffres.length === 0) {{
                input.value = '';
                return;
            }}
            var nums = [];
            var i = 0;
            while (i < chiffres.length && nums.length < 8) {{
                if (chiffres[i] === '1' && i + 1 < chiffres.length && '0123456'.indexOf(chiffres[i+1]) !== -1) {{
                    nums.push(chiffres[i] + chiffres[i+1]);
                    i += 2;
                }} else if (chiffres[i] !== '0') {{
                    nums.push(chiffres[i]);
                    i++;
                }} else {{
                    i++;
                }}
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
            
            if (synInput) {{
                synInput.addEventListener('input', function() {{ formaterAvecTirets(this); }});
            }}
            if (combInput) {{
                combInput.addEventListener('input', function() {{ formaterAvecTirets(this); }});
            }}
        }}
        
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', init);
        }} else {{
            init();
        }}
    }})();
    
    var selectedNumbers = [];
    
    function toggleGrille(num) {{
        var btn = document.getElementById('btn-' + num);
        var index = selectedNumbers.indexOf(num);
        if (index > -1) {{
            selectedNumbers.splice(index, 1);
            btn.classList.remove('active');
        }} else {{
            if (selectedNumbers.length >= 8) {{
                alert('Maximum 8 chevaux autorisés !');
                return;
            }}
            selectedNumbers.push(num);
            btn.classList.add('active');
        }}
        document.getElementById('combinaison-input').value = selectedNumbers.join(' - ');
    }}
    
    function resetGrille() {{
        selectedNumbers = [];
        var btns = document.querySelectorAll('.grille-btn');
        for (var i = 0; i < btns.length; i++) {{
            btns[i].classList.remove('active');
        }}
        document.getElementById('combinaison-input').value = '';
    }}
    </script>
</body>
</html>"""

# ==============================================================================
# 3. ROUTES FASTAPI
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    saisie_defaut = "13 - 6 - 5 - 12 - 11"
    nums_saisis = [int(n) for n in saisie_defaut.replace("-", " ").split()]
    prono = generer_prono_automatique(nums_saisis)
    
    return HTMLResponse(content=generer_interface(
        saisie_str=saisie_defaut,
        prono_list=prono,
        score_prono=calculer_score_sge(prono),
        score_saisie=calculer_score_sge(nums_saisis)
    ))

@app.post("/analyser", response_class=HTMLResponse)
async def analyser(combinaison: str = Form(...), synthesis_pmu: str = Form(...)):
    nums_saisis = [int(n.strip()) for n in combinaison.replace(",", " ").replace("-", " ").split() if n.strip().isdigit() and 1 <= int(n.strip()) <= 16]
    
    prono = generer_prono_automatique(nums_saisis)
    score_prono = calculer_score_sge(prono)
    score_saisie = calculer_score_sge(nums_saisis) if len(nums_saisis) >= 5 else 0
    
    saisie_formatee = " - ".join(map(str, nums_saisis)) if nums_saisis else ""

    return HTMLResponse(content=generer_interface(
        saisie_str=saisie_formatee,
        prono_list=prono,
        score_prono=score_prono,
        score_saisie=score_saisie,
        message_succes="✅ Analyse SGE effectuée ! Les scores et le pronostic ont été recalculés sur 244 courses."
    ))
