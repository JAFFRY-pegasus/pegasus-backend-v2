# Script de nettoyage pour votre fichier historique.py

HISTORIQUE_SGE_DATA = [
    # Copiez-collez l'intégralité de vos données ici
]

def nettoyer_et_reindexer(data):
    arrivees_vues = set()
    donnees_nettoyees = []
    compteur = 1
    
    for course in data:
        # Transformation en tuple pour pouvoir vérifier s'il existe dans le set
        combinaison = tuple(course["arrivee"])
        
        if combinaison not in arrivees_vues:
            arrivees_vues.add(combinaison)
            # On réindexe proprement de 1 en 1
            donnees_nettoyees.append({
                "id": str(compteur),
                "arrivee": course["arrivee"]
            })
            compteur += 1
        else:
            print(f"⚠️ Doublon supprimé : course avec l'ancienne ID {course['id']} -> {course['arrivee']}")
            
    return donnees_nettoyees

# Exécution du nettoyage
HISTORIQUE_SGE_DATA = nettoyer_et_reindexer(HISTORIQUE_SGE_DATA)
print(f"✅ Base nettoyée. Nouveau nombre total de Quintés+ valides : {len(HISTORIQUE_SGE_DATA)}")
