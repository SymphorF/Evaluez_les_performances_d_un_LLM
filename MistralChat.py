
# MistralChat.py (version RAG)
'''
import os
import logging
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from dotenv import load_dotenv
import streamlit as st

# --- Importations depuis vos modules ---
try:
    from utils.config import (
        MISTRAL_API_KEY, MODEL_NAME, SEARCH_K,
        APP_TITLE, NAME
    )
    from utils.vector_store import VectorStoreManager
except ImportError as e:
    st.error(f"Erreur d'importation: {e}. Vérifiez la structure de vos dossiers et les fichiers dans 'utils'.")
    st.stop()


# --- Configuration du Logging ---
# Note: Streamlit peut avoir sa propre gestion de logs. Configurer ici est une bonne pratique.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

# --- Configuration de l'API Mistral ---
api_key = MISTRAL_API_KEY
model = MODEL_NAME

if not api_key:
    st.error("Erreur : Clé API Mistral non trouvée (MISTRAL_API_KEY). Veuillez la définir dans le fichier .env.")
    st.stop()

try:
    client = MistralClient(api_key=api_key)
    logging.info("Client Mistral initialisé.")
except Exception as e:
    st.error(f"Erreur lors de l'initialisation du client Mistral : {e}")
    logging.exception("Erreur initialisation client Mistral")
    st.stop()

# --- Chargement du Vector Store (mis en cache) ---
@st.cache_resource # Garde le manager chargé en mémoire pour la session
def get_vector_store_manager():
    logging.info("Tentative de chargement du VectorStoreManager...")
    try:
        manager = VectorStoreManager()
        # Vérifie si l'index a bien été chargé par le constructeur
        if manager.index is None or not manager.document_chunks:
            st.error("L'index vectoriel ou les chunks n'ont pas pu être chargés.")
            st.warning("Assurez-vous d'avoir exécuté 'python indexer.py' après avoir placé vos fichiers dans le dossier 'inputs'.")
            logging.error("Index Faiss ou chunks non trouvés/chargés par VectorStoreManager.")
            return None # Retourne None si échec
        logging.info(f"VectorStoreManager chargé avec succès ({manager.index.ntotal} vecteurs).")
        return manager
    except FileNotFoundError:
         st.error("Fichiers d'index ou de chunks non trouvés.")
         st.warning("Veuillez exécuter 'python indexer.py' pour créer la base de connaissances.")
         logging.error("FileNotFoundError lors de l'init de VectorStoreManager.")
         return None
    except Exception as e:
        st.error(f"Erreur inattendue lors du chargement du VectorStoreManager: {e}")
        logging.exception("Erreur chargement VectorStoreManager")
        return None

vector_store_manager = get_vector_store_manager()

# --- Prompt Système pour RAG ---
# Adaptez ce prompt selon vos besoins
SYSTEM_PROMPT = f"""Tu es 'NBA Analyst AI', un assistant expert sur la ligue de basketball NBA.
Ta mission est de répondre aux questions des fans en animant le débat.

---
{{context_str}}
---

QUESTION DU FAN:
{{question}}

RÉPONSE DE L'ANALYSTE NBA:"""


# --- Initialisation de l'historique de conversation ---
if "messages" not in st.session_state:
    # Message d'accueil initial
    st.session_state.messages = [{"role": "assistant", "content": f"Bonjour ! Je suis votre analyste IA pour la {NAME}. Posez-moi vos questions sur les équipes, les joueurs ou les statistiques, et je vous répondrai en me basant sur les données les plus récentes."}]

# --- Fonctions ---

def generer_reponse(prompt_messages: list[ChatMessage]) -> str:
    """
    Envoie le prompt (qui inclut maintenant le contexte) à l'API Mistral.
    """
    if not prompt_messages:
         logging.warning("Tentative de génération de réponse avec un prompt vide.")
         return "Je ne peux pas traiter une demande vide."
    try:
        logging.info(f"Appel à l'API Mistral modèle '{model}' avec {len(prompt_messages)} message(s).")
        # Log le contenu du prompt (peut être long) - commenter si trop verbeux
        # logging.debug(f"Prompt envoyé à l'API: {prompt_messages}")

        response = client.chat(
            model=model,
            messages=prompt_messages,
            temperature=0.1, # Température basse pour des réponses factuelles basées sur le contexte
            # top_p=0.9,
        )
        if response.choices and len(response.choices) > 0:
            logging.info("Réponse reçue de l'API Mistral.")
            return response.choices[0].message.content
        else:
            logging.warning("L'API n'a pas retourné de choix valide.")
            return "Désolé, je n'ai pas pu générer de réponse valide pour le moment."
    except Exception as e:
        st.error(f"Erreur lors de l'appel à l'API Mistral: {e}")
        logging.exception("Erreur API Mistral pendant client.chat")
        return "Je suis désolé, une erreur technique m'empêche de répondre. Veuillez réessayer plus tard."

# --- Interface Utilisateur Streamlit ---
st.title(APP_TITLE)
st.caption(f"Assistant virtuel pour {NAME} | Modèle: {model}")

# Affichage des messages de l'historique (pour l'UI)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Zone de saisie utilisateur
if prompt := st.chat_input(f"Posez votre question sur la {NAME}..."):
    # 1. Ajouter et afficher le message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # === Début de la logique RAG ===

    # 2. Vérifier si le Vector Store est disponible
    if vector_store_manager is None:
        st.error("Le service de recherche de connaissances n'est pas disponible. Impossible de traiter votre demande.")
        logging.error("VectorStoreManager non disponible pour la recherche.")
        # On arrête ici car on ne peut pas faire de RAG
        st.stop()

    # 3. Rechercher le contexte dans le Vector Store
    try:
        logging.info(f"Recherche de contexte pour la question: '{prompt}' avec k={SEARCH_K}")
        search_results = vector_store_manager.search(prompt, k=SEARCH_K)
        logging.info(f"{len(search_results)} chunks trouvés dans le Vector Store.")
    except Exception as e:
        st.error(f"Une erreur est survenue lors de la recherche d'informations pertinentes: {e}")
        logging.exception(f"Erreur pendant vector_store_manager.search pour la query: {prompt}")
        search_results = [] # On continue sans contexte si la recherche échoue

    # 4. Formater le contexte pour le prompt LLM
    context_str = "\n\n---\n\n".join([
        f"Source: {res['metadata'].get('source', 'Inconnue')} (Score: {res['score']:.1f}%)\nContenu: {res['text']}"
        for res in search_results
    ])

    if not search_results:
        context_str = "Aucune information pertinente trouvée dans la base de connaissances pour cette question."
        logging.warning(f"Aucun contexte trouvé pour la query: {prompt}")

    # 👉 AJOUT MINIMAL POUR AFFICHER LE CONTEXTE DANS LA CONSOLE
    logging.info(f"CONTEXTE UTILISÉ POUR LA RÉPONSE :\n{context_str}")        

    # 5. Construire le prompt final pour l'API Mistral en utilisant le System Prompt RAG
    final_prompt_for_llm = SYSTEM_PROMPT.format(context_str=context_str, question=prompt)

    # Créer la liste de messages pour l'API (juste le prompt système/utilisateur combiné)
    messages_for_api = [
        # On pourrait séparer system et user, mais Mistral gère bien un long message user structuré
        ChatMessage(role="user", content=final_prompt_for_llm)
    ]

    # === Fin de la logique RAG ===


    # 6. Afficher indicateur + Générer la réponse de l'assistant via LLM
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.text("...") # Indicateur simple

        # Génération de la réponse de l'assistant en utilisant le prompt augmenté
        response_content = generer_reponse(messages_for_api)

        # Affichage de la réponse complète
        message_placeholder.write(response_content)

    # 7. Ajouter la réponse de l'assistant à l'historique (pour affichage UI)
    st.session_state.messages.append({"role": "assistant", "content": response_content})

# Petit pied de page optionnel
st.markdown("---")
st.caption("Powered by Mistral AI & Faiss | Data-driven NBA Insights")
'''













































