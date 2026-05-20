"""
M2 — Analyse DuckDB du CSV de dépenses.

DuckDB lit le CSV comme s'il s'agissait d'une table SQL. On pose 6 requêtes
représentatives. Aucune base à monter : le fichier EST la base.
"""

import duckdb

CHEMIN = "data/depenses.csv"

con = duckdb.connect(":memory:")
# On crée une "vue" t qui pointe vers le CSV — pratique pour ne pas
# répéter read_csv_auto(...) dans chaque requête.
con.execute(f"""
    create view t as
    select * from read_csv_auto('{CHEMIN}', header=true)
""")


def afficher(titre, sql):
    print(f"\n── {titre} ──")
    print(con.execute(sql).fetchdf().to_string(index=False))


# 1. Total par mois — la courbe principale du dashboard.
afficher("Total par mois", """
    select date_trunc('month', date)::date as mois,
           round(sum(montant), 2) as total_eur,
           count(*) as nb_tx
    from t
    group by 1
    order by 1
""")

# 2. Total par catégorie + part en %.
afficher("Total par catégorie", """
    select categorie,
           round(sum(montant), 2) as total_eur,
           round(sum(montant) * 100.0 / (select sum(montant) from t), 1) as pct
    from t
    group by 1
    order by total_eur desc
""")

# 3. Top 10 marchands.
afficher("Top 10 marchands", """
    select marchand, categorie,
           round(sum(montant), 2) as total_eur,
           count(*) as nb
    from t
    group by 1, 2
    order by total_eur desc
    limit 10
""")

# 4. Évolution Tech mois par mois — voir la stabilité des abonnements.
afficher("Évolution mensuelle — Tech & outils dev", """
    select date_trunc('month', date)::date as mois,
           round(sum(montant), 2) as tech_eur
    from t
    where categorie = 'Tech & outils dev'
    group by 1
    order by 1
""")

# 5. Les extrêmes : 3 mois les plus chers / les moins chers.
afficher("3 mois les plus chers", """
    select date_trunc('month', date)::date as mois,
           round(sum(montant), 2) as total_eur
    from t
    group by 1
    order by total_eur desc
    limit 3
""")
afficher("3 mois les moins chers", """
    select date_trunc('month', date)::date as mois,
           round(sum(montant), 2) as total_eur
    from t
    group by 1
    order by total_eur asc
    limit 3
""")

# 6. Détecter les marchands récurrents (>= 12 mois sur 15 distincts).
# Pattern classique pour repérer automatiquement les "abonnements".
afficher("Marchands récurrents (≥ 12 mois distincts)", """
    select marchand,
           count(distinct date_trunc('month', date)) as mois_distincts,
           round(avg(montant), 2) as montant_moyen
    from t
    group by 1
    having count(distinct date_trunc('month', date)) >= 12
    order by mois_distincts desc, montant_moyen desc
""")
