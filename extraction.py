import datetime
import requests

# Configuration globale de l'API officielle PMU (Offline)
# Format de date dynamique attendu par le serveur : DDMMYYYY
date_str = datetime.date.today().strftime("%d%m%Y")
BASE_URL = "https://pmu.fr"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def extraire_general_quinte():
    """
    Analyse le programme, identifie le Quinté du jour et extrait
    uniquement les caractéristiques structurelles et les numéros.
    """
    programme_url = f"{BASE_URL}/courses/{date_str}/programme"
    
    try:
        response = requests.get(programme_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        programme = response.json()
    except Exception as e:
        print(f"[ERREUR PEGASUS] Connexion au programme PMU impossible : {e}")
        return None

    code_reunion = None
    num_course = None
    bloc_course_pmu = {}

    # 1. Repérage de la course Quinté dans la structure du programme
    for reunion in programme.get("reunions", []):
        for course in reunion.get("courses", []):
            paris = course.get("lesParisProposes", [])
            if "E_QUINTE_PLUS" in paris or "QUINTE_PLUS" in paris:
                code_reunion = reunion.get("numOfficiel")
                num_course = course.get("numFormate")
                bloc_course_pmu = course
                break
        if code_reunion:
            break

    if not code_reunion or not num_course:
        print("[INFO PEGASUS] Aucun événement Quinté+ détecté pour cette journée.")
        return None

    # 2. Conversion du timestamp horaire en format lisible HH:MM
    ts_ms = bloc_course_pmu.get("heureDepart", 0)
    heure_depart = datetime.datetime.fromtimestamp(ts_ms / 1000).strftime("%H:%M") if ts_ms else "00:00"

    # 3. Récupération de la liste brute des numéros des chevaux inscrits
    participants_url = f"{BASE_URL}/courses/{date_str}/R{code_reunion}/C{num_course}/participants"
    try:
        res_part = requests.get(participants_url, headers=HEADERS, timeout=10)
        res_part.raise_for_status()
        donnees_participants = res_part.json()
    except Exception as e:
        print(f"[ERREUR PEGASUS] Impossible de récupérer les partants de la course R{code_reunion}C{num_course} : {e}")
        return None

    # Extraction exclusive des numéros (numProno) des chevaux confirmés partants
    suite_numerique = [
        int(p.get("numProno"))
        for p in donnees_participants.get("participants", [])
        if p.get("statut") == "PARTANT" and p.get("numProno") is not None
    ]

    # 4. Synthèse des données générales de la course pour votre algorithme
    donnees_generales = {
        "date": datetime.date.today().strftime("%Y-%m-%d"),
        "code_pmu": f"R{code_reunion}C{num_course}",
        "nom_prix": bloc_course_pmu.get("libelle", "PRIX INCONNU"),
        "heure_depart": heure_depart,
        "discipline": bloc_course_pmu.get("discipline", "INCONNUE").replace("_", " "),
        "distance": bloc_course_pmu.get("distance", 0),
        "nombre_partants": len(suite_numerique),
        "suite_numerique": sorted(suite_numerique)
    }

    return donnees_generales

if __name__ == "__main__":
    # Test local de l'extraction
    resultat = extraire_general_quinte()
    if resultat:
        print("\n--- DONNÉES GÉNÉRALES DU QUINTÉ EXTRAITES ---")
        for cle, valeur in resultat.items():
            print(f"{cle:<17} : {valeur}")
        print("---------------------------------------------")
