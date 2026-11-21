"""Carte de santé de la végétation d'un champ, à partir des images NASA HLS lues directement.

Demande du responsable du 21 novembre 2026, après la question d'un jury sur un champ de
10 hectares. L'agriculteur envoie la position de son champ, et AgriBot lui renvoie une
carte de 15 sur 15 carrés de 30 m, 450 m de côté, centrée sur cette position, où chaque
carré est vert si sa végétation est dans les valeurs habituelles, rouge si elle est plus
faible que d'habitude, et gris faute d'assez d'images sans nuages. Le satellite fait le
tour du champ, la photo d'une plante vient ensuite confirmer.

Règle. Chaque carré suit exactement la règle de l'alerte de végétation de
moteur/alerte.py, même masque des nuages, même fenêtre de 8 jours, même 10e centile,
mêmes minimums de 20 observations sur 5 années. La date de la carte est celle de la
dernière image des 30 derniers jours où au moins la moitié des carrés est sans nuages.
Aucune cause n'est jamais déduite.

Données. Produits HLSL30_VI et HLSS30_VI version 2.0, couches NDVI et Fmask, trouvés par
le catalogue STAC de la NASA, https://cmr.earthdata.nasa.gov/stac/LPCLOUD, et lus
directement sur le stockage du LP DAAC, seule la fenêtre du champ étant téléchargée.
Essai du 21 novembre 2026 près de Korhogo, 17 images en 50 jours, fenêtre de 15 sur 15
lue en environ 3 secondes par couche après une première authentification d'environ 40
secondes. Le NDVI est stocké en entier, facteur 0,0001, valeur absente -19999. La couche
Fmask d'une image VI du catalogue pointe vers le fichier Fmask du produit HLSL30 ou
HLSS30 lui-même, celui que décode l'alerte, vérifié le 21 novembre 2026. Seules les images de
la tuile la plus fréquente sont gardées, pour que chaque carré soit le même point d'une
image à l'autre.

Authentification. Jeton Earthdata EARTHDATA_TOKEN de l'environnement, envoyé en en-tête
Bearer pour obtenir l'adresse signée de chaque fichier, ou à défaut le compte de ~/.netrc. Ni le jeton ni le mot de passe ne sont jamais
affichés.

Vie privée. La position exacte du champ ne quitte jamais le serveur et n'est jamais
gardée. Le catalogue ne reçoit qu'une position arrondie à 0,05 degré, environ 5 km, qui
suffit à trouver les tuiles de 110 km.
"""

import functools
import logging
import os
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import requests

from .alerte import DEMI_FENETRE_JOURS, etat_vegetation

journal = logging.getLogger("moteur")
URL_STAC = "https://cmr.earthdata.nasa.gov/stac/LPCLOUD/search"
COLLECTIONS = ["HLSS30_VI_2.0", "HLSL30_VI_2.0"]
DEMI_COTE = 7
COTE_PIXEL_M = 30
PREMIERE_ANNEE = 2013
JOURS_RECENTS = 30
PART_CLAIRE_MIN = 0.5
ARRONDI_CATALOGUE = 0.05
FILS = 24
# Une carte est gardée en mémoire vive jusqu'à la fin du jour, pour une position à environ 30 m près.
CARTES_GARDEES_MAX = 500
ARRONDI_MEMOIRE = 4
ECHELLE_NDVI = 0.0001
NDVI_ABSENT = -19999


@dataclass
class CarteChamp:
    date: str | None
    statuts: np.ndarray
    images: int
    tuile: str | None
    reference_annees: list[int] = field(default_factory=list)

    def compte(self, statut: str) -> int:
        return int((self.statuts == statut).sum())


def position_pour_le_catalogue(latitude: float, longitude: float) -> tuple[float, float]:
    """Position arrondie envoyée au catalogue, jamais la position exacte du champ."""
    arrondir = lambda v: round(round(v / ARRONDI_CATALOGUE) * ARRONDI_CATALOGUE, 2)
    return arrondir(latitude), arrondir(longitude)


