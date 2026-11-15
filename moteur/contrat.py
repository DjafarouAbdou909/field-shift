"""Contrat entre le moteur et ses interfaces.

Le moteur renvoie trois objets, la Recommandation de rotations, l'AlerteVegetation et le
Diagnostic d'une photo de plante. Ce sont les seules choses que l'application Streamlit
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


AVERTISSEMENT_DIAGNOSTIC = ("⚠️ Diagnostic indicatif basé sur l'image, ne remplace pas l'avis de votre conseiller "
                            "ANADER pour les cas graves ou incertains.")


class Diagnostic(_Strict):
    """Diagnostic d'une photo de plante rédigé librement par le modèle, à la manière du projet agri-bot.

    Décision du responsable du 15 novembre 2026. Le modèle identifie la plante, donne le
    diagnostic probable, l'explique et recommande une action concrète, pour toute culture,
    sans liste fermée. statut analyse quand le modèle a rendu un texte, qui se termine
    toujours par AVERTISSEMENT_DIAGNOSTIC. statut echec quand la photo n'a pas pu être
    analysée, le texte étant alors un message du bot.
    """

    version: Literal["2"] = VERSION
    donnees_fictives: bool
    culture_declaree: str | None = None
    statut: Literal["analyse", "echec"]
    texte: str = Field(min_length=1)
    origine_images: str = Field(min_length=1)

    @model_validator(mode="after")
    def _avertissement_final(self):
        if self.statut == "analyse" and not self.texte.rstrip().endswith(AVERTISSEMENT_DIAGNOSTIC):
            raise ValueError("une analyse se termine par l'avertissement du diagnostic")
        return self

