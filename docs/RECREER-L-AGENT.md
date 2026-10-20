# Recréer l'agent sur un autre PC : guide pour Claude

Ce guide s'adresse au Claude qui installe l'agent chez un nouvel utilisateur, par exemple Claude Code ouvert dans un dossier de son PC Windows. Il reprend ce qui a été fait et vérifié chez Gaëtan.

## Comment travailler avec l'utilisateur

- L'utilisateur n'est pas développeur. Avance **une étape à la fois**, attends son « fait » avant de passer à la suivante, et explique chaque étape en une ou deux phrases simples.
- **Ne lui demande jamais de coller un secret dans la conversation** : clé API, jeton Telegram, mot de passe d'application, adresse iCal, jeton de routine. Ouvre-lui le fichier `.env` dans le Bloc-notes (`notepad .env`). Il colle lui-même la valeur, puis enregistre avec Ctrl+S. Pour vérifier une ligne, contrôle son format (longueur, caractères) sans jamais afficher la valeur.
- Fais toi-même les commandes : clone, installation, tests, démarrage. L'utilisateur ne fait que ce qui demande son compte ou son téléphone.
- Ne propose jamais d'affaiblir un réglage de sécurité, ni de rendre un agenda public.
- L'agent ne lit le `.env` qu'au démarrage : relance-le après chaque changement. Vérifie qu'**une seule instance** tourne.

## Ce dont l'utilisateur a besoin