def chercher_images(latitude: float, longitude: float, debut: pd.Timestamp, fin: pd.Timestamp,
                    session=None) -> list[dict]:
    """Images HLS VI du catalogue STAC entre deux dates autour d'une position arrondie, pages suivies."""
    lat, lon = position_pour_le_catalogue(latitude, longitude)
    corps = {"collections": COLLECTIONS, "intersects": {"type": "Point", "coordinates": [lon, lat]},
             "datetime": f"{debut:%Y-%m-%d}T00:00:00Z/{fin:%Y-%m-%d}T23:59:59Z", "limit": 250}
    http = session or requests
    images, url = [], URL_STAC
    while url:
        reponse = http.post(url, json=corps, timeout=60)
        reponse.raise_for_status()
        page = reponse.json()
        images += page.get("features", [])
        suivant = next((l for l in page.get("links", []) if l.get("rel") == "next"), None)
        url, corps = (suivant["href"], suivant.get("body", corps)) if suivant else (None, None)
    return images


def tuile(image: dict) -> str:
    return image["id"].split(".")[2]


def date_image(image: dict) -> pd.Timestamp:
    return pd.Timestamp(image["properties"]["datetime"]).tz_localize(None).normalize()


def environnement_gdal() -> dict:
    """Réglages GDAL de lecture des fichiers du LP DAAC, avec ~/.netrc quand aucun jeton n'est donné."""
    # L'en-tête d'un fichier est lu en une seule requête, et les plages contiguës sont fusionnées.
    reglages = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": "TIF",
                "GDAL_HTTP_MAX_RETRY": "3", "GDAL_HTTP_RETRY_DELAY": "2", "GDAL_INGESTED_BYTES_AT_OPEN": "32768",
                "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES", "GDAL_HTTP_VERSION": "2TLS", "GDAL_HTTP_MULTIPLEX": "YES",
                # Une image bloquée échoue vite et compte comme nuageuse, sans retarder toute la carte.
                "GDAL_HTTP_TIMEOUT": "10", "GDAL_HTTP_CONNECTTIMEOUT": "5"}
    if not os.environ.get("EARTHDATA_TOKEN"):
        cookies = os.path.join(tempfile.gettempdir(), "agribot-earthdata-cookies.txt")
        reglages.update(GDAL_HTTP_NETRC="YES", GDAL_HTTP_COOKIEFILE=cookies, GDAL_HTTP_COOKIEJAR=cookies)
    return reglages


@functools.cache
def _session_lpdaac() -> requests.Session:
    """Connexion gardée ouverte vers le LP DAAC, une poignée de main TLS au lieu d'une par fichier."""
    from requests.adapters import HTTPAdapter

    session = requests.Session()
    session.mount("https://", HTTPAdapter(pool_connections=4, pool_maxsize=2 * FILS))
    return session


def adresse_lisible(href: str, session=None) -> str:
    """Adresse à ouvrir par GDAL. Avec un jeton, l'adresse signée vers laquelle le LP DAAC redirige.

    Essai du 21 novembre 2026 sur le serveur, GDAL renvoie l'en-tête Bearer au stockage après la
    redirection 303 et la lecture échoue, alors qu'une requête qui suit la redirection sans
    l'en-tête reçoit le fichier. La redirection est donc demandée ici avec le jeton, et
    l'adresse signée, valable un temps limité, est lue sans jeton.
    """
    jeton = os.environ.get("EARTHDATA_TOKEN")
    if not jeton:
        return href
    reponse = (session or _session_lpdaac()).get(href, headers={"Authorization": f"Bearer {jeton}"},
                                                 allow_redirects=False, timeout=15)
    if reponse.status_code in (301, 302, 303, 307, 308) and reponse.headers.get("location"):
        return reponse.headers["location"]
    reponse.raise_for_status()
    raise RuntimeError(f"pas de redirection du LP DAAC, code {reponse.status_code}")


