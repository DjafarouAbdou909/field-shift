"""Paramètres du bot, lus dans l'environnement, jamais écrits dans le dépôt."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Parametres:
    verify_token: str
    app_secret: str
    access_token: str
    phone_number_id: str
    sel_numeros: str
    base_de_donnees: str
    url_application: str


def parametres() -> Parametres:
    """Lit les paramètres à chaque appel, pour que les tests puissent les changer."""
    return Parametres(
        verify_token=os.environ.get("WHATSAPP_VERIFY_TOKEN", ""),
        app_secret=os.environ.get("WHATSAPP_APP_SECRET", ""),
        access_token=os.environ.get("WHATSAPP_ACCESS_TOKEN", ""),
        phone_number_id=os.environ.get("WHATSAPP_PHONE_NUMBER_ID", ""),
        sel_numeros=os.environ.get("SEL_NUMEROS", ""),
        base_de_donnees=os.environ.get("BASE_DE_DONNEES", "data/bot.sqlite3"),
        url_application=os.environ.get("URL_APPLICATION", "http://localhost:8501"),
    )
