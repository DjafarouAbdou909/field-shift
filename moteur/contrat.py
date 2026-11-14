"""Contrat entre le moteur de rotation et ses interfaces.

Une Recommandation est la seule chose que le moteur renvoie, et la seule chose que
l'application Streamlit et le bot WhatsApp lisent. Toute modification de ce fichier
incrémente VERSION, met à jour exemple.json et est notée dans docs/decisions.md.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSION = "1"

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
    version: Literal["1"] = VERSION
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
