"""Construit entrainement/diagnostic_cacao_colab.ipynb à partir du notebook du maïs.

    python entrainement/construire_notebook_cacao.py

Les cellules du modèle et du seuil sont reprises du notebook du maïs, pour que les deux
entraînements suivent exactement la même méthode.
"""

import ast
from pathlib import Path

import nbformat

DOSSIER = Path(__file__).resolve().parent
mais = nbformat.read(DOSSIER / "diagnostic_mais_colab.ipynb", 4)
codes = [c.source for c in mais.cells if c.cell_type == "code"]
modele_cell = next(s for s in codes if "def epoques" in s)
seuil_cell = next(s for s in codes if "def predire" in s)
m = nbformat.v4.new_markdown_cell
c = nbformat.v4.new_code_cell

cellules = [
m("""# Diagnostic du swollen shoot du cacaoyer, entraînement dans Google Colab

Ce notebook entraîne un petit modèle de reconnaissance des feuilles de cacaoyer, qui fonctionne ensuite **sans connexion** dans l'application Conseil Rotation. Choisissez d'abord Exécution, Modifier le type d'exécution, GPU T4, puis Tout exécuter.

**Données**

| Rôle | Jeu | Pays | Licence |
|---|---|---|---|
| Entraînement | KaraAgroAI Cocoa Dataset, doi 10.7910/DVN/BBGQSP, Harvard Dataverse | Ghana, 7 régions cacaoyères | CC0 1.0 |
| Test indépendant | CocoaSwolSet, projet Deep Cacao de l'ESATIC et de l'INPHB, doi 10.17632/hvwth9dsfd.2, Mendeley Data | Côte d'Ivoire | CC BY 4.0, à citer |

**Règles de rigueur**

- Le modèle apprend au Ghana et il est testé sur des feuilles ivoiriennes, jamais vues. Sa fiabilité est donc mesurée en Côte d'Ivoire.
- Seules les feuilles sont utilisées. Les arbres et les cabosses du jeu ivoirien sont écartés.
- L'anthracnose n'existe que dans le jeu du Ghana, dont la fiche la décrit à tort comme une maladie du lupin. Elle n'est pas une classe du modèle. Ses images servent à vérifier qu'une maladie hors de la liste n'est pas prise pour le swollen shoot.
- Le jeu ivoirien mélange des formats. Les photos JPG, PNG et HEIC sont retenues. Les photos RAW au format DNG, 164 feuilles au 14 novembre 2026, sont écartées et comptées, comme tout fichier illisible, par exemple un RAW nommé en jpg.
- Le seuil de confiance est choisi sur la validation du Ghana, jamais sur le test ivoirien.
- Le modèle ne donne jamais de traitement."""),
c("""!nvidia-smi -L || echo "Pas de carte graphique, choisissez GPU T4 dans le type d'exécution"
!apt-get -qq install -y unrar p7zip-full > /dev/null
!pip -q install onnx onnxruntime onnxscript pillow-heif"""),
c("""import hashlib, json, math, os, random, shutil, subprocess, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import requests
import torch
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()  # photos HEIC des iPhone, présentes dans le jeu ivoirien
GRAINE = 20261114
random.seed(GRAINE); np.random.seed(GRAINE); torch.manual_seed(GRAINE)
RACINE = Path("/content/cacao")
CLASSES = ["saine", "swollen_shoot"]
MAX_PAR_ARCHIVE_ENTRAINEMENT = 1500
MAX_PAR_CLASSE_TEST = 700
TAILLE = 224
ENTETES = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Colab cocoa-leaf-training", "Accept": "application/json"}

DOI_GHANA = "10.7910/DVN/BBGQSP"
ARCHIVES_GHANA = [
    ("entrainement", "healthy_01.zip", "saine"), ("entrainement", "healthy_02.zip", "saine"),
    ("entrainement", "cssvd_01.zip", "swollen_shoot"), ("entrainement", "cssvd_02.zip", "swollen_shoot"),
    ("hors_liste", "anthracnose_04.zip", "anthracnose"),
]
MENDELEY = "hvwth9dsfd"
DOSSIERS_IVOIRIENS = {
    "CocoaSwolSet/Leaves/Adults/Healthy": "saine", "CocoaSwolSet/Leaves/Young/Healthy": "saine",
    "CocoaSwolSet/Leaves/Adults/Diseaded": "swollen_shoot", "CocoaSwolSet/Leaves/Young/Diseased": "swollen_shoot",
}"""),
m("""### 1. Téléchargement vérifié

Les archives du Ghana sont vérifiées par leur MD5 publié sur Harvard Dataverse. Chaque photo ivoirienne est vérifiée par son SHA-256 publié sur Mendeley Data."""),
c("""def obtenir(url, **options):
    delai = options.pop("timeout", 120)
    for essai in range(5):
        r = requests.get(url, headers=ENTETES, timeout=delai, **options)
        if r.status_code == 200:
            return r
        print(f"Réponse {r.status_code}, nouvel essai dans {10 * (essai + 1)} s. Début, {r.text[:200]!r}")
        time.sleep(10 * (essai + 1))
    raise RuntimeError(f"Refus de {url} après 5 essais, code {r.status_code}")

def md5(chemin):
    h = hashlib.md5()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 22), b""):
            h.update(bloc)
    return h.hexdigest()

def extraire(archive, dossier):
    dossier.mkdir(parents=True, exist_ok=True)
    commande = ["unrar", "x", "-o+", "-inul", str(archive), str(dossier) + "/"] if archive.suffix == ".rar" \\
        else ["7z", "x", "-y", "-bd", f"-o{dossier}", str(archive)]
    subprocess.run(commande, check=True, stdout=subprocess.DEVNULL)

version = obtenir(f"https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:{DOI_GHANA}").json()["data"]["latestVersion"]
catalogue = {f["dataFile"]["filename"]: f["dataFile"] for f in version["files"]}
licences = {"KARAAGRO_COCOA": version.get("license", {}).get("name")}
for role, nom, etiquette in ARCHIVES_GHANA:
    dossier = RACINE / role / Path(nom).stem
    if dossier.exists() and any(dossier.rglob("*")):
        continue
    info = catalogue[nom]
    archive = RACINE / "archives" / nom
    archive.parent.mkdir(parents=True, exist_ok=True)
    with obtenir(f"https://dataverse.harvard.edu/api/access/datafile/{info['id']}", stream=True, timeout=600) as r:
        with open(archive, "wb") as f:
            for bloc in r.iter_content(1 << 22):
                f.write(bloc)
    if md5(archive) != (info.get("md5") or info.get("checksum", {}).get("value")):
        raise ValueError(f"empreinte MD5 différente pour {nom}")
    extraire(archive, dossier)
    archive.unlink()
    print(f"{nom} vérifié et extrait")

jeu = obtenir(f"https://data.mendeley.com/public-api/datasets/{MENDELEY}").json()
dossiers = {d["id"]: d for d in obtenir(f"https://data.mendeley.com/public-api/datasets/{MENDELEY}/folders/{jeu['version']}").json()}
licences["COCOASWOLSET"] = jeu["data_licence"]["url"]

def chemin_mendeley(fid):
    noms = []
    while fid in dossiers:
        noms.append(dossiers[fid]["name"]); fid = dossiers[fid].get("parent_id")
    return "/".join(reversed(noms))

FORMATS_RETENUS = {"jpg", "jpeg", "png", "heic"}
par_classe, ecartees = defaultdict(list), Counter()
for f in jeu["files"]:
    classe = DOSSIERS_IVOIRIENS.get(chemin_mendeley(f["folder_id"]))
    if not classe:
        continue
    extension = f["filename"].rsplit(".", 1)[-1].lower()
    if extension in FORMATS_RETENUS:
        par_classe[classe].append(f)
    else:
        ecartees[(classe, extension)] += 1
print("Photos ivoiriennes écartées pour leur format", dict(ecartees))
choisis = [(f, c) for c, liste in par_classe.items()
           for f in random.Random(GRAINE).sample(liste, min(MAX_PAR_CLASSE_TEST, len(liste)))]
print("Photos ivoiriennes disponibles", {c: len(l) for c, l in par_classe.items()}, "retenues", len(choisis))

def telecharger_ivoirien(element):
    f, classe = element
    chemin = RACINE / "test_ivoirien" / classe / f["filename"]
    if chemin.exists():
        return True
    chemin.parent.mkdir(parents=True, exist_ok=True)
    contenu = obtenir(f["content_details"]["download_url"], timeout=300).content
    if hashlib.sha256(contenu).hexdigest() != f["content_details"]["sha256_hash"]:
        return False
    chemin.write_bytes(contenu)
    return True

with ThreadPoolExecutor(8) as groupe:
    resultats = list(groupe.map(telecharger_ivoirien, choisis))
print("Photos ivoiriennes vérifiées", sum(resultats), "rejetées pour empreinte différente", resultats.count(False))"""),
m("""### 2. Inventaire, tirage et aperçu

Un aperçu de chaque source permet de vérifier à l'œil que les photos montrent bien des feuilles, et de comparer les symptômes du Ghana et de Côte d'Ivoire."""),
c("""EXTENSIONS = {".jpg", ".jpeg", ".png"}

def lisible(p):
    try:
        with Image.open(p) as im:
            im.verify()
        return True
    except Exception:
        return False

ensembles, inventaire = defaultdict(list), []
for role, nom, etiquette in ARCHIVES_GHANA:
    trouvees = sorted(p for p in (RACINE / role / Path(nom).stem).rglob("*") if p.suffix.lower() in EXTENSIONS)
    tirees = random.Random(GRAINE).sample(trouvees, min(MAX_PAR_ARCHIVE_ENTRAINEMENT, len(trouvees)))
    lisibles = [p for p in tirees if lisible(p)]
    ensembles[role] += [(p, etiquette, "GHANA") for p in lisibles]
    inventaire.append((role, "GHANA", nom, etiquette, len(trouvees), len(tirees), len(tirees) - len(lisibles)))
for classe in CLASSES:
    trouvees = sorted(p for p in (RACINE / "test_ivoirien" / classe).glob("*") if not p.name.endswith(".partiel"))
    lisibles = [p for p in trouvees if lisible(p)]
    ensembles["test_ivoirien"] += [(p, classe, "COTE_D_IVOIRE") for p in lisibles]
    inventaire.append(("test_ivoirien", "COTE_D_IVOIRE", classe, classe, len(trouvees), len(trouvees), len(trouvees) - len(lisibles)))
print("rôle, source, archive, classe, trouvées, tirées, illisibles écartées")
for ligne in inventaire:
    print(*ligne)

import matplotlib.pyplot as plt
fig, axes = plt.subplots(4, 4, figsize=(12, 12))
groupes = [("entrainement", "saine"), ("entrainement", "swollen_shoot"), ("test_ivoirien", "saine"), ("test_ivoirien", "swollen_shoot")]
for ligne_axes, (role, classe) in zip(axes, groupes):
    exemples = random.Random(1).sample([e for e in ensembles[role] if e[1] == classe], 4)
    for ax, (p, _, source) in zip(ligne_axes, exemples):
        ax.imshow(ImageOps.exif_transpose(Image.open(p)).convert("RGB").resize((300, 300))); ax.axis("off")
        ax.set_title(f"{source} {classe}", fontsize=9)
plt.tight_layout(); plt.show()"""),
m("""### 3. Validation tirée du seul Ghana"""),
c("""entrainement = ensembles["entrainement"]
random.Random(GRAINE).shuffle(entrainement)
groupes_classe = defaultdict(list)
for e in entrainement:
    groupes_classe[e[1]].append(e)
apprentissage, validation = [], []
for classe, liste in groupes_classe.items():
    coupe = int(0.15 * len(liste))
    validation += liste[:coupe]
    apprentissage += liste[coupe:]
print("Apprentissage", Counter(e[1] for e in apprentissage))
print("Validation", Counter(e[1] for e in validation))"""),
m("""### 4. Modèle

Même méthode que pour le maïs, MobileNetV3 Small pré-entraîné sur ImageNet. Les photos des téléphones sont redressées selon leur orientation EXIF avant d'être lues."""),
c(modele_cell.replace('image = Image.open(chemin).convert("RGB")',
                      'image = ImageOps.exif_transpose(Image.open(chemin)).convert("RGB")')),
m("""### 5. Seuil de confiance, choisi sur la validation du Ghana"""),
c(seuil_cell),
m("""### 6. Fiabilité sur les feuilles ivoiriennes et sur l'anthracnose hors liste"""),
c("""def wilson(k, n, z=1.959964):
    if n == 0:
        return [None, None]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    demi = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0, centre - demi), 3), round(min(1, centre + demi), 3)]

def reponses(p):
    return np.where(p.max(1) >= SEUIL, p.argmax(1), -1)

fiabilite = {}
p, y = predire(ensembles["test_ivoirien"])
r = reponses(p)
for i, classe in enumerate(CLASSES):
    n = int((y == i).sum()); k = int(((r == i) & (y == i)).sum()); rendues = int((r == i).sum())
    fiabilite[f"test_ivoirien_{classe}"] = {
        "images": n, "rappel": round(k / n, 3), "rappel_ic95": wilson(k, n),
        "precision": round(k / rendues, 3) if rendues else None,
        "precision_ic95": wilson(k, rendues) if rendues else None,
        "part_inconnu": round(float((r[y == i] == -1).mean()), 3)}
fiabilite["test_ivoirien_exactitude_sans_seuil"] = round(float((p.argmax(1) == y).mean()), 3)
p, _ = predire(ensembles["hors_liste"])
r = reponses(p)
fiabilite["hors_liste_anthracnose"] = {"images": int(len(r)), "part_inconnu": round(float((r == -1).mean()), 3),
                                      "part_saine": round(float((r == 0).mean()), 3),
                                      "part_swollen_shoot": round(float((r == 1).mean()), 3)}
print(json.dumps(fiabilite, indent=1, ensure_ascii=False))"""),
m("""### 7. Export pour le téléphone

Placez ensuite `modele_cacao.onnx` et `modele_cacao.json` dans `app/diagnostic/` du dépôt."""),
c("""import onnxruntime as ort
modele = modele.cpu().eval()
SORTIE = Path("/content/diagnostic_cacao")
SORTIE.mkdir(exist_ok=True)
exemple = torch.randn(1, 3, TAILLE, TAILLE)
try:
    torch.onnx.export(modele, exemple, SORTIE / "modele_cacao.onnx", input_names=["image"], output_names=["logits"],
                      opset_version=17, dynamo=False)
except TypeError:
    torch.onnx.export(modele, exemple, SORTIE / "modele_cacao.onnx", input_names=["image"], output_names=["logits"],
                      opset_version=17)
image = transformation_evaluation(ImageOps.exif_transpose(Image.open(ensembles["test_ivoirien"][0][0])).convert("RGB")).unsqueeze(0)
ecart_max = float(np.abs(ort.InferenceSession(str(SORTIE / "modele_cacao.onnx")).run(None, {"image": image.numpy()})[0]
                         - modele(image).detach().numpy()).max())
print("Écart maximal entre ONNX et PyTorch", ecart_max)
assert ecart_max < 1e-3
fiche = {
    "culture": "cacao", "classes": CLASSES, "taille": TAILLE, "redimension": 256, "moyenne": MOYENNE, "ecart_type": ECART,
    "seuil": round(SEUIL, 4), "fiabilite": fiabilite, "inventaire": inventaire, "licences": licences,
    "sources": {"KARAAGRO_COCOA": DOI_GHANA, "COCOASWOLSET": "10.17632/hvwth9dsfd.2"},
    "attribution": "CocoaSwolSet, projet Deep Cacao, ESATIC et INPHB, Mendeley Data, CC BY 4.0",
    "graine": GRAINE, "torch": torch.__version__, "date": time.strftime("%Y-%m-%d"),
    "avertissement": "Maladie possible, à faire confirmer par votre conseiller ANADER. Aucun traitement n'est proposé.",
}
(SORTIE / "modele_cacao.json").write_text(json.dumps(fiche, indent=1, ensure_ascii=False), encoding="utf-8")
print("Taille du modèle", round((SORTIE / "modele_cacao.onnx").stat().st_size / 1e6, 1), "Mo")
shutil.make_archive("/content/diagnostic_cacao", "zip", SORTIE)
from google.colab import files
files.download("/content/diagnostic_cacao.zip")"""),
]

nb = nbformat.v4.new_notebook()
nb.cells = cellules
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nb.metadata["accelerator"] = "GPU"
for cellule in nb.cells:
    if cellule.cell_type == "code":
        ast.parse("\n".join(l for l in cellule.source.splitlines() if not l.startswith("!")))
nbformat.write(nb, DOSSIER / "diagnostic_cacao_colab.ipynb")
print("notebook écrit, syntaxe valide")
