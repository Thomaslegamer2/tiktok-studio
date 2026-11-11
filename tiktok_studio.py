#!/usr/bin/env python3
"""TikTok Studio — montage vertical 1080×1920 à partir de clips locaux.

Les vidéos viennent uniquement des fichiers choisis dans la fenêtre.
Le programme ne se connecte pas à TikTok et ne télécharge rien.

ffmpeg et ffprobe sont cherchés à côté du programme, dans le dossier
temporaire PyInstaller (sys._MEIPASS), puis dans le PATH.
"""

from __future__ import annotations

import ctypes
import os
import random
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ---------------------------------------------------------------------------
# Phrases automatiques
# Modifie ces listes pour changer « Générer automatiquement ».
# Une phrase fixe est utilisée telle quelle.
# Un sujet est combiné avec une action : « Les riches épargnent d'abord ».
# Le bouton mélange le français, l'anglais, ou les deux.
# ---------------------------------------------------------------------------

PHRASES_FR = [
    "Pense comme un riche",
    "Ta richesse commence aujourd'hui",
    "Investis avant de dépenser",
    "Le temps, c'est de l'argent",
    "Tes habitudes font ta richesse",
    "Ne vends pas ton temps",
    "Ton argent doit travailler",
    "Le contrôle fait la richesse",
    "La patience paie toujours",
    "L'argent aime le calme",
    "Deviens difficile à arrêter",
    "Encore une année",
    "Reste dans le jeu",
    "La liberté se construit",
    "Moins de bruit, plus d'argent",
    "Le luxe est une conséquence",
    "Gagne lentement",
    "Ton futur te regarde",
    "Fais le travail ennuyeux",
    "Le plan bat l'humeur",
    "Du cash-flow, pas un salaire",
    "Possède, ne loue pas ta vie",
    "La discipline bat la chance",
    "Construis avant de montrer",
    "L'intérêt composé travaille",
    "Petit à petit, puis tout",
    "Choisis l'ennui rentable",
    "Ta liberté a un prix",
    "Sors des mauvaises dettes",
    "Apprends, puis investis",
    "Le calme est une stratégie",
    "Ne cours pas après l'argent",
    "Laisse l'argent venir",
    "Une décision par jour",
    "Protège ton attention",
    "Le temps perdu ne revient pas",
    "Deviens ton propre banquier",
    "Simple, régulier, riche",
    "La constance bat le talent",
    "Arrête de consommer",
    "Commence à posséder",
    "Aujourd'hui compte",
    "Demain se prépare",
    "Pas aujourd'hui",
    "Pas demain non plus",
    "Je continue",
    "Encore un mois",
    "La promesse, c'est le travail",
    "Le mois prochain",
    "Fais-le quand même",
    "Reste jusqu'au bout",
    "Ça arrive, reste",
    "Un pas de plus",
    "Ne lâche pas le plan",
    "La richesse est silencieuse",
    "Riche est une habitude",
    "Joue sur la durée",
    "Tiens ta parole",
    "Reviens demain",
    "Cette année change tout",
    "N'abandonne pas trop tôt",
    "L'attente fait le travail",
    "Toujours en construction",
    "Presque, puis encore",
    "Pas de raccourci, du temps",
    "Lâche les excuses",
    "Moins d'envies, plus d'actifs",
    "Paie-toi en premier",
    "Automatise ton épargne",
    "Trois mois de côté",
    "Achète quand c'est calme",
    "Vends une compétence",
    "Crée une fois",
    "Gagne plusieurs fois",
    "Note chaque dépense",
    "Coupe ce qui ne sert pas",
    "Augmente ce que tu vaux",
    "Garde tes meilleures idées",
    "N'achète pas pour montrer",
    "Travaille le skill",
    "La liberté se mérite",
    "Sois long terme",
    "Ignore le bruit du jour",
    "Un actif de plus",
    "Zéro dette toxique",
    "Sommeil, plan, argent",
    "Reste difficile à distraire",
    "Le marché récompense l'attente",
    "Ta place se construit",
    "Fais moins, mieux",
    "Choisis tes heures",
    "L'argent suit l'ordre",
    "Range ta vie, puis investis",
    "Personne ne viendra le faire",
    "C'est ton tour de rester",
    "Promis, tu continues",
    "Le vrai luxe, c'est le temps",
    "Garde le cap",
    "Encore un actif",
    "Puis encore un",
]

SUJETS_FR = [
    "Les riches",
    "Les millionnaires",
    "Ceux qui gagnent",
    "Les disciplinés",
    "Les bâtisseurs",
    "Les ambitieux",
    "Les discrets",
    "Les constants",
    "Ceux qui restent",
    "Les lucides",
    "Les déterminés",
    "Les tenaces",
]

ACTIONS_FR = [
    "investissent tôt",
    "épargnent d'abord",
    "achètent des actifs",
    "ignorent le bruit",
    "visent loin",
    "gardent le cap",
    "apprennent chaque jour",
    "protègent leur temps",
    "refusent les dettes",
    "font travailler l'argent",
    "restent patients",
    "construisent en silence",
    "choisissent la liberté",
    "évitent la foule",
    "réinvestissent les gains",
    "suivent le plan",
]

PHRASES_EN = [
    "Think like the rich",
    "Your wealth starts today",
    "Invest before you spend",
    "Time is money",
    "Habits build wealth",
    "Don't sell your time",
    "Make your money work",
    "Control creates wealth",
    "Patience always pays",
    "Money likes calm",
    "Become hard to stop",
    "One more year",
    "Stay in the game",
    "Freedom is built",
    "Less noise, more money",
    "Luxury is a result",
    "Get rich slow",
    "Future you is watching",
    "Do the boring work",
    "The plan beats the mood",
    "Cash flow, not a salary",
    "Own your life",
    "Discipline beats luck",
    "Build before you show",
    "Compound interest works",
    "Small steps, then everything",
    "Choose profitable boring",
    "Freedom has a price",
    "Leave bad debt behind",
    "Learn, then invest",
    "Calm is a strategy",
    "Don't chase money",
    "Let money come to you",
    "One decision a day",
    "Protect your attention",
    "Lost time never returns",
    "Be your own bank",
    "Simple, steady, rich",
    "Consistency beats talent",
    "Stop consuming",
    "Start owning",
    "Today counts",
    "Tomorrow is prepared",
    "Maybe not today",
    "Maybe not tomorrow",
    "I keep going",
    "One more month",
    "The promise is the work",
    "Next month",
    "Do it anyway",
    "Stay until it works",
    "It's coming, stay",
    "One more step",
    "Don't drop the plan",
    "Wealth is quiet",
    "Rich is a habit",
    "Play the long game",
    "Keep your word",
    "Show up again",
    "This year changes it",
    "Don't quit early",
    "The wait is the work",
    "Still building",
    "Almost, then more",
    "No shortcut, just time",
    "Drop the excuses",
    "Fewer wants, more assets",
    "Pay yourself first",
    "Automate your savings",
    "Keep three months aside",
    "Buy when it's quiet",
    "Sell a skill",
    "Create it once",
    "Get paid many times",
    "Track every expense",
    "Cut what doesn't serve",
    "Raise what you're worth",
    "Keep your best ideas",
    "Don't buy to impress",
    "Train the skill",
    "Freedom is earned",
    "Think in decades",
    "Ignore today's noise",
    "One more asset",
    "Zero toxic debt",
    "Sleep, plan, money",
    "Stay hard to distract",
    "Markets reward waiting",
    "Your seat is built",
    "Do less, better",
    "Choose your hours",
    "Money follows order",
    "Tidy your life, then invest",
    "Nobody will do it for you",
    "This is your turn to stay",
    "Promise you'll continue",
    "Real luxury is time",
    "Hold the line",
    "Another asset",
    "Then another",
    "I promise",
    "True",
    "Keep going",
    "Not yet, but soon",
    "Stay with the plan",
    "Boring money wins",
    "Your future is expensive",
    "Make it inevitable",
]

SUJETS_EN = [
    "The rich",
    "Millionaires",
    "Winners",
    "Disciplined people",
    "Builders",
    "The ambitious",
    "Quiet people",
    "Steady people",
    "Those who stay",
    "Clear minds",
    "The determined",
    "Patient people",
]

ACTIONS_EN = [
    "invest early",
    "pay themselves first",
    "buy assets",
    "ignore the noise",
    "play the long game",
    "stay on the plan",
    "learn every day",
    "protect their time",
    "refuse bad debt",
    "let money work",
    "stay patient",
    "build in silence",
    "choose freedom",
    "skip the crowd",
    "reinvest the gains",
    "think in decades",
]

# Anciens noms, pour garder les listes françaises faciles à trouver.
PHRASES_FIXES = PHRASES_FR
SUJETS = SUJETS_FR
ACTIONS = ACTIONS_FR


# Apparence de la fenêtre.
FOND = "#14161c"
CARTE = "#1e2129"
CHAMP = "#12141a"
BORDURE = "#313744"
TEXTE = "#f4f5f7"
GRIS = "#9aa0ab"
OR = "#ffd700"
OR_SURVOL = "#ffe56a"
BOUTON = "#2a3040"
BOUTON_SURVOL = "#364055"
ENCRE = "#14161c"

# Format TikTok et look du montage.
LARGEUR = 1080
HAUTEUR = 1920
FPS = 30
FONDU = 0.18
LETTRES_PAR_LIGNE = 18
DUREE_MIN = 1.0
DUREE_MAX = 60.0
DUREE_DEFAUT = 3.0
DUREE_ENTIER_MAX = 900.0
# Espace fine entre les lettres : le texte reste lisible, avec de l'air.
ESPACE_LETTRE = "\u2009"

