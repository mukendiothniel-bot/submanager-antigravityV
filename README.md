# SubManager (V1.0)

SubManager est un tableau de bord local moderne pour automatiser la gestion, le suivi et la répartition des abonnements Spotify et Apple Music partagés (en cercles familiaux).

## Fonctionnalités

- **Suivi automatique des échéances :** Classification dynamique des abonnements (Actif, Relance nécessaire à J-2/J-1, Expiré).
- **Tableau de bord des actions (Compensateur d'API) :**
  - **Relances WhatsApp en un clic :** Génère un lien direct vers WhatsApp avec un message poli pré-rempli contenant le nom du client et la date d'échéance.
  - **Confirmation de retrait :** Tâche ordonnée indiquant quel membre doit être retiré manuellement des groupes familiaux de partage (Spotify/Apple Music) ; la validation libère immédiatement la place.
  - **Affectations :** Indique les clients actifs qui n'ont pas encore d'abonnement attribué.
- **Répartition intelligente des places :** Suivi en temps réel des places occupées/disponibles par groupe de partage (limite stricte à 5/6 places selon les plateformes).
- **Interface ultra-premium :** Thème sombre raffiné, effet de verre (glassmorphism), transitions fluides et boutons interactifs.

## Installation

1. **Prérequis :** Assurez-vous d'avoir Python 3 installé.
2. **Installer les dépendances :**
   ```bash
   pip install -r requirements.txt
   ```

## Lancement

Exécutez le script principal pour démarrer le serveur local :
```bash
python app.py
```

Le serveur sera accessible sur : **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

## Structure des fichiers

- `app.py` : Serveur backend FastAPI assurant la logique d'alerte, la liaison avec la base et le service du frontend.
- `database.py` : Fonctions CRUD d'accès à la base de données relationnelle SQLite (`submanager.db`).
- `requirements.txt` : Dépendances Python.
- `static/` :
  - `index.html` : Structure de l'interface SPA.
  - `style.css` : Thème sombre et styles premium.
  - `app.js` : Logique client (AJAX, gestion du DOM et des modals).
