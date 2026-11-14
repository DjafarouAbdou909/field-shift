# Field Shift CI, consignes pour Claude

Ce fichier est chargé automatiquement dans toute session Claude ouverte dans ce dépôt. Il vaut pour tous les membres de l'équipe.

## 1. Mission

Nous sommes l'équipe CodeX Africa, en Côte d'Ivoire, au NASA Space Apps Challenge 2026, défi « Field Shift: Adapting Farms with NASA Data ». Nous visons la première place. L'usage de l'IA est autorisé.

Nous construisons un outil d'aide à la décision qui aide un agriculteur ivoirien à comparer au moins trois stratégies de rotation des cultures, dont sa rotation actuelle, à partir d'observations de la NASA, des sols locaux, des caractéristiques des cultures et de ses priorités, à savoir économiser l'eau, gagner plus ou soigner le sol.

- **Zone pilote.** Région du Poro, autour de Korhogo, savane soudanienne du nord. Rotation actuelle de référence, coton puis maïs.
- **Zone de contraste.** Région de Gbêkê, autour de Bouaké, zone de transition plus humide du centre.
- **Cultures candidates.** Coton, maïs, sorgho, mil, arachide, niébé, soja, riz pluvial, igname, et mucuna comme plante de couverture.

Pour chaque stratégie, l'outil dit pourquoi elle est proposée, quelles données la soutiennent, ses bénéfices, les lacunes d'information et les risques à vérifier localement. Il soutient le jugement de l'agriculteur et de son conseiller ANADER, il ne le remplace jamais, et il le dit.

L'outil a deux interfaces branchées sur un même moteur.

```
Données NASA (IMERG, POWER, SMAP, MODIS, SRTM) et SoilGrids
                       |
                  moteur/            recommander(lieu, rotation_actuelle, poids)
                       |             renvoie une Recommandation, voir moteur/contrat.py
          +------------+------------+
          |                         |
       app/                       bot/
   Streamlit pour le          WhatsApp, texte et voix,
   conseiller et le jury      pour l'agriculteur
```

## 2. Règles non négociables

1. **Git.** Claude ne fait jamais de `git push`, ce sont les humains qui poussent. Claude ne se présente pas comme coauteur, n'ajoute aucune ligne `Co-Authored-By` et ne modifie pas l'attribution des commits. Petits commits, une phrase simple en anglais.
2. **Aucune invention.** Aucune donnée, aucun chiffre, aucune référence inventés. Chaque valeur vient d'un jeu de données identifié, avec sa source, sa résolution et sa période, consigné dans `docs/sources.md`. Une connaissance agronomique cite une source précise, par exemple FAO, CNRA ou ICRISAT, sinon elle porte le niveau `hypothese`.
3. **Trois niveaux, toujours distingués.** `mesure` pour ce que les données observent, `calcule` pour ce qu'une règle visible produit, `hypothese` pour la connaissance générale à confirmer localement. Le contrat l'impose, un élément `mesure` ou `calcule` sans source est refusé.
4. **Pas de meilleure rotation prouvée.** Il n'existe pas de vérité terrain. L'outil présente des comparaisons argumentées avec leur incertitude, jamais une solution optimale. Jamais un chiffre seul, toujours sa variabilité ou sa plage.
5. **Travail antérieur déclaré.** Tout ce qui existait avant le hackathon est déclaré dans `docs/travail_anterieur.md`. AGRI-BOT est une source d'inspiration, **aucun fichier n'en est copié**, le bot est réécrit ici. Le code repris de `~/African-Crop-Yield-Intelligence` porte en tête la mention de son origine et du commit.
6. **Données fictives jamais présentées.** `moteur/exemple.json` sert au développement et porte `donnees_fictives: true`. Les interfaces affichent alors un bandeau, et rien de fictif n'apparaît dans la démo ni dans la présentation.
7. **Le bot ne dit que ce que dit le moteur.** Les messages viennent de gabarits déterministes. Un texte produit par un modèle de langage passe par `bot/langage/garde_fou.py`, et s'il échoue, le gabarit est envoyé à la place.
8. **Vie privée.** Le numéro de téléphone n'est stocké que sous forme d'empreinte salée, les audios sont supprimés après transcription, le consentement est demandé au premier message, conformément à la loi ivoirienne n° 2013-450 sur les données personnelles. Aucun secret dans le dépôt, tout passe par `.env`.
9. **Rigueur de vérification.**
   - Aucune affirmation sans vérification. Chaque chiffre annoncé renvoie à la commande ou au fichier qui le produit, et se reproduit à l'identique.
   - Chaque calcul a un test dont la valeur attendue est calculée à la main ou tirée d'un exemple publié, comme l'exemple FAO-56 pour l'évapotranspiration.
   - Chaque série est contrôlée, avec ses unités, ses dates, ses manques, ses bornes physiques et ses ruptures, et la pluie est comparée entre deux sources.
   - Versions figées, graines fixées, empreintes des fichiers téléchargés consignées.
   - Un test qui échoue ne se modifie jamais pour passer, et un avertissement ne se fait pas taire sans en comprendre la cause.
   - Ce qui n'est pas vérifié se dit, « je ne sais pas » est une réponse acceptable, et toute anomalie est signalée, jamais masquée.
   - Avant chaque commit, relis ton propre diff comme le ferait un relecteur exigeant.
