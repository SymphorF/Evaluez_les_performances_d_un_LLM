from dotenv import load_dotenv
load_dotenv()
import json
import warnings
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from langchain_community.embeddings import HuggingFaceEmbeddings
import pandas as pd
import os

# Supprimer les avertissements
warnings.filterwarnings("ignore")

# -----------------------------
# 1. Charger le dataset JSONL
# -----------------------------
def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return Dataset.from_list(records)

# -----------------------------
# 2. Créer un wrapper pour SentenceTransformer
# -----------------------------
class SentenceTransformerWrapper:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
    
    def embed_query(self, text):
        """Wrapper pour compatibilité avec RAGAS"""
        return self.model.encode(text).tolist()
    
    def embed_documents(self, texts):
        """Wrapper pour compatibilité avec RAGAS"""
        return [self.model.encode(text).tolist() for text in texts]

# -----------------------------
# 3. Fonction d'évaluation
# -----------------------------
def evaluate_ragas(jsonl_path):
    print("📥 Chargement du dataset...")
    dataset = load_jsonl(jsonl_path)
    
    # Vérifier la structure du dataset
    print(f"📊 Dataset chargé: {len(dataset)} exemples")
    print(f"Colonnes disponibles: {dataset.column_names}")
    
    # Afficher un exemple
    if len(dataset) > 0:
        print("\n🔍 Exemple d'entrée:")
        for key, value in dataset[0].items():
            print(f"  {key}: {str(value)[:100]}...")
    
    print("\n🔎 Chargement du modèle d'embeddings...")
    
    # Option 1: Utiliser HuggingFaceEmbeddings (compatible avec RAGAS)
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        print("✅ Embeddings HuggingFace chargés")
    except Exception as e:
        print(f"⚠️ Erreur avec HuggingFaceEmbeddings: {e}")
        # Option 2: Utiliser notre wrapper
        print("🔄 Utilisation du wrapper SentenceTransformer...")
        embeddings = SentenceTransformerWrapper()
    
    print("\n📊 Lancement de l'évaluation RAGAS...")
    
    try:
        result = evaluate(
            dataset=dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall
            ],
            embeddings=embeddings
        )
        
        print("✅ Évaluation terminée avec succès.")
        return result
        
    except Exception as e:
        print(f"❌ Erreur lors de l'évaluation: {e}")
        print("\n🔧 Tentative avec une configuration alternative...")
        
        # Tentative alternative avec moins de métriques
        try:
            result = evaluate(
                dataset=dataset,
                metrics=[faithfulness, answer_relevancy],
                embeddings=embeddings
            )
            print("✅ Évaluation partielle terminée.")
            return result
        except Exception as e2:
            print(f"❌ Échec de l'évaluation alternative: {e2}")
            return None

# -----------------------------
# 4. Export CSV avec plus de détails
# -----------------------------
def save_results_to_csv(result, filename="../notebooks/ragas_results_2.csv"):
    try:
        df = result.to_pandas()
        df.to_csv(filename, index=False)
        
        # Calculer les moyennes
        if not df.empty:
            summary = {
                'Metric': ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall'],
                'Average': [
                    df['faithfulness'].mean() if 'faithfulness' in df.columns else 'N/A',
                    df['answer_relevancy'].mean() if 'answer_relevancy' in df.columns else 'N/A',
                    df['context_precision'].mean() if 'context_precision' in df.columns else 'N/A',
                    df['context_recall'].mean() if 'context_recall' in df.columns else 'N/A'
                ],
                'Std': [
                    df['faithfulness'].std() if 'faithfulness' in df.columns else 'N/A',
                    df['answer_relevancy'].std() if 'answer_relevancy' in df.columns else 'N/A',
                    df['context_precision'].std() if 'context_precision' in df.columns else 'N/A',
                    df['context_recall'].std() if 'context_recall' in df.columns else 'N/A'
                ]
            }
            
            summary_df = pd.DataFrame(summary)
            summary_filename = "../notebooks/ragas_summary_2.csv"
            summary_df.to_csv(summary_filename, index=False)
            print(f"📊 Résumé enregistré dans {summary_filename}")
        
        print(f"📄 Résultats détaillés enregistrés dans {filename}")
        
    except Exception as e:
        print(f"⚠️ Erreur lors de l'enregistrement CSV: {e}")
        
        # Sauvegarder les résultats bruts
        try:
            results_dict = result.to_dict()
            with open("ragas_results_2.json", "w") as f:
                json.dump(results_dict, f, indent=2)
            print("💾 Résultats bruts enregistrés dans ragas_results_2.json")
        except:
            print("❌ Impossible d'enregistrer les résultats")

