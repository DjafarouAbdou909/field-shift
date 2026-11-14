# Compréhension du métier

Phase 1 de CRISP-DM, validée par le responsable de l'équipe le 14 novembre 2026, avec les modifications notées dans `docs/decisions.md`. Chaque affirmation sur l'agriculture du nord ivoirien renvoie à une référence numérotée, relue dans le texte de la source avec sa page, ou porte la mention *hypothèse à confirmer*. L'énoncé officiel du défi est la référence 5, que nous n'avons pas pu lire à ce jour.

## Problème

Dans les zones de savane ivoiriennes, le coton est la principale ressource économique [1, page 325]. Dans la région de Korhogo, il est passé de la culture associée aux vivriers à la culture pure, il occupait environ 49 % des surfaces emblavées en 2002, et il allonge la durée d'occupation du sol, ce qui raccourcit la jachère [1, page 328]. Les sols y sont décrits comme peu humifères et de fertilité moyenne. Le climat compte une seule saison des pluies, d'avril ou mai à octobre, pour 800 à 1 200 mm de pluie par an [1, page 327]. Ces valeurs reposent sur des études de 1965 à 2000 et seront actualisées par nos séries de 2001 à 2025.

L'agriculteur choisit chaque année ce qu'il sème. Il ne dispose ni d'une lecture simple de ce que sa zone a connu en pluie, en début de saison et en séquences sèches, ni d'une comparaison argumentée entre sa rotation et d'autres, *hypothèse à confirmer* auprès de l'ANADER. Que le début des pluies soit devenu plus tardif ou plus irrégulier est aussi une *hypothèse à confirmer*. La phase 2 la testera sur les données, et l'outil n'en parlera que si elle est établie.

## Utilisateur

- **L'agriculteur.** Un producteur du Poro qui cultive le coton et le maïs, joint par WhatsApp, en français, en texte et en voix. Que coton puis maïs soit la rotation la plus courante du Poro est une *hypothèse à confirmer*, la référence 1 ne décrivant pas les successions de cultures. Son usage de WhatsApp et sa lecture du français sont des *hypothèses à confirmer*, et justifient la voix. La région est peuplée surtout de Sénoufo et de Dioula [1, page 327].
- **Son conseiller.** Un agent de l'ANADER, l'agence de conseil agricole et rural créée le 29 septembre 1993 [2], par l'application web.
- **Le jury**, par la même application.

## Décisions que l'outil éclaire

1. Garder sa rotation ou en discuter une autre pour la saison suivante.
2. Introduire une légumineuse, arachide, niébé ou soja, ou la plante de couverture mucuna, au profit du sol.
3. Remplacer une partie du maïs par le sorgho ou le mil là où les débuts de saison secs sont fréquents.
4. Pondérer ces choix selon sa priorité, l'eau, le revenu ou le sol, et voir si le classement résiste à une saison plus sèche ou plus tardive.

L'outil ne tranche aucune de ces décisions, il prépare la discussion avec le conseiller.

## Critères de réussite du projet

Proposés par le rôle données et moteur, à valider par l'équipe.

1. Pour Korhogo et Bouaké, au moins trois stratégies dont la rotation actuelle, chacune avec ses raisons, preuves, bénéfices, lacunes et risques, chaque élément classé `mesure`, `calcule` ou `hypothese`.
2. Chaque chiffre affiché se reproduit à l'identique par une commande consignée, avec sa plage interannuelle, et sa source figure dans `docs/sources.md`.
3. Les vérifications de bon sens passent. Le mil et le sorgho sont mieux notés que le maïs pour l'eau, les légumineuses mieux notées pour le sol, et l'écart entre Korhogo et Bouaké suit ce que montrent les données, ou son absence est expliquée.
4. L'outil dit si le classement change avec une pluie réduite de 20 % ou un début de saison retardé de deux semaines, et lequel de ces scénarios le fait changer.
5. Un parcours WhatsApp complet, voix comprise, sur données réelles, dont chaque message passe le garde-fou, et une vidéo de secours.
6. Un agronome ou un conseiller ANADER relit les stratégies proposées, ou cette absence est écrite dans les limites.
7. Chaque membre de l'équipe sait expliquer chaque règle de calcul devant le jury.