10. **Écriture sobre et professionnelle.**
   - Aucune signature d'outil dans le dépôt, ni dans les commits, ni dans le code, ni dans les documents.
   - Pas d'émojis, pas de formules creuses comme « robuste », « innovant » ou « de pointe », pas de commentaires qui répètent le code.
   - Noms explicites, fonctions courtes, commentaires réservés au pourquoi.
   - Chaque choix technique doit pouvoir être expliqué et défendu par un membre de l'équipe devant le jury. Explique donc chaque élément que tu écris, assez simplement pour que nous puissions le refaire.

## 3. Le contrat entre le moteur et les interfaces

`moteur/contrat.py` définit la `Recommandation`. C'est la seule frontière entre les rôles.

- Toute modification du contrat est décidée ensemble, incrémente `VERSION`, met à jour `moteur/exemple.json` et est notée dans `docs/decisions.md`.
- Les interfaces se développent sur `moteur.charger_exemple()` jusqu'à ce que `moteur.recommander()` soit prêt.
- `python -m unittest discover -s tests -t .` doit passer avant chaque commit.

## 4. Rôles et branches

| Rôle | Dossiers | Branche |
|---|---|---|
| Données et moteur | `moteur/`, `app/`, `docs/sources.md`, `docs/cadrage.md`, `docs/donnees.md`, `docs/evaluation.md` | `moteur` |
| Membre A, canal WhatsApp | `bot/main.py`, `bot/config.py`, `bot/securite.py`, `bot/sessions.py`, `bot/dialogue.py`, `bot/whatsapp.py` | `bot-canal` |
| Membre B, langage et voix | `bot/langage/` | `bot-langage` |
| Présentation | `presentation/`, sources agronomiques de `docs/sources.md` | `presentation` |

Chacun ne modifie que ses dossiers. Un besoin dans le dossier d'un autre se signale à lui. La fusion dans `main` est faite par le responsable de l'équipe.

## 5. Le moteur

- **Données retenues, peu mais bien exploitées.**
  - NASA POWER pour la température, le rayonnement, le vent et l'humidité de la zone racinaire `GWETROOT` ;
  - GPM IMERG pour la pluie, par le paramètre `IMERG_PRECTOT` de l'API POWER. La pluie `PRECTOTCORR` de POWER présente une rupture en 2020 et n'est pas utilisée, selon la section 10 de `docs/explanatory_variables.md` de `~/African-Crop-Yield-Intelligence` au commit `2b4c18c` ;
  - SMAP pour l'humidité du sol en surface, depuis 2015 ;
  - MODIS pour le NDVI et les périodes de sol nu ;
  - SRTM pour la pente ;
  - SoilGrids pour la texture, le carbone organique et le pH.
- **Indicateurs pour Korhogo et Bouaké**, de 2001 à la dernière année complète, chacun avec sa tendance et sa variabilité interannuelle. Pluie de saison, date de début des pluies, longueur de saison, plus longue séquence sèche en début de saison, jours au-dessus de 35 °C, évapotranspiration FAO-56, indice d'aridité, humidité du sol, sol nu, pente, propriétés du sol.
- **Contrôles.** Valeurs manquantes, ruptures, valeurs physiquement impossibles, comparaison IMERG et POWER.
- **Comparaison des rotations.** Critères eau, revenu et sol, avec des poids réglables, une analyse de sensibilité à une pluie réduite de 20 % et à un début de saison retardé de deux semaines, et la mention explicite des cas où le classement change.
- **Vérifications de bon sens.** Le mil et le sorgho tolèrent mieux la sécheresse que le maïs, les légumineuses fixent l'azote, Korhogo et Bouaké ne reçoivent pas la même recommandation. Une contradiction signale une erreur avant d'être une découverte.
- **Code à reprendre, avec mention d'origine.** Dans `~/African-Crop-Yield-Intelligence`, au commit `2b4c18c`, il y a `src/features/acquisition.py` pour le téléchargement vérifié, `src/features/climat.py` pour POWER et IMERG, `src/features/indicateurs.py` pour l'évapotranspiration FAO-56 et les séquences sèches, `src/features/sols.py`, `src/features/relief.py` et `src/recherche/zones_climatiques.py`.
- **Leçons de ce projet.** Le climat de saison n'explique que 0,9 % à 6,3 % de la variation annuelle des rendements selon l'aridité et n'en améliore pas la prévision, selon `docs/research_climate_zones_results.md` du même projet au même commit. Les données NASA servent donc de preuves de contexte, pas de prédiction du rendement de chaque rotation.