# -----------------------------
# 5. Fonction pour analyser les résultats
# -----------------------------
def analyze_results(result):
    """Analyse les résultats et donne des recommandations"""
    if result is None:
        print("❌ Aucun résultat à analyser")
        return
    
    try:
        # Convertir en dictionnaire
        results_dict = result.to_dict()
        
        print("\n" + "="*60)
        print("📈 ANALYSE DES RÉSULTATS RAGAS")
        print("="*60)
        
        for metric, score in results_dict.items():
            print(f"\n🔹 {metric.upper()}: {score:.4f}")
            
            # Recommandations basées sur les scores
            if metric == 'faithfulness':
                if score >= 0.8:
                    print("   ✅ Excellent! Les réponses sont fidèles aux sources.")
                elif score >= 0.6:
                    print("   ⚠️ Correct. Quelques réponses peuvent être inexactes.")
                elif score >= 0.4:
                    print("   ❌ Problème modéré. Vérifiez l'exactitude des réponses.")
                else:
                    print("   🔴 Critique! Les réponses ne sont pas fiables.")
                    
            elif metric == 'answer_relevancy':
                if score >= 0.8:
                    print("   ✅ Excellent! Les réponses sont très pertinentes.")
                elif score >= 0.6:
                    print("   ⚠️ Correct. Certaines réponses pourraient être plus ciblées.")
                elif score >= 0.4:
                    print("   ❌ Problème modéré. Les réponses sont souvent hors sujet.")
                else:
                    print("   🔴 Critique! Les réponses ne répondent pas aux questions.")
                    
            elif metric == 'context_precision':
                if score >= 0.8:
                    print("   ✅ Excellent! Contexte très précis.")
                elif score >= 0.6:
                    print("   ⚠️ Correct. Le contexte pourrait être mieux ciblé.")
                else:
                    print("   ❌ Problème! Le contexte manque de précision.")
                    
            elif metric == 'context_recall':
                if score >= 0.8:
                    print("   ✅ Excellent! Tout le contexte pertinent est récupéré.")
                elif score >= 0.6:
                    print("   ⚠️ Correct. Quelques informations pertinentes manquent.")
                else:
                    print("   ❌ Problème! Beaucoup d'informations pertinentes manquent.")
    
    except Exception as e:
        print(f"⚠️ Erreur lors de l'analyse: {e}")

# -----------------------------
# 6. Programme principal
# -----------------------------
if __name__ == "__main__":
    DATASET = "dataset_2.jsonl"
    
    # Vérifier si le fichier existe
    if not os.path.exists(DATASET):
        print(f"❌ Fichier {DATASET} non trouvé!")
        
        # Créer un dataset exemple si nécessaire
        print("📝 Création d'un dataset exemple...")
        example_data = [
            {
                "question": "Qui a remporté le championnat NBA en 2020?",
                "answer": "Les Los Angeles Lakers ont remporté le championnat NBA en 2020.",
                "contexts": ["En 2020, les Los Angeles Lakers ont remporté le championnat NBA face au Miami Heat."],
                "ground_truth": "Les Los Angeles Lakers"
            },
            {
                "question": "Quel joueur a le plus de titres de MVP?",
                "answer": "Kareem Abdul-Jabbar a gagné 6 titres de MVP.",
                "contexts": ["Kareem Abdul-Jabbar détient le record avec 6 titres de MVP."],
                "ground_truth": "Kareem Abdul-Jabbar"
            }
        ]
        
        with open(DATASET, "w", encoding="utf-8") as f:
            for item in example_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        
        print(f"✅ Dataset exemple créé: {DATASET}")
    
    print("🚀 Début de l'évaluation RAGAS...")
    
    try:
        results = evaluate_ragas(DATASET)
        
        if results is not None:
            print("\n" + "="*60)
            print("📊 RÉSULTATS COMPLETS :")
            print("="*60)
            
            # Afficher les résultats
            try:
                print(results)
            except:
                # Alternative pour l'affichage
                results_dict = results.to_dict()
                for key, value in results_dict.items():
                    print(f"{key}: {value}")
            
            # Analyser les résultats
            analyze_results(results)
            
            # Sauvegarder les résultats
            save_results_to_csv(results)
            
            print("\n" + "="*60)
            print("✅ ÉVALUATION TERMINÉE")
            print("="*60)
        else:
            print("❌ L'évaluation a échoué")
            
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
