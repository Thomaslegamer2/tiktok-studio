#!/usr/bin/env python3
"""Site mobile de TikTok Studio.

L'ordinateur encode avec ffmpeg. Le téléphone ouvre la page sur le même Wi-Fi,
envoie les clips, puis récupère la vidéo.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

RACINE = os.path.dirname(os.path.abspath(__file__))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import tiktok_studio as studio  # noqa: E402


def lire_port() -> int:
    """Le port du service. L'hébergeur peut l'imposer avec la variable PORT."""
    brut = os.environ.get("PORT", "8765")
    try:
        port = int(brut)
    except ValueError:
        return 8765
    if not 1 <= port <= 65535:
        return 8765
    return port


PORT = lire_port()
PAGE = os.path.join(RACINE, "studio_mobile.html")
TAILLE_CLIP_MAX = 800 * 1024 * 1024
EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm", ".3gp"}

_verrou = threading.Lock()
_clips: dict[str, dict] = {}
_travaux: dict[str, dict] = {}
_phrases_vues: set[str] = set()
_dernier_travail = ""
_depot = ""


def dossier_donnees() -> str:
    """Dossier stable : un redémarrage ne doit pas effacer le montage terminé."""
    base = os.environ.get("STUDIO_DATA") or os.path.join(os.path.expanduser("~"), ".tiktok-studio")
    try:
        os.makedirs(base, exist_ok=True)
        return base
    except OSError:
        secours = os.path.join(tempfile.gettempdir(), "tiktok-studio")
        os.makedirs(secours, exist_ok=True)
        return secours


def preparer_depot() -> str:
    """Dossier des clips envoyés. Il reste en place après la fin du montage."""
    global _depot
    if _depot and os.path.isdir(_depot):
        return _depot
    _depot = os.path.join(dossier_donnees(), "clips")
    os.makedirs(_depot, exist_ok=True)
    return _depot


def identifiant_sur(valeur: str) -> str:
    """Garde seulement un identifiant hexadécimal, pour le nom du fichier."""
    propre = valeur.strip().strip("/").lower()
    if not propre or len(propre) > 64:
        return ""
    if any(caractere not in "0123456789abcdef" for caractere in propre):
        return ""
    return propre


def chemin_travail(identifiant: str) -> str:
    dossier = os.path.join(dossier_donnees(), "travaux")
    os.makedirs(dossier, exist_ok=True)
    return os.path.join(dossier, identifiant + ".json")


def ecrire_travail(identifiant: str, fiche: dict) -> None:
    """Écrit l'état du montage tout de suite, pas seulement en mémoire."""
    identifiant = identifiant_sur(identifiant)
    if not identifiant:
        return
    try:
        chemin = chemin_travail(identifiant)
        temporaire = chemin + ".tmp"
        with open(temporaire, "w", encoding="utf-8") as fichier:
            json.dump(fiche, fichier, ensure_ascii=False)
        os.replace(temporaire, chemin)
    except OSError:
        return


def lire_travail(identifiant: str) -> dict | None:
    identifiant = identifiant_sur(identifiant)
    if not identifiant:
        return None
    chemin = chemin_travail(identifiant)
    try:
        with open(chemin, encoding="utf-8") as fichier:
            fiche = json.load(fichier)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(fiche, dict):
        return None
    return fiche


def memoriser_travail(identifiant: str, **champs) -> None:
    with _verrou:
        fiche = _travaux.get(identifiant)
        if fiche is None:
            return
        fiche.update(champs)
        copie = dict(fiche)
    ecrire_travail(identifiant, copie)


def obtenir_travail(identifiant: str) -> dict | None:
    """Lit le montage en mémoire, puis sur le disque si le processus a redémarré."""
    identifiant = identifiant_sur(identifiant)
    if not identifiant:
        return None
    with _verrou:
        fiche = _travaux.get(identifiant)
        if fiche is not None:
            return dict(fiche)
    return lire_travail(identifiant)