def ndvi_clair(ndvi_brut: np.ndarray, fmask: np.ndarray) -> np.ndarray:
    """NDVI des carrés sans nuages, en valeur réelle, NaN ailleurs, selon le masque de l'alerte."""
    from .alerte import AEROSOLS_ELEVES

    codes = fmask.astype(int)
    claire = (((codes >> 1) & 0b11111) == 0) & (((codes >> 6) & 0b11) != AEROSOLS_ELEVES) & (fmask != 255)
    ndvi = np.where(ndvi_brut == NDVI_ABSENT, np.nan, ndvi_brut * ECHELLE_NDVI)
    ndvi = np.where((ndvi >= -1) & (ndvi <= 1) & claire, ndvi, np.nan)
    return ndvi.astype(float)


def lire_fenetre(image: dict, latitude: float, longitude: float, demi_cote: int = DEMI_COTE) -> np.ndarray:
    """NDVI sans nuages de la fenêtre du champ dans une image, NaN hors image ou sous les nuages."""
    import rasterio
    from rasterio.warp import transform
    from rasterio.windows import Window

    cote = 2 * demi_cote + 1

    def lire_couche(couche: str) -> np.ndarray:
        with rasterio.Env(**environnement_gdal()):
            with rasterio.open(adresse_lisible(image["assets"][couche]["href"])) as source:
                x, y = transform("EPSG:4326", source.crs, [longitude], [latitude])
                ligne, colonne = source.index(x[0], y[0])
                fenetre = Window(colonne - demi_cote, ligne - demi_cote, cote, cote)
                return source.read(1, window=fenetre, boundless=True,
                                   fill_value=NDVI_ABSENT if couche == "NDVI" else 255)

    # Les deux fichiers d'une image sont lus en même temps.
    with ThreadPoolExecutor(2) as fils:
        ndvi, fmask = fils.map(lire_couche, ("NDVI", "Fmask"))
    return ndvi_clair(ndvi, fmask)


