# Journal des décisions

## 14 novembre 2026

- **Application hors connexion.** Les recommandations sont calculées à l'avance et embarquées dans l'application, qui fonctionne en mode avion après une première ouverture.
- **Pluie IMERG en temps universel.** En heure solaire locale, l'API POWER renvoie moins 999 pour IMERG.
- **Pluie et évapotranspiration d'un lieu.** Moyenne des neuf points de sa grille.
- **Valeurs de FAO 56.** Pour une plage du tableau 12, la valeur retenue est le milieu de la plage. La ligne du tableau 11 retenue est la plus proche du contexte ouest-africain disponible.
- **Tendance du début des pluies.** Annoncée seulement si elle tient avec les durées maximales de séquence sèche de 7, 10 et 14 jours. Ce n'est le cas dans aucun des deux lieux.
- **Égalités.** Deux rotations de totaux égaux partagent leur rang, sans départage arbitraire.
- **Stabilité.** Le message nomme le scénario qui change le classement.
- **Égalité départagée.** Quand un scénario ne fait que départager des rotations à égalité, sans inverser aucun écart du classement de référence, le classement est déclaré stable et les rotations à égalité sont présentées comme équivalentes.
- **Voix.** Un enregistrement humain placé dans `app/audio` remplace la voix du téléphone. Le texte exact à enregistrer est produit par le moteur.
- **Mise en ligne.** L'application est publiée par GitHub Pages, pour la première ouverture avec connexion.
- **Inclusion des personnes qui ne lisent pas.** Chaque bouton porte un pictogramme. Le mode voix lit chaque message, et un bouton se touche une fois pour entendre son nom, une seconde fois pour le choisir.
- **Notes vocales.** L'agriculteur enregistre un message dans sa langue, gardé sur le téléphone sans réseau et partageable avec son conseiller. L'application ne l'interprète pas. La reconnaissance vocale hors connexion n'est pas fiable dans un navigateur et n'existe pas en dioula ni en sénoufo.
- **Réponse courte.** Le résultat tient en trois phrases, la rotation conseillée, une raison simple tirée des données et le renvoi au conseiller. Le détail chiffré reste derrière le bouton Pourquoi.
- **Alerte faux départs.** Un faux départ est une première pluie de 20 mm en 3 jours qui ne satisfait pas le critère de début des pluies. Il est arrivé 8 années sur 24 à Korhogo comme à Bouaké. L'alerte invite à attendre une pluie bien installée et à consulter le conseiller, sans donner de date de semis.
