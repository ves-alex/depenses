"""
Génère un historique de dépenses synthétique aligné sur le profil d'Alex
(tech, espace, santé, finance + vie courante FR), sur 15 mois.

Aucune donnée réelle : tout est inventé via une distribution paramétrée
par catégorie/marchand. Reproductible (seed fixé).

Sortie : data/depenses.csv (colonnes : date, montant, categorie, marchand).
"""

import csv
import random
from datetime import date
from pathlib import Path

SEED = 42
random.seed(SEED)


def mois_en_arriere(d, n):
    """Renvoie le 1er jour du mois situé n mois avant d."""
    y, m = d.year, d.month - n
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)


# Fenêtre glissante : 15 mois finissant aujourd'hui. Quand le mois change,
# le cron régénère un CSV qui a vraiment évolué → commit non-vide.
DATE_FIN = date.today()
DATE_DEBUT = mois_en_arriere(DATE_FIN, 14)

# Config par catégorie. 4 leviers possibles :
#   subs          : abonnements mensuels (jour fixe + montant moyen + jitter)
#   bimestriels   : un mois sur deux (mois pairs)
#   trimestriels  : janvier / avril / juillet / octobre
#   ponctuels     : transactions aléatoires (n par mois, marchands pondérés)
#   annuels       : événements ponctuels une fois par an au mois donné
CATEGORIES = {
    "Logement & factures": {
        "subs": [
            {"marchand": "Loyer studio Tours", "jour": 3, "moyenne": 720, "jitter": 0},
            {"marchand": "Free Box Pop", "jour": 8, "moyenne": 29.99, "jitter": 0},
            {"marchand": "Free Mobile", "jour": 8, "moyenne": 15.99, "jitter": 0},
        ],
        "bimestriels": [{"marchand": "EDF", "jour": 15, "moyenne": 62, "jitter": 12}],
        "trimestriels": [{"marchand": "Veolia eau", "jour": 20, "moyenne": 38, "jitter": 8}],
        "annuels": [{"marchand": "MAIF assurance habitation", "mois": 9, "jour": 12, "moyenne": 135, "jitter": 0}],
    },
    "Courses": {
        "ponctuels": {
            "par_mois": (4, 6),
            "marchands": [("Carrefour Tours", 0.30), ("Lidl", 0.30), ("Biocoop", 0.18),
                          ("Marché des Halles", 0.12), ("Picard", 0.10)],
            "moyenne": 62, "ecart": 22,
        },
    },
    "Restos & cafés": {
        "ponctuels": {
            "par_mois": (6, 12),
            "marchands": [("La Souris Gourmande", 0.12), ("Le Café Leffe", 0.10),
                          ("Boulangerie Lhuillier", 0.20), ("Starbucks Tours", 0.10),
                          ("Uber Eats", 0.18), ("La Pizza Cosy", 0.15),
                          ("Café Méo", 0.10), ("Brasserie de l'Univers", 0.05)],
            "moyenne": 17, "ecart": 11,
        },
    },
    "Transport": {
        "subs": [{"marchand": "Vélociti Tours", "jour": 1, "moyenne": 3.50, "jitter": 0}],
        "ponctuels": {
            "par_mois": (3, 8),
            "marchands": [("Total Énergies", 0.28), ("SNCF Connect", 0.18), ("Bolt", 0.14),
                          ("Avia", 0.10), ("Parking Centre Tours", 0.10),
                          ("Péages Vinci Autoroutes", 0.15), ("Hertz location", 0.05)],
            "moyenne": 38, "ecart": 35,
        },
    },
    "Tech & outils dev": {
        "subs": [
            {"marchand": "Claude Pro", "jour": 5, "moyenne": 19, "jitter": 0},
            {"marchand": "ChatGPT Plus", "jour": 7, "moyenne": 22, "jitter": 0},
            {"marchand": "GitHub Copilot Pro", "jour": 10, "moyenne": 10, "jitter": 0},
            {"marchand": "Cursor Pro", "jour": 12, "moyenne": 20, "jitter": 0},
            {"marchand": "Vercel Pro", "jour": 14, "moyenne": 20, "jitter": 0},
            {"marchand": "Notion Plus", "jour": 18, "moyenne": 10, "jitter": 0},
            {"marchand": "Figma Pro", "jour": 22, "moyenne": 15, "jitter": 0},
            {"marchand": "iCloud 200 Go", "jour": 24, "moyenne": 2.99, "jitter": 0},
            {"marchand": "Anthropic API", "jour": 28, "moyenne": 9, "jitter": 14},
        ],
        "ponctuels": {
            "par_mois": (0, 2),
            "marchands": [("Apple Store accessoires", 0.25), ("Amazon hardware", 0.30),
                          ("Backmarket", 0.18), ("Anker", 0.12), ("OVH domaine .fr", 0.15)],
            "moyenne": 55, "ecart": 45,
        },
        "annuels": [{"marchand": "Apple Store iPhone", "mois": 3, "jour": 18, "moyenne": 1099, "jitter": 0}],
    },
    "Espace & astronomie": {
        "subs": [
            {"marchand": "Nebula", "jour": 17, "moyenne": 6.99, "jitter": 0},
            {"marchand": "Curiosity Stream", "jour": 19, "moyenne": 5.99, "jitter": 0},
        ],
        "ponctuels": {
            "par_mois": (0, 2),
            "marchands": [("Eyrolles livre astrophysique", 0.22), ("Fnac livre espace", 0.18),
                          ("Planétarium de Paris", 0.15), ("Observatoire de Tours", 0.10),
                          ("La Maison de l'Astronomie", 0.15), ("Librairie des Sciences", 0.20)],
            "moyenne": 24, "ecart": 12,
        },
        "annuels": [
            {"marchand": "Stellarium Mobile Plus", "mois": 6, "jour": 14, "moyenne": 13.99, "jitter": 0},
            {"marchand": "Celestron Outland 10x42", "mois": 11, "jour": 22, "moyenne": 285, "jitter": 0},
        ],
    },
    "Santé & sport": {
        "subs": [
            {"marchand": "Basic-Fit Premium", "jour": 2, "moyenne": 29.99, "jitter": 0},
            {"marchand": "Strava Premium", "jour": 9, "moyenne": 7.99, "jitter": 0},
        ],
        "ponctuels": {
            "par_mois": (2, 5),
            "marchands": [("Pharmacie centrale", 0.28), ("Nutripure", 0.20),
                          ("Decathlon Tours", 0.20), ("Doctolib consultation", 0.10),
                          ("Cabinet ostéopathe", 0.10), ("Dentiste Dr Martin", 0.07),
                          ("Kinésithérapeute", 0.05)],
            "moyenne": 45, "ecart": 32,
        },
    },
    "Finance": {
        "subs": [{"marchand": "Substack The Macro Compass", "jour": 11, "moyenne": 8, "jitter": 0}],
        "ponctuels": {
            "par_mois": (2, 5),
            "marchands": [("Trade Republic ordre", 0.55), ("Bourse Direct ordre", 0.18),
                          ("Fnac livre finance", 0.12), ("Eyrolles livre Bourse", 0.10),
                          ("Investopedia book", 0.05)],
            "moyenne": 5, "ecart": 6,
        },
    },
    "Loisirs & divers": {
        "subs": [
            {"marchand": "Spotify Famille", "jour": 6, "moyenne": 17.99, "jitter": 0},
            {"marchand": "Netflix Standard", "jour": 13, "moyenne": 14.99, "jitter": 0},
            {"marchand": "Kindle Unlimited", "jour": 21, "moyenne": 9.99, "jitter": 0},
        ],
        "ponctuels": {
            "par_mois": (2, 6),
            "marchands": [("Cinéma CGR Tours", 0.15), ("Cinéma UGC", 0.10),
                          ("Librairie Le Livre", 0.15), ("Uniqlo", 0.10),
                          ("COS", 0.05), ("Sephora", 0.08), ("Cadeau anniv", 0.08),
                          ("AirBnB weekend", 0.10), ("FNAC", 0.10), ("Decathlon vêtements", 0.09)],
            "moyenne": 52, "ecart": 38,
        },
        "annuels": [
            {"marchand": "Voyage été (TGV + AirBnB)", "mois": 7, "jour": 15, "moyenne": 860, "jitter": 80},
            {"marchand": "Cadeaux de Noël", "mois": 12, "jour": 18, "moyenne": 185, "jitter": 25},
        ],
    },
}


