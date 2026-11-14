"""Contrat entre le moteur et ses interfaces.

Le moteur renvoie trois objets, la Recommandation de rotations, l'AlerteVegetation et le
Diagnostic d'une photo de feuille. Ce sont les seules choses que l'application Streamlit
et le bot WhatsApp lisent. Toute modification de ce fichier incrémente VERSION, met à
jour les exemples fictifs et est notée dans docs/decisions.md.

Version 2. Ajout de l'AlerteVegetation et du Diagnostic, la Recommandation ne changeant
que de numéro de version.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSION = "2"

Niveau = Literal["mesure", "calcule", "hypothese"]
Confiance = Literal["faible", "moyenne", "elevee"]
Priorite = Literal["eau", "revenu", "sol"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Source(_Strict):
    """Jeu de données ou publication d'où vient une valeur."""

    nom: str = Field(min_length=1)
    reference: str = Field(min_length=1, description="URL, DOI ou citation complète")
    periode: str | None = None
    resolution: str | None = None


class Element(_Strict):
    """Une raison, une preuve, un bénéfice, une lacune ou un risque."""

    texte: str = Field(min_length=1)
    niveau: Niveau
    source: Source | None = None

    @model_validator(mode="after")
    def _source_obligatoire(self):
        if self.niveau != "hypothese" and self.source is None:
            raise ValueError(f"un élément de niveau {self.niveau} doit citer sa source")
        return self


class Lieu(_Strict):
    id: str = Field(min_length=1)
    nom: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class Indicateur(_Strict):
    """Valeur observée ou calculée, toujours accompagnée de sa plage."""

    code: str = Field(min_length=1)
    texte: str = Field(min_length=1)
    valeur: float
    bas: float
    haut: float
    unite: str
    niveau: Literal["mesure", "calcule"]
    source: Source

    @model_validator(mode="after")
    def _plage_coherente(self):
        if not self.bas <= self.valeur <= self.haut:
            raise ValueError(f"{self.code} doit vérifier bas <= valeur <= haut")
        return self


class Scores(_Strict):
    """Note de 0 à 5 sur chaque critère, 5 étant le plus favorable."""

    eau: float = Field(ge=0, le=5)
    revenu: float = Field(ge=0, le=5)
    sol: float = Field(ge=0, le=5)


class Poids(_Strict):
    eau: float = Field(ge=0, le=1)
    revenu: float = Field(ge=0, le=1)
    sol: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _somme_unite(self):
        if abs(self.eau + self.revenu + self.sol - 1) > 1e-6:
            raise ValueError("les poids doivent sommer à 1")
        return self


class Strategie(_Strict):
    id: str = Field(min_length=1)
    nom: str = Field(min_length=1)
    actuelle: bool
    cultures: list[str] = Field(min_length=1)
    scores: Scores
    pourquoi: list[Element] = Field(min_length=1)
    preuves: list[Element] = Field(min_length=1)
    benefices: list[Element]
    lacunes: list[Element]
    risques: list[Element]
    confiance: Confiance


class Recommandation(_Strict):
    version: Literal["2"] = VERSION
    donnees_fictives: bool
    lieu: Lieu
    priorite: Priorite | None
    poids: Poids
    indicateurs: list[Indicateur] = Field(min_length=1)
    strategies: list[Strategie] = Field(min_length=3)
    classement: list[str]
    classement_stable: bool = Field(description="vrai si le classement résiste aux scénarios de sensibilité")
    lien_detail: str | None = None
    avertissement: str = Field(min_length=1)

    @model_validator(mode="after")
    def _coherence(self):
        ids = [s.id for s in self.strategies]
        if len(set(ids)) != len(ids):
            raise ValueError("les identifiants de stratégie doivent être uniques")
        if sum(s.actuelle for s in self.strategies) != 1:
            raise ValueError("une et une seule stratégie doit être la rotation actuelle")
        if sorted(self.classement) != sorted(ids):
            raise ValueError("le classement doit contenir chaque stratégie une fois")
        return self


class AlerteVegetation(_Strict):
    """Végétation d'un champ comparée aux mêmes dates des autres années, sans aucune cause déduite.

    statut faible si la valeur est sous le seuil, normale sinon, indisponible si les
    observations sans nuage ne suffisent pas, auquel cas valeur et seuil sont absents.
    """

    version: Literal["2"] = VERSION
    donnees_fictives: bool
    lieu: Lieu
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    indice: Literal["NDVI"]
    statut: Literal["faible", "normale", "indisponible"]
    valeur: float | None = None
    seuil: float | None = None
    observations_reference: int = Field(ge=0)
    annees_reference: int = Field(ge=0)
    texte: str = Field(min_length=1)
    niveau: Literal["mesure", "calcule"]
    source: Source
    avertissement: str = Field(min_length=1)

    @model_validator(mode="after")
    def _statut_coherent(self):
        if self.statut == "indisponible":
            if self.valeur is not None or self.seuil is not None:
                raise ValueError("une alerte indisponible n'a ni valeur ni seuil")
        elif self.valeur is None or self.seuil is None:
            raise ValueError("une alerte faible ou normale porte sa valeur et son seuil")
        elif (self.statut == "faible") != (self.valeur < self.seuil):
            raise ValueError("le statut faible exige une valeur sous le seuil, et seulement dans ce cas")
        return self


MESSAGES_DIAGNOSTIC = {
    "maladie_possible": "Maladie possible, à faire confirmer par votre conseiller ANADER.",
    "aucune_maladie_reconnue": ("Je ne reconnais aucune des maladies que je connais. Si la plante va mal, "
                                "montrez-la à votre conseiller ANADER."),
    "inconnu": ("Je ne reconnais pas bien cette photo. Prenez une photo nette d'une seule feuille, à la lumière "
                "du jour, ou montrez la plante à votre conseiller ANADER."),
}


class Diagnostic(_Strict):
    """Maladie possible d'après une photo de feuille, choisie dans une liste fermée.

    Trois statuts. maladie_possible nomme une maladie de la liste avec sa source.
    aucune_maladie_reconnue dit que la feuille ne ressemble à aucune maladie de la liste,
    sans jamais garantir que la plante est saine. inconnu dit que le modèle ne sait pas
    répondre, photo illisible ou confiance sous le seuil, ce qui couvre aussi les maladies
    hors de la liste. Le diagnostic ne recommande jamais de traitement ni de produit, et
    renvoie toujours au conseiller ANADER, dans les messages de MESSAGES_DIAGNOSTIC.
    """

    version: Literal["2"] = VERSION
    donnees_fictives: bool
    culture: str = Field(min_length=1)
    statut: Literal["maladie_possible", "aucune_maladie_reconnue", "inconnu"]
    maladie: str | None = None
    confiance: float = Field(ge=0, le=1)
    liste: list[str] = Field(min_length=1)
    source_maladie: Source | None = None
    origine_images: str = Field(min_length=1)
    avertissement: str = Field(min_length=1)

    @model_validator(mode="after")
    def _diagnostic_coherent(self):
        if self.statut == "maladie_possible":
            if self.maladie not in self.liste or self.source_maladie is None:
                raise ValueError("une maladie possible appartient à la liste fermée et cite sa source")
        elif self.maladie is not None or self.source_maladie is not None:
            raise ValueError("seul un diagnostic de maladie possible nomme une maladie")
        if "conseiller ANADER" not in self.avertissement:
            raise ValueError("l'avertissement renvoie au conseiller ANADER")
        return self