## 6. Le bot WhatsApp

- **Pile technique.** FastAPI dans le même processus que le moteur, SQLite, WhatsApp Cloud API, ffmpeg pour l'audio.
- **Parcours.** Accueil et consentement, puis le lieu, par partage de position ou liste de départements, puis la rotation actuelle, puis la priorité en trois boutons, puis le résultat en texte et en note vocale, avec les boutons « Pourquoi ? », « Écouter » et « Voir le détail », ce dernier ouvrant l'application Streamlit filtrée par paramètres d'URL. Une note vocale reçue est transcrite puis traitée comme du texte. Hors de la zone couverte, le bot le dit.
- **Webhook.** Signature `X-Hub-Signature-256` vérifiée sur le corps brut, réponse 200 immédiate et traitement en tâche de fond, idempotence sur l'identifiant `wamid` du message.
- **Pièges connus.** Le jeton temporaire de Meta expire en 24 heures environ, il faut un jeton d'utilisateur système. Le numéro de test n'écrit qu'à quelques destinataires déclarés à l'avance. Les boutons sont limités à 3 par message avec des titres très courts, les listes à 10 lignes. L'audio sortant se téléverse d'abord, puis s'envoie par son identifiant, en OGG Opus pour une note vocale. Le webhook exige une URL HTTPS publique.

## 7. Méthode CRISP-DM, proportionnée aux 48 heures

Le projet suit les six phases de CRISP-DM. Chaque phase produit un livrable court et se termine par une entrée dans `docs/decisions.md`. On revient à une phase antérieure dès qu'une phase suivante le justifie, et on le note.

| Phase | Heures | Livrable | Critère de sortie |
|---|---|---|---|
| 1. Compréhension du métier | 0 à 2 | `docs/cadrage.md` | Problème, utilisateur, décisions éclairées, critères de réussite et exclusions validés par l'équipe |
| 2. Compréhension des données | 2 à 8 | Section dédiée de `docs/donnees.md`, `docs/sources.md` | Chaque source décrite, couverture, résolution, manques et anomalies constatés, pluie comparée entre deux sources |
| 3. Préparation des données | 8 à 16 | `moteur/donnees.py`, `moteur/indicateurs.py`, leurs tests | Indicateurs de Korhogo et Bouaké calculés, contrôlés et reproductibles |
| 4. Modélisation | 16 à 24 | `moteur/cultures.py`, `moteur/rotations.py`, `moteur/criteres.py`, `moteur/recommander.py` | Comparaison multicritère à règles visibles, sources des caractéristiques des cultures, aucune prédiction de rendement |
| 5. Évaluation | 24 à 32 | Section dédiée de `docs/evaluation.md` | Cohérence avec les faits agronomiques établis, différence attendue entre Korhogo et Bouaké, sensibilité à la pluie et au début de saison, avis d'un agronome si possible, limites écrites |
| 6. Déploiement | 24 à 48 | `app/`, `bot/`, `presentation/` | Démo de bout en bout, vidéo de secours, soumission |

Il n'existe pas de vérité terrain pour la meilleure rotation. L'évaluation ne mesure donc pas une précision, elle établit ce que la comparaison permet d'affirmer et ce qu'elle ne permet pas. Le bot et l'application se construisent en parallèle des phases 1 à 5 sur l'exemple fictif, et se branchent sur le moteur réel en phase 6.

## 8. Calendrier

| Heure | Jalon |
|---|---|
| 2 | Contrat et exemple validés par tous, comptes Meta prêts |
| 8 | Bot écho joignable par WhatsApp, signature et idempotence testées |
| 16 | Parcours complet sur l'exemple, indicateurs de Korhogo calculés |
| 24 | Moteur réel branché sur le bot et l'application, Korhogo et Bouaké |
| 32 | Voix en entrée et en sortie, sensibilité calculée |
| 40 | Gel des fonctionnalités, uniquement fiabilisation et répétition |
| 44 | Vidéo de secours de la démo enregistrée |
| 48 | Soumission |

## 9. Façon de travailler

- **En début de session**, lis ce fichier, `docs/decisions.md` et `git log --oneline -15`, puis résume en trois lignes où en est le projet pour ton rôle.
- Annonce le plan de chaque étape en quelques lignes, puis exécute-le sans attendre si la décision est évidente.
- Une version qui marche de bout en bout passe avant toute amélioration.
- Signale immédiatement toute donnée douteuse ou conclusion fragile, sans la masquer.
- **En fin d'étape**, ajoute une entrée à `docs/decisions.md` et fais un bilan court, avec ce qui est fait, ce qui reste et les décisions qui reviennent à l'équipe.
- Écris en français, simplement. Les fichiers de `docs/` suivent le style de l'équipe, français soutenu, sans deux-points, sans parenthèses, sans tirets longs ni flèches dans la prose.
