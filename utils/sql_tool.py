# sql_tool.py
import traceback
import os
import requests
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Charger les variables d'environnement du fichier .env
load_dotenv()

# ============================================================
# 1) Configuration
# ============================================================

# PostgreSQL
DATABASE_URL = os.getenv("POSTGRES_DATABASE_URL", "postgresql://postgres:1992@localhost:5432/sport_db")

# Mistral API
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    print("⚠️ Attention: La clé API Mistral (MISTRAL_API_KEY) n'est pas définie dans le fichier .env")

# ============================================================
# 2) Connexion à PostgreSQL
# ============================================================

def get_db_connection():
    """Établit une connexion à PostgreSQL"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("✅ Connexion PostgreSQL établie")
        return conn
    except Exception as e:
        print(f"❌ Erreur de connexion PostgreSQL: {e}")
        return None

# ============================================================
# 3) Description des tables
# ============================================================

TABLE_DESCRIPTIONS = {
    "players_stats": """
    Statistiques des joueurs NBA.
    Colonnes (toujours entre guillemets doubles):
      "Player", "Team", "Age", "GP", "W", "L", "Min", "PTS", "FGM", "FGA", 
      "FG_percent", "_3PA", "_3P_percent", "FTM", "FTA", "FT_percent", 
      "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "PF", "Plus_Minus", "PIE"
    """,
    
    "equipe": """
    Équipes NBA.
    Colonnes (toujours entre guillemets doubles):
      "Code", "Nom_complet_de_l_equipe"
    """,
    
    "analyse_saison_nba": """
    Analyse saison par équipe.
    Colonnes (toujours entre guillemets doubles):
      "id", "Code", "Nom_complet_de_l_equipe", "Nombre_de_joueur_par_equipe", "Nombre_de_point_total_par_equipe"
    """,
    
    "analyse_une_equipe": """
    Statistiques agrégées par joueur.
    Colonnes (toujours entre guillemets doubles):
      "id", "Player", "SUM_of_OREB", "SUM_of_DREB", "SUM_of_PIE", "SUM_of_AST", "SUM_of_STL", "SUM_of_BLK"
    """,
    
    "analyse_top_15_joueurs_points": """
    Top 15 des joueurs par points.
    Colonnes (toujours entre guillemets doubles):
      "id", "Players", "Nombre_de_point_total", "FGM", "Pourcentage_de_tirs_reussis", 
      "Pourcentage_de_reussite_aux_tirs_a_3_points", "Pourcentage_de_reussite_aux_lancers_francs", 
      "Rebonds_offensifs", "Estimation_de_l_impact_du_joueur"
    """,
    
    "dictionnaire_des_donnees": """
    Dictionnaire des colonnes.
    Colonnes (toujours entre guillemets doubles):
      "id", "Nom_de_colonne", "Signification"
    """
}

# ============================================================
# 4) Exemples de requêtes
# ============================================================

examples = [
    {
        "query": "Quels sont les 5 joueurs les plus âgés ?",
        "sql": """
SELECT "Player", "Age", "Team"
FROM players_stats
ORDER BY "Age" DESC
LIMIT 5;
        """
    },
    {
        "query": "Donne-moi les 10 joueurs qui ont marqué le plus de points par match.",
        "sql": """
SELECT "Player", "PTS", "Team"
FROM players_stats
ORDER BY "PTS" DESC
LIMIT 10;
        """
    },
    {
        "query": "Liste toutes les équipes NBA disponibles.",
        "sql": """
SELECT "Code", "Nom_complet_de_l_equipe"
FROM equipe;
        """
    },
    {
        "query": "Quels joueurs ont un pourcentage de tirs réussis supérieur à 50% ?",
        "sql": """
SELECT "Player", "FG_percent", "Team"
FROM players_stats
WHERE "FG_percent" > 50
ORDER BY "FG_percent" DESC;
        """
    },
    {
        "query": "Montre-moi le top 15 des joueurs par points totaux.",
        "sql": """
SELECT "Players", "Nombre_de_point_total", "Pourcentage_de_tirs_reussis"
FROM analyse_top_15_joueurs_points
ORDER BY "Nombre_de_point_total" DESC;
        """
    }
]

# ============================================================
# 5) Fonction API Mistral
# ============================================================

def call_mistral_api(prompt: str, max_tokens: int = 500) -> str:
    """Appelle l'API Mistral avec requests"""
    if not MISTRAL_API_KEY:
        return "Erreur: Clé API Mistral non définie"
    
    try:
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "mistral-small-latest",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": max_tokens
        }
        
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"Erreur API: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Erreur lors de l'appel API: {str(e)}"