# Police fine d'abord : le texte des montages luxe est léger, pas en gras.
POLICES_TEXTE = {
    "fine": [
        r"C:\Windows\Fonts\segoeuil.ttf",
        r"C:\Windows\Fonts\segoeuisl.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "gras": [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "marque": [
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\segoeuisl.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeuil.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
}

# Chaque thème d'image est un petit lot de filtres ffmpeg.
THEMES_IMAGE = {
    "luxe": {
        "nom": "Luxe",
        "zoom": True,
        "filtres": ["eq=contrast=1.12:saturation=1.18:gamma=0.96", "vignette=PI/5"],
    },
    "nuit": {
        "nom": "Nuit",
        "zoom": True,
        "filtres": [
            "eq=contrast=1.22:brightness=-0.05:saturation=0.88:gamma=0.9",
            "colorbalance=bs=0.07:bm=0.04:rs=-0.05",
            "vignette=PI/6",
        ],
    },
    "or": {
        "nom": "Or",
        "zoom": True,
        "filtres": [
            "eq=contrast=1.1:saturation=1.28:gamma=1.02",
            "colorbalance=rs=0.1:gs=0.04:bs=-0.08:rm=0.04",
            "vignette=PI/4.6",
        ],
    },
    "cinema": {
        "nom": "Cinéma",
        "zoom": True,
        "filtres": [
            "eq=contrast=1.18:saturation=0.78:gamma=0.94",
            "colorbalance=rs=0.03:bs=0.05",
            "vignette=PI/5",
        ],
    },
    "eclat": {
        "nom": "Éclat",
        "zoom": False,
        "filtres": ["eq=contrast=1.05:brightness=0.03:saturation=1.35"],
    },
    "brut": {
        "nom": "Brut",
        "zoom": False,
        "filtres": [],
    },
}

# Chaque thème de texte change la police, la place et le relief.
THEMES_TEXTE = {
    "fin": {
        "nom": "Fin",
        "style": "espace",
        "police": "fine",
        "taille": 50,
        "couleur": "white",
        "ombre": True,
        "boite": False,
        "place": "centre",
    },
    "impact": {
        "nom": "Impact",
        "style": "plein",
        "police": "gras",
        "taille": 72,
        "couleur": "white",
        "ombre": True,
        "boite": False,
        "place": "centre",
    },
    "bandeau": {
        "nom": "Bandeau",
        "style": "plein",
        "police": "fine",
        "taille": 40,
        "couleur": "white",
        "ombre": False,
        "boite": True,
        "place": "bas",
    },
    "or": {
        "nom": "Or",
        "style": "espace",
        "police": "fine",
        "taille": 50,
        "couleur": "0xF5D76E",
        "ombre": True,
        "boite": False,
        "place": "centre",
    },
    "minimal": {
        "nom": "Minimal",
        "style": "plein",
        "police": "fine",
        "taille": 44,
        "couleur": "white",
        "ombre": False,
        "boite": False,
        "place": "centre",
    },
    "titre": {
        "nom": "Titre",
        "style": "plein",
        "police": "gras",
        "taille": 64,
        "couleur": "white",
        "ombre": True,
        "boite": False,
        "place": "haut",
    },
}

# Pastille de couleur et phrase courte, affichées sous les choix.
PIP_IMAGE = {
    "luxe": "#e7c56a",
    "nuit": "#7f8cff",
    "or": "#ffd700",
    "cinema": "#9aa8c2",
    "eclat": "#ff8b5a",
    "brut": "#8b93a1",
}
AIDE_IMAGE = {
    "luxe": "Zoom lent, contraste doux, bords assombris.",
    "nuit": "Image plus sombre et plus froide, vignette marquée.",
    "or": "Lumière chaude, légèrement dorée.",
    "cinema": "Contraste plus fort, couleurs plus retenues.",
    "eclat": "Image plus claire et plus saturée, sans zoom.",
    "brut": "Recadrage vertical seul, sans effet.",
}
PIP_TEXTE = {
    "fin": "#f4f5f7",
    "impact": "#ffffff",
    "bandeau": "#9aa0ab",
    "or": "#f5d76e",
    "minimal": "#c5c9d1",
    "titre": "#ffe56a",
}
AIDE_TEXTE = {
    "fin": "Lettres fines, un peu espacées, au centre.",
    "impact": "Gros titre blanc, bien lisible.",
    "bandeau": "Phrase en bas, sur un bandeau sombre.",
    "or": "Lettres fines, en couleur or.",
    "minimal": "Blanc simple, sans ombre.",
    "titre": "Gros titre placé en haut de l'image.",
}

TYPES_VIDEO = [
    ("Vidéos", "*.mp4 *.mov *.mkv *.avi"),
    ("MP4", "*.mp4"),
    ("MOV", "*.mov"),
    ("MKV", "*.mkv"),
    ("AVI", "*.avi"),
    ("Tous les fichiers", "*.*"),
]


class ErreurMontage(Exception):
    """Erreur que l'on peut montrer telle quelle à l'utilisateur."""


def banque_phrases(langue: str) -> list[str]:
    """Phrases uniques en français, en anglais, ou dans les deux."""
    if langue == "en":
        blocs = [(PHRASES_EN, SUJETS_EN, ACTIONS_EN)]
    elif langue == "mix":
        blocs = [
            (PHRASES_FR, SUJETS_FR, ACTIONS_FR),
            (PHRASES_EN, SUJETS_EN, ACTIONS_EN),
        ]
    else:
        blocs = [(PHRASES_FR, SUJETS_FR, ACTIONS_FR)]

    vues: list[str] = []
    for fixes, sujets, actions in blocs:
        vues.extend(fixes)
        vues.extend(f"{sujet} {action}" for sujet in sujets for action in actions)
    return list(dict.fromkeys(phrase.strip() for phrase in vues if phrase.strip()))


def _premier_mot(phrase: str) -> str:
    return phrase.split(" ", 1)[0].lower()


def _piocher_varie(restantes: list[str], n: int) -> list[str]:
    """Prend n phrases, avec un début différent à chaque ligne quand c'est possible."""
    melange = list(restantes)
    random.shuffle(melange)
    choix: list[str] = []
    while melange and len(choix) < n:
        debut = _premier_mot(choix[-1]) if choix else ""
        index = next((i for i, phrase in enumerate(melange) if _premier_mot(phrase) != debut), None)
        if index is None:
            choix.extend(melange[: n - len(choix)])
            break
        choix.append(melange.pop(index))
    return choix


def generer_phrases(
    n: int,
    langue: str = "fr",
    deja_vues: set[str] | None = None,
) -> list[str]:
    """Pioche n phrases nouvelles. La liste ne recommence qu'une fois épuisée."""
    if n <= 0:
        return []

    banque = banque_phrases(langue)
    if not banque:
        return ["Ta richesse commence aujourd'hui"] * n

    vues = deja_vues if deja_vues is not None else set()
    resultat: list[str] = []
    while len(resultat) < n:
        restantes = [phrase for phrase in banque if phrase not in vues and phrase not in resultat]
        if not restantes:
            vues.clear()
            restantes = [phrase for phrase in banque if phrase not in resultat]
        if not restantes:
            restantes = list(banque)
        for phrase in _piocher_varie(restantes, n - len(resultat)):
            resultat.append(phrase)
            vues.add(phrase)
    return resultat[:n]


def dossiers_programme() -> list[str]:
    """Dossier du programme, puis dossier temporaire PyInstaller."""
    dossiers: list[str] = []

    def ajouter(chemin: str | None) -> None:
        if not chemin:
            return
        absolu = os.path.abspath(chemin)
        if absolu not in dossiers:
            dossiers.append(absolu)

    if getattr(sys, "frozen", False):
        ajouter(os.path.dirname(sys.executable))
    ajouter(os.path.dirname(os.path.abspath(__file__)))
    ajouter(getattr(sys, "_MEIPASS", None))
    return dossiers


def noms_outil(nom: str) -> list[str]:
    """ffmpeg et ffmpeg.exe, selon le système."""
    base = nom[:-4] if nom.lower().endswith(".exe") else nom
    if os.name == "nt":
        return [base + ".exe", base]
    return [base, base + ".exe"]


def trouver_executable(nom: str) -> str | None:
    """Cherche un outil à côté du programme, dans _MEIPASS, puis dans le PATH."""
    for dossier in dossiers_programme():
        for candidat in noms_outil(nom):
            chemin = os.path.join(dossier, candidat)
            if os.path.isfile(chemin):
                return os.path.abspath(chemin)

    for candidat in noms_outil(nom):
        trouve = shutil.which(candidat)
        if trouve:
            return os.path.abspath(trouve)
    return None


def chemin_reglage(nom: str) -> str:
    """Fichier de réglage à côté du programme, pas dans le dossier temporaire."""
    temporaire = getattr(sys, "_MEIPASS", None)
    temporaire = os.path.abspath(temporaire) if temporaire else ""
    for dossier in dossiers_programme():
        if temporaire and os.path.abspath(dossier) == temporaire:
            continue
        return os.path.join(dossier, nom)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), nom)


