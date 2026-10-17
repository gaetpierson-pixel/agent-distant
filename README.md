# Agent à distance

Assistant personnel de Gaëtan, qui tourne sur son PC. On le sollicite à distance. Pour l'instant, cela marche **par e-mail** : WhatsApp (texte, vocal, photos de notes) et le téléphone viendront dans les étapes suivantes.

Ce qu'il sait faire aujourd'hui :
- **Notes** : il range vos notes dans un carnet du jour (`NOTES_DIR/2026-10-17.md`).
- **Agenda** : il consulte votre agenda Google et y ajoute des événements.
- **Recherches** : il cherche sur le web et cite ses sources.
- **Projets en cours** : il lit, crée et modifie des fichiers dans votre dossier de projets (`PROJECTS_DIR`).
- **Mails à des tiers** : il prépare des **brouillons** et ne les envoie jamais lui-même.

Sécurité :
- Il n'obéit qu'aux adresses listées dans `ALLOWED_SENDERS` et ignore les autres mails.
- Il ne peut lancer aucune commande sur le PC (l'outil de commandes est désactivé). Il travaille dans les deux dossiers ci-dessus.
- Chaque tâche est plafonnée par `MAX_BUDGET_USD` (0,50 $ par défaut).

## Installation (une seule fois)

### 1. Python
Installez Python 3.11 ou plus récent depuis [python.org](https://www.python.org/downloads/). Sous Windows, cochez « Add Python to PATH ».

### 2. Le code
Dans un terminal, depuis le dossier du projet :

```
python -m venv .venv
.venv\Scripts\activate        (Windows)
source .venv/bin/activate     (Mac / Linux)
pip install -r requirements.txt
```

### 3. Les réglages
Copiez `.env.example` en `.env`, puis remplissez-le :
- la clé API Anthropic ;
- vos dossiers de projets et de notes ;
- l'agenda à gérer.

### 4. Le compte Google de l'agent
1. Créez un compte Gmail dédié à l'agent, par exemple `prenom.agent@gmail.com`.
2. Avec ce compte, ouvrez la [console Google Cloud](https://console.cloud.google.com/) et créez un projet.
3. Activez **Gmail API** et **Google Calendar API**.
4. Configurez l'écran de consentement OAuth : type « Externe », puis ajoutez l'adresse de l'agent comme utilisateur test.
5. Créez un identifiant **OAuth client ID** de type **Desktop app**, téléchargez le fichier JSON et enregistrez-le sous le nom `credentials.json` à la racine du projet.
6. Depuis **votre** Google Agenda, partagez votre agenda avec l'adresse de l'agent, avec le droit de modifier les événements.
7. Lancez `python -m agent connecter`. Le navigateur s'ouvre : connectez-vous **avec le compte de l'agent** et acceptez.

## Utilisation

- Tester le cerveau seul : `python -m agent demander "Quels sont mes rendez-vous demain ?"`
- Démarrer l'agent : `python -m agent lancer`, puis envoyez un mail depuis votre adresse à celle de l'agent. Il répond dans le même fil.

Exemples de mails :
- « Note : rappeler le fournisseur pour le devis inox »
- « Ajoute un rendez-vous chez le dentiste jeudi à 14 h »
- « Dans le projet Station X, prépare un fichier avec les points à voir lundi »

## Tests

```
python -m pytest
```

## Étapes suivantes
1. Lancement automatique au démarrage du PC.
2. WhatsApp texte.
3. WhatsApp vocal et photos de notes manuscrites.
4. Appel téléphonique.
