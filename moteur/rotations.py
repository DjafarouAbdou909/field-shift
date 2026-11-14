"""Stratégies de rotation comparées, dont la rotation actuelle.

Les trois stratégies sont celles retenues par le responsable de l'équipe le 14 novembre
2026, notées dans docs/decisions.md. Chaque bénéfice, lacune ou risque porte son niveau,
mesure, calcule ou hypothese, et le code de sa source dans docs/sources.md quand elle a
été lue. Un bénéfice sans source lue reste une hypothese sans code. Les stratégies sont à
valider avec l'ANADER ou un agronome avant la démo.

L'arachide a été retirée de la deuxième stratégie, aucune source lue n'appuyant encore
son effet sur le maïs suivant.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Appui:
    texte: str
    niveau: str
    source: str | None = None


@dataclass(frozen=True)
class Strategie:
    id: str
    nom: str
    cultures: tuple[str, ...]
    actuelle: bool
    benefices: tuple[Appui, ...] = field(default_factory=tuple)
    lacunes: tuple[Appui, ...] = field(default_factory=tuple)
    risques: tuple[Appui, ...] = field(default_factory=tuple)


DEGRADATION_DU_SOL = Appui(
    "La culture continue sans restitution organique fait baisser les rendements, la matière organique et le pH "
    "du sol, et le coton raccourcit la jachère dans la région de Korhogo.",
    "hypothese", "CATTAN2001, GOURO_VALL2010, ZAGBAI2006")

STRATEGIES = (
    Strategie(
        "coton_mais", "Coton puis maïs", ("coton", "maïs"), True,
        benefices=(Appui("Les sociétés cotonnières ouest-africaines encouragent la culture du maïs en rotation avec "
                         "le coton, selon une étude au Burkina Faso, page 107.", "hypothese", "GUENOT2014"),),
        lacunes=(Appui("L'arrière-effet des engrais du coton sur le maïs n'est appuyé par aucune source lue.",
                       "hypothese"),),
        risques=(DEGRADATION_DU_SOL,),
    ),
    Strategie(
        "coton_niebe_mais", "Coton, niébé puis maïs", ("coton", "niébé", "maïs"), False,
        benefices=(Appui("Au nord du Nigeria, le maïs qui suit un niébé a un rendement supérieur au maïs continu, "
                         "page 915.", "hypothese", "YUSUF2009"),),
        lacunes=(Appui("L'effet du niébé y dépend de la variété et reste inférieur à celui du soja, pages 915 et 920. "
                       "Il n'est pas mesuré dans le Poro.", "hypothese", "YUSUF2009"),
                 Appui("La durée du cycle du niébé vient d'une seule ligne du tableau 11 de FAO-56, établie pour le "
                       "climat méditerranéen.", "hypothese", "FAO56_T11_T12")),
        risques=(Appui("Une année de plus sans coton réduit le revenu monétaire, non chiffré faute de prix sourcés.",
                       "hypothese"),),
    ),
    Strategie(
        "sorgho_niebe", "Sorgho puis niébé", ("sorgho", "niébé"), False,
        benefices=(Appui("Le sorgho demande moins d'eau que le maïs sur son cycle.", "calcule", "FAO56_T11_T12"),
                   Appui("Le sorgho et les mils poussent dans des milieux difficiles où d'autres cultures poussent mal.",
                         "hypothese", "FAO1995_SORGHO_MIL")),
        lacunes=(Appui("L'effet du niébé sur le sorgho suivant n'est appuyé par aucune source lue.", "hypothese"),
                 Appui("La meilleure tolérance du sorgho à la sécheresse par rapport au maïs n'est affirmée que "
                       "qualitativement.", "hypothese", "FAO1995_SORGHO_MIL")),
        risques=(Appui("Sans coton, la stratégie quitte la filière cotonnière et son débouché.", "hypothese"),),
    ),
)
