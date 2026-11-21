"""Lieux couverts par l'outil, les chefs-lieux des 31 régions et des deux districts autonomes.

Extension à toute la Côte d'Ivoire décidée par le responsable le 20 novembre 2026. Les
coordonnées sont celles que rend OpenStreetMap par Nominatim le 20 novembre 2026, gardées
avec la réponse brute dans data/raw/lieux/nominatim_2026-11-20.json, sous licence ODbL.
Pour Aboisso, le premier résultat est le département, le second, la ville, est retenu.
Korhogo et Bouaké gardent les coordonnées de centre-ville du 14 novembre 2026, qui
diffèrent de celles d'OpenStreetMap de moins de 0,003 degré, pour ne pas changer leurs
résultats publiés. Les noms de région et de district sont confirmés par la même réponse.

Zone. Le conseil de rotation de moteur/rotations.py compare des rotations de savane,
coton, maïs, sorgho et niébé, sur une seule saison des pluies. La zone de chaque ville
dit quelles rotations lui conviennent. Règle provisoire du 20 novembre 2026, à valider par
le responsable sur sources, savane pour les districts des Savanes, du Denguélé, du
Woroba, du Zanzan et de la Vallée du Bandama, forêt pour les autres.
"""

import math

DISTRICTS_DE_SAVANE = {"Savanes", "Denguélé", "Woroba", "Zanzan", "Vallée du Bandama"}

_VILLES = [
    # identifiant, nom, région, district, latitude, longitude
    ("korhogo", "Korhogo", "Poro", "Savanes", 9.458, -5.629),
    ("bouake", "Bouaké", "Gbêkê", "Vallée du Bandama", 7.690, -5.030),
    ("boundiali", "Boundiali", "Bagoué", "Savanes", 9.523, -6.482),
    ("ferkessedougou", "Ferkessédougou", "Tchologo", "Savanes", 9.594, -5.198),
    ("odienne", "Odienné", "Kabadougou", "Denguélé", 9.504, -7.562),
    ("minignan", "Minignan", "Folon", "Denguélé", 9.999, -7.836),
    ("touba", "Touba", "Bafing", "Woroba", 8.284, -7.682),
    ("mankono", "Mankono", "Béré", "Woroba", 8.045, -6.074),
    ("seguela", "Séguéla", "Worodougou", "Woroba", 7.961, -6.670),
    ("bouna", "Bouna", "Bounkani", "Zanzan", 9.269, -2.999),
    ("bondoukou", "Bondoukou", "Gontougo", "Zanzan", 8.084, -2.799),
    ("katiola", "Katiola", "Hambol", "Vallée du Bandama", 8.091, -5.151),
    ("yamoussoukro", "Yamoussoukro", "District autonome de Yamoussoukro", "Yamoussoukro", 6.820, -5.278),
    ("abidjan", "Abidjan", "District autonome d'Abidjan", "Abidjan", 5.320, -4.016),
    ("sassandra", "Sassandra", "Gbôklé", "Bas-Sassandra", 4.949, -6.092),
    ("soubre", "Soubré", "Nawa", "Bas-Sassandra", 5.785, -6.593),
    ("san_pedro", "San-Pédro", "San-Pédro", "Bas-Sassandra", 4.759, -6.646),
    ("abengourou", "Abengourou", "Indénié-Djuablin", "Comoé", 6.727, -3.497),
    ("aboisso", "Aboisso", "Sud-Comoé", "Comoé", 5.467, -3.207),
    ("gagnoa", "Gagnoa", "Gôh", "Gôh-Djiboua", 6.133, -5.951),
    ("divo", "Divo", "Lôh-Djiboua", "Gôh-Djiboua", 5.841, -5.355),
    ("toumodi", "Toumodi", "Bélier", "Lacs", 6.560, -5.016),
    ("daoukro", "Daoukro", "Iffou", "Lacs", 7.058, -3.966),
    ("bongouanou", "Bongouanou", "Moronou", "Lacs", 6.648, -4.205),
    ("dimbokro", "Dimbokro", "N'Zi", "Lacs", 6.649, -4.704),
    ("agboville", "Agboville", "Agnéby-Tiassa", "Lagunes", 5.931, -4.213),
    ("dabou", "Dabou", "Grands-Ponts", "Lagunes", 5.324, -4.372),
    ("adzope", "Adzopé", "La Mé", "Lagunes", 6.106, -3.864),
    ("guiglo", "Guiglo", "Cavally", "Montagnes", 6.430, -7.591),
    ("duekoue", "Duékoué", "Guémon", "Montagnes", 6.714, -7.425),
    ("man", "Man", "Tonkpi", "Montagnes", 7.410, -7.550),
    ("daloa", "Daloa", "Haut-Sassandra", "Sassandra-Marahoué", 6.887, -6.453),
    ("bouafle", "Bouaflé", "Marahoué", "Sassandra-Marahoué", 6.980, -5.746),
]