def carte_du_champ(latitude: float, longitude: float, aujourdhui: pd.Timestamp | None = None,
                   chercheur=chercher_images, lecteur=lire_fenetre, demi_cote: int = DEMI_COTE) -> CarteChamp:
    """Statut de chaque carré de 30 m autour de la position, normale, faible ou indisponible."""
    aujourdhui = (aujourdhui or pd.Timestamp.now()).normalize()
    cote = 2 * demi_cote + 1
    vide = CarteChamp(None, np.full((cote, cote), "indisponible", dtype=object), 0, None)
    # Seule la position arrondie part au catalogue, la position exacte ne sert qu'à lire la fenêtre.
    lat_catalogue, lon_catalogue = position_pour_le_catalogue(latitude, longitude)
    recentes = chercheur(lat_catalogue, lon_catalogue, aujourdhui - pd.Timedelta(days=JOURS_RECENTS), aujourdhui)
    if not recentes:
        return vide
    tuile_retenue = Counter(tuile(i) for i in recentes).most_common(1)[0][0]
    recentes = sorted((i for i in recentes if tuile(i) == tuile_retenue), key=date_image, reverse=True)

    echecs = []
    marge = pd.Timedelta(days=DEMI_FENETRE_JOURS)

    def lire_une(image: dict) -> np.ndarray:
        """Lecture retentée deux fois, une image illisible comptant comme entièrement nuageuse."""
        for essai in range(3):
            try:
                return lecteur(image, latitude, longitude, demi_cote)
            except Exception as erreur:
                derniere = erreur
                time.sleep(2 * (essai + 1))
        journal.warning("image HLS illisible, %s", type(derniere).__name__)
        echecs.append(image["id"])
        return np.full((cote, cote), np.nan)

    def reference_de(date: pd.Timestamp) -> list[dict]:
        """Images de la tuile autour du même jour de chaque année passée, recherches en parallèle."""
        def meme_jour(annee: int) -> pd.Timestamp:
            try:
                return date.replace(year=annee)
            except ValueError:
                return date.replace(year=annee, day=28)

        with ThreadPoolExecutor(FILS) as recherches:
            par_annee = recherches.map(
                lambda a: chercheur(lat_catalogue, lon_catalogue, meme_jour(a) - marge, meme_jour(a) + marge),
                range(PREMIERE_ANNEE, date.year))
            return [i for images in par_annee for i in images if tuile(i) == tuile_retenue]

    # Date supposée de la carte, la plus récente image peu nuageuse selon le catalogue. Les images des
    # années passées autour de cette date sont lues en même temps que les images récentes, puis
    # complétées si la vraie date, connue après lecture du champ, est différente.
    supposee = next((date_image(i) for i in recentes
                     if (i.get("properties", {}).get("eo:cloud_cover") or 100) <= 100 * PART_CLAIRE_MIN), None)
    lectures: dict[str, tuple[pd.Timestamp, object]] = {}
    with ThreadPoolExecutor(FILS) as fils:
        def soumettre(images: list[dict]) -> None:
            for image in images:
                if image["id"] not in lectures:
                    lectures[image["id"]] = (date_image(image), fils.submit(lire_une, image))

        if not os.environ.get("EARTHDATA_TOKEN"):
            # Avec ~/.netrc, la première lecture ouvre seule la session Earthdata.
            lectures[recentes[0]["id"]] = (date_image(recentes[0]), fils.submit(lire_une, recentes[0]))
            lectures[recentes[0]["id"]][1].result()
        soumettre(recentes)
        if supposee is not None:
            soumettre(reference_de(supposee))
        recents = {i["id"]: lectures[i["id"]][1].result() for i in recentes}
        if len(echecs) >= len(recentes):
            raise RuntimeError("aucune image HLS lisible, la carte serait faussement nuageuse")
        cible = next((date_image(i) for i in recentes if np.isfinite(recents[i["id"]]).mean() >= PART_CLAIRE_MIN), None)
        if cible is None:
            for _, futur in lectures.values():
                futur.cancel()
            return CarteChamp(None, vide.statuts, len(recentes), tuile_retenue)
        if cible != supposee:
            soumettre(reference_de(cible))
        lues = {identifiant: (date, futur.result()) for identifiant, (date, futur) in lectures.items()}

    dates = [d for d, _ in lues.values()]
    pile = np.stack([v for _, v in lues.values()])
    statuts = np.empty((cote, cote), dtype=object)
    for ligne in range(cote):
        for colonne in range(cote):
            valeurs = pile[:, ligne, colonne]
            serie = pd.Series(valeurs, index=pd.DatetimeIndex(dates)).dropna().sort_index()
            statuts[ligne, colonne] = etat_vegetation(serie, str(cible.date()))["statut"]
    annees = sorted({d.year for d in dates if d.year != cible.year})
    return CarteChamp(str(cible.date()), statuts, len(lues), tuile_retenue, annees)


_cartes_du_jour: dict[tuple[str, float, float], CarteChamp] = {}


def carte_du_jour(latitude: float, longitude: float, aujourdhui: pd.Timestamp | None = None, **options) -> CarteChamp:
    """Carte du champ, recalculée au plus une fois par jour pour une même position à environ 30 m près.

    Gardée en mémoire vive seulement, jamais sur disque, et perdue au redémarrage. Une panne
    n'est pas gardée, si bien qu'une nouvelle demande réessaie.
    """
    jour = (aujourdhui or pd.Timestamp.now()).normalize()
    cle = (str(jour.date()), round(latitude, ARRONDI_MEMOIRE), round(longitude, ARRONDI_MEMOIRE))
    if cle not in _cartes_du_jour:
        for ancienne in [c for c in _cartes_du_jour if c[0] != cle[0]]:
            del _cartes_du_jour[ancienne]
        if len(_cartes_du_jour) >= CARTES_GARDEES_MAX:
            del _cartes_du_jour[next(iter(_cartes_du_jour))]
        _cartes_du_jour[cle] = carte_du_champ(latitude, longitude, jour, **options)
    return _cartes_du_jour[cle]