# ---------- Helpers ----------

def jitter(moyenne, ecart):
    """Renvoie un montant gaussien autour de la moyenne, arrondi, jamais négatif."""
    if ecart == 0:
        return round(moyenne, 2)
    val = random.gauss(moyenne, ecart / 2)
    return max(round(val, 2), 0.50)


def choisir_marchand(marchands_ponderes):
    noms = [n for n, _ in marchands_ponderes]
    poids = [p for _, p in marchands_ponderes]
    return random.choices(noms, weights=poids, k=1)[0]


def parcourir_mois(debut, fin):
    a, m = debut.year, debut.month
    while (a, m) <= (fin.year, fin.month):
        yield a, m
        m += 1
        if m == 13:
            a += 1
            m = 1


def date_safe(an, mo, jour):
    """Construit une date en bornant le jour (évite les soucis de mois courts)."""
    try:
        return date(an, mo, jour)
    except ValueError:
        return date(an, mo, 28)


def dans_periode(d):
    return DATE_DEBUT <= d <= DATE_FIN


# ---------- Génération ----------

def ajouter_subs(transactions, categorie, items, an, mo):
    for s in items:
        d = date_safe(an, mo, s["jour"])
        if dans_periode(d):
            transactions.append((d, jitter(s["moyenne"], s["jitter"]), categorie, s["marchand"]))


