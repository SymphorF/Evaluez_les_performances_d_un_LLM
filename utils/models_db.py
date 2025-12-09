# models_db.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Player(Base):
    __tablename__ = "players_stats"

    Player = Column(String,  primary_key=True)
    Team = Column(String)
    Age = Column(Integer)
    GP = Column(Integer)
    W = Column(Integer)
    L = Column(Integer)
    Min = Column(Float)
    PTS = Column(Integer)
    FGM = Column(Integer)
    FGA = Column(Integer)
    FG_percent = Column(Float)
    datatime_15_00 = Column(Integer)
    _3PA = Column(Integer)
    _3P_percent = Column(Float)
    FTM = Column(Integer)
    FTA = Column(Integer)
    FT_percent = Column(Float)
    OREB = Column(Integer)
    DREB = Column(Integer)
    REB = Column(Integer)
    AST = Column(Integer)
    TOV = Column(Integer)
    STL = Column(Integer)
    BLK = Column(Integer)
    PF = Column(Integer)
    FP = Column(Integer)
    DD2 = Column(Integer)
    TD3 = Column(Integer)
    Plus_Minus = Column(Float)
    OFFRTG = Column(Float)
    DEFRTG = Column(Float)
    NETRTG = Column(Float)
    AST_percent = Column(Float)
    AST_TO = Column(Float)
    AST_RATIO = Column(Float)
    OREB_percent = Column(Float)
    DREB_percent = Column(Float)
    REB_percent = Column(Float)
    TO_RATIO = Column(Float)
    EFG_percent = Column(Float)
    TS_percent = Column(Float)
    USG_percent = Column(Float)
    PACE = Column(Float)
    PIE = Column(Float)
    POSS = Column(Integer)

# =========================================================
# TABLE 2 : Analyse_de_la_saison_NBA (CORRIGÉE)
# =========================================================

class TeamSeasonAnalysis(Base):
    __tablename__ = "analyse_saison_nba"

    id = Column(Integer, primary_key=True, autoincrement=True)
    Code = Column(String, ForeignKey("equipe.Code"))
    Nom_complet_de_l_equipe = Column(String)
    Nombre_de_joueur_par_equipe = Column(Integer)
    Nombre_de_point_total_par_equipe = Column(Integer)

# =========================================================
# TABLE 3 : Analyse_d_une_equipe (CORRIGÉE)
# =========================================================

class TeamStatsAnalysis(Base):
    __tablename__ = "analyse_une_equipe"

    id = Column(Integer, primary_key=True, autoincrement=True)
    Player = Column(String, ForeignKey("players_stats.Player"))
    SUM_of_OREB = Column(Integer)
    SUM_of_DREB = Column(Integer)
    SUM_of_PIE = Column(Float)
    SUM_of_AST = Column(Integer)
    SUM_of_STL = Column(Integer)
    SUM_of_BLK = Column(Integer)

# =========================================================
# TABLE 4 : Analyse_du_top_15_des_joueurs_en_nombre_de_points (CORRIGÉE)
# =========================================================

class Top15Players(Base):
    __tablename__ = "analyse_top_15_joueurs_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    Players = Column(String, ForeignKey("players_stats.Player"))
    Nombre_de_point_total = Column(Integer)
    FGM = Column(Integer)
    Pourcentage_de_tirs_reussis = Column(Float)
    Pourcentage_de_reussite_aux_tirs_a_3_points = Column(Float)
    Pourcentage_de_reussite_aux_lancers_francs = Column(Float)
    Rebonds_offensifs = Column(Integer)
    Estimation_de_l_impact_du_joueur = Column(Float)

# =========================================================
# TABLE 5 : Equipe (EXISTANTE)
# =========================================================

class Equipe(Base):
    __tablename__ = "equipe"
    Code = Column(String, primary_key=True)
    Nom_complet_de_l_equipe = Column(String)

# =========================================================
# TABLE 6 : Dictionnaire_des_donnes (EXISTANTE)
# =========================================================

class Dictionary(Base):
    __tablename__ = "dictionnaire_des_donnees"
    id = Column(Integer, primary_key=True, autoincrement=True)
    Nom_de_colonne = Column(String)
    Signification = Column(String)


# =========================================================
# TABLE 7 : Matches (NOUVELLE TABLE)
# =========================================================

class Match(Base):
    __tablename__ = "matchs"

    match_id = Column(Integer, primary_key=True)
    home_team = Column(String, ForeignKey("equipe.Code"))
    away_team = Column(String)
    match_date = Column(String)  # Utilisation de String pour simplifier
    home_score = Column(Integer)
    away_score = Column(Integer)