def direction(statuts: np.ndarray, statut: str = "faible") -> str | None:
    """Direction, depuis le centre, où se trouvent surtout les carrés d'un statut, ou None s'ils sont au centre."""
    lignes, colonnes = np.nonzero(statuts == statut)
    if not len(lignes):
        return None
    centre = (statuts.shape[0] - 1) / 2
    nord, est = centre - lignes.mean(), colonnes.mean() - centre
    if max(abs(nord), abs(est)) < 1.5:
        return "au centre"
    vertical = "nord" if nord > 0 else "sud"
    horizontal = "est" if est > 0 else "ouest"
    if abs(nord) >= 2 * abs(est):
        return f"vers le {vertical}"
    if abs(est) >= 2 * abs(nord):
        return f"vers l'{horizontal}"
    return f"vers le {vertical}-{horizontal}"


COULEURS = {"normale": "#3FA34D", "faible": "#D7263D", "indisponible": "#BDBDBD"}


def dessiner(carte: CarteChamp, date_en_mots) -> bytes:
    """Image PNG de la carte, carrés colorés, position au centre, nord, échelle et légende courte."""
    import io

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb
    from matplotlib.patches import Patch

    cote = carte.statuts.shape[0]
    couleurs = np.array([[to_rgb(COULEURS[s]) for s in ligne] for ligne in carte.statuts])
    figure, axe = plt.subplots(figsize=(6, 7.2), dpi=130)
    axe.imshow(couleurs, interpolation="nearest")
    axe.set_xticks(np.arange(-0.5, cote, 1), minor=True)
    axe.set_yticks(np.arange(-0.5, cote, 1), minor=True)
    axe.grid(which="minor", color="white", linewidth=1.2)
    axe.tick_params(which="both", bottom=False, left=False, labelbottom=False, labelleft=False)
    centre = (cote - 1) / 2
    axe.plot(centre, centre, "o", markersize=15, markerfacecolor="white", markeredgecolor="#0B4F17", markeredgewidth=3)
    axe.annotate("N", xy=(cote - 1.2, 0.4), xytext=(cote - 1.2, 2.6), ha="center", fontsize=15, fontweight="bold",
                 color="#0B4F17", arrowprops={"arrowstyle": "-|>", "color": "#0B4F17", "lw": 2.5})
    pixels_100m = 100 / COTE_PIXEL_M
    axe.plot([0.2, 0.2 + pixels_100m], [cote - 1.0, cote - 1.0], color="black", linewidth=4)
    axe.text(0.2 + pixels_100m / 2, cote - 1.35, "100 m", ha="center", fontsize=11, fontweight="bold")
    titre = "Votre champ vu par satellite"
    sous_titre = f"Images NASA du {date_en_mots(carte.date)}" if carte.date else "Pas d'image assez claire"
    axe.set_title(f"{titre}\n{sous_titre}", fontsize=14, color="#0B4F17", fontweight="bold")
    legende = [Patch(color=COULEURS["normale"], label="Comme d'habitude"),
               Patch(color=COULEURS["faible"], label="Plus faible que d'habitude"),
               Patch(color=COULEURS["indisponible"], label="Nuages, pas de mesure"),
               plt.Line2D([], [], marker="o", color="white", markeredgecolor="#0B4F17", markeredgewidth=3,
                          markersize=12, linestyle="", label="Vous êtes ici")]
    axe.legend(handles=legende, loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=2, fontsize=10, frameon=False)
    figure.tight_layout()
    tampon = io.BytesIO()
    figure.savefig(tampon, format="png")
    plt.close(figure)
    return tampon.getvalue()