def ajouter_bimestriels(transactions, categorie, items, an, mo):
    if mo % 2 != 0:
        return
    ajouter_subs(transactions, categorie, items, an, mo)


def ajouter_trimestriels(transactions, categorie, items, an, mo):
    if mo not in (1, 4, 7, 10):
        return
    ajouter_subs(transactions, categorie, items, an, mo)


def ajouter_ponctuels(transactions, categorie, p, an, mo):
    n_min, n_max = p["par_mois"]
    for _ in range(random.randint(n_min, n_max)):
        d = date(an, mo, random.randint(1, 28))
        if dans_periode(d):
            marchand = choisir_marchand(p["marchands"])
            montant = jitter(p["moyenne"], p["ecart"])
            transactions.append((d, montant, categorie, marchand))


def ajouter_annuels(transactions, categorie, items, an):
    for a in items:
        d = date_safe(an, a["mois"], a["jour"])
        if dans_periode(d):
            transactions.append((d, jitter(a["moyenne"], a["jitter"]), categorie, a["marchand"]))


def generer():
    transactions = []
    annees_vues = set()
    for an, mo in parcourir_mois(DATE_DEBUT, DATE_FIN):
        for cat, conf in CATEGORIES.items():
            ajouter_subs(transactions, cat, conf.get("subs", []), an, mo)
            ajouter_bimestriels(transactions, cat, conf.get("bimestriels", []), an, mo)
            ajouter_trimestriels(transactions, cat, conf.get("trimestriels", []), an, mo)
            if "ponctuels" in conf:
                ajouter_ponctuels(transactions, cat, conf["ponctuels"], an, mo)
        if an not in annees_vues:
            annees_vues.add(an)
            for cat, conf in CATEGORIES.items():
                ajouter_annuels(transactions, cat, conf.get("annuels", []), an)
    transactions.sort(key=lambda t: t[0])
    return transactions


def main():
    Path("data").mkdir(exist_ok=True)
    transactions = generer()
    chemin = Path("data") / "depenses.csv"
    with chemin.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "montant", "categorie", "marchand"])
        for d, m, c, mar in transactions:
            writer.writerow([d.isoformat(), f"{m:.2f}", c, mar])
    total = sum(t[1] for t in transactions)
    n_mois = sum(1 for _ in parcourir_mois(DATE_DEBUT, DATE_FIN))
    print(f"{len(transactions)} transactions écrites dans {chemin}")
    print(f"Total : {total:,.2f} €  •  moyenne mensuelle : {total/n_mois:,.2f} €  •  {n_mois} mois couverts")


if __name__ == "__main__":
    main()
