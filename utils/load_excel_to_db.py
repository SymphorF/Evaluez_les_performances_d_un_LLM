# load_excel_to_db.py
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Importer toutes les classes
from models_db import Base, Player, Equipe, Dictionary, TeamSeasonAnalysis, TeamStatsAnalysis, Top15Players, Match


def load_excel_to_db(file_path: str):
    print("📘 Chargement du fichier :", file_path)
    xls = pd.ExcelFile(file_path, engine="openpyxl")

    # =============== CONFIG ===============
    SHEET_PLAYERS = "Données NBA"
    SHEET_TEAM = "Equipe"
    SHEET_DICT = "Dictionnaire des données"
    SHEET_ANALYSE = "Analyse"

    DATABASE_URL = "postgresql://postgres:1992@localhost:5432/sport_db"
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    Base.metadata.create_all(engine)
    print("✅ Toutes les tables créées/vérifiées")

    # ======================================
    # 1) INSERTION TABLE Player
    # ======================================
    print("\n=== FEUILLE PLAYERS ===")
    df_players = pd.read_excel(xls, sheet_name=SHEET_PLAYERS)

    column_mapping_players = {
        "FG%": "FG_percent",
        "3PA": "_3PA",
        "3P%": "_3P_percent",
        "FT%": "FT_percent",
        "+/-": "Plus_Minus",
        "AST%": "AST_percent",
        "AST/TO": "AST_TO",
        "AST RATIO": "AST_RATIO",
        "OREB%": "OREB_percent",
        "DREB%": "DREB_percent",
        "REB%": "REB_percent",
        "TO RATIO": "TO_RATIO",
        "EFG%": "EFG_percent",
        "TS%": "TS_percent",
        "USG%": "USG_percent",
    }

    df_players = df_players.rename(columns=column_mapping_players)
    df_players = df_players.replace({np.nan: None})

    print("→ Insertion des players =", len(df_players))

    for index, row in df_players.iterrows():
        try:
            data = {col: row[col] for col in df_players.columns}
            session.add(Player(**data))
        except Exception as e:
            print(f"⚠️ Ligne Player {index+1}: {e}")

    session.commit()
    print("✔️ Players insérés")

    # ======================================
    # 2) INSERTION TABLE Equipe
    # ======================================
    print("\n=== FEUILLE EQUIPE ===")
    df_team = pd.read_excel(xls, sheet_name=SHEET_TEAM)

    print("Colonnes Equipe trouvées:", df_team.columns.tolist())

    df_team = df_team.rename(columns={
        "Code": "Code",
        "Nom complet de l'équipe": "Nom_complet_de_l_equipe"
    })
    df_team = df_team.replace({np.nan: None})

    print("→ Insertion des équipes =", len(df_team))

    for index, row in df_team.iterrows():
        try:
            session.add(Equipe(
                Code=row["Code"],
                Nom_complet_de_l_equipe=row["Nom_complet_de_l_equipe"]
            ))
        except Exception as e:
            print(f"⚠️ Ligne Equipe {index+1}: {e}")

    session.commit()
    print("✔️ Équipes insérées")

    # ======================================
    # 3) INSERTION TABLE Dictionary
    # ======================================
    print("\n=== FEUILLE DICTIONNAIRE ===")
    try:
        # Forcer le type string pour éviter les problèmes de time
        df_dict = pd.read_excel(xls, sheet_name=SHEET_DICT, dtype={"Nom de colonne": str})
        
        print("ℹ️ Feuille Dictionnaire chargée. Insertion en cours...")
        
        df_dict = df_dict.rename(columns={
            "Nom de colonne": "Nom_de_colonne",
            "Signification": "Signification"
        })
        
        # Conversion explicite en string
        df_dict["Nom_de_colonne"] = df_dict["Nom_de_colonne"].astype(str)
        df_dict["Signification"] = df_dict["Signification"].astype(str)
        df_dict = df_dict.replace({np.nan: None})
        
        print("→ Insertion des entrées du dictionnaire =", len(df_dict))

        successful_dict = 0
        for index, row in df_dict.iterrows():
            try:
                nom_colonne = str(row["Nom_de_colonne"]) if pd.notna(row["Nom_de_colonne"]) else None
                signification = str(row["Signification"]) if pd.notna(row["Signification"]) else None
                
                if nom_colonne and signification:
                    session.add(Dictionary(
                        Nom_de_colonne=nom_colonne,
                        Signification=signification
                    ))
                    successful_dict += 1
            except Exception as e:
                print(f"⚠️ Ligne Dictionnaire {index+1}: {e}")

        session.commit()
        print(f"✔️ Dictionnaire inséré: {successful_dict}/{len(df_dict)} entrées")
        
    except Exception as e:
        print(f"⚠️ Erreur lors du traitement de la feuille Dictionnaire: {e}")

    # ======================================
    # 4) INSERTION FEUILLE ANALYSE (CORRIGÉE AVEC LES BONNES POSITIONS)
    # ======================================
    print("\n=== FEUILLE ANALYSE ===")
    try:
        # A. Premier tableau : Analyse de la saison NBA
        print("\n--- Tableau 1: Analyse de la saison NBA ---")
        # Ligne 6 = en-têtes, données de ligne 7 à 36 (30 lignes)
        df_saison = pd.read_excel(xls, sheet_name=SHEET_ANALYSE, skiprows=6, nrows=30)
        df_saison.columns = ["Code", "Nom_complet_de_l_equipe", "Nombre_de_joueur_par_equipe", "Nombre_de_point_total_par_equipe"]
        df_saison = df_saison.replace({np.nan: None})
        
        print(f"→ Insertion analyse saison = {len(df_saison)} équipes")
        
        successful_saison = 0
        for index, row in df_saison.iterrows():
            try:
                # CORRECTION : Vérifier que ce n'est pas une ligne d'en-tête
                if (pd.notna(row["Code"]) and 
                    row["Code"] != "Code" and 
                    not str(row["Code"]).startswith("Analyse")):
                    
                    session.add(TeamSeasonAnalysis(
                        Code=row["Code"],
                        Nom_complet_de_l_equipe=row["Nom_complet_de_l_equipe"],
                        Nombre_de_joueur_par_equipe=int(row["Nombre_de_joueur_par_equipe"]) if pd.notna(row["Nombre_de_joueur_par_equipe"]) else None,
                        Nombre_de_point_total_par_equipe=int(row["Nombre_de_point_total_par_equipe"]) if pd.notna(row["Nombre_de_point_total_par_equipe"]) else None
                    ))
                    successful_saison += 1
            except Exception as e:
                print(f"⚠️ Ligne Analyse Saison {index+1} ('{row['Code']}'): {e}")

        session.commit()
        print(f"✔️ Tableau 1 inséré: {successful_saison}/{len(df_saison)} équipes")

        # B. Deuxième tableau : Analyse d'une équipe  
        print("\n--- Tableau 2: Analyse d'une équipe ---")
        # Ligne 43 = en-têtes, données de ligne 44 à 63 (20 lignes)
        df_equipe_stats = pd.read_excel(xls, sheet_name=SHEET_ANALYSE, skiprows=43, nrows=20)
        df_equipe_stats.columns = ["Player", "SUM_of_OREB", "SUM_of_DREB", "SUM_of_PIE", "SUM_of_AST", "SUM_of_STL", "SUM_of_BLK"]
        df_equipe_stats = df_equipe_stats.replace({np.nan: None})
        
        print(f"→ Insertion analyse équipe = {len(df_equipe_stats)} joueurs")
        
        successful_equipe = 0
        for index, row in df_equipe_stats.iterrows():
            try:
                # CORRECTION : Vérifier que c'est un vrai nom de joueur
                if (pd.notna(row["Player"]) and 
                    row["Player"] != "Player" and 
                    not str(row["Player"]).startswith("Analyse") and
                    not str(row["Player"]).startswith("SUM")):
                    
                    session.add(TeamStatsAnalysis(
                        Player=row["Player"],
                        SUM_of_OREB=int(row["SUM_of_OREB"]) if pd.notna(row["SUM_of_OREB"]) else None,
                        SUM_of_DREB=int(row["SUM_of_DREB"]) if pd.notna(row["SUM_of_DREB"]) else None,
                        SUM_of_PIE=float(row["SUM_of_PIE"]) if pd.notna(row["SUM_of_PIE"]) else None,
                        SUM_of_AST=int(row["SUM_of_AST"]) if pd.notna(row["SUM_of_AST"]) else None,
                        SUM_of_STL=int(row["SUM_of_STL"]) if pd.notna(row["SUM_of_STL"]) else None,
                        SUM_of_BLK=int(row["SUM_of_BLK"]) if pd.notna(row["SUM_of_BLK"]) else None
                    ))
                    successful_equipe += 1
            except Exception as e:
                print(f"⚠️ Ligne Analyse Équipe {index+1} ('{row['Player']}'): {e}")

        session.commit()
        print(f"✔️ Tableau 2 inséré: {successful_equipe}/{len(df_equipe_stats)} joueurs")

        # C. Troisième tableau : Top 15 joueurs
        print("\n--- Tableau 3: Top 15 joueurs ---")
        # Ligne 89 = en-têtes, données de ligne 90 à 104 (15 lignes)
        df_top15 = pd.read_excel(xls, sheet_name=SHEET_ANALYSE, skiprows=89, nrows=15)
        df_top15.columns = ["Players", "Nombre_de_point_total", "FGM", "Pourcentage_de_tirs_reussis", 
                           "Pourcentage_de_reussite_aux_tirs_a_3_points", "Pourcentage_de_reussite_aux_lancers_francs",
                           "Rebonds_offensifs", "Estimation_de_l_impact_du_joueur"]
        df_top15 = df_top15.replace({np.nan: None})
        
        print(f"→ Insertion top 15 = {len(df_top15)} joueurs")
        
        successful_top15 = 0
        for index, row in df_top15.iterrows():
            try:
                # CORRECTION : Vérifier que c'est un vrai nom de joueur
                if (pd.notna(row["Players"]) and 
                    row["Players"] != "Players" and 
                    not str(row["Players"]).startswith("Analyse")):
                    
                    session.add(Top15Players(
                        Players=row["Players"],
                        Nombre_de_point_total=int(row["Nombre_de_point_total"]) if pd.notna(row["Nombre_de_point_total"]) else None,
                        FGM=int(row["FGM"]) if pd.notna(row["FGM"]) else None,
                        Pourcentage_de_tirs_reussis=float(row["Pourcentage_de_tirs_reussis"]) if pd.notna(row["Pourcentage_de_tirs_reussis"]) else None,
                        Pourcentage_de_reussite_aux_tirs_a_3_points=float(row["Pourcentage_de_reussite_aux_tirs_a_3_points"]) if pd.notna(row["Pourcentage_de_reussite_aux_tirs_a_3_points"]) else None,
                        Pourcentage_de_reussite_aux_lancers_francs=float(row["Pourcentage_de_reussite_aux_lancers_francs"]) if pd.notna(row["Pourcentage_de_reussite_aux_lancers_francs"]) else None,
                        Rebonds_offensifs=int(row["Rebonds_offensifs"]) if pd.notna(row["Rebonds_offensifs"]) else None,
                        Estimation_de_l_impact_du_joueur=float(row["Estimation_de_l_impact_du_joueur"]) if pd.notna(row["Estimation_de_l_impact_du_joueur"]) else None
                    ))
                    successful_top15 += 1
            except Exception as e:
                print(f"⚠️ Ligne Top 15 {index+1} ('{row['Players']}'): {e}")

        session.commit()
        print(f"✔️ Tableau 3 inséré: {successful_top15}/{len(df_top15)} joueurs")
        
    except Exception as e:
        print(f"⚠️ Erreur lors du traitement de la feuille Analyse: {e}")
        import traceback
        traceback.print_exc()

    session.close()
    print("\n🎉 IMPORTATION TERMINÉE - TOUTES LES TABLES SONT MAINTENANT REMPLIES !")


if __name__ == "__main__":
    load_excel_to_db("donnees_nba.xlsx")