def chemin_fiche_clip(identifiant: str) -> str:
    dossier = os.path.join(dossier_donnees(), "fiches")
    os.makedirs(dossier, exist_ok=True)
    return os.path.join(dossier, identifiant + ".json")


def enregistrer_clip(identifiant: str, nom: str, chemin: str) -> None:
    """Garde le lien entre l'identifiant et le fichier, même après un redémarrage."""
    fiche = {"nom": nom, "chemin": chemin}
    with _verrou:
        _clips[identifiant] = fiche
    identifiant = identifiant_sur(identifiant)
    if not identifiant:
        return
    try:
        destination = chemin_fiche_clip(identifiant)
        temporaire = destination + ".tmp"
        with open(temporaire, "w", encoding="utf-8") as fichier:
            json.dump(fiche, fichier, ensure_ascii=False)
        os.replace(temporaire, destination)
    except OSError:
        return


def retrouver_clip(identifiant: str) -> dict | None:
    """Retrouve une vidéo envoyée, en mémoire puis sur le disque."""
    propre = identifiant_sur(str(identifiant))
    if not propre:
        return None
    with _verrou:
        fiche = _clips.get(propre)
        if fiche is not None:
            copie = dict(fiche)
        else:
            copie = None
    if copie is None:
        try:
            with open(chemin_fiche_clip(propre), encoding="utf-8") as fichier:
                lu = json.load(fichier)
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(lu, dict) or not lu.get("chemin"):
            return None
        copie = {"nom": str(lu.get("nom", "")), "chemin": str(lu["chemin"])}
        with _verrou:
            _clips[propre] = copie
    if not os.path.isfile(copie["chemin"]):
        return None
    return copie


def interrompre_orphelins() -> None:
    """Un encodage encore marqué en cours au démarrage n'a plus de thread."""
    dossier = os.path.join(dossier_donnees(), "travaux")
    if not os.path.isdir(dossier):
        return
    for nom in os.listdir(dossier):
        if not nom.endswith(".json"):
            continue
        identifiant = nom[:-5]
        fiche = lire_travail(identifiant)
        if not fiche or fiche.get("etat") != "encodage":
            continue
        fiche["etat"] = "erreur"
        fiche["erreur"] = "Le montage a été interrompu. Relance la création."
        fiche["message"] = "Le montage a été interrompu."
        ecrire_travail(identifiant, fiche)


def adresse_locale() -> str:
    """Adresse à ouvrir sur le téléphone, sur le même réseau."""
    import socket

    essai = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        essai.connect(("8.8.8.8", 80))
        return essai.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        essai.close()


def nom_propre(nom: str) -> str:
    """Nom de fichier sûr, gardé pour que le montage s'appelle new + ce nom."""
    base = os.path.splitext(os.path.basename(nom.replace("\\", "/")))[0]
    interdit = '<>:"/\\|?*'
    propre = "".join(caractere for caractere in base if caractere not in interdit).strip().rstrip(".")
    if not propre:
        propre = "video"
    return propre[:80]


def chemin_clip(nom: str) -> str:
    dossier = preparer_depot()
    ext = extension_sure(nom)
    tige = nom_propre(nom)
    candidat = os.path.join(dossier, tige + ext)
    numero = 2
    while os.path.exists(candidat):
        candidat = os.path.join(dossier, f"{tige}-{numero}{ext}")
        numero += 1
    return candidat


def extension_sure(nom: str) -> str:
    ext = os.path.splitext(nom)[1].lower()
    if ext in EXTENSIONS:
        return ext
    return ".mp4"


def dans_depot(chemin: str) -> bool:
    depot = os.path.abspath(preparer_depot())
    cible = os.path.abspath(chemin)
    try:
        return os.path.commonpath([depot, cible]) == depot
    except ValueError:
        return False


def lire_json(handler: BaseHTTPRequestHandler, limite: int = 1_000_000) -> dict:
    longueur = int(handler.headers.get("Content-Length", "0") or "0")
    if longueur <= 0 or longueur > limite:
        raise ValueError("Requête vide ou trop lourde.")
    brut = handler.rfile.read(longueur)
    donnees = json.loads(brut.decode("utf-8"))
    if not isinstance(donnees, dict):
        raise ValueError("Le contenu doit être un objet.")
    return donnees


def themes_publics() -> dict:
    def liste(source: dict, aides: dict, pips: dict) -> list[dict]:
        return [
            {
                "id": cle,
                "nom": info["nom"],
                "aide": aides.get(cle, ""),
                "pip": pips.get(cle, "#ffd700"),
                "place": info.get("place", ""),
                "style": info.get("style", ""),
            }
            for cle, info in source.items()
        ]

    return {
        "images": liste(studio.THEMES_IMAGE, studio.AIDE_IMAGE, studio.PIP_IMAGE),
        "textes": liste(studio.THEMES_TEXTE, studio.AIDE_TEXTE, studio.PIP_TEXTE),
    }


def etat_public() -> dict:
    ffmpeg = studio.trouver_executable("ffmpeg")
    return {
        "ffmpeg": bool(ffmpeg),
        "filigrane": studio.lire_filigrane(),
        "url": f"http://{adresse_locale()}:{PORT}",
        "themes": themes_publics(),
        "travail": _dernier_travail,
    }


class SiteStudio(BaseHTTPRequestHandler):
    """Pages et actions du studio mobile."""

    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args) -> None:
        return

    def _envoyer(self, code: int, contenu: bytes, type_mime: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", type_mime)
        self.send_header("Content-Length", str(len(contenu)))
        self.send_header("Cache-Control", "no-store")
        if extra:
            for cle, valeur in extra.items():
                self.send_header(cle, valeur)
        self.end_headers()
        self.wfile.write(contenu)

    def _json(self, code: int, donnees: dict) -> None:
        corps = json.dumps(donnees, ensure_ascii=False).encode("utf-8")
        self._envoyer(code, corps, "application/json; charset=utf-8")

    def _erreur(self, code: int, message: str) -> None:
        self._json(code, {"erreur": message})

    def do_GET(self) -> None:
        chemin = urlparse(self.path).path
        try:
            if chemin in ("/", "/index.html"):
                self._page()
            elif chemin in ("/health", "/healthz"):
                self._json(200, {"ok": True})
            elif chemin == "/api/etat":
                self._json(200, etat_public())
            elif chemin.startswith("/api/montage/"):
                self._suivi(chemin.removeprefix("/api/montage/"))
            elif chemin.startswith("/api/video/"):
                self._video(chemin.removeprefix("/api/video/"))
            else:
                self._erreur(404, "Page introuvable.")
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            self._signaler(chemin, exc)

    def do_POST(self) -> None:
        chemin = urlparse(self.path).path
        try:
            if chemin == "/api/clips":
                self._recevoir_clip()
            elif chemin == "/api/phrases":
                self._phrases()
            elif chemin.rstrip("/") == "/api/montage":
                self._lancer()
            else:
                self._erreur(404, "Action introuvable.")
        except ValueError as exc:
            self._erreur(400, str(exc))
        except studio.ErreurMontage as exc:
            self._erreur(400, str(exc))
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            self._signaler(chemin, exc)

    def _signaler(self, chemin: str, exc: Exception) -> None:
        """Affiche l'erreur dans les logs et la renvoie en JSON, jamais en page HTML."""
        print(f"ERREUR {chemin} : {exc}", flush=True)
        traceback.print_exc()
        try:
            self._erreur(500, str(exc) or "La demande a échoué.")
        except Exception:
            return

    def send_error(self, code: int = 500, message: str | None = None, explain: str | None = None) -> None:
        try:
            self._erreur(int(code), message or "La demande a échoué.")
        except Exception:
            return

    def _page(self) -> None:
        try:
            with open(PAGE, "rb") as fichier:
                contenu = fichier.read()
        except OSError:
            self._erreur(500, "La page du studio est introuvable.")
            return
        self._envoyer(200, contenu, "text/html; charset=utf-8")

    def _phrases(self) -> None:
        global _phrases_vues
        donnees = lire_json(self)
        try:
            nombre = int(donnees.get("nombre", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("Indique combien de phrases générer.") from exc
        if nombre < 1 or nombre > 30:
            raise ValueError("Génère entre 1 et 30 phrases.")
        langue = str(donnees.get("langue", "mix"))
        if langue not in ("fr", "en", "mix"):
            langue = "mix"
        with _verrou:
            phrases = studio.generer_phrases(nombre, langue, _phrases_vues)
        self._json(200, {"phrases": phrases})

    def _recevoir_clip(self) -> None:
        longueur = int(self.headers.get("Content-Length", "0") or "0")
        if longueur <= 0:
            raise ValueError("La vidéo est vide.")
        if longueur > TAILLE_CLIP_MAX:
            raise ValueError("Cette vidéo dépasse 800 Mo.")
        nom = unquote(self.headers.get("X-Nom", "clip.mp4"))
        nom = os.path.basename(nom.replace("\\", "/")).strip() or "clip.mp4"
        identifiant = uuid.uuid4().hex
        chemin = chemin_clip(nom)
        reste = longueur
        with open(chemin, "wb") as fichier:
            while reste > 0:
                bloc = self.rfile.read(min(1024 * 1024, reste))
                if not bloc:
                    break
                fichier.write(bloc)
                reste -= len(bloc)
        if reste > 0 or not os.path.isfile(chemin) or os.path.getsize(chemin) == 0:
            studio.supprimer_fichier(chemin)
            raise ValueError("La vidéo n'a pas été reçue en entier.")
        enregistrer_clip(identifiant, nom, chemin)
        self._json(200, {"id": identifiant, "nom": nom})

    def _lancer(self) -> None:
        global _dernier_travail
        donnees = lire_json(self)
        identifiants = donnees.get("clips")
        if not isinstance(identifiants, list) or not identifiants:
            raise ValueError("Ajoute au moins une vidéo.")
        if len(identifiants) > 20:
            raise ValueError("Vingt vidéos maximum par montage.")
        manquants = []
        chemins = []
        for cle in identifiants:
            fiche = retrouver_clip(str(cle))
            if fiche is None:
                manquants.append(cle)
            else:
                chemins.append(fiche["chemin"])
        if manquants or len(chemins) != len(identifiants):
            raise ValueError("Une vidéo n'est plus disponible. Ajoute-la de nouveau.")

        phrases = donnees.get("phrases", [])
        if not isinstance(phrases, list):
            phrases = []
        phrases = [str(phrase) for phrase in phrases]
        while len(phrases) < len(chemins):
            phrases.append("")
        phrases = phrases[: len(chemins)]

        couper = bool(donnees.get("couper", True))
        try:
            duree = float(donnees.get("duree", studio.DUREE_DEFAUT))
        except (TypeError, ValueError) as exc:
            raise ValueError("La durée doit être un nombre.") from exc
        if couper and (duree < studio.DUREE_MIN or duree > studio.DUREE_MAX):
            raise ValueError("La durée doit être comprise entre 1 et 60 secondes.")

        theme_image = str(donnees.get("theme_image", "luxe"))
        theme_texte = str(donnees.get("theme_texte", "fin"))
        if theme_image not in studio.THEMES_IMAGE:
            theme_image = "luxe"
        if theme_texte not in studio.THEMES_TEXTE:
            theme_texte = "fin"
        filigrane = studio.texte_filigrane(str(donnees.get("filigrane", "")))
        studio.enregistrer_filigrane(filigrane)

        travail = uuid.uuid4().hex
        fiche = {
            "etat": "encodage",
            "message": "Préparation du montage…",
            "video": "",
            "nom": "",
            "erreur": "",
        }
        with _verrou:
            _travaux[travail] = fiche
            _dernier_travail = travail
            copie = dict(fiche)
        ecrire_travail(travail, copie)
        threading.Thread(
            target=self._encoder,
            args=(travail, chemins, phrases, duree, couper, theme_image, theme_texte, filigrane),
            daemon=True,
            name="montage-web",
        ).start()
        self._json(200, {"id": travail})

    def _encoder(
        self,
        travail: str,
        chemins: list[str],
        phrases: list[str],
        duree: float,
        couper: bool,
        theme_image: str,
        theme_texte: str,
        filigrane: str,
    ) -> None:
        def maj(message: str) -> None:
            memoriser_travail(travail, message=message)

        try:
            ffmpeg = studio.trouver_executable("ffmpeg") or ""
            ffprobe = studio.trouver_executable("ffprobe")
            sortie = studio.assembler(
                ffmpeg,
                ffprobe,
                chemins,
                phrases,
                duree,
                couper,
                theme_image,
                theme_texte,
                filigrane,
                maj,
            )
            if not dans_depot(sortie):
                raise studio.ErreurMontage("La vidéo a été écrite hors du dossier de travail.")
            memoriser_travail(
                travail,
                etat="pret",
                video=sortie,
                nom=os.path.basename(sortie),
                message="Montage prêt.",
            )
        except Exception as exc:
            texte = str(exc) if isinstance(exc, studio.ErreurMontage) else "Le montage n'a pas pu être créé.\n\n" + str(exc)
            memoriser_travail(
                travail,
                etat="erreur",
                erreur=texte,
                message="Le montage n'a pas pu être créé.",
            )

    def _suivi(self, identifiant: str) -> None:
        fiche = obtenir_travail(identifiant)
        if not fiche:
            self._erreur(404, "Montage introuvable.")
            return
        self._json(200, {
            "etat": fiche.get("etat", ""),
            "message": fiche.get("message", ""),
            "nom": fiche.get("nom", ""),
            "erreur": fiche.get("erreur", ""),
        })

    def _video(self, identifiant: str) -> None:
        fiche = obtenir_travail(identifiant)
        chemin = fiche.get("video", "") if fiche else ""
        nom = fiche.get("nom", "") if fiche else ""
        if not chemin or not os.path.isfile(chemin) or not dans_depot(chemin):
            self._erreur(404, "La vidéo n'est pas encore prête.")
            return
        taille = os.path.getsize(chemin)
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(taille))
        self.send_header("Content-Disposition", f'attachment; filename="{nom}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with open(chemin, "rb") as fichier:
            while True:
                bloc = fichier.read(1024 * 1024)
                if not bloc:
                    break
                try:
                    self.wfile.write(bloc)
                except (BrokenPipeError, ConnectionResetError):
                    return


def ouvrir_parefeu(port: int) -> None:
    """Autorise le téléphone sur le réseau local, si Windows le permet."""
    if os.name != "nt":
        return
    import subprocess

    commande = [
        "netsh",
        "advfirewall",
        "firewall",
        "add",
        "rule",
        f"name=TikTok Studio {port}",
        "dir=in",
        "action=allow",
        "protocol=TCP",
        f"localport={port}",
        "profile=private",
    ]
    try:
        subprocess.run(commande, capture_output=True, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return


def servir() -> None:
    preparer_depot()
    interrompre_orphelins()
    ouvrir_parefeu(PORT)
    serveur = ThreadingHTTPServer(("0.0.0.0", PORT), SiteStudio)
    locale = adresse_locale()
    print(f"Sur cet ordinateur : http://127.0.0.1:{PORT}", flush=True)
    print(f"Sur le téléphone    : http://{locale}:{PORT}", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        serveur.shutdown()


if __name__ == "__main__":
    servir()
