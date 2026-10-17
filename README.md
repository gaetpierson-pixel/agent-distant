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
Installez Python 3.11 ou plus récent depuis [python.org](https://www.python.org/downloads/). Pendant l'installation, cochez « Add Python to PATH ».

### 2. Le code
Sur la page GitHub du dépôt, cliquez sur **Code**, puis sur **Download ZIP**. Décompressez le fichier dans un dossier, par exemple `Documents\agent-distant`, puis double-cliquez sur **`installer.bat`**.

### 3. Les réglages
`installer.bat` a créé un fichier `.env`. Ouvrez-le avec le Bloc-notes et remplissez :
- la clé API Anthropic ;
- vos dossiers de projets et de notes ;
- l'agenda à gérer.

### 4. La boîte Gmail de l'agent (méthode simple, recommandée)
1. Créez un compte Gmail dédié à l'agent.
2. Sur ce compte, activez la **Validation en deux étapes** (Compte Google > Sécurité).
3. Dans la barre de recherche de ce même compte Google, tapez **Mots de passe des applications**. Créez-en un nommé `agent`, puis copiez le code de 16 lettres.
4. Dans `.env`, remplissez `GMAIL_ADDRESS` (l'adresse de l'agent) et `GMAIL_APP_PASSWORD` (le code).

Avec cette méthode, l'agent lit et répond aux mails, mais n'a pas encore accès à l'agenda.

### 4 bis. Méthode complète avec Google Cloud (agenda inclus)
1. Créez un compte Gmail dédié à l'agent, par exemple `prenom.agent@gmail.com`.
2. Avec ce compte, ouvrez la [console Google Cloud](https://console.cloud.google.com/) et créez un projet.
3. Activez **Gmail API** et **Google Calendar API**.
4. Configurez l'écran de consentement OAuth : type « Externe », puis ajoutez l'adresse de l'agent comme utilisateur test.
5. Créez un identifiant **OAuth client ID** de type **Desktop app**, téléchargez le fichier JSON et enregistrez-le sous le nom `credentials.json` à la racine du projet.
6. Depuis **votre** Google Agenda, partagez votre agenda avec l'adresse de l'agent, avec le droit de modifier les événements.
7. Dans l'Explorateur, ouvrez le dossier de l'agent, cliquez dans la barre d'adresse, tapez `cmd` puis Entrée. Dans la fenêtre noire, lancez `.venv\Scripts\python -m agent connecter`. Le navigateur s'ouvre : connectez-vous **avec le compte de l'agent** et acceptez.

### 5. WhatsApp (via Twilio, en essai)
L'agent va chercher vos messages WhatsApp chez Twilio toutes les 20 secondes : pas besoin d'ouvrir le PC sur Internet.
1. Créez un compte sur [twilio.com](https://www.twilio.com/).
2. Dans la console Twilio, ouvrez **Messaging > Try it out > Send a WhatsApp message**. Depuis votre téléphone, envoyez le message `join ...` indiqué au numéro du bac à sable. Le bac à sable sert aux essais : il faut renvoyer ce message tous les 3 jours.
3. Dans `.env`, remplissez `TWILIO_ACCOUNT_SID` et `TWILIO_AUTH_TOKEN` (page d'accueil de la console), `TWILIO_WHATSAPP_NUMBER` (le numéro du bac à sable) et `WHATSAPP_ALLOWED` (votre portable, par exemple `+33612345678`).
4. Relancez l'agent. Pour l'instant, il lit le texte ; les vocaux et les photos viendront ensuite.

## Utilisation

- Tester le cerveau seul (dans la même fenêtre `cmd`) : `.venv\Scripts\python -m agent demander "Quels sont mes rendez-vous demain ?"`
- Démarrer l'agent : double-cliquez sur **`demarrer-agent.bat`**, puis envoyez un mail depuis votre adresse à celle de l'agent. Il répond dans le même fil. Laissez la fenêtre noire ouverte, car la fermer arrête l'agent. Le journal se trouve dans `state\agent.log`.

### Démarrage automatique avec Windows
1. Clic droit sur `demarrer-agent.bat`, puis **Créer un raccourci**.
2. Appuyez sur Windows + R, tapez `shell:startup` puis Entrée.
3. Déplacez le raccourci dans le dossier qui s'ouvre. L'agent démarrera à chaque ouverture de session. Pour arrêter le démarrage automatique, supprimez ce raccourci.

Pour que l'agent reste joignable, le PC ne doit pas se mettre en veille. Réglez la mise en veille sur « Jamais » dans les paramètres d'alimentation de Windows.

Exemples de mails :
- « Note : rappeler le fournisseur pour le devis inox »
- « Ajoute un rendez-vous chez le dentiste jeudi à 14 h »
- « Dans le projet Station X, prépare un fichier avec les points à voir lundi »

## Tests

```
python -m pytest
```

## Étapes suivantes
1. WhatsApp avec un vrai numéro (au lieu du bac à sable).
2. WhatsApp vocal et photos de notes manuscrites.
3. Appel téléphonique.