LIEUX = {
    identifiant: {"nom": nom, "region": region, "district": district, "lat": lat, "lon": lon,
                  "zone": "savane" if district in DISTRICTS_DE_SAVANE else "foret",
                  "role": {"korhogo": "pilote", "bouake": "contraste"}.get(identifiant, "extension")}
    for identifiant, nom, region, district, lat, lon in _VILLES
}

# Nom de la région, ou du district autonome, tel qu'OpenStreetMap l'écrit dans l'adresse d'un lieu, champs
# state_district puis state, relevé le 20 novembre 2026, quand il diffère du nom retenu ci-dessus.
NOMS_OSM = {"adzope": "Mé", "dimbokro": "N’zi", "abidjan": "Abidjan", "yamoussoukro": "Yamoussoukro"}


def chef_lieu_de_region(region: str | None) -> str | None:
    """Ville couverte qui est le chef-lieu de la région nommée par OpenStreetMap, ou None."""
    from unicodedata import combining, normalize

    def simple(texte: str) -> str:
        return "".join(c for c in normalize("NFKD", texte.lower().replace("’", "'")) if not combining(c)).strip()

    if not region:
        return None
    for identifiant, lieu in LIEUX.items():
        if simple(region) in (simple(lieu["region"]), simple(NOMS_OSM.get(identifiant, lieu["region"]))):
            return identifiant
    return None


# Villes de l'étude d'origine du 14 novembre 2026, sur lesquelles portent les notebooks, les commandes
# d'évaluation et les chiffres de docs/, gardés tels quels.
LIEUX_ETUDE = {identifiant: LIEUX[identifiant] for identifiant in ("korhogo", "bouake")}

# Au-delà de cette distance de la ville couverte la plus proche, un point est hors de la Côte d'Ivoire couverte.
DISTANCE_MAX_KM = 150.0
RAYON_TERRE_KM = 6371.0


def lieux_de_zone(zone: str) -> list[str]:
    return [identifiant for identifiant, lieu in LIEUX.items() if lieu["zone"] == zone]


def rotation_disponible(identifiant: str) -> bool:
    """Le conseil de rotation n'existe que là où les rotations comparées ont un sens, la savane pour l'instant."""
    return LIEUX[identifiant]["zone"] == "savane"


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance à vol d'oiseau, formule de haversine sur une Terre sphérique."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RAYON_TERRE_KM * math.asin(math.sqrt(a))


def ville_la_plus_proche(latitude: float, longitude: float) -> tuple[str, float] | None:
    """Identifiant de la ville couverte la plus proche et sa distance, ou None au-delà de DISTANCE_MAX_KM."""
    identifiant, distance = min(((i, distance_km(latitude, longitude, l["lat"], l["lon"])) for i, l in LIEUX.items()),
                                key=lambda paire: paire[1])
    return (identifiant, distance) if distance <= DISTANCE_MAX_KM else None
