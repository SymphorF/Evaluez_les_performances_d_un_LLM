# Assistant RAG avec Mistral

Ce projet implémente un assistant virtuel basé sur le modèle Mistral, utilisant la technique de Retrieval-Augmented Generation (RAG) pour fournir des réponses précises et contextuelles à partir d'une base de connaissances personnalisée.

## Fonctionnalités

- 🔍 **Recherche sémantique** avec FAISS pour trouver les documents pertinents
- 🤖 **Génération de réponses** avec les modèles Mistral (Small ou Large)
- ⚙️ **Paramètres personnalisables** (modèle, nombre de documents, score minimum)

## Prérequis

- Python 3.9+ 
- Clé API Mistral (obtenue sur [console.mistral.ai](https://console.mistral.ai/))

## Installation

1. **Cloner le dépôt**

```bash
git clone <url-du-repo>
cd <nom-du-repo>
```

2. **Créer un l'environnement virtuel principal**

```bash
# Création de l'environnement virtuel
python -m venv venv

# Activation de l'environnement virtuel
# Sur Windows
venv\Scripts\activate
# Sur macOS/Linux
source venv/bin/activate
```

3. **Installer les dépendances**

```bash
pip install -r requirements.txt
```

4. **Créer un l'environnement virtuel pour ragas**

Pour éviter les conflits de versions, ce nouvel environnemnt est créé spécialement pour les scripts d'évaluation

➡️ En effet Ragas 0.3.9 n’est pas compatible avec LangChain récent
➡️ Or langchain>=1.0.2,<2.0.0 est la version qui fonctionne parfaitement avec non RAG

```bash
# Sortez de l'environnement virtuel actuel
deactivate

# Déplacez vous dans le même repertoire de l'environnement principal 

cd ..

# Création de l'environnement virtuel
python -m venv ragas_env

# Activation de l'environnement virtuel
# Sur Windows
ragas_env\Scripts\activate
# Sur macOS/Linux
source ragas_env/bin/activate
```

5. **Installer les dépendances de cet environnement**

```bash
pip install -r requirements_ragas.txt
```

6. **Pour la suite revenez dans l'environnement principal**

```bash
# Sortez de l'environnement virtuel actuel
deactivate

# Déplacez vous dans le même repertoire de création des environements

cd ..

# Activation de l'environnement virtuel
# Sur Windows
venv\Scripts\activate
# Sur macOS/Linux
source venv/bin/activate
```

7. **Configurer la clé API**

Créez un fichier `.env` à la racine du projet avec le contenu suivant :

```
MISTRAL_API_KEY=votre_clé_api_mistral
```

## Structure du projet

```
.
├── documents/              # Ensembles des documents (Rapport de présentations, autres documents...)
├── inputs/                 # Dossier pour les documents sources
├── notebooks/              # Notebook pour visualiser les scores RAGAS 
├── postgreSQL/             # Script SQL et schéma UML
├── utils/                  # Modules utilitaires
|   ├── config.py           # Configuration de l'application
|   ├── data_loader_.py     # Gestion de la base de données
|   ├── evaluate_ragas.py   # Evaluation de performance du RAG
|   ├── load_excel_to_db.py # Introduction des données Excel dans la base
|   ├── sql_tool.py         # Enrichissement du RAG avec les données ajoutées
|   ├── donnees_nba.xlsx    # Données d'enrichissement de la base format Excel
|   └── vector_store.py     # Gestion de l'index vectoriel
├── vector_db/              # Dossier pour l'index FAISS et les chunks
├── MistralChat.py          # Application Streamlit principale
├── indexer.py              # Script pour indexer les documents
├── pipeline_rag.py         # Contrôle et validation des données via pydantic    
├── requirements.txt        # Dépendances et version de ce projet     
├── requirements_ragas.txt  # Dépendances et version évaluation ragas              
└── README                  # Ce fichier  

```

## Utilisation

### 1. Ajouter des documents

Placez vos documents dans le dossier `inputs/`. Les formats supportés sont :
- PDF
- TXT
- DOCX
- CSV
- JSON

Vous pouvez organiser vos documents dans des sous-dossiers pour une meilleure organisation.

### 2. Indexer les documents

Exécutez le script d'indexation pour traiter les documents et créer l'index FAISS :

```bash
python indexer.py
```

Ce script va :
1. Charger les documents depuis le dossier `inputs/`
2. Découper les documents en chunks
3. Générer des embeddings avec Mistral
4. Créer un index FAISS pour la recherche sémantique
5. Sauvegarder l'index et les chunks dans le dossier `vector_db/`

### 3. Lancer l'application

```bash
streamlit run MistralChat.py
```

L'application sera accessible à l'adresse http://localhost:8501 dans votre navigateur.


## Modules principaux

### `utils/vector_store.py`

Gère l'index vectoriel FAISS et la recherche sémantique :
- Chargement et découpage des documents
- Génération des embeddings avec Mistral
- Création et interrogation de l'index FAISS

### `utils/query_classifier.py` (script non trouvé!!!)

Détermine si une requête nécessite une recherche RAG :
- Analyse des mots-clés
- Classification avec le modèle Mistral
- Détection des questions spécifiques vs générales

### `utils/database.py` (script non trouvé!!! `data_loader` ?)

Gère la base de données SQLite pour les interactions :
- Enregistrement des questions et réponses
- Stockage des feedbacks utilisateurs
- Récupération des statistiques

## Personnalisation

Vous pouvez personnaliser l'application en modifiant les paramètres dans `utils/config.py` :
- Modèles Mistral utilisés
- Taille des chunks et chevauchement
- Nombre de documents par défaut
- Nom de la commune ou organisation


## Lancement du test evaluation avec Ragas

Ce test permettra de voir les performance du système RAG actuellement développé afin de trouver les points à améliorer, il donnera ainsi les scores suivants :
- context_precision : 
- context_recall : La pertinence des contextes récupéré par rapport à la question (compris entre 0 et 1)
- faithfulness : la fidélité de la réponse par rapport au contexte (compris entre 0 et 1)
- answer_relevancy : la pertinence de la réponse par rapport à la question (compris entre 0 et 1) 

Pour exécuter le test  :

```bash
 python evaluate_ragas.py
```

Ce script va génerer un fichier csv rag_evaluation.csv il faudra donc le lancer avec le notebook score_ragas.ipynb pour voir le résultat sous format Data_frame.


## Création du pipeline de validation des étapes avec Pydantic :

Le pipeline est créé via le script pipeline_rag.py, en exécutant ce script, Pydantic va valider les différentes étapes du process : chargement des données - nettoyage - génération des embeddings

Pour exécuter : 

```bash
 python pipeline_rag.py
```

## Création du pipeline d'ingestion des données dans posgreSQL


```bash
 python load_excel_to_db.py
```

Ce script permet de créer et compléter les tables dans la base de données PosgreSQL, c'est ici que le script sql_tool.py puisera ses réponses pour répondres aux questions purement statistiques. 


## Tool LangChain SQL (sql_tool.py)


Le fichier sql_tool.py fait tout ce qui est nécessaire :

✔️ 1. Génération dynamique de requêtes SQL

Le LLM produit du SQL propre grâce aux few-shots et au prompt contrôlé.

✔️ 2. Exécution SQL

db.run(sql_query) retourne une liste de tuples facile à exploiter.

✔️ 3. Few-shot Templates pour éviter les hallucinations

On a rajouté des exemples représentatifs.
C’est ce qui permet à Mistral d’être précis.


## Enrichissement des données (ajout de SQL)

Après avoir ajouté sql_tool dans le RAG (MistralChat) on peut maintenant poser des questions statistiques et avoir des réponses en lien avec notre fichier Excel

Il suffit de relancer le chat sur streamlit :

```bash
streamlit run MistralChat.py
```

Et reposer des questions statistique du type :

"Quels sont les 3 meilleurs joueurs ayant le pourcantage de 3 point le plus élevé ?" 

Selon le fichier Excel, la réponse devrait être : 

  - Alondes Williams 100%
  - Skal Labissiere 100%
  - PJ Dozier 66.7%

Ou encore, "Quels sont les 3 joueurs ayant des tentative de 3 points les plus élevé ?" 

Selon le fichier Excel et la base de données ça devrait être : 

  - Anthony Edwards 814
  - Stephen Curry  784
  - Malik Beasley 763

Si ce ne sont pas ces réponses alors le RAG est à revoir au niveau de la recherche des réponses dans la base de données. 