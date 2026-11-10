# 🐎 Pegasus Quinté - Algorithme de Pronostics Hippiques par Analyse Géométrique

> **Un moteur de prédiction qui applique les lois de la physique (frottement, résonance, vitesse limite) aux courses hippiques.**

![Version](https://img.shields.io/badge/version-3.18-orange)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

---

## 📖 À propos du projet

**Pegasus Quinté** est une application web open-source qui génère des pronostics pour les courses de Quinté+ (PMU) en se basant sur une approche originale : **l'analyse géométrique des arrivées passées**, couplée à un modèle mathématique inspiré de la physique classique.

Contrairement aux sites de pronostics traditionnels qui se basent sur les cotes ou la forme des chevaux, Pegasus détecte des **motifs récurrents** (les "axes") dans l'historique des courses et applique un principe d'**amortissement physique** pour éviter la sur-optimisation.

🌐 **Site en ligne :** [pegasus-backend-v2.onrender.com](https://pegasus-backend-v2.onrender.com)

---

## ✨ Fonctionnalités principales

### 🔮 Analyse Géométrique Pegasus
- **Détection d'axes verticaux** : Le moteur identifie les paires de numéros qui apparaissent fréquemment ensemble dans les arrivées (ex: 5-13, 4-12).
- **Coefficient de résonance** : Plus une combinaison valide d'axes, plus son score augmente de manière non-linéaire.
- **Amortissement physique (frottement)** : Inspiré de la vitesse limite d'un objet dans un fluide, le score est pondéré pour pénaliser les combinaisons trop larges qui "diluent" la qualité géométrique.

### 📊 Données en temps réel
- Widget officiel **Boturfers** intégré (partants, cotes PMU/Zeturf, arrivées).
- Affichage des **non-partants** (NC) directement dans l'interface.
- Mise à jour automatique toutes les 30 minutes via un scheduler.

### 🎯 Interface utilisateur
- **Grille de sélection rapide** (1 à 20 chevaux).
- **Saisie libre** de combinaison (5 à 8 chevaux).
- **Pronostic Pegasus optimisé** affiché en temps réel.
- **Bouton de partage** : copiez votre pronostic en un clic pour WhatsApp, SMS, réseaux sociaux.
- **Persistance LocalStorage** : votre combinaison est sauvegardée dans votre navigateur.

### 🛡️ Robustesse technique
- Routes GET/POST sécurisées (anti-erreur de rafraîchissement).
- Base de données historique nettoyée et renumérotée (220 courses valides).
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

### 📐 La formule du score



