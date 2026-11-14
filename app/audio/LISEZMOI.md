# Enregistrements vocaux

Chaque message de résultat peut être lu par une voix humaine enregistrée, qui fonctionne sans connexion. Sans enregistrement, l'application utilise la voix française du téléphone si elle est installée.

1. Lancez `python -m moteur.exporter`, qui écrit dans `textes_a_enregistrer.md` le texte exact de chaque message et le nom de son fichier.
2. Enregistrez chaque texte avec un téléphone, au format mp3, m4a ou ogg, et placez le fichier dans ce dossier sous le nom indiqué, par exemple `korhogo_eau.m4a`.
3. Relancez `python -m moteur.exporter`, qui associe chaque enregistrement à son message.

Un enregistrement doit dire exactement le texte prévu, sans ajout. Un enregistrement en dioula ou en sénoufo doit être une traduction fidèle, relue par une seconde personne qui parle la langue.