## Données envisagées

- **Observations.** Pluie GPM IMERG par l'API NASA POWER, température, rayonnement et vent de NASA POWER, humidité du sol en surface SMAP depuis 2015, NDVI et sol nu MODIS, pente SRTM, texture, carbone organique et pH ISRIC SoilGrids, qui n'est pas produit par la NASA. Couverture, résolution et manques sont établis en phase 2.
- **Humidité du sol.** Elle vient de SMAP seul. `GWETROOT` de NASA POWER est écarté, pour la même rupture de 2020 que la pluie `PRECTOTCORR`, constatée dans le projet antérieur [3].
- **Caractéristiques des cultures.** Durée du cycle, besoins en eau, tolérance à la sécheresse et fixation de l'azote, tirés de la FAO, du CNRA ou de l'ICRISAT, sinon marqués `hypothese`.
- **Prix aux producteurs.** Le critère revenu reste qualitatif. Il ne sera chiffré que si chaque culture comparée a une source de prix vérifiable, car un prix pour le coton seul fausserait la comparaison.

## Ce que l'outil ne fera pas

- Il ne prédit pas le rendement de chaque rotation. Dans le projet antérieur, le climat de saison n'explique que 0,9 % à 6,3 % de la variation annuelle des rendements et n'en améliore pas la prévision [4].
- Il ne désigne pas une meilleure rotation prouvée, faute de vérité terrain.
- Il ne remplace ni l'agriculteur ni son conseiller.
- Il montre la date habituelle de début des pluies, mais ne conseille aucune date de semis. Il ne donne ni dose d'engrais ni traitement phytosanitaire.
- Il ne décrit pas la parcelle elle-même, les données climatiques couvrant des mailles de plusieurs kilomètres, et il ne couvre que Korhogo et Bouaké.
- Il ne traite que la première des deux saisons des pluies de Bouaké, dont le début est en outre tronqué par la recherche à partir du 1er mars, selon `docs/donnees.md`.
- Il ne parle que le français dans cette version. Les langues locales sont une perspective.

## Références

1. Zagbaï H. S., Berti F., Lebailly P., 2006. Impact de la dynamique cotonnière sur le développement rural. Étude de cas de la région de Korhogo, au Nord et au Centre de la Côte d'Ivoire. *Biotechnologie, Agronomie, Société et Environnement*, volume 10, numéro 4, pages 325 à 334. Texte intégral sur ORBi, https://orbi.uliege.be/bitstream/2268/65333/1/Impact%20de%20la%20dynamique%20cotonni%c3%a8re%20sur%20le%20d%c3%a9veloppement%20rural.%20Etude%20de%20cas%20de%20la%20r%c3%a9gion%20de%20Korhogo%2c%20au%20Nord%20et%20au%20Centre%20de%20la%20C%c3%b4te%20d%27Ivoire.pdf, empreinte SHA-256 du PDF lu a2b0908a666ffc8086c581dd267e9cbab76c70f455242ba53d95a7033054f33a.
2. ANADER, page d'accueil du site officiel, https://www.anader.ci/, consultée le 14 novembre 2026.
3. African Crop Yield Intelligence, `docs/explanatory_variables.md`, section 10, commit `2b4c18c`, travail antérieur déclaré.
4. African Crop Yield Intelligence, `docs/research_climate_zones_results.md`, commit `2b4c18c`, travail antérieur déclaré.
5. NASA Space Apps Challenge 2026, Field Shift, Adapting Farms with NASA Data, énoncé à https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/ et ressources à https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=resources. Non lu, le 14 novembre 2026 la vérification du certificat TLS du site échoue et n'a pas été contournée.

Repérés par une recherche mais non lus, et donc non cités. Dekoula et collègues 2018 sur la pluie intrasaisonnière du bassin cotonnier, Noufé et collègues 2015 sur la variabilité climatique et le maïs, N'Guessan et collègues 2019 sur le carbone des sols cultivés du nord. Le responsable les dépose dans `data/references/` pour lecture.
