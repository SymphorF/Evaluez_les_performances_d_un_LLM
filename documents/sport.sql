CREATE TABLE "players" (
  "Player" varchar PRIMARY KEY,
  "Team" varchar,
  "Age" int
);

CREATE TABLE "stats" (
  "Player" varchar,
  "Team" varchar,
  "Age" int,
  "GP" int,
  "W" int,
  "L" int,
  "Min" float,
  "PTS" int,
  "FGM" int,
  "FGA" int,
  "FG_percent" float,
  "datatime_15_00" int,
  "3PA" int,
  "3P_percent" float,
  "FTM" int,
  "FTA" int,
  "FT_percent" float,
  "OREB" int,
  "DREB" int,
  "AST" int,
  "TOV" int,
  "STL" int,
  "BLK" int,
  "PF" int,
  "FP" int,
  "DD2" int,
  "TD3" int,
  "Plus_Minus" float,
  "OFFRTG" float,
  "DEFRTG" float,
  "NETRTG" float,
  "AST_percent" float,
  "AST_TO" float,
  "AST_RATIO" float,
  "OREB_percent" float,
  "DREB_percent" float,
  "REB_percent" float,
  "TO_RATIO" float,
  "EFG_percent" float,
  "TS_percent" float,
  "USG_percent" float,
  "PACE" float,
  "PIE" float,
  "POSS" int
);

CREATE TABLE "Equipe" (
  "Code" varchar PRIMARY KEY,
  "Nom_complet_de_l_equipe" varchar
);

CREATE TABLE "matches" (
  "match_id" int PRIMARY KEY,
  "home_team" varchar,
  "away_team" varchar,
  "match_date" date,
  "home_score" int,
  "away_score" int
);

CREATE TABLE "Analyse_de_la_saison_NBA" (
  "Code" varchar,
  "Nom_complet_de_l_equipe" varchar,
  "Nombre_de_joueur_par_equipe" varchar,
  "Nombre_de_point_total_par_equipe" varchar
);

CREATE TABLE "Analyse_d_une_equipe" (
  "Player" varchar,
  "SUM_of_OREB" int,
  "SUM_of_DREB" int,
  "SUM_of_PIE" float,
  "SUM_of_AST" int,
  "SUM_of_STL" int,
  "SUM_of_BLK" int
);

CREATE TABLE "Analyse_du_top_15_des_joueurs_en_nombre_de_points" (
  "Players" varchar,
  "Nombre_de_point_total" int,
  "FGM" int,
  "Pourcentage_de_tirs_reussis" float,
  "Pourcentage_de_reussite_aux_tirs_a_3_points" float,
  "Pourcentage_de_reussite_aux_lancers_francs" float,
  "Rebonds_offensifs" int,
  "Estimation_de_l_impact_du_joueur" float
);

CREATE TABLE "Dictionnaire_des_donnes" (
  "Nom_de_colonne" varchar,
  "Signification" varchar
);

ALTER TABLE "stats" ADD FOREIGN KEY ("Player") REFERENCES "players" ("Player");

ALTER TABLE "matches" ADD FOREIGN KEY ("home_team") REFERENCES "Equipe" ("Code");

ALTER TABLE "matches" ADD FOREIGN KEY ("away_team") REFERENCES "Equipe" ("Code");

ALTER TABLE "Analyse_de_la_saison_NBA" ADD FOREIGN KEY ("Code") REFERENCES "Equipe" ("Code");

ALTER TABLE "Analyse_d_une_equipe" ADD FOREIGN KEY ("Player") REFERENCES "players" ("Player");

ALTER TABLE "Analyse_du_top_15_des_joueurs_en_nombre_de_points" ADD FOREIGN KEY ("Players") REFERENCES "players" ("Player");
