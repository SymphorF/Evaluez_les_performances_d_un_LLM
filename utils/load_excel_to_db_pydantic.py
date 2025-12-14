
# load_excel_to_db.py # avec validation Pydantic avant insertion
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Importer SQLAlchemy models
from models_db import (
    Base, Player, Equipe, Dictionary, TeamSeasonAnalysis,
    TeamStatsAnalysis, Top15Players, Match
)

# Importer Pydantic models
from validation_models import (
    PlayerModel, EquipeModel, DictionaryModel,
    TeamSeasonAnalysisModel, TeamStatsAnalysisModel,
    Top15PlayersModel
)

# Importer toutes les classes
from models_db import Base, Player, Equipe, Dictionary, TeamSeasonAnalysis, TeamStatsAnalysis, Top15Players, Match



def validate_and_insert(session, row_dict, pydantic_model, sqlalchemy_model, index, table_name):
    """
    Valide les données via Pydantic puis insère dans la base via SQLAlchemy.
    """
    try:
        # Validation Pydantic
        validated = pydantic_model.model_validate(row_dict)

        # Insertion SQLAlchemy
        session.add(sqlalchemy_model(**validated.model_dump()))
        return True

    except Exception as e:
        print(f"⚠️ Erreur {table_name} ligne {index+1}: {e}")
        return False