##########################################################
def extract_sql_from_response(response: str) -> str:
    """Extrait le SQL de la réponse de l'API Mistral"""
    response = response.strip()
    
    # Si la réponse contient du SQL entre backticks
    if "```sql" in response:
        start = response.find("```sql") + 6
        end = response.find("```", start)
        if end != -1:
            return response[start:end].strip()
    
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        if end != -1:
            return response[start:end].strip()
    
    # Si la réponse est directement du SQL
    # Vérifier si ça ressemble à du SQL (contient SELECT, FROM, WHERE, etc.)
    sql_keywords = ["SELECT", "FROM", "WHERE", "ORDER BY", "LIMIT", "JOIN", "GROUP BY"]
    if any(keyword in response.upper() for keyword in sql_keywords):
        # Retirer les éventuels commentaires en début de ligne
        lines = response.split('\n')
        sql_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith('--') and not stripped.startswith('/*'):
                sql_lines.append(stripped)
        return ' '.join(sql_lines).strip()
    
    return response
# ============================================================
# 6) Prompt pour génération SQL
# ============================================================

def create_sql_prompt(question: str) -> str:
    """Crée un prompt pour générer du SQL"""
    
    tables_desc = "\n\n".join([f"Table: {table_name}\n{desc}" 
                              for table_name, desc in TABLE_DESCRIPTIONS.items()])
    
    examples_str = "\n\n".join([
        f"Question: {ex['query']}\nSQL: {ex['sql'].strip()}"
        for ex in examples
    ])
    
    prompt = f"""Tu es un assistant expert SQL pour les statistiques NBA.

BASE DE DONNÉES:
{tables_desc}

RÈGLES STRICTES:
1. Utilise UNIQUEMENT les tables ci-dessus
2. Les noms de colonnes DOIVENT être entre GUILLEMETS DOUBLES
3. Retourne UNIQUEMENT le code SQL
4. Ajoute LIMIT quand c'est utile
5. N'utilise pas de colonnes qui n'existent pas

EXEMPLES:

{examples_str}

CONVERTIS CETTE QUESTION EN SQL:

Question: {question}

SQL:"""
    
    return prompt

# ============================================================
# 7) Fonction principale
# ============================================================