- Un PC Windows qui reste allumé, avec la mise en veille réglée sur « Jamais ».
- Python 3.11 ou plus récent ([python.org](https://www.python.org/downloads/), case « Add Python to PATH » cochée), et Git.
- Une clé API Anthropic avec du crédit (console.anthropic.com > API keys). C'est facturé à part de l'abonnement Claude.
- Telegram sur son téléphone.
- Un compte Gmail **dédié à l'agent**, distinct de son adresse habituelle.
- Facultatif : une carte graphique NVIDIA, pour transcrire les vocaux en moins d'une seconde.

## Étapes

### 1. Le code
Le code à jour est sur la branche **`windows-demarrage`**, pas sur `main`. Le dépôt est public.
```
git clone -b windows-demarrage https://github.com/gaetpierson-pixel/agent-distant.git
```
Place-le **hors** de tout dossier synchronisé (OneDrive, SharePoint), par exemple dans `C:\Users\<nom>\agent-distant`.

### 2. L'installation
Lance `installer.bat`. Il crée l'environnement `.venv`, installe les dépendances et copie `.env.example` en `.env`.
Sous Windows, les bibliothèques NVIDIA (environ 1 Go) s'installent même sans carte NVIDIA. C'est sans effet si `WHISPER_APPAREIL=cpu`.
Les captures de maquettes Autodesk utilisent Microsoft Edge, déjà présent sur Windows : il n'y a pas de navigateur à installer.

### 3. Le fichier `.env`
Le fichier `.env.example` contient des valeurs propres à Gaëtan. **Remplace-les toutes** par celles du nouvel utilisateur :

| Ligne | Quoi mettre |
|---|---|
| `ANTHROPIC_API_KEY` | Sa clé API, qu'il colle lui-même. |
| `ALLOWED_SENDERS` | **Son** adresse mail, la seule qui peut donner des ordres par mail. |
| `PROJECTS_DIR`, `NOTES_DIR` | Le dossier de travail de l'agent et son carnet de notes. |
| `CALENDAR_ID` | Son adresse Gmail, celle de son agenda. |
| `CLAUDE_MODEL`, `MAX_BUDGET_USD` | `claude-sonnet-5-5` et `0.50` par défaut. Avec `claude-opus-5-5`, deux fois plus cher, monte le plafond à environ 1 à 2 $. |
| `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` | Le compte Gmail de l'agent et son mot de passe d'application (étape 4). |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED` | Étape 5. |
| `CALENDAR_ICS_URL` | Étape 6. |
| `READ_ONLY_DIRS` | Les dossiers que l'agent peut lire sans jamais les modifier, séparés par `;`. Vide si aucun. |
| `CR_DOSSIER_CHANTIERS`, `CR_SOUS_DOSSIER` | Le dossier des chantiers où l'agent **ajoute** ses comptes-rendus. Vide : les CR restent dans le dossier de l'agent. Ne le remplis que si l'utilisateur l'autorise explicitement. |
| `GMAIL_PERSO_ADRESSE`, `GMAIL_PERSO_MOT_DE_PASSE` | Facultatif : sa boîte Gmail perso, en lecture seule. Il faut un autre mot de passe d'application, créé sur **son** compte. |
| `OUTLOOK_COMPTES` | Facultatif : **ses** adresses Outlook sur ce PC. Toute autre boîte présente dans Outlook est ignorée. Vide : pas de recherche dans Outlook. |
| `VOCABULAIRE` | **Ses** noms propres (clients, chantiers, sigles) : ils guident la transcription des vocaux. |
| `WHISPER_MODEL` | `large-v3-turbo`, bien plus juste que `small` sur le français et les noms propres. |
| `WHISPER_APPAREIL` | `cuda` s'il a une carte NVIDIA compatible CUDA 12 (vérifie avec `nvidia-smi`), sinon `cpu`. En cas d'échec sur la carte, l'agent repasse tout seul sur le processeur. |
| `ROUTINE_URL`, `ROUTINE_TOKEN` | Facultatif, étape 7. |

### 4. Le compte Gmail de l'agent
1. Sur le compte de l'agent, active la validation en deux étapes (myaccount.google.com/security). Le plus simple est le numéro de téléphone avec code par SMS.
2. Sur myaccount.google.com/apppasswords, crée un mot de passe nommé « agent ». Google affiche 16 lettres minuscules, une seule fois.
3. L'utilisateur colle l'adresse et ces 16 lettres dans le `.env`. Vérifie le format : 16 lettres, espaces tolérés. 9 caractères ou des majuscules signalent souvent son mot de passe habituel : fais-le effacer.

Le même procédé sert pour `GMAIL_PERSO_*`, sur son propre compte. Une boîte d'entreprise (Microsoft 365 ou Google Workspace gérée par une DSI) ne se branche pas sans l'accord de cette DSI : ne contourne jamais un blocage.

### 5. Telegram
1. Dans Telegram, l'utilisateur ouvre **@BotFather**, envoie `/newbot`, choisit un nom puis un identifiant finissant par `bot`. Il colle le jeton dans `TELEGRAM_BOT_TOKEN`.
2. Relance l'agent. L'utilisateur écrit au robot, qui lui répond avec son identifiant Telegram. Mets cet identifiant dans `TELEGRAM_ALLOWED`, puis relance.

### 6. L'agenda, sans Google Cloud
1. Dans Google Agenda sur ordinateur : roue dentée > Paramètres > son agenda > Intégrer l'agenda > **Adresse secrète au format iCal**. Il la colle dans `CALENDAR_ICS_URL`.
2. Il ajoute l'adresse de l'agent à ses contacts Google, pour que les invitations de l'agent arrivent dans son agenda.

### 7. Les tâches Claude (facultatif)
Pour qu'un message contenant « tâche Claude » lance un travail long dans le cloud, l'utilisateur crée une routine sur claude.ai/code/routines. Puis, dans la routine : Modifier > API. Il colle l'URL et le jeton dans `ROUTINE_URL` et `ROUTINE_TOKEN`.

### 8. Tests et démarrage
```
.venv\Scripts\python -m pytest
```
Deux tests peuvent être ignorés sur un PC : ceux qui demandent le navigateur des tests Linux.
Démarre ensuite l'agent avec `demarrer-agent.bat`. Le journal `state\agent.log` doit indiquer « Canal e-mail démarré » puis « Canal Telegram démarré ».
Pour le démarrage automatique, mets un raccourci de `demarrer-agent.bat` dans `shell:startup`.

### 9. La fiche de contexte
Au premier message, l'agent crée `NOTES_DIR\contexte.md`, qu'il relit à chaque demande. Le modèle de départ contient des faits sur **Gaëtan** (EPUR, Perrier…) : **remplace tout** par ceux du nouvel utilisateur (ses sociétés, clients, chantiers, rangement, vocabulaire), uniquement des faits qu'il te donne ou que tu as vérifiés. Ensuite, il complète la fiche lui-même en écrivant « retiens que… » sur Telegram.

## Premiers essais à proposer
- Un vocal Telegram : « Note : rappeler le fournisseur demain. »
- « Quels sont mes rendez-vous demain ? »
- Une photo suivie de « fais un compte-rendu de visite du chantier X ». Le CR Word revient sur Telegram, photo insérée.
- « Cherche dans mes mails ce que le client a dit sur les délais de X. »

## Pièges déjà rencontrés
- **Photos envoyées « en tant que fichier »** : elles sont acceptées, mais une photo normale est plus simple.
- **L'agent semble avoir oublié une capacité** : il reprenait une conversation ancienne. Écrire « nouvelle conversation » repart de zéro. Une mise à jour du code le fait aussi automatiquement.
- **Recherche Outlook** : Outlook doit être ouvert sur le PC. Sur un PC partagé, sans `OUTLOOK_COMPTES`, la recherche est refusée, et c'est voulu.
- **Mot de passe d'application refusé** : la validation en deux étapes n'est pas activée, ou la valeur collée n'est pas les 16 lettres.
- **Transcription lente** : sur processeur, `large-v3-turbo` prend environ 12 s par vocal. Sur une RTX 4050, moins d'une seconde.

## Ce que l'agent ne fait jamais
- Il n'envoie aucun mail à des tiers : il prépare des brouillons.
- Il ne modifie ni ne supprime rien dans les dossiers `READ_ONLY_DIRS`. Les CR sont seulement **ajoutés**, sans jamais écraser un fichier.
- Il lit les boîtes mail en lecture seule : pas d'envoi, de déplacement, de suppression ni de marquage comme lu.
- Il ne lance aucune commande sur le PC : l'outil Bash est désactivé.