# MistralChat.py (version RAG + SQL Tool minimal changes)

import streamlit as st
import os
import logging
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from dotenv import load_dotenv
import re
import json
from datetime import datetime

# Charger .env
load_dotenv()

# --- Importations depuis vos modules ---
try:
    from utils.config import (
        MISTRAL_API_KEY, MODEL_NAME, SEARCH_K,
        APP_TITLE, NAME
    )
    from utils.vector_store import VectorStoreManager
except ImportError as e:
    st.error(f"Erreur d'importation: {e}. Vérifiez la structure de vos dossiers et les fichiers dans 'utils'.")
    st.stop()

# Import du SQL tool (minimal change)
try:
    from utils.sql_tool import run_sql_query
    SQL_TOOL_AVAILABLE = True
except Exception as e:
    SQL_TOOL_AVAILABLE = False
    logging.warning(f"Impossible d'importer run_sql_query depuis utils.sql_tool: {e}")

# --- Configuration de logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    handlers=[
        logging.FileHandler('mistralchat_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Configuration de l'API Mistral ---
api_key = MISTRAL_API_KEY
model = MODEL_NAME

if not api_key:
    st.error("Erreur : Clé API Mistral non trouvée (MISTRAL_API_KEY). Veuillez la définir dans le fichier .env.")
    st.stop()

try:
    client = MistralClient(api_key=api_key)
    logging.info("Client Mistral initialisé.")
except Exception as e:
    st.error(f"Erreur lors de l'initialisation du client Mistral : {e}")
    logging.exception("Erreur initialisation client Mistral")
    st.stop()

# --- Chargement du Vector Store (mis en cache) ---
@st.cache_resource
def get_vector_store_manager():
    logging.info("Tentative de chargement du VectorStoreManager...")
    try:
        manager = VectorStoreManager()
        if manager.index is None or not manager.document_chunks:
            st.error("L'index vectoriel ou les chunks n'ont pas pu être chargés.")
            st.warning("Assurez-vous d'avoir exécuté 'python indexer.py' après avoir placé vos fichiers dans le dossier 'inputs'.")
            logging.error("Index Faiss ou chunks non trouvés/chargés par VectorStoreManager.")
            return None
        logging.info(f"VectorStoreManager chargé avec succès ({manager.index.ntotal} vecteurs).")
        return manager
    except FileNotFoundError:
         st.error("Fichiers d'index ou de chunks non trouvés.")
         st.warning("Veuillez exécuter 'python indexer.py' pour créer la base de connaissances.")
         logging.error("FileNotFoundError lors de l'init de VectorStoreManager.")
         return None
    except Exception as e:
        st.error(f"Erreur inattendue lors du chargement du VectorStoreManager: {e}")
        logging.exception("Erreur chargement VectorStoreManager")
        return None

vector_store_manager = get_vector_store_manager()

# --- Prompt Système pour RAG ---
SYSTEM_PROMPT = f"""Tu es 'NBA Analyst AI', un assistant expert sur la ligue de basketball NBA.
Ta mission est de répondre aux questions des fans en animant le débat.

---
{{context_str}}
---

QUESTION DU FAN:
{{question}}

RÉPONSE DE L'ANALYSTE NBA:"""

# --- Initialisation de l'historique de conversation ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": f"Bonjour ! Je suis votre analyste IA pour la {NAME}. Posez-moi vos questions sur les équipes, les joueurs ou les statistiques, et je vous répondrai en me basant sur les données les plus récentes."}]

# ---------------------
# Fonction : détecter si question nécessite du SQL
# (version simple, basée sur mots-clés et présence de chiffres)
# ---------------------
def question_needs_sql(question: str) -> bool:
    """Détecte si une question nécessite une requête SQL"""
    if not question:
        return False
    
    q = question.lower()
    
    # Mots-clés statistiques
    statistical_keywords = [
        "combien", "nombre", "total", "somme", "addition", "compter",
        "moyenne", "moyen", "moyennes", "moyenné", "moyennée",
        "maximum", "max", "minimum", "min", "plus grand", "plus petit",
        "plus haut", "plus bas", "supérieur", "inférieur", "au-dessus", "en dessous",
        "classement", "classer", "rang", "position", "top", "meilleur", "pire",
        "pourcentage", "%", "ratio", "taux", "proportion",
        "statistique", "stats", "chiffre", "donnée", "données", "quantité",
        "point", "points", "rebond", "rebonds", "passe", "passes", "assist", "assists",
        "victoire", "victoires", "défaite", "défaites", "match", "matchs",
        "âge", "age", "vieille", "vieux", "jeune", "jeunes",
        "comparer", "comparaison", "différence", "écart",
        "dépasse", "excède", "dépasser", "excéder", "bat", "battre",
        "par match", "par saison", "par jeu", "par équipe",
        "efficacité", "efficace", "performance", "performant"
    ]
    
    # Phrases types
    statistical_patterns = [
        r"quel est le", r"quelle est la", r"quels sont les", r"quelles sont les",
        r"quel joueur a le", r"quelle équipe a la", r"qui a le", r"qui a la",
        r"combien de", r"combien y a-t-il", r"nombre de", r"quantité de",
        r"moyenne de", r"total de", r"somme des", r"addition des",
        r"plus grand", r"plus petit", r"plus élevé", r"plus bas",
        r"meilleur", r"pire", r"premier", r"dernier",
        r"supérieur à", r"inférieur à", r"au-dessus de", r"en dessous de",
        r"classé", r"classement des"
    ]
    
    # Vérifier les mots-clés
    has_keyword = any(keyword in q for keyword in statistical_keywords)
    
    # Vérifier les patterns
    has_pattern = any(re.search(pattern, q) for pattern in statistical_patterns)
    
    # Vérifier la présence de chiffres
    has_numbers = bool(re.search(r'\d', question))
    
    # Vérifier la présence d'opérateurs de comparaison
    has_comparison = any(op in q for op in [">", "<", ">=", "<=", "=", "!="])
    
    # Log pour le débogage
    logging.info(f"Détection SQL - Question: '{question}'")
    logging.info(f"  Keywords: {has_keyword}, Patterns: {has_pattern}, Nombres: {has_numbers}, Comparaison: {has_comparison}")
    
    # Retourne True si au moins 2 critères sont remplis
    criteria = [has_keyword, has_pattern, has_numbers, has_comparison]
    return sum(criteria) >= 2

# ---------------------
# Fonction : appel synthèse LLM sur résultats SQL
# ---------------------
def synthesize_sql_result(sql_result: str, user_question: str) -> str:
    """Synthétise les résultats SQL en réponse naturelle"""
    
    synth_prompt = f"""
Tu es 'NBA Analyst AI', un assistant expert en statistiques NBA.

Un utilisateur a posé une question sur les statistiques NBA. 
Voici les résultats bruts obtenus depuis la base de données :

QUESTION: {user_question}

RÉSULTATS BRUTS:
{sql_result[:1500]}  # Limité à 1500 caractères

Tâche : Analyse ces résultats et formule une réponse naturelle et informative en français.
Règles importantes :
1. Sois concis mais informatif (2-4 phrases maximum)
2. Mets en avant les points clés et les chiffres importants
3. Donne du contexte si nécessaire
4. Évite de simplement répéter les chiffres bruts
5. Si c'est une liste de données, résume les 3-5 principaux éléments
6. Utilise un ton professionnel mais accessible pour un fan de basket
7. N'invente pas de données qui ne sont pas dans les résultats
8. Si le résultat montre une absence de données, explique-le clairement

RÉPONSE SYNTHÉTIQUE (en français, style conversationnel) :
"""
    
    try:
        resp = client.chat(
            model=model,
            messages=[ChatMessage(role="user", content=synth_prompt)],
            temperature=0.1,
            max_tokens=300  # Limite pour garder la réponse concise
        )
        
        if resp.choices and len(resp.choices) > 0:
            return resp.choices[0].message.content
        else:
            return "Désolé, impossible de synthétiser les résultats pour le moment."
            
    except Exception as e:
        logging.exception("Erreur lors de la synthèse SQL par le LLM")
        return f"**Résultats statistiques :**\n\n{sql_result[:500]}..."

# ---------------------
# Fonction : génération réponse LLM pour RAG
# ---------------------
def generer_reponse(prompt_messages: list[ChatMessage]) -> str:
    if not prompt_messages:
         logging.warning("Tentative de génération de réponse avec un prompt vide.")
         return "Je ne peux pas traiter une demande vide."
    try:
        logging.info(f"Appel à l'API Mistral modèle '{model}' avec {len(prompt_messages)} message(s).")
        response = client.chat(
            model=model,
            messages=prompt_messages,
            temperature=0.1,
        )
        if response.choices and len(response.choices) > 0:
            logging.info("Réponse reçue de l'API Mistral.")
            return response.choices[0].message.content
        else:
            logging.warning("L'API n'a pas retourné de choix valide.")
            return "Désolé, je n'ai pas pu générer de réponse valide pour le moment."
    except Exception as e:
        st.error(f"Erreur lors de l'appel à l'API Mistral: {e}")
        logging.exception("Erreur API Mistral pendant client.chat")
        return "Je suis désolé, une erreur technique m'empêche de répondre. Veuillez réessayer plus tard."

# ---------------------
# Interface Streamlit
# ---------------------
st.title(APP_TITLE)
st.caption(f"Assistant virtuel pour {NAME} | Modèle: {model}")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input(f"Posez votre question sur la {NAME}..."):
    # Ajouter et afficher le message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    handled = False  # si True, on a déjà répondu (via SQL) et on sautera le RAG

    # === Gestion SQL améliorée ===
    if SQL_TOOL_AVAILABLE and question_needs_sql(prompt):
        with st.chat_message("assistant"):
            status = st.empty()
            status.markdown("**🔢 Analyse statistique en cours...**")
            
            try:
                sql_result = run_sql_query(prompt)
            except Exception as e:
                sql_result = f"❌ Erreur lors de l'appel au SQL Tool: {str(e)}"
                logging.exception("Erreur run_sql_query")
            
            # Log pour débogage
            logging.info(f"Résultat SQL: {sql_result[:500]}...")
            
            # Vérifier si le résultat est valide et exploitable
            is_valid_result = (
                sql_result and 
                isinstance(sql_result, str) and 
                not sql_result.startswith("❌") and 
                not sql_result.startswith("Erreur") and
                not sql_result.startswith("ERROR") and
                "aucun résultat" not in sql_result.lower() and
                "Aucun résultat" not in sql_result
            )
            
            if is_valid_result:
                # Synthétiser le résultat
                try:
                    synthesis = synthesize_sql_result(sql_result, prompt)
                    
                    # Afficher la synthèse
                    st.markdown(synthesis)
                    
                    # Afficher aussi les résultats bruts dans un expander
                    with st.expander("📊 Voir les données complètes"):
                        st.code(sql_result, language="text")
                    
                    # Ajouter à l'historique
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"{synthesis}\n\n*(Données disponibles en cliquant sur '📊 Voir les données complètes')*"
                    })
                    
                    handled = True
                    
                except Exception as e:
                    logging.error(f"Erreur lors de la synthèse: {e}")
                    # Fallback: afficher directement les résultats
                    st.markdown("**📊 Résultats statistiques:**")
                    st.code(sql_result, language="text")
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"**Résultats statistiques:**\n```\n{sql_result}\n```"
                    })
                    handled = True
            else:
                # Indiquer l'échec et continuer avec RAG
                st.warning("La tentative SQL n'a pas fourni de résultats exploitables — je bascule sur la recherche contextuelle.")
                
                # Log du problème
                if sql_result:
                    logging.warning(f"Résultat SQL non exploitable: {sql_result[:200]}")
                
                handled = False

    # === Si pas géré par SQL, procéder au RAG classique ===
    if not handled:
        # Vérifier si le Vector Store est disponible
        if vector_store_manager is None:
            st.error("Le service de recherche de connaissances n'est pas disponible. Impossible de traiter votre demande.")
            logging.error("VectorStoreManager non disponible pour la recherche.")
            st.stop()

        # Recherche de contexte dans le Vector Store
        try:
            logging.info(f"Recherche de contexte pour la question: '{prompt}' avec k={SEARCH_K}")
            search_results = vector_store_manager.search(prompt, k=SEARCH_K)
            logging.info(f"{len(search_results)} chunks trouvés dans le Vector Store.")
        except Exception as e:
            st.error(f"Une erreur est survenue lors de la recherche d'informations pertinentes: {e}")
            logging.exception(f"Erreur pendant vector_store_manager.search pour la query: {prompt}")
            search_results = []

        # Formater le contexte pour le prompt LLM
        context_str = "\n\n---\n\n".join([
            f"Source: {res['metadata'].get('source', 'Inconnue')} (Score: {res.get('score', 0):.1f}%)\nContenu: {res.get('text','')}"
            for res in search_results
        ])

        if not search_results:
            context_str = "Aucune information pertinente trouvée dans la base de connaissances pour cette question."
            logging.warning(f"Aucun contexte trouvé pour la query: {prompt}")

        # 👉 AJOUT MINIMAL POUR AFFICHER LE CONTEXTE DANS LA CONSOLE
        logging.info(f"CONTEXTE UTILISÉ POUR LA RÉPONSE :\n{context_str}")

        # Construire le prompt final pour l'API Mistral
        final_prompt_for_llm = SYSTEM_PROMPT.format(context_str=context_str, question=prompt)
        messages_for_api = [ChatMessage(role="user", content=final_prompt_for_llm)]

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.text("...")

            response_content = generer_reponse(messages_for_api)

            message_placeholder.write(response_content)

        st.session_state.messages.append({"role": "assistant", "content": response_content})

# Footer
st.markdown("---")
st.caption("Powered by Mistral AI & Faiss | Data-driven NBA Insights")














































