def run_sql_query(question: str, max_rows: int = 100) -> str:
    """Exécute une requête SQL à partir d'une question"""
    
    if not MISTRAL_API_KEY:
        return "❌ Erreur: Clé API Mistral non définie"
    
    conn = get_db_connection()
    if conn is None:
        return "❌ Erreur: Base de données non connectée"
    
    try:
        print(f"\n{'='*60}")
        print(f"Question: {question}")
        print(f"{'='*60}")
        
        # 1. Générer SQL
        prompt = create_sql_prompt(question)
        print("📝 Génération SQL...")
        
        sql_response = call_mistral_api(prompt)
        
        # 🔹 AJOUT DEBUG : afficher la réponse brute
        print("📄 Réponse brute du modèle:\n", sql_response)
        
        if sql_response.startswith("Erreur"):
            return f"❌ {sql_response}"
        
        # 2. Extraire le SQL proprement
        sql_query = extract_sql_from_response(sql_response)
        
        if not sql_query:
            return "❌ Impossible d'extraire une requête SQL de la réponse"
        
        print(f"🧹 SQL extrait:\n{sql_query}")
        
        # 3. Nettoyer SQL
        sql_query = sql_query.strip()
        
        if not sql_query.endswith(';'):
            sql_query += ';'
        
        print(f"📊 SQL final:\n{sql_query}")
        
        # 4. Exécuter SQL
        print("⚡ Exécution...")
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql_query)
            
            if sql_query.strip().upper().startswith("SELECT"):
                rows = cursor.fetchmany(max_rows)
                
                if rows:
                    # Formater les résultats de manière plus lisible
                    result_lines = []
                    
                    # En-tête
                    if rows:
                        headers = rows[0].keys()
                        result_lines.append(" | ".join(headers))
                        result_lines.append("-" * 50)
                    
                    # Données
                    for row in rows:
                        values = []
                        for key in headers:
                            value = row[key]
                            # Formater les floats pour éviter trop de décimales
                            if isinstance(value, float):
                                values.append(f"{value:.2f}")
                            else:
                                values.append(str(value))
                        result_lines.append(" | ".join(values))
                    
                    result = "\n".join(result_lines)
                    
                    # Ajouter un résumé
                    result = f"📊 Résultats ({len(rows)} ligne(s)):\n\n{result}"
                    
                    if len(rows) >= max_rows:
                        result += f"\n\nℹ️ Résultats limités à {max_rows} lignes"
                    
                    print(f"✅ Résultats: {len(rows)} ligne(s)")
                    return result
                else:
                    print("ℹ️ Aucun résultat")
                    return "🔍 Aucun résultat trouvé pour cette requête."
            else:
                conn.commit()
                affected = cursor.rowcount
                print(f"✅ Requête exécutée: {affected} ligne(s) affectée(s)")
                return f"✅ Requête exécutée avec succès. {affected} ligne(s) affectée(s)."
            
    except Exception as e:
        error_msg = f"❌ ERREUR SQL: {str(e)}"
        print(error_msg)
        
        # Suggestions plus détaillées
        error_str = str(e).lower()
        
        if "column" in error_str and "does not exist" in error_str:
            # Extraire le nom de la colonne problématique
            import re
            match = re.search(r'column "([^"]+)" does not exist', error_str)
            if match:
                column = match.group(1)
                error_msg += f"\n💡 La colonne '{column}' n'existe pas. Vérifiez le nom exact."
        elif "relation" in error_str and "does not exist" in error_str:
            match = re.search(r'relation "([^"]+)" does not exist', error_str)
            if match:
                table = match.group(1)
                error_msg += f"\n💡 La table '{table}' n'existe pas. Tables disponibles: {list(TABLE_DESCRIPTIONS.keys())}"
        elif "syntax" in error_str:
            error_msg += "\n💡 Erreur de syntaxe SQL. Vérifiez la requête générée."
        elif "division by zero" in error_str:
            error_msg += "\n💡 Division par zéro détectée. Vérifiez les données."
        
        return error_msg
        
    finally:
        if conn:
            conn.close()

# ============================================================
# 8) Fonctions utilitaires
# ============================================================

def test_connection():
    """Teste les connexions"""
    print("\n🔧 Test de connexion...")
    
    # Test DB
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM players_stats;")
                count = cursor.fetchone()[0]
                print(f"✅ PostgreSQL: OK ({count} joueurs)")
        except Exception as e:
            print(f"❌ PostgreSQL: Erreur - {e}")
        finally:
            conn.close()
    else:
        print("❌ PostgreSQL: Non connecté")
    
    # Test API
    if MISTRAL_API_KEY:
        response = call_mistral_api("Réponds 'OK'")
        if "OK" in response or "ok" in response:
            print("✅ API Mistral: OK")
        else:
            print(f"✅ API Mistral: Réponse ({len(response)} chars)")
    else:
        print("❌ API Mistral: Clé manquante")

# ============================================================
# 9) Programme principal
# ============================================================

if __name__ == "__main__":
    test_connection()
    
    test_questions = [
        "Quels sont les 5 joueurs les plus âgés ?",
        "Donne-moi les 10 joueurs avec le plus de points par match",
        "Liste les équipes NBA",
        "Quels joueurs ont FG% > 50% ?",
        "Montre le top 15 des joueurs par points totaux"
    ]
    
    print(f"\n{'='*60}")
    print("🧪 TESTS")
    print(f"{'='*60}")
    
    results = []
    
    for i, question in enumerate(test_questions, 1):
        print(f"\nTest {i}/{len(test_questions)}")
        result = run_sql_query(question)
        
        # Aperçu
        if result and len(result) > 200:
            print(f"Résultat:\n{result[:200]}...")
        else:
            print(f"Résultat:\n{result}")
        
        results.append({
            "question": question,
            "result": result[:300] if result else "",
            "success": not result.startswith("❌") if result else False
        })
        
        print("-" * 40)
    
    # Résumé
    print(f"\n{'='*60}")
    print("📈 RÉSUMÉ")
    print(f"{'='*60}")
    
    success = sum(1 for r in results if r["success"])
    print(f"✅ Réussis: {success}/{len(results)}")
    print(f"❌ Échoués: {len(results)-success}/{len(results)}")
    
    # Export
    try:
        with open("sql_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("💾 Exporté: responses_json/sql_results.json")
    except Exception as e:
        print(f"⚠️ Export échoué: {e}")