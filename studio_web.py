#!/usr/bin/env python3
"""Site mobile de TikTok Studio.

L'ordinateur encode avec ffmpeg. Le téléphone ouvre la page sur le même Wi-Fi,
envoie les clips, puis récupère la vidéo.
"""

from __future__ import annotations

import json
import os
import sys
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
_temporaire = None


def preparer_depot() -> str:
    """Dossier temporaire des clips envoyés par le téléphone. Il reste ouvert."""
    global _depot, _temporaire
    if _temporaire is None:
        _temporaire = studio.dossier_temporaire()
        _depot = _temporaire.__enter__()
    return _depot


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
            traceback.print_exc()
            self._erreur(500, str(exc))

    def do_POST(self) -> None:
        chemin = urlparse(self.path).path
        try:
            if chemin == "/api/clips":
                self._recevoir_clip()
            elif chemin == "/api/phrases":
                self._phrases()
            elif chemin == "/api/montage":
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
            traceback.print_exc()
            self._erreur(500, str(exc))

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
        with _verrou:
            _clips[identifiant] = {"nom": nom, "chemin": chemin}
        self._json(200, {"id": identifiant, "nom": nom})

    def _lancer(self) -> None:
        global _dernier_travail
        donnees = lire_json(self)
        identifiants = donnees.get("clips")
        if not isinstance(identifiants, list) or not identifiants:
            raise ValueError("Ajoute au moins une vidéo.")
        if len(identifiants) > 20:
            raise ValueError("Vingt vidéos maximum par montage.")
        with _verrou:
            manquants = [cle for cle in identifiants if cle not in _clips]
            chemins = [_clips[cle]["chemin"] for cle in identifiants if cle in _clips]
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
        threading.Thread(
            target=self._encoder,
            args=(travail, chemins, phrases, duree, couper, theme_image, theme_texte, filigrane),
            daemon=True,
            name="montage-web",
        ).start()
        self._json(202, {"id": travail})

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
            with _verrou:
                if travail in _travaux:
                    _travaux[travail]["message"] = message

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
            with _verrou:
                _travaux[travail]["etat"] = "pret"
                _travaux[travail]["video"] = sortie
                _travaux[travail]["nom"] = os.path.basename(sortie)
                _travaux[travail]["message"] = "Montage prêt."
        except Exception as exc:
            texte = str(exc) if isinstance(exc, studio.ErreurMontage) else "Le montage n'a pas pu être créé.\n\n" + str(exc)
            with _verrou:
                _travaux[travail]["etat"] = "erreur"
                _travaux[travail]["erreur"] = texte
                _travaux[travail]["message"] = "Le montage n'a pas pu être créé."

    def _suivi(self, identifiant: str) -> None:
        identifiant = identifiant.strip("/")
        with _verrou:
            fiche = _travaux.get(identifiant)
            if not fiche:
                self._erreur(404, "Montage introuvable.")
                return
            copie = {
                "etat": fiche["etat"],
                "message": fiche["message"],
                "nom": fiche["nom"],
                "erreur": fiche["erreur"],
            }
        self._json(200, copie)

    def _video(self, identifiant: str) -> None:
        identifiant = identifiant.strip("/")
        with _verrou:
            fiche = _travaux.get(identifiant)
            chemin = fiche["video"] if fiche else ""
            nom = fiche["nom"] if fiche else ""
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
