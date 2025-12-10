# validation_models.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional


# ============================================================
# CONFIG GLOBAL
# ============================================================

class BaseCleanModel(BaseModel):
    """Modèle de base : convertit NaN → None et force les bons types."""

    @field_validator("*", mode="before")
    def clean_nan(cls, v):
        if v != v:  # NaN
            return None
        return v

    class Config:
        extra = "ignore"   # ignore colonnes inutiles
        arbitrary_types_allowed = True


# ============================================================
# 1️⃣ PLAYER MODEL
# ============================================================

class PlayerModel(BaseCleanModel):
    Player: str
    Team: Optional[str]
    Age: Optional[int]
    GP: Optional[int]
    W: Optional[int]
    L: Optional[int]
    Min: Optional[float]
    PTS: Optional[int]
    FGM: Optional[int]
    FGA: Optional[int]
    FG_percent: Optional[float]
    datatime_15_00: Optional[int]
    _3PA: Optional[int]
    _3P_percent: Optional[float]
    FTM: Optional[int]
    FTA: Optional[int]
    FT_percent: Optional[float]
    OREB: Optional[int]
    DREB: Optional[int]
    REB: Optional[int]
    AST: Optional[int]
    TOV: Optional[int]
    STL: Optional[int]
    BLK: Optional[int]
    PF: Optional[int]
    FP: Optional[int]
    DD2: Optional[int]
    TD3: Optional[int]
    Plus_Minus: Optional[float]
    OFFRTG: Optional[float]
    DEFRTG: Optional[float]
    NETRTG: Optional[float]
    AST_percent: Optional[float]
    AST_TO: Optional[float]
    AST_RATIO: Optional[float]
    OREB_percent: Optional[float]
    DREB_percent: Optional[float]
    REB_percent: Optional[float]
    TO_RATIO: Optional[float]
    EFG_percent: Optional[float]
    TS_percent: Optional[float]
    USG_percent: Optional[float]
    PACE: Optional[float]
    PIE: Optional[float]
    POSS: Optional[int]


# ============================================================
# 2️⃣ EQUIPE MODEL
# ============================================================

class EquipeModel(BaseCleanModel):
    Code: str
    Nom_complet_de_l_equipe: Optional[str]


# ============================================================
# 3️⃣ DICTIONARY MODEL
# ============================================================

class DictionaryModel(BaseCleanModel):
    Nom_de_colonne: Optional[str]
    Signification: Optional[str]


# ============================================================
# 4️⃣ TeamSeasonAnalysis MODEL
# ============================================================

class TeamSeasonAnalysisModel(BaseCleanModel):
    Code: str
    Nom_complet_de_l_equipe: Optional[str]
    Nombre_de_joueur_par_equipe: Optional[int]
    Nombre_de_point_total_par_equipe: Optional[int]


# ============================================================
# 5️⃣ TeamStatsAnalysis MODEL
# ============================================================

class TeamStatsAnalysisModel(BaseCleanModel):
    Player: str
    SUM_of_OREB: Optional[int]
    SUM_of_DREB: Optional[int]
    SUM_of_PIE: Optional[float]
    SUM_of_AST: Optional[int]
    SUM_of_STL: Optional[int]
    SUM_of_BLK: Optional[int]


# ============================================================
# 6️⃣ Top15Players MODEL
# ============================================================

class Top15PlayersModel(BaseCleanModel):
    Players: str
    Nombre_de_point_total: Optional[int]
    FGM: Optional[int]
    Pourcentage_de_tirs_reussis: Optional[float]
    Pourcentage_de_reussite_aux_tirs_a_3_points: Optional[float]
    Pourcentage_de_reussite_aux_lancers_francs: Optional[float]
    Rebonds_offensifs: Optional[int]
    Estimation_de_l_impact_du_joueur: Optional[float]