def load_excel_to_db(file_path: str):
    print("📘 Chargement du fichier :", file_path)
    xls = pd.ExcelFile(file_path, engine="openpyxl")

    # CONFIG
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
    # PLAYERS
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
    inserted = 0

    for index, row in df_players.iterrows():
        if validate_and_insert(
            session,
            {col: row[col] for col in df_players.columns},
            PlayerModel,
            Player,
            index,
            "Player"
        ):
            inserted += 1

    session.commit()
    print(f"✔️ Players insérés : {inserted}/{len(df_players)}")

    # ======================================
    # EQUIPE
    # ======================================
    print("\n=== FEUILLE EQUIPE ===")
    df_team = pd.read_excel(xls, sheet_name=SHEET_TEAM)

    df_team = df_team.rename(columns={
        "Code": "Code",
        "Nom complet de l'équipe": "Nom_complet_de_l_equipe"
    })
    df_team = df_team.replace({np.nan: None})

    print("→ Insertion des équipes =", len(df_team))
    inserted = 0

    for index, row in df_team.iterrows():
        if validate_and_insert(
            session,
            {
                "Code": row["Code"],
                "Nom_complet_de_l_equipe": row["Nom_complet_de_l_equipe"]
            },
            EquipeModel,
            Equipe,
            index,
            "Equipe"
        ):
            inserted += 1

    session.commit()
    print(f"✔️ Équipes insérées : {inserted}/{len(df_team)}")

    # ======================================
    # DICTIONNAIRE
    # ======================================
    print("\n=== FEUILLE DICTIONNAIRE ===")

    df_dict = pd.read_excel(xls, sheet_name=SHEET_DICT, dtype={"Nom de colonne": str})
    df_dict = df_dict.rename(columns={
        "Nom de colonne": "Nom_de_colonne",
        "Signification": "Signification"
    })
    df_dict = df_dict.replace({np.nan: None})

    print("→ Insertion du dictionnaire =", len(df_dict))
    inserted = 0

    for index, row in df_dict.iterrows():
        data = {
            "Nom_de_colonne": str(row["Nom_de_colonne"]) if row["Nom_de_colonne"] else None,
            "Signification": str(row["Signification"]) if row["Signification"] else None
        }

        if validate_and_insert(session, data, DictionaryModel, Dictionary, index, "Dictionary"):
            inserted += 1

    session.commit()
    print(f"✔️ Dictionnaire inséré : {inserted}/{len(df_dict)}")

    # ======================================
    # TABLEAU 1 – SAISON
    # ======================================
    print("\n=== FEUILLE ANALYSE / Tableau 1 ===")

    df_saison = pd.read_excel(xls, sheet_name=SHEET_ANALYSE, skiprows=6, nrows=30)
    df_saison.columns = [
        "Code",
        "Nom_complet_de_l_equipe",
        "Nombre_de_joueur_par_equipe",
        "Nombre_de_point_total_par_equipe"
    ]
    df_saison = df_saison.replace({np.nan: None})

    inserted = 0
    for index, row in df_saison.iterrows():
        if row["Code"] and row["Code"] != "Code":
            data = {
                "Code": row["Code"],
                "Nom_complet_de_l_equipe": row["Nom_complet_de_l_equipe"],
                "Nombre_de_joueur_par_equipe": row["Nombre_de_joueur_par_equipe"],
                "Nombre_de_point_total_par_equipe": row["Nombre_de_point_total_par_equipe"]
            }
            if validate_and_insert(
                session,
                data,
                TeamSeasonAnalysisModel,
                TeamSeasonAnalysis,
                index,
                "TeamSeasonAnalysis"
            ):
                inserted += 1

    session.commit()
    print(f"✔️ Tableau 1 inséré : {inserted}/{len(df_saison)}")

    # ======================================
    # TABLEAU 2 – ANALYSE INDIVIDUELLE
    # ======================================
    print("\n=== Tableau 2: Analyse équipe ===")

    df_stats = pd.read_excel(xls, sheet_name=SHEET_ANALYSE, skiprows=43, nrows=20)
    df_stats.columns = [
        "Player", "SUM_of_OREB", "SUM_of_DREB", "SUM_of_PIE",
        "SUM_of_AST", "SUM_of_STL", "SUM_of_BLK"
    ]
    df_stats = df_stats.replace({np.nan: None})

    inserted = 0
    for index, row in df_stats.iterrows():
        if row["Player"] and row["Player"] not in ["Player"]:

            data = {
                "Player": row["Player"],
                "SUM_of_OREB": row["SUM_of_OREB"],
                "SUM_of_DREB": row["SUM_of_DREB"],
                "SUM_of_PIE": row["SUM_of_PIE"],
                "SUM_of_AST": row["SUM_of_AST"],
                "SUM_of_STL": row["SUM_of_STL"],
                "SUM_of_BLK": row["SUM_of_BLK"],
            }

            if validate_and_insert(
                session,
                data,
                TeamStatsAnalysisModel,
                TeamStatsAnalysis,
                index,
                "TeamStatsAnalysis"
            ):
                inserted += 1

    session.commit()
    print(f"✔️ Tableau 2 inséré : {inserted}/{len(df_stats)}")

    # ======================================
    # TABLEAU 3 – TOP 15
    # ======================================
    print("\n=== Tableau 3: Top 15 joueurs ===")

    df_top15 = pd.read_excel(xls, sheet_name=SHEET_ANALYSE, skiprows=89, nrows=15)
    df_top15.columns = [
        "Players", "Nombre_de_point_total", "FGM",
        "Pourcentage_de_tirs_reussis",
        "Pourcentage_de_reussite_aux_tirs_a_3_points",
        "Pourcentage_de_reussite_aux_lancers_francs",
        "Rebonds_offensifs", "Estimation_de_l_impact_du_joueur"
    ]
    df_top15 = df_top15.replace({np.nan: None})

    inserted = 0
    for index, row in df_top15.iterrows():
        if row["Players"]:

            data = row.to_dict()

            if validate_and_insert(
                session,
                data,
                Top15PlayersModel,
                Top15Players,
                index,
                "Top15Players"
            ):
                inserted += 1

    session.commit()
    print(f"✔️ Tableau 3 inséré : {inserted}/{len(df_top15)}")

    session.close()
    print("\n🎉 IMPORTATION TERMINÉE AVEC VALIDATION PYDANTIC !")
if __name__ == "__main__":
    print("➡️ Démarrage du chargement Excel -> Base de données...")
    load_excel_to_db("donnees_nba.xlsx")
    print("✔️ Fin du chargement.")









