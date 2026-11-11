# 🐎 Pegasus Quinté - Algorithme de Pronostics Hippiques par Analyse Géométrique

> **Un moteur de prédiction qui applique les lois de la physique (frottement, résonance, vitesse limite) aux courses hippiques.**

![Version](https://img.shields.io/badge/version-3.21-orange)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![Licence](https://img.shields.io/badge/licence-Propriétaire_(Non_Commercial)-red)

---

## 📖 À propos du projet

**Pegasus Quinté** est une application web qui génère des pronostics pour les courses de Quinté+ (PMU) en se basant sur une approche originale : **l'analyse géométrique des arrivées passées**, couplée à un modèle mathématique inspiré de la physique classique.

Contrairement aux sites de pronostics traditionnels qui se basent sur les cotes ou la forme des chevaux, Pegasus détecte des **motifs récurrents** (les "axes") dans l'historique des courses et applique un principe d'**amortissement physique** pour éviter la sur-optimisation.

🌐 **Site en ligne :** [pegasus-backend-v2.onrender.com](https://pegasus-backend-v2.onrender.com)

---

## ⚠️ Avertissement sur la licence

**Ce projet est protégé par une licence propriétaire à usage strictement non-commercial.**

- ✅ **Autorisé** : Consultation, utilisation personnelle, démonstration non-lucrative, recherche académique.
- ❌ **Interdit** : Utilisation commerciale, revente, intégration dans un produit payant, monétisation directe ou indirecte.

Pour toute demande de licence commerciale ou de partenariat, veuillez contacter le propriétaire du dépôt via GitHub.

---

## ✨ Fonctionnalités principales

### 🔮 Analyse Géométrique Pegasus
- **Détection d'axes verticaux** : Le moteur identifie les paires de numéros qui apparaissent fréquemment ensemble dans les arrivées (ex: 5-13, 4-12).
- **Coefficient de résonance** : Plus une combinaison valide d'axes, plus son score augmente de manière non-linéaire.
- **Amortissement physique (frottement)** : Inspiré de la vitesse limite d'un objet dans un fluide, le score est pondéré pour pénaliser les combinaisons trop larges qui "diluent" la qualité géométrique.
- **Bonus Signature Géométrique** : Les axes (6-14) et (7-15), découverts par analyse exhaustive, bénéficient d'un multiplicateur +20% chacun.

### 📊 Données en temps réel
- Widget officiel **Boturfers** intégré (partants, cotes PMU/Zeturf, arrivées).
- Affichage des **non-partants** (NC) directement dans l'interface.
- Mise à jour automatique toutes les 30 minutes via un scheduler.

### 🎯 Interface utilisateur
- **Grille de sélection rapide** (1 à 20 chevaux).
- **Saisie libre** de combinaison (5 à 8 chevaux).
- **Pronostic Pegasus optimisé** affiché en temps réel.
- **Échelle visuelle de performance** (Faible → Exceptionnel 🚀).
- **Bouton de partage** : copiez votre pronostic en un clic pour WhatsApp, SMS, réseaux sociaux.
- **Persistance LocalStorage** : votre combinaison est sauvegardée dans votre navigateur.

### 🛡️ Robustesse technique
- Routes GET/POST sécurisées (anti-erreur de rafraîchissement).
- Base de données historique nettoyée et renumérotée (220 courses valides).
- Paramètres optimisés par IA (Google Colab) : frottement = 0.05, résonance max = 2.0.
- Déploiement continu via GitHub + Render.

---

## 🧠 Le concept : la physique appliquée au turf

Le cœur de Pegasus repose sur une analogie avec la **mécanique newtonienne** :

| Concept physique | Équivalent dans Pegasus |
|---|---|
| **Force du champ** (gravité) | Poids des axes historiques détectés |
| **Force de frottement** (résistance de l'air) | Pénalisation des combinaisons trop larges |
| **Vitesse limite** (équilibre des forces) | Score maximal atteint par une combinaison optimale |
| **Accélération** | Ajout de chevaux validant de nouveaux axes |
| **Bonus signature** | Multiplicateur +20% pour les axes dominants (6-14, 7-15) |

### 📐 La formule du score
