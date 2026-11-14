"""Conversations en cours, stockées dans SQLite, à écrire par le membre A.

Table prévue
    sessions(empreinte TEXT PRIMARY KEY, etat TEXT, consentement INTEGER,
             lieu TEXT, rotation TEXT, priorite TEXT, mise_a_jour TEXT)

La clé est securite.empreinte_numero, jamais le numéro en clair.
"""