def lire_filigrane() -> str:
    """Le @compte mémorisé, ou une chaîne vide."""
    try:
        with open(chemin_reglage("filigrane.txt"), encoding="utf-8") as fichier:
            ligne = fichier.read().strip().splitlines()
    except OSError:
        return ""
    return ligne[0].strip() if ligne else ""


def enregistrer_filigrane(texte: str) -> None:
    """Mémorise le filigrane pour le prochain lancement."""
    try:
        with open(chemin_reglage("filigrane.txt"), "w", encoding="utf-8", newline="\n") as fichier:
            fichier.write(texte.strip())
    except OSError:
        return


def texte_filigrane(brut: str) -> str:
    """Prépare le @compte : une seule ligne, avec l'arobase."""
    propre = " ".join(brut.strip().split())
    if not propre:
        return ""
    if not propre.startswith("@"):
        propre = "@" + propre
    if len(propre) > 32:
        propre = propre[:32].rstrip()
    return propre


def taille_filigrane(texte: str, base: int) -> int:
    """Réduit un peu le @compte s'il est long, pour qu'il tienne en haut."""
    if len(texte) > 20:
        return max(26, base - 10)
    if len(texte) > 15:
        return max(28, base - 6)
    return base


def ligne_filigrane(texte: str, style: str) -> str:
    """Le @compte suit le même style que la phrase : majuscules, et lettres espacées."""
    propre = " ".join(texte.strip().split()).upper()
    if not propre:
        return ""
    if style == "espace":
        return _espacer(propre.split(" "))
    return propre


def trouver_police(role: str = "fine") -> str | None:
    """Cherche une police fine, grasse ou de filigrane."""
    for chemin in POLICES_TEXTE.get(role, POLICES_TEXTE["fine"]):
        if os.path.isfile(chemin):
            return os.path.abspath(chemin)
    return None


def echapper(chemin: str) -> str:
    """Prépare un chemin Windows pour un filtre ffmpeg.

    Les antislashs deviennent des slashs, et chaque deux-points est écrit \\:
    Le filtre reçoit donc un chemin du type C\\:/Users/clips/texte.txt.
    """
    texte = os.path.abspath(chemin).replace("\\", "/")
    texte = texte.replace("'", "\\'")
    texte = texte.replace(":", "\\:")
    return texte


def _espacer(mots: list[str]) -> str:
    """Écarte légèrement les lettres, et un peu plus les mots."""
    return (" " + ESPACE_LETTRE).join(ESPACE_LETTRE.join(mot) for mot in mots)


def lignes_texte(phrase: str, style: str = "espace") -> list[str]:
    """Découpe la phrase en majuscules. « espace » écarte les lettres."""
    propre = " ".join(phrase.strip().split()).upper()
    if not propre:
        return []
    limite = LETTRES_PAR_LIGNE if style == "espace" else 22
    groupes: list[list[str]] = []
    courant: list[str] = []
    lettres = 0
    for mot in propre.split(" "):
        poids = len(mot) + (1 if courant else 0)
        if courant and lettres + poids > limite:
            groupes.append(courant)
            courant = [mot]
            lettres = len(mot)
        else:
            courant.append(mot)
            lettres += poids
    if courant:
        groupes.append(courant)
    if style == "espace":
        return [_espacer(groupe) for groupe in groupes]
    return [" ".join(groupe) for groupe in groupes]


def taille_texte(lignes: list[str], base: int) -> int:
    """Réduit un peu la taille si une ligne est longue."""
    def lettres(ligne: str) -> int:
        return sum(1 for caractere in ligne if not caractere.isspace())

    plus_longue = max((lettres(ligne) for ligne in lignes), default=0)
    if plus_longue >= 18:
        return max(32, base - 16)
    if plus_longue >= 13:
        return max(36, base - 8)
    return base


def expression_y(index: int, nombre: int, pas: int, place: str) -> str:
    """Place le bloc au centre, en haut, ou dans le bas de l'image."""
    if place == "bas":
        return f"h*0.74+{index * pas}"
    if place == "haut":
        return f"h*0.16+{index * pas}"
    decalage = (index - (nombre - 1) / 2) * pas
    if abs(decalage) < 0.05:
        return "h/2-text_h/2"
    if decalage > 0:
        return f"h/2-text_h/2+{decalage:.1f}"
    return f"h/2-text_h/2-{abs(decalage):.1f}"


def _options_lancement() -> dict:
    """Évite l'ouverture d'une console quand le programme est un .exe fenêtré."""
    options: dict = {"stdin": subprocess.DEVNULL}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    return options


def lancer_processus(commande: list[str], **extra) -> subprocess.CompletedProcess:
    """Lance ffmpeg ou ffprobe sans passer par l'interpréteur de commandes."""
    options = _options_lancement()
    options.update(extra)
    return subprocess.run(commande, **options)


def decoder(donnees: bytes | None) -> str:
    """Lit la sortie de ffmpeg, en UTF-8 puis en encodage Windows."""
    if not donnees:
        return ""
    try:
        return donnees.decode("utf-8")
    except UnicodeDecodeError:
        return donnees.decode("cp1252", errors="replace")


def _flottant(texte: str) -> float | None:
    try:
        valeur = float(texte.strip())
    except ValueError:
        return None
    if valeur <= 0:
        return None
    return valeur


def _horodatage(texte: str) -> float | None:
    """Convertit 00:01:02.34 en secondes."""
    morceaux = texte.strip().split(":")
    if len(morceaux) != 3:
        return None
    try:
        heures = int(morceaux[0])
        minutes = int(morceaux[1])
        secondes = float(morceaux[2])
    except ValueError:
        return None
    return heures * 3600 + minutes * 60 + secondes


