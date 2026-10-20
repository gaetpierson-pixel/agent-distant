# Agent à distance

Assistant personnel de Gaëtan, qui tourne sur son PC. On le sollicite à distance. Il répond **par e-mail** et **sur Telegram** (texte, vocaux, photos de notes). Le téléphone viendra ensuite.

Ce qu'il sait faire aujourd'hui :
- **Notes** : il range vos notes dans un carnet du jour (`NOTES_DIR/2026-10-17.md`).
- **Agenda** : il consulte votre agenda Google et y ajoute des événements.
- **Recherches** : il cherche sur le web et cite ses sources.
- **Projets en cours** : il lit (y compris Excel, Word et PDF) vos dossiers listés dans `READ_ONLY_DIRS` (par exemple le SharePoint synchronisé) sans jamais pouvoir les modifier, et range ce qu'il produit dans son dossier `PROJECTS_DIR`.
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

Avec cette méthode, l'agent lit et répond aux mails. Pour l'agenda, sans Google Cloud :
5. Dans Google Agenda (sur ordinateur) : roue dentée > **Paramètres** > votre agenda > **Intégrer l'agenda**, copiez l'**Adresse secrète au format iCal** et collez-la dans `CALENDAR_ICS_URL`. Ne la partagez pas ; en cas de fuite, cliquez sur **Réinitialiser**.
6. Ajoutez l'adresse de l'agent à vos contacts Google : ses invitations s'ajouteront alors à votre agenda. L'agent lit l'agenda et ajoute des rendez-vous par invitation ; il ne peut ni modifier ni supprimer un rendez-vous.

### 4 bis. Méthode complète avec Google Cloud (agenda inclus)
1. Créez un compte Gmail dédié à l'agent, par exemple `prenom.agent@gmail.com`.
2. Avec ce compte, ouvrez la [console Google Cloud](https://console.cloud.google.com/) et créez un projet.
3. Activez **Gmail API** et **Google Calendar API**.
4. Configurez l'écran de consentement OAuth : type « Externe », puis ajoutez l'adresse de l'agent comme utilisateur test.
5. Créez un identifiant **OAuth client ID** de type **Desktop app**, téléchargez le fichier JSON et enregistrez-le sous le nom `credentials.json` à la racine du projet.
6. Depuis **votre** Google Agenda, partagez votre agenda avec l'adresse de l'agent, avec le droit de modifier les événements.
7. Dans l'Explorateur, ouvrez le dossier de l'agent, cliquez dans la barre d'adresse, tapez `cmd` puis Entrée. Dans la fenêtre noire, lancez `.venv\Scripts\python -m agent connecter`. Le navigateur s'ouvre : connectez-vous **avec le compte de l'agent** et acceptez.

### 5. Telegram (texte, vocaux, photos)
L'agent va chercher lui-même les messages de son robot Telegram : pas besoin d'ouvrir le PC sur Internet.
1. Installez Telegram sur votre téléphone.
2. Dans Telegram, ouvrez **@BotFather** (coche bleue), envoyez `/newbot`, choisissez un nom puis un identifiant qui finit par `bot`. Copiez le jeton (« token ») qu'il vous donne.
3. Dans `.env`, collez-le dans `TELEGRAM_BOT_TOKEN`, puis relancez l'agent.
4. Écrivez à votre robot : il vous répond avec votre identifiant Telegram. Mettez-le dans `TELEGRAM_ALLOWED`, puis relancez l'agent. Il n'obéit qu'à cet identifiant.

Les vocaux sont transcrits sur le PC (le modèle de transcription se télécharge au premier vocal). L'agent répond aux vocaux par un vocal, avec une voix de synthèse fabriquée sur le PC (Piper, téléchargée au premier usage) ; `REPONSE_VOCALE=0` pour couper. Les photos sont rangées dans `NOTES_DIR/medias` et lues par l'agent.

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
1. Appel téléphonique.
