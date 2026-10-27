import datetime
import json
import os
import requests

# Utilisation du dossier /tmp, seul espace autorisé en écriture sous Vercel
FICHIER_DONNEES = "/tmp/quinte_du_jour.json"


def recuperer_et_sauvegarder_quinte():
  """Interroge l'API PMU et stocke le résultat dans le cache temporaire."""
  print("⏰ Extraction automatique du Quinté PMU lancée...")
  date_du_jour = datetime.datetime.now().strftime("%m/%d/%Y")

  try:
    response = requests.get(
        "https://vercel.app",
        params={"date": date_du_jour},
        timeout=15,
    )
    response.raise_for_status()
    courses = response.json().get("message", [])

    quinte = None
    for course in courses:
      if course.get("typeEnjeu") == "QUINTE" or "QUINTE" in str(
          course.get("libelle", "")
      ).upper():
        quinte = course
        break

    if quinte:
      backup_data = {
          "derniere_extraction": datetime.date.today().isoformat(),
          "donnees": quinte,
      }
      with open(FICHIER_DONNEES, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=4)
      print("✅ Données du Quinté enregistrées avec succès dans /tmp.")
      return quinte
    else:
      print("⚠️ Aucun Quinté+ identifié pour le moment dans la réponse API.")

  except Exception as e:
    print(f"❌ Échec de l'extraction automatique PMU : {e}")
  return None


def obtenir_quinte_du_jour():
  """Récupère le Quinté depuis le cache temporaire local ou force une nouvelle

  requête si obsolète.
  """
  date_aujourdhui = datetime.date.today().isoformat()

  if os.path.exists(FICHIER_DONNEES):
    try:
      with open(FICHIER_DONNEES, "r", encoding="utf-8") as f:
        cache = json.load(f)
        if cache.get("derniere_extraction") == date_aujourdhui:
          print("📦 Données récupérées depuis le cache temporaire /tmp.")
          return cache.get("donnees")
    except Exception:
      pass

  return recuperer_et_sauvegarder_quinte()