def _duree_ffprobe(ffprobe: str, chemin: str) -> float | None:
    requetes = (
        ["-select_streams", "v:0", "-show_entries", "stream=duration"],
        ["-show_entries", "format=duration"],
    )
    for requete in requetes:
        commande = [
            ffprobe,
            "-v", "error",
            *requete,
            "-of", "default=noprint_wrappers=1:nokey=1",
            chemin,
        ]
        try:
            resultat = lancer_processus(
                commande,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        valeur = _flottant(decoder(resultat.stdout))
        if valeur:
            return valeur
    return None


def _duree_ffmpeg(ffmpeg: str, chemin: str) -> float | None:
    """Secours quand ffprobe est absent : lit « Duration: » dans le message."""
    commande = [ffmpeg, "-hide_banner", "-nostdin", "-i", chemin]
    try:
        resultat = lancer_processus(
            commande,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    texte = decoder(resultat.stderr)
    marqueur = "Duration:"
    position = texte.find(marqueur)
    if position < 0:
        return None
    horloge = texte[position + len(marqueur):].strip().split(",", 1)[0]
    valeur = _horodatage(horloge)
    if valeur and valeur > 0:
        return valeur
    return None


def mesurer_duree(ffprobe: str | None, ffmpeg: str, chemin: str) -> float | None:
    """Durée réelle du fichier, ou None si elle est illisible."""
    if ffprobe:
        valeur = _duree_ffprobe(ffprobe, chemin)
        if valeur:
            return valeur
    return _duree_ffmpeg(ffmpeg, chemin)


def _contient_piste(ffprobe: str | None, chemin: str, selecteur: str, mot: str) -> bool | None:
    """True ou False si ffprobe a répondu, None s'il n'a pas pu vérifier."""
    if not ffprobe:
        return None
    commande = [
        ffprobe,
        "-v", "error",
        "-select_streams", selecteur,
        "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1:nokey=1",
        chemin,
    ]
    try:
        resultat = lancer_processus(
            commande,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return mot in decoder(resultat.stdout).lower()


def contient_video(ffprobe: str | None, chemin: str) -> bool | None:
    """Indique si le fichier a une piste image."""
    return _contient_piste(ffprobe, chemin, "v:0", "video")


def contient_audio(ffprobe: str | None, chemin: str) -> bool | None:
    """Indique si le fichier a une piste son."""
    return _contient_piste(ffprobe, chemin, "a:0", "audio")


def duree_utile(demandee: float, reelle: float | None, couper: bool) -> float:
    """Coupe à la durée choisie, ou garde le clip entier."""
    if not couper:
        if reelle is None or reelle <= 0:
            raise ErreurMontage(
                "La durée d'un clip n'a pas pu être lue.\n\n"
                "Active « Couper les clips » et indique une durée."
            )
        if reelle > DUREE_ENTIER_MAX:
            raise ErreurMontage(
                "Un clip dépasse 15 minutes.\n\n"
                "Active « Couper les clips » pour n'en garder qu'une partie."
            )
        return round(reelle, 3)
    if reelle is None or reelle <= 0:
        return round(float(demandee), 3)
    return round(min(float(demandee), reelle), 3)


def duree_fondu(duree: float) -> float:
    """0,3 s, réduit si le clip est trop court pour un fondu entrant et sortant."""
    if duree <= FONDU * 2:
        return max(0.05, round(duree / 4, 3))
    return FONDU


def ecrire_filigrane(dossier: str, texte: str) -> str | None:
    """Écrit le @compte une seule fois, réutilisé sur chaque clip."""
    if not texte:
        return None
    chemin = os.path.join(dossier, "filigrane.txt")
    with open(chemin, "w", encoding="utf-8", newline="\n") as fichier:
        fichier.write(texte)
    return chemin


def ecrire_lignes(dossier: str, index_clip: int, lignes: list[str]) -> list[str]:
    """Écrit chaque ligne dans un fichier UTF-8, sans BOM."""
    chemins = []
    for index_ligne, ligne in enumerate(lignes):
        chemin = os.path.join(dossier, f"texte_{index_clip:02d}_{index_ligne:02d}.txt")
        with open(chemin, "w", encoding="utf-8", newline="\n") as fichier:
            fichier.write(ligne)
        chemins.append(chemin)
    return chemins


def filtre_drawtext(
    fichier: str,
    police: str | None,
    y: str,
    taille: int,
    couleur: str,
    ombre: bool,
    boite: bool,
) -> str:
    """Une ligne de texte, selon le thème choisi."""
    options = []
    if police:
        options.append(f"fontfile='{echapper(police)}'")
    options.append(f"textfile='{echapper(fichier)}'")
    options.extend([
        "expansion=none",
        f"fontsize={taille}",
        f"fontcolor={couleur}",
        "alpha='min(1\\,t/0.4)'",
        "x=(w-text_w)/2",
        f"y={y}",
    ])
    if ombre:
        options.extend([
            "shadowcolor=black@0.6",
            "shadowx=0",
            "shadowy=3",
        ])
    if boite:
        options.extend([
            "box=1",
            "boxcolor=black@0.42",
            "boxborderw=18",
        ])
    return "drawtext=" + ":".join(options)


def filtre_filigrane(fichier: str, texte: str, theme: dict) -> str:
    """Le @compte en haut, avec la même police, couleur et relief que la phrase."""
    police = trouver_police(theme["police"])
    base = max(30, round(theme["taille"] * 0.62))
    return filtre_drawtext(
        fichier,
        police,
        "h*0.1",
        taille_filigrane(texte, base),
        theme["couleur"],
        theme["ombre"],
        theme["boite"],
    )


def filtre_zoom(duree: float) -> list[str]:
    """Léger zoom avant, du plan large vers le centre, sans changer la durée."""
    progression = f"min(t/{duree:.3f}\\,1)"
    large = int(LARGEUR * 1.12)
    haut = int(HAUTEUR * 1.12)
    return [
        f"scale={large}:{haut}:force_original_aspect_ratio=increase",
        (
            "crop="
            f"w='trunc((in_w-(in_w-{LARGEUR})*{progression})/2)*2':"
            f"h='trunc((in_h-(in_h-{HAUTEUR})*{progression})/2)*2':"
            "x='(in_w-out_w)/2':y='(in_h-out_h)/2'"
        ),
        f"scale={LARGEUR}:{HAUTEUR}",
    ]


def filtre_clip(
    index: int,
    duree: float,
    fondu: float,
    fichiers_texte: list[str],
    lignes: list[str],
    theme_image: str,
    theme_texte: str,
    fichier_filigrane: str | None = None,
    filigrane: str = "",
) -> str:
    """Recadrage 9:16, thème d'image, puis thème de texte."""
    image = THEMES_IMAGE.get(theme_image, THEMES_IMAGE["luxe"])
    texte = THEMES_TEXTE.get(theme_texte, THEMES_TEXTE["fin"])
    sortie = max(0.0, duree - fondu)
    etapes = [
        f"trim=start=0:duration={duree:.3f}",
        "setpts=PTS-STARTPTS",
    ]
    if image["zoom"]:
        etapes.extend(filtre_zoom(duree))
    else:
        etapes.append(f"scale={LARGEUR}:{HAUTEUR}:force_original_aspect_ratio=increase")
        etapes.append(f"crop={LARGEUR}:{HAUTEUR}")
    etapes.extend(["setsar=1", f"fps={FPS}", "format=yuv420p"])
    etapes.extend(image["filtres"])
    if fichiers_texte:
        police = trouver_police(texte["police"])
        taille = taille_texte(lignes, texte["taille"])
        pas = taille + 24
        for numero, chemin in enumerate(fichiers_texte):
            etapes.append(
                filtre_drawtext(
                    chemin,
                    police,
                    expression_y(numero, len(fichiers_texte), pas, texte["place"]),
                    taille,
                    texte["couleur"],
                    texte["ombre"],
                    texte["boite"],
                )
            )
    if fichier_filigrane and filigrane:
        etapes.append(filtre_filigrane(fichier_filigrane, filigrane, texte))
    etapes.append(f"fade=t=in:st=0:d={fondu:.3f}")
    etapes.append(f"fade=t=out:st={sortie:.3f}:d={fondu:.3f}")
    return f"[{index}:v]{','.join(etapes)}[v{index}]"


def filtre_audio(index: int, duree: float, a_du_son: bool) -> str:
    """Garde la musique du clip, alignée sur la même durée que l'image."""
    fondu = 0.04 if duree > 0.25 else max(0.01, round(duree / 8, 3))
    sortie = max(0.0, duree - fondu)
    if a_du_son:
        return (
            f"[{index}:a]atrim=start=0:duration={duree:.3f},"
            "asetpts=PTS-STARTPTS,aresample=44100,"
            "aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"apad=whole_dur={duree:.3f},"
            f"afade=t=in:st=0:d={fondu:.3f},"
            f"afade=t=out:st={sortie:.3f}:d={fondu:.3f}[a{index}]"
        )
    return (
        "anullsrc=channel_layout=stereo:sample_rate=44100,"
        f"atrim=duration={duree:.3f},asetpts=PTS-STARTPTS[a{index}]"
    )


def nom_montage(clip: str) -> str:
    """new + le nom de la vidéo de base, en mp4."""
    nom = os.path.splitext(os.path.basename(clip))[0].strip()
    if not nom:
        nom = "video"
    if len(nom) > 120:
        nom = nom[:120].rstrip()
    return f"new {nom}.mp4"


def chemin_sortie(clips: list[str]) -> str:
    """Le montage est enregistré à côté du premier clip, sous son nom."""
    dossier = os.path.dirname(os.path.abspath(clips[0]))
    occupe = {os.path.normcase(os.path.abspath(clip)) for clip in clips}
    base = nom_montage(clips[0])
    candidat = os.path.join(dossier, base)
    if os.path.normcase(os.path.abspath(candidat)) not in occupe:
        return candidat
    racine, ext = os.path.splitext(base)
    for numero in range(2, 40):
        autre = os.path.join(dossier, f"{racine} ({numero}){ext}")
        if os.path.normcase(os.path.abspath(autre)) not in occupe:
            return autre
    return os.path.join(dossier, f"{racine} sortie{ext}")


def chemin_brouillon(sortie: str, clips: list[str]) -> str:
    """Fichier temporaire à côté de la sortie, pour ne pas écraser un montage raté."""
    dossier = os.path.dirname(sortie)
    racine, ext = os.path.splitext(os.path.basename(sortie))
    occupe = {os.path.normcase(os.path.abspath(clip)) for clip in clips}
    for suffixe in (".part", ".part2", ".part3"):
        candidat = os.path.join(dossier, f"{racine}{suffixe}{ext}")
        if os.path.normcase(os.path.abspath(candidat)) not in occupe:
            return candidat
    return os.path.join(dossier, f"{racine}.part4{ext}")


def construire_commande(
    ffmpeg: str,
    clips: list[str],
    phrases: list[str],
    duree: float,
    couper: bool,
    theme_image: str,
    theme_texte: str,
    filigrane: str,
    durees_reelles: list[float | None],
    pistes_audio: list[bool],
    sortie: str,
    dossier_tmp: str,
) -> list[str]:
    """Un seul appel ffmpeg : image, musique, puis concaténation."""
    if not clips:
        raise ErreurMontage("Ajoute au moins une vidéo.")
    if couper and duree <= 0:
        raise ErreurMontage("La durée doit être supérieure à zéro.")
    if theme_image not in THEMES_IMAGE:
        theme_image = "luxe"
    if theme_texte not in THEMES_TEXTE:
        theme_texte = "fin"

    style = THEMES_TEXTE[theme_texte]["style"]
    marque = texte_filigrane(filigrane)
    fichier_marque = ecrire_filigrane(dossier_tmp, ligne_filigrane(marque, style))
    chaines = []
    for index, clip in enumerate(clips):
        phrase = phrases[index] if index < len(phrases) else ""
        lignes = lignes_texte(phrase, style)
        fichiers = ecrire_lignes(dossier_tmp, index, lignes) if lignes else []
        reelle = durees_reelles[index] if index < len(durees_reelles) else None
        utile = duree_utile(duree, reelle, couper)
        if utile < 0.1:
            raise ErreurMontage(
                "Cette vidéo est trop courte pour être montée :\n"
                + os.path.basename(clip)
            )
        a_du_son = pistes_audio[index] if index < len(pistes_audio) else True
        chaines.append(
            filtre_clip(
                index,
                utile,
                duree_fondu(utile),
                fichiers,
                lignes,
                theme_image,
                theme_texte,
                fichier_marque,
                marque,
            )
        )
        chaines.append(filtre_audio(index, utile, a_du_son))

    lien = "".join(f"[v{index}][a{index}]" for index in range(len(clips)))
    graphe = ";".join(chaines) + f";{lien}concat=n={len(clips)}:v=1:a=1[outv][outa]"

    commande = [ffmpeg, "-y", "-nostdin", "-hide_banner", "-loglevel", "error"]
    for clip in clips:
        commande.extend(["-i", clip])
    commande.extend([
        "-filter_complex", graphe,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-movflags", "+faststart",
        sortie,
    ])
    return commande


def dossier_temporaire() -> tempfile.TemporaryDirectory:
    try:
        return tempfile.TemporaryDirectory(prefix="tiktok_studio_", ignore_cleanup_errors=True)
    except TypeError:
        return tempfile.TemporaryDirectory(prefix="tiktok_studio_")


def _rendre_modifiable(chemin: str) -> None:
    """Retire l'attribut lecture seule, s'il empêche de remplacer la vidéo."""
    try:
        os.chmod(chemin, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        return


def publier_video(brouillon: str, sortie: str) -> str:
    """Pose le montage à la place prévue. Si ce fichier est ouvert, en crée un autre."""
    dernier: OSError | None = None
    for _ in range(4):
        try:
            if os.path.isfile(sortie):
                _rendre_modifiable(sortie)
            os.replace(brouillon, sortie)
            return sortie
        except OSError as exc:
            dernier = exc
            time.sleep(0.35)

    dossier = os.path.dirname(sortie)
    base, ext = os.path.splitext(os.path.basename(sortie))
    for numero in range(2, 40):
        candidat = os.path.join(dossier, f"{base} ({numero}){ext}")
        if os.path.exists(candidat):
            continue
        try:
            os.replace(brouillon, candidat)
            return candidat
        except OSError as exc:
            dernier = exc
            try:
                shutil.copy2(brouillon, candidat)
            except OSError as copie:
                dernier = copie
                continue
            supprimer_fichier(brouillon)
            return candidat

    raise ErreurMontage(
        "L'encodage est terminé, mais le fichier final n'a pas pu être enregistré.\n\n"
        "Ferme la vidéo déjà enregistrée si elle est ouverte dans un lecteur "
        "ou dans l'aperçu de l'Explorateur, puis relance.\n\n"
        f"Le montage est toujours ici :\n{brouillon}\n\n{dernier}"
    )


def supprimer_fichier(chemin: str) -> None:
    try:
        if os.path.isfile(chemin):
            os.remove(chemin)
    except OSError:
        pass


def extraire_erreur(texte: str, code: int) -> str:
    """Garde les dernières lignes utiles du message ffmpeg."""
    lignes = []
    for ligne in texte.splitlines():
        propre = ligne.strip()
        if not propre or propre.startswith("frame=") or propre.startswith("size="):
            continue
        lignes.append(propre)
    extrait = "\n".join(lignes[-12:])
    if not extrait:
        extrait = f"ffmpeg s'est terminé avec le code {code}, sans message."
    if len(extrait) > 1800:
        extrait = extrait[-1800:]
    return extrait


def _signaler(maj, message: str) -> None:
    if maj:
        maj(message)


def assembler(
    ffmpeg: str,
    ffprobe: str | None,
    clips: list[str],
    phrases: list[str],
    duree: float,
    couper: bool = True,
    theme_image: str = "luxe",
    theme_texte: str = "fin",
    filigrane: str = "",
    maj=None,
) -> str:
    """Mesure les clips, lance ffmpeg, puis publie le montage."""
    if not ffmpeg or not os.path.isfile(ffmpeg):
        raise ErreurMontage(
            "ffmpeg est introuvable.\n\n"
            "Place ffmpeg.exe à côté du programme, ou ajoute-le au PATH."
        )
    if not clips:
        raise ErreurMontage("Ajoute au moins une vidéo.")

    for clip in clips:
        if not os.path.isfile(clip):
            raise ErreurMontage("Fichier introuvable :\n" + clip)

    durees: list[float | None] = []
    pistes_audio: list[bool] = []
    total = len(clips)
    for index, clip in enumerate(clips, start=1):
        _signaler(maj, f"Analyse du clip {index} sur {total}…")
        if contient_video(ffprobe, clip) is False:
            raise ErreurMontage("Ce fichier n'a pas de piste vidéo :\n" + clip)
        durees.append(mesurer_duree(ffprobe, ffmpeg, clip))
        # None veut dire « on n'a pas pu vérifier » : on tente de garder le son.
        pistes_audio.append(contient_audio(ffprobe, clip) is not False)

    sortie = chemin_sortie(clips)
    brouillon = chemin_brouillon(sortie, clips)
    supprimer_fichier(brouillon)
    _signaler(maj, "Encodage du montage… cela peut prendre un moment.")

    with dossier_temporaire() as tmp:
        commande = construire_commande(
            ffmpeg,
            clips,
            phrases,
            duree,
            couper,
            theme_image,
            theme_texte,
            filigrane,
            durees,
            pistes_audio,
            brouillon,
            tmp,
        )
        try:
            resultat = lancer_processus(
                commande,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise ErreurMontage(
                "ffmpeg est introuvable.\n\n"
                "Place ffmpeg.exe à côté du programme, ou ajoute-le au PATH."
            ) from exc
        except OSError as exc:
            raise ErreurMontage("Impossible de lancer ffmpeg.\n\n" + str(exc)) from exc

    fichier_ok = os.path.isfile(brouillon) and os.path.getsize(brouillon) > 0
    if resultat.returncode != 0 or not fichier_ok:
        detail = extraire_erreur(decoder(resultat.stderr), resultat.returncode)
        if detail.startswith("ffmpeg s'est terminé"):
            autre = extraire_erreur(decoder(resultat.stdout), resultat.returncode)
            if not autre.startswith("ffmpeg s'est terminé"):
                detail = autre
        supprimer_fichier(brouillon)
        raise ErreurMontage("ffmpeg n'a pas pu créer la vidéo.\n\n" + detail)

    try:
        return publier_video(brouillon, sortie)
    except ErreurMontage:
        raise
    except OSError as exc:
        raise ErreurMontage(
            "L'encodage est terminé, mais le fichier final n'a pas pu être enregistré.\n\n"
            f"{brouillon}\n\n{exc}"
        ) from exc


def ouvrir_dossier(dossier: str) -> None:
    """Ouvre le dossier du montage dans l'Explorateur Windows."""
    if os.name != "nt":
        return
    os.startfile(dossier)  # disponible seulement sous Windows


def sombre_barre_titre(fenetre: tk.Tk) -> None:
    """Passe la barre de titre Windows en sombre. Sans effet ailleurs."""
    if os.name != "nt":
        return
    try:
        fenetre.update_idletasks()
        identifiant = fenetre.winfo_id()
        parent = ctypes.windll.user32.GetParent(identifiant)
        hwnd = parent or identifiant
        valeur = ctypes.c_int(1)
        taille = ctypes.sizeof(valeur)
        # 20 : Windows récent. 19 : anciennes versions de Windows 10.
        for attribut in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribut, ctypes.byref(valeur), taille
            )
    except (AttributeError, OSError, tk.TclError, ValueError):
        return


def etiquette_clip(chemin: str, tous: list[str]) -> str:
    """Nom du fichier, avec son dossier s'il y a un homonyme."""
    nom = os.path.basename(chemin)
    if sum(os.path.basename(autre) == nom for autre in tous) > 1:
        return os.path.join(os.path.basename(os.path.dirname(chemin)), nom)
    return nom


class Studio:
    """Interface : clips, phrases, durée, puis lancement du montage."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.clips: list[str] = []
        self.en_cours = False
        self.ffmpeg = trouver_executable("ffmpeg")
        self.ffprobe = trouver_executable("ffprobe")
        self.statut = tk.StringVar(value="Prêt.")
        self._configurer_fenetre()
        self._style_progression()
        self._construire()
        self._afficher_clips()
        self._statut_initial()
        self.root.after(250, self._avertir_si_besoin)

    def _configurer_fenetre(self) -> None:
        self.root.title("TikTok Studio")
        self.root.configure(bg=FOND)
        self.root.minsize(600, 720)
        largeur, hauteur = 640, 900
        ecran_h = self.root.winfo_screenheight()
        if ecran_h and ecran_h < hauteur + 90:
            hauteur = max(700, ecran_h - 90)
        x = max(0, (self.root.winfo_screenwidth() - largeur) // 2)
        y = max(0, (self.root.winfo_screenheight() - hauteur) // 3)
        self.root.geometry(f"{largeur}x{hauteur}+{x}+{y}")
        self.root.protocol("WM_DELETE_WINDOW", self._fermer)
        self.root.report_callback_exception = self._erreur_interface

    def _style_progression(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            return
        style.configure(
            "Or.Horizontal.TProgressbar",
            troughcolor="#2e3442",
            background=OR,
            bordercolor=FOND,
            lightcolor=OR,
            darkcolor="#e1c200",
            borderwidth=0,
            thickness=8,
        )
        style.configure(
            "Dark.Vertical.TScrollbar",
            gripcount=0,
            background="#3a4150",
            troughcolor=CHAMP,
            bordercolor=CHAMP,
            arrowcolor="#d5d8e0",
            lightcolor="#3a4150",
            darkcolor="#3a4150",
            arrowsize=12,
        )
        style.map(
            "Dark.Vertical.TScrollbar",
            background=[("active", "#4c5568"), ("pressed", "#6a5a20")],
        )

    def _construire(self) -> None:
        # La zone du bouton est packée en premier, en bas, pour rester visible.
        self._zone_basse()
        self._entete()
        self._zone_cartes()

    def _entete(self) -> None:
        entete = tk.Frame(self.root, bg=FOND)
        entete.pack(side="top", fill="x", padx=18, pady=(16, 0))
        tk.Label(
            entete,
            text="TikTok Studio",
            bg=FOND,
            fg=TEXTE,
            font=("Segoe UI", 22, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            entete,
            text="Montage vertical 1080 × 1920. Coupe, image et texte au choix. La musique reste.",
            bg=FOND,
            fg=GRIS,
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        ligne = tk.Frame(entete, bg=FOND)
        ligne.pack(fill="x", pady=(12, 0))
        tk.Label(
            ligne,
            text="Filigrane",
            bg=FOND,
            fg=TEXTE,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")
        self.filigrane = tk.Entry(
            ligne,
            bg=CHAMP,
            fg=TEXTE,
            insertbackground=TEXTE,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDURE,
            highlightcolor=OR,
            font=("Segoe UI", 12),
        )
        self.filigrane.pack(side="left", fill="x", expand=True, padx=(10, 0), ipady=5, ipadx=8)
        memorise = lire_filigrane()
        if memorise:
            self.filigrane.insert(0, memorise)
        self.filigrane.bind("<FocusOut>", self._memoriser_filigrane)
        self.filigrane.bind("<Return>", self._memoriser_filigrane)
        tk.Label(
            entete,
            text="Ton @compte, en haut de la vidéo, dans le même thème que la phrase.",
            bg=FOND,
            fg=GRIS,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(anchor="w", pady=(6, 0))

        trait = tk.Frame(entete, bg=OR, height=2)
        trait.pack(fill="x", pady=(12, 0))
        trait.pack_propagate(False)

    def _zone_cartes(self) -> None:
        coque = tk.Frame(self.root, bg=FOND)
        coque.pack(side="top", fill="both", expand=True, padx=18, pady=(12, 8))
        self.toile = tk.Canvas(coque, bg=FOND, highlightthickness=0, bd=0)
        barre = ttk.Scrollbar(coque, command=self.toile.yview, style="Dark.Vertical.TScrollbar")
        self.toile.configure(yscrollcommand=barre.set)
        barre.pack(side="right", fill="y")
        self.toile.pack(side="left", fill="both", expand=True)
        self.interieur = tk.Frame(self.toile, bg=FOND)
        self._fenetre_scroll = self.toile.create_window((0, 0), window=self.interieur, anchor="nw")
        self.interieur.bind("<Configure>", self._region_scroll)
        self.toile.bind("<Configure>", self._largeur_scroll)

        self.theme_image = "luxe"
        self.theme_texte = "fin"
        self.couper = tk.BooleanVar(value=True)
        self.langue_phrases = "mix"
        self.phrases_vues: set[str] = set()
        self._carte_clips(self.interieur)
        self._carte_phrases(self.interieur)
        self._carte_themes(self.interieur)
        self._carte_duree(self.interieur)
        self.root.bind_all("<MouseWheel>", self._molette)

    def _region_scroll(self, _event=None) -> None:
        self.toile.configure(scrollregion=self.toile.bbox("all"))

    def _largeur_scroll(self, event) -> None:
        self.toile.itemconfigure(self._fenetre_scroll, width=event.width)

    def _molette(self, event) -> None:
        try:
            if not self.root.winfo_exists():
                return
        except tk.TclError:
            return
        focus = self.root.focus_get()
        if focus in (self.liste, self.texte, self.spin, self.filigrane):
            return
        x, y = self.root.winfo_pointerxy()
        cible = self.root.winfo_containing(x, y)
        if cible is None or cible.winfo_toplevel() is not self.root:
            return
        self.toile.yview_scroll(int(-event.delta / 120), "units")

    def _nouvelle_carte(self, parent: tk.Frame) -> tuple[tk.Frame, tk.Frame]:
        enveloppe = tk.Frame(
            parent,
            bg=CARTE,
            highlightthickness=1,
            highlightbackground=BORDURE,
            highlightcolor=BORDURE,
            bd=0,
        )
        interieur = tk.Frame(enveloppe, bg=CARTE)
        interieur.pack(fill="both", expand=True, padx=14, pady=12)
        return enveloppe, interieur

    def _titre(self, parent: tk.Frame, numero: str, titre: str) -> None:
        ligne = tk.Frame(parent, bg=CARTE)
        ligne.pack(fill="x")
        tk.Label(
            ligne,
            text=numero,
            bg=OR,
            fg=ENCRE,
            font=("Segoe UI", 9, "bold"),
            width=2,
            padx=1,
        ).pack(side="left")
        tk.Label(
            ligne,
            text=titre,
            bg=CARTE,
            fg=TEXTE,
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).pack(side="left", padx=(8, 0))

    def _aide(self, parent: tk.Frame, texte: str) -> None:
        tk.Label(
            parent,
            text=texte,
            bg=CARTE,
            fg=GRIS,
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=560,
        ).pack(fill="x", pady=(4, 0))

    def _bouton(self, parent: tk.Frame, texte: str, commande, largeur: int | None = None) -> tk.Button:
        bouton = tk.Button(
            parent,
            text=texte,
            command=commande,
            bg=BOUTON,
            fg=TEXTE,
            activebackground=BOUTON_SURVOL,
            activeforeground=TEXTE,
            disabledforeground=GRIS,
            font=("Segoe UI", 9),
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=5,
            cursor="hand2",
            width=largeur,
        )
        self._lier_survol(bouton, BOUTON, BOUTON_SURVOL)
        return bouton

    def _lier_survol(self, bouton: tk.Button, repos: str, survol: str) -> None:
        def entrer(_event) -> None:
            if str(bouton.cget("state")) == "normal":
                bouton.configure(bg=survol)

        def sortir(_event) -> None:
            if str(bouton.cget("state")) == "normal":
                bouton.configure(bg=repos)

        bouton.bind("<Enter>", entrer)
        bouton.bind("<Leave>", sortir)

    def _carte_clips(self, parent: tk.Frame) -> None:
        enveloppe, carte = self._nouvelle_carte(parent)
        enveloppe.pack(side="top", fill="x")
        self._titre(carte, "1", "Tes clips")
        self._aide(carte, "Dans l'ordre du montage. Ajoute des mp4, mov, mkv ou avi.")

        barre = tk.Frame(carte, bg=CARTE)
        barre.pack(side="bottom", fill="x", pady=(8, 0))
        for texte, commande in (
            ("Ajouter", self.ajouter),
            ("Monter", lambda: self.deplacer(-1)),
            ("Descendre", lambda: self.deplacer(1)),
            ("Retirer", self.retirer),
        ):
            self._bouton(barre, texte, commande).pack(side="left", padx=(0, 8))

        cadre = tk.Frame(carte, bg=CHAMP, highlightthickness=1, highlightbackground=BORDURE)
        cadre.pack(side="top", fill="both", expand=True, pady=(8, 0))
        self.liste = tk.Listbox(
            cadre,
            bg=CHAMP,
            fg=TEXTE,
            font=("Segoe UI", 10),
            relief="flat",
            bd=0,
            highlightthickness=0,
            activestyle="none",
            selectmode="single",
            exportselection=False,
            selectbackground="#4a3f14",
            selectforeground=OR,
            height=4,
        )
        defilement = ttk.Scrollbar(cadre, command=self.liste.yview, style="Dark.Vertical.TScrollbar")
        self.liste.configure(yscrollcommand=defilement.set)
        defilement.pack(side="right", fill="y")
        self.liste.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=4)
        self.liste.bind("<<ListboxSelect>>", self._montrer_chemin)
        self.liste.bind("<Delete>", self._raccourci_retirer)

        self.indication = tk.Label(
            cadre,
            text="Aucun clip pour l'instant",
            bg=CHAMP,
            fg=GRIS,
            font=("Segoe UI", 10),
            cursor="hand2",
        )
        self.indication.bind("<Button-1>", lambda _event: self.ajouter())

    def _carte_phrases(self, parent: tk.Frame) -> None:
        enveloppe, carte = self._nouvelle_carte(parent)
        enveloppe.pack(side="top", fill="x", pady=(10, 0))
        self._titre(carte, "2", "Une phrase par clip")
        self._aide(carte, "Une ligne par clip. Une ligne vide n'écrit rien. Chaque clic pioche des phrases nouvelles.")

        self._bouton(carte, "Générer automatiquement", self.generer).pack(
            side="bottom", fill="x", pady=(8, 0)
        )
        langues = tk.Frame(carte, bg=CARTE)
        langues.pack(side="bottom", fill="x", pady=(8, 0))
        self.boutons_langue: dict[str, tk.Button] = {}
        for cle, nom in (("fr", "Français"), ("en", "English"), ("mix", "Mixte")):
            bouton = tk.Button(
                langues,
                text=nom,
                command=lambda c=cle: self._choisir_langue(c),
                bg=BOUTON,
                fg=TEXTE,
                activebackground=BOUTON_SURVOL,
                activeforeground=TEXTE,
                font=("Segoe UI", 9),
                relief="flat",
                bd=0,
                highlightthickness=0,
                padx=12,
                pady=6,
                cursor="hand2",
            )
            bouton.pack(side="left", fill="x", expand=True, padx=(0, 6))
            self.boutons_langue[cle] = bouton
        self._peindre_langue()

        cadre = tk.Frame(carte, bg=CHAMP, highlightthickness=1, highlightbackground=BORDURE)
        cadre.pack(side="top", fill="both", expand=True, pady=(8, 0))
        self.texte = tk.Text(
            cadre,
            bg=CHAMP,
            fg=TEXTE,
            font=("Segoe UI", 10),
            relief="flat",
            bd=0,
            highlightthickness=0,
            insertbackground=TEXTE,
            selectbackground="#4a3f14",
            selectforeground=TEXTE,
            wrap="word",
            undo=True,
            height=4,
            padx=8,
            pady=6,
        )
        defilement = ttk.Scrollbar(cadre, command=self.texte.yview, style="Dark.Vertical.TScrollbar")
        self.texte.configure(yscrollcommand=defilement.set)
        defilement.pack(side="right", fill="y")
        self.texte.pack(side="left", fill="both", expand=True)

    def _carte_themes(self, parent: tk.Frame) -> None:
        enveloppe, carte = self._nouvelle_carte(parent)
        enveloppe.pack(side="top", fill="x", pady=(10, 0))
        self._titre(carte, "3", "Thèmes")
        self._aide(carte, "Un look pour l'image, un style pour le texte. Les deux s'appliquent à tout le montage.")

        self._rubrique(carte, "Image")
        self.boutons_image = self._grille_themes(carte, THEMES_IMAGE, PIP_IMAGE, "image")
        self.label_image = self._legende(carte, AIDE_IMAGE["luxe"])

        self._rubrique(carte, "Texte")
        self.boutons_texte = self._grille_themes(carte, THEMES_TEXTE, PIP_TEXTE, "texte")
        self.label_texte = self._legende(carte, AIDE_TEXTE["fin"])
        self._peindre_themes(self.boutons_image, self.theme_image)
        self._peindre_themes(self.boutons_texte, self.theme_texte)

    def _rubrique(self, parent: tk.Frame, texte: str) -> None:
        tk.Label(
            parent,
            text=texte.upper(),
            bg=CARTE,
            fg=OR,
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(12, 4))

    def _legende(self, parent: tk.Frame, texte: str) -> tk.Label:
        label = tk.Label(
            parent,
            text=texte,
            bg=CARTE,
            fg=GRIS,
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        )
        label.pack(fill="x", pady=(4, 0))
        return label

    def _grille_themes(
        self,
        parent: tk.Frame,
        themes: dict,
        pips: dict,
        famille: str,
    ) -> dict[str, tk.Button]:
        grille = tk.Frame(parent, bg=CARTE)
        grille.pack(fill="x")
        boutons: dict[str, tk.Button] = {}
        for index, (cle, info) in enumerate(themes.items()):
            coque = tk.Frame(grille, bg=BORDURE)
            coque.grid(row=index // 3, column=index % 3, sticky="ew", padx=3, pady=3)
            trait = tk.Frame(coque, bg=pips.get(cle, OR), width=4)
            trait.pack(side="left", fill="y")
            bouton = tk.Button(
                coque,
                text=info["nom"],
                command=lambda c=cle, f=famille: self._choisir_theme(f, c),
                bg=BOUTON,
                fg=TEXTE,
                activebackground=BOUTON_SURVOL,
                activeforeground=TEXTE,
                font=("Segoe UI", 9),
                relief="flat",
                bd=0,
                highlightthickness=0,
                anchor="w",
                padx=10,
                pady=7,
                cursor="hand2",
            )
            bouton.pack(side="left", fill="both", expand=True)
            boutons[cle] = bouton
        for colonne in range(3):
            grille.columnconfigure(colonne, weight=1)
        return boutons

    def _choisir_theme(self, famille: str, cle: str) -> None:
        if self.en_cours:
            return
        if famille == "image":
            self.theme_image = cle
            self._peindre_themes(self.boutons_image, cle)
            self.label_image.configure(text=AIDE_IMAGE.get(cle, ""))
            return
        self.theme_texte = cle
        self._peindre_themes(self.boutons_texte, cle)
        self.label_texte.configure(text=AIDE_TEXTE.get(cle, ""))

    def _peindre_themes(self, boutons: dict[str, tk.Button], actif: str) -> None:
        for cle, bouton in boutons.items():
            if cle == actif:
                bouton.configure(
                    bg=OR,
                    fg=ENCRE,
                    activebackground=OR_SURVOL,
                    activeforeground=ENCRE,
                )
            else:
                bouton.configure(
                    bg=BOUTON,
                    fg=TEXTE,
                    activebackground=BOUTON_SURVOL,
                    activeforeground=TEXTE,
                )

    def _carte_duree(self, parent: tk.Frame) -> None:
        enveloppe, carte = self._nouvelle_carte(parent)
        enveloppe.pack(side="top", fill="x", pady=(10, 0))
        self._titre(carte, "4", "Durée")
        self._aide(carte, "Coupe chaque clip, ou garde la vidéo entière.")

        ligne = tk.Frame(carte, bg=CARTE)
        ligne.pack(fill="x", pady=(10, 0))
        self.bouton_coupe = tk.Button(
            ligne,
            text="Couper les clips",
            command=self._basculer_coupe,
            bg=OR,
            fg=ENCRE,
            activebackground=OR_SURVOL,
            activeforeground=ENCRE,
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=12,
            pady=6,
            cursor="hand2",
        )
        self.bouton_coupe.pack(side="left")
        self.spin = tk.Spinbox(
            ligne,
            from_=DUREE_MIN,
            to=DUREE_MAX,
            increment=0.5,
            format="%.1f",
            width=6,
            justify="center",
            bg=CHAMP,
            fg=TEXTE,
            disabledbackground=CHAMP,
            disabledforeground=GRIS,
            buttonbackground=BOUTON,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDURE,
            highlightcolor=OR,
            insertbackground=TEXTE,
            font=("Segoe UI", 12),
            bd=0,
        )
        self.spin.pack(side="left", padx=(12, 8), ipady=2)
        self.spin.delete(0, "end")
        self.spin.insert(0, f"{DUREE_DEFAUT:.1f}")
        tk.Label(
            ligne,
            text="secondes   ·   1 à 60, par pas de 0,5",
            bg=CARTE,
            fg=GRIS,
            font=("Segoe UI", 9),
        ).pack(side="left")
        self.label_coupe = self._legende(
            carte,
            "Chaque clip est limité à cette durée. Un clip plus court est gardé entier.",
        )

    def _basculer_coupe(self) -> None:
        if self.en_cours:
            return
        self.couper.set(not self.couper.get())
        self._peindre_coupe()

    def _peindre_coupe(self) -> None:
        if self.couper.get():
            self.bouton_coupe.configure(
                text="Couper les clips",
                bg=OR,
                fg=ENCRE,
                activebackground=OR_SURVOL,
                activeforeground=ENCRE,
            )
            self.spin.configure(state="normal")
            self.label_coupe.configure(
                text="Chaque clip est limité à cette durée. Un clip plus court est gardé entier."
            )
            return
        self.bouton_coupe.configure(
            text="Clips entiers",
            bg=BOUTON,
            fg=TEXTE,
            activebackground=BOUTON_SURVOL,
            activeforeground=TEXTE,
        )
        self.spin.configure(state="disabled")
        self.label_coupe.configure(
            text="Toute la vidéo est gardée. Au-delà de 15 minutes, la coupe redevient nécessaire."
        )

    def _zone_basse(self) -> None:
        zone = tk.Frame(self.root, bg=FOND)
        zone.pack(side="bottom", fill="x", padx=18, pady=(0, 16))
        self.bouton = tk.Button(
            zone,
            text="Créer le montage",
            command=self.creer,
            bg=OR,
            fg=ENCRE,
            activebackground=OR_SURVOL,
            activeforeground=ENCRE,
            disabledforeground=ENCRE,
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.bouton.pack(fill="x", ipady=8)
        self._lier_survol(self.bouton, OR, OR_SURVOL)

        piste = tk.Frame(zone, bg="#2e3442", height=8)
        piste.pack(fill="x", pady=(12, 0))
        piste.pack_propagate(False)
        self.progression = ttk.Progressbar(
            piste,
            style="Or.Horizontal.TProgressbar",
            mode="determinate",
            maximum=100,
        )
        self.progression.pack(fill="both", expand=True)

        self.etiquette_statut = tk.Label(
            zone,
            textvariable=self.statut,
            bg=FOND,
            fg=GRIS,
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=510,
        )
        self.etiquette_statut.pack(fill="x", pady=(8, 0))
        self.root.bind("<Configure>", self._ajuster_retour, add="+")

    def _ajuster_retour(self, _event=None) -> None:
        if _event is not None and _event.widget is not self.root:
            return
        self.etiquette_statut.configure(wraplength=max(200, self.root.winfo_width() - 48))

    def _statut_initial(self) -> None:
        if not self.ffmpeg:
            self.statut.set("ffmpeg est introuvable. Place ffmpeg.exe à côté du programme.")
            return
        if not self.ffprobe:
            self.statut.set("Prêt. ffprobe est absent : les clips seront coupés à la durée choisie.")
            return
        if not trouver_police("fine"):
            self.statut.set("Prêt. Police fine introuvable : ffmpeg choisira la sienne.")
            return
        self.statut.set("Prêt. Ajoute tes clips pour commencer.")

    def _avertir_si_besoin(self) -> None:
        if self.ffmpeg:
            return
        messagebox.showwarning(
            "ffmpeg introuvable",
            "ffmpeg est introuvable.\n\n"
            "Sans lui, le montage ne peut pas être créé.\n\n"
            "Le programme le cherche dans cet ordre :\n"
            "1. À côté de ce programme\n"
            "2. Dans le dossier temporaire de l'application\n"
            "3. Dans le PATH Windows\n\n"
            "Copie ffmpeg.exe et ffprobe.exe à côté du programme, "
            "ou installe ffmpeg, puis relance.",
            parent=self.root,
        )

    def _afficher_clips(self, selection: int | None = None) -> None:
        self.liste.delete(0, "end")
        for index, chemin in enumerate(self.clips, start=1):
            self.liste.insert("end", f"{index:02d}    {etiquette_clip(chemin, self.clips)}")
        if self.clips and selection is not None and 0 <= selection < len(self.clips):
            self.liste.selection_clear(0, "end")
            self.liste.selection_set(selection)
            self.liste.activate(selection)
            self.liste.see(selection)
        if self.clips:
            self.indication.place_forget()
        else:
            self.indication.place(relx=0.5, rely=0.5, anchor="center")

    def _texte_compte(self) -> str:
        nombre = len(self.clips)
        if nombre == 0:
            return "Aucun clip."
        if nombre == 1:
            return "1 clip dans le montage."
        return f"{nombre} clips dans le montage."

    def lire_phrases(self) -> list[str]:
        """Lignes de la zone de texte. Une ligne vide reste une ligne vide."""
        contenu = self.texte.get("1.0", "end-1c")
        if contenu == "":
            return []
        return contenu.split("\n")

    def _phrases_alignees(self) -> list[str]:
        lignes = self.lire_phrases()
        if len(lignes) < len(self.clips):
            lignes.extend([""] * (len(self.clips) - len(lignes)))
        return lignes

    def _ecrire_phrases(self, lignes: list[str]) -> None:
        self.texte.delete("1.0", "end")
        if lignes:
            self.texte.insert("1.0", "\n".join(lignes))

    def ajouter(self) -> None:
        fichiers = filedialog.askopenfilenames(
            parent=self.root,
            title="Choisir tes vidéos",
            filetypes=TYPES_VIDEO,
        )
        if not fichiers:
            return
        for fichier in fichiers:
            chemin = os.path.abspath(fichier)
            if os.path.isfile(chemin):
                self.clips.append(chemin)
        if self.clips:
            self._afficher_clips(selection=len(self.clips) - 1)
        self.statut.set(self._texte_compte())

    def deplacer(self, sens: int) -> None:
        selection = self.liste.curselection()
        if not selection:
            self.statut.set("Sélectionne un clip dans la liste.")
            return
        index = selection[0]
        cible = index + sens
        if cible < 0 or cible >= len(self.clips):
            return
        lignes = self._phrases_alignees()
        self.clips[index], self.clips[cible] = self.clips[cible], self.clips[index]
        lignes[index], lignes[cible] = lignes[cible], lignes[index]
        self._afficher_clips(selection=cible)
        self._ecrire_phrases(lignes)

    def retirer(self) -> None:
        selection = self.liste.curselection()
        if not selection:
            self.statut.set("Sélectionne le clip à retirer.")
            return
        index = selection[0]
        lignes = self.lire_phrases()
        del self.clips[index]
        if index < len(lignes):
            del lignes[index]
        prochaine = None
        if self.clips:
            prochaine = min(index, len(self.clips) - 1)
        self._afficher_clips(selection=prochaine)
        self._ecrire_phrases(lignes)
        self.statut.set(self._texte_compte())

    def _raccourci_retirer(self, _event) -> str:
        self.retirer()
        return "break"

    def _montrer_chemin(self, _event=None) -> None:
        if self.en_cours:
            return
        selection = self.liste.curselection()
        if not selection:
            return
        self.statut.set(self.clips[selection[0]])

    def _choisir_langue(self, cle: str) -> None:
        if self.en_cours or cle not in self.boutons_langue:
            return
        self.langue_phrases = cle
        self._peindre_langue()

    def _peindre_langue(self) -> None:
        for cle, bouton in self.boutons_langue.items():
            if cle == self.langue_phrases:
                bouton.configure(
                    bg=OR,
                    fg=ENCRE,
                    activebackground=OR_SURVOL,
                    activeforeground=ENCRE,
                )
            else:
                bouton.configure(
                    bg=BOUTON,
                    fg=TEXTE,
                    activebackground=BOUTON_SURVOL,
                    activeforeground=TEXTE,
                )

    def generer(self) -> None:
        nombre = len(self.clips)
        if nombre == 0:
            messagebox.showinfo(
                "Phrases",
                "Ajoute d'abord tes clips. Une phrase sera proposée pour chacun.",
                parent=self.root,
            )
            return
        self._ecrire_phrases(generer_phrases(nombre, self.langue_phrases, self.phrases_vues))
        noms = {
            "fr": "en français",
            "en": "en anglais",
            "mix": "en français et en anglais",
        }
        self.statut.set(f"{nombre} nouvelles phrases, {noms.get(self.langue_phrases, 'en français')}.")

    def _duree_saisie(self) -> float | None:
        brut = self.spin.get().strip().replace(",", ".")
        try:
            duree = round(float(brut), 2)
        except ValueError:
            messagebox.showwarning(
                "Durée",
                "Indique une durée en secondes, par exemple 3 ou 2,5.",
                parent=self.root,
            )
            return None
        if duree < DUREE_MIN or duree > DUREE_MAX:
            messagebox.showwarning(
                "Durée",
                "La durée doit être comprise entre 1 et 60 secondes.",
                parent=self.root,
            )
            return None
        return duree

    def _memoriser_filigrane(self, _event=None) -> str:
        """Enregistre le @compte et l'affiche avec l'arobase."""
        texte = texte_filigrane(self.filigrane.get())
        if self.filigrane.get() != texte:
            self.filigrane.delete(0, "end")
            if texte:
                self.filigrane.insert(0, texte)
        enregistrer_filigrane(texte)
        return texte

    def creer(self) -> None:
        if self.en_cours:
            return
        if not self.clips:
            messagebox.showwarning(
                "Clips manquants",
                "Ajoute au moins une vidéo avant de créer le montage.",
                parent=self.root,
            )
            return
        if not self.ffmpeg:
            self._avertir_si_besoin()
            return
        couper = bool(self.couper.get())
        duree = DUREE_DEFAUT
        if couper:
            saisie = self._duree_saisie()
            if saisie is None:
                return
            duree = saisie

        clips = list(self.clips)
        phrases = self.lire_phrases()
        theme_image = self.theme_image
        theme_texte = self.theme_texte
        filigrane = self._memoriser_filigrane()
        self.en_cours = True
        self.bouton.configure(state="disabled", text="Création en cours…", bg="#6b6228")
        self.progression.configure(mode="indeterminate")
        self.progression.start(14)
        self.statut.set("Montage en cours…")
        threading.Thread(
            target=self._travail,
            args=(clips, phrases, duree, couper, theme_image, theme_texte, filigrane),
            daemon=True,
            name="montage",
        ).start()

    def _travail(
        self,
        clips: list[str],
        phrases: list[str],
        duree: float,
        couper: bool,
        theme_image: str,
        theme_texte: str,
        filigrane: str,
    ) -> None:
        def maj(message: str) -> None:
            self._apres(lambda m=message: self.statut.set(m))

        try:
            sortie = assembler(
                self.ffmpeg or "",
                self.ffprobe,
                clips,
                phrases,
                duree,
                couper,
                theme_image,
                theme_texte,
                filigrane,
                maj,
            )
        except Exception as exc:
            self._apres(lambda e=exc: self._echec(e))
            return
        self._apres(lambda s=sortie: self._reussite(s))

    def _apres(self, callback) -> None:
        try:
            if self.root.winfo_exists():
                self.root.after(0, callback)
        except tk.TclError:
            return

    def _fin_travail(self) -> None:
        self.en_cours = False
        self.progression.stop()
        self.progression.configure(mode="determinate", value=0)
        self.bouton.configure(state="normal", text="Créer le montage", bg=OR, fg=ENCRE)

    def _echec(self, exc: BaseException) -> None:
        try:
            self._fin_travail()
            if isinstance(exc, ErreurMontage):
                message = str(exc)
            else:
                message = "Une erreur inattendue s'est produite.\n\n" + str(exc)
            self.statut.set("Le montage n'a pas pu être créé.")
            messagebox.showerror("Montage impossible", message, parent=self.root)
        except tk.TclError:
            return

    def _reussite(self, sortie: str) -> None:
        try:
            self._fin_travail()
            self.statut.set("Montage créé.")
            messagebox.showinfo(
                "Montage créé",
                "La vidéo a été enregistrée ici :\n\n" + sortie,
                parent=self.root,
            )
            try:
                ouvrir_dossier(os.path.dirname(sortie))
            except OSError as exc:
                messagebox.showwarning(
                    "Dossier",
                    "La vidéo est prête, mais le dossier n'a pas pu s'ouvrir.\n\n" + str(exc),
                    parent=self.root,
                )
        except tk.TclError:
            return

    def _fermer(self) -> None:
        if self.en_cours:
            continuer = messagebox.askokcancel(
                "Montage en cours",
                "Un montage est en cours de création. Fermer la fenêtre l'interrompt.",
                parent=self.root,
            )
            if not continuer:
                return
        try:
            self.root.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass
        self.root.destroy()

    def _erreur_interface(self, _type, valeur, _trace) -> None:
        try:
            messagebox.showerror(
                "TikTok Studio",
                "Erreur inattendue.\n\n" + str(valeur),
                parent=self.root,
            )
        except tk.TclError:
            return


def creer_fenetre() -> tk.Tk:
    """Construit la fenêtre, sans encore entrer dans la boucle d'événements."""
    root = tk.Tk()
    root.withdraw()
    Studio(root)
    root.update_idletasks()
    sombre_barre_titre(root)
    root.deiconify()
    return root


if __name__ == "__main__":
    root = creer_fenetre()
    root.mainloop()
