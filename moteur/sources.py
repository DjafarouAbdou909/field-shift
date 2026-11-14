"""Sources citées par le moteur, sous la forme du contrat, avec les mêmes codes que docs/sources.md."""

from .contrat import Source

SOURCES = {
    "IMERG": Source(nom="NASA GPM IMERG, par l'API NASA POWER", periode="2001 à 2025", resolution="0,1 degré",
                    reference="https://power.larc.nasa.gov/api/temporal/daily/point, paramètre IMERG_PRECTOT"),
    "POWER": Source(nom="NASA POWER, réanalyse MERRA-2 et rayonnement CERES SYN1deg", periode="2001 à 2025",
                    resolution="0,5 par 0,625 degré",
                    reference="https://power.larc.nasa.gov/api/temporal/daily/point"),
    "HLS": Source(nom="NASA HLS, Harmonized Landsat and Sentinel-2, indice NDVI et masque Fmask", resolution="30 m",
                  periode="Landsat depuis le 11 avril 2013, Sentinel-2 depuis le 28 novembre 2015",
                  reference="Produits HLSL30_VI.020, HLSS30_VI.020, HLSL30.020 et HLSS30.020 par AppEEARS, DOI "
                            "10.5067/HLS/HLSL30_VI.002, 10.5067/HLS/HLSS30_VI.002, 10.5067/HLS/HLSL30.002 et "
                            "10.5067/HLS/HLSS30.002"),
    "FAO56_ET0": Source(nom="FAO-56, évapotranspiration de référence FAO Penman-Monteith",
                        reference="Allen R. G., Pereira L. S., Raes D., Smith M., 1998. FAO Irrigation and drainage "
                                  "paper 56, chapitre 2, équation 6, https://www.fao.org/4/x0490e/x0490e06.htm"),
    "FAO56_T11_T12": Source(nom="FAO-56, durées des stades et coefficients culturaux",
                            reference="Allen R. G., Pereira L. S., Raes D., Smith M., 1998. Crop evapotranspiration, "
                                      "FAO Irrigation and drainage paper 56, chapitre 6, tableaux 11 et 12, "
                                      "https://www.fao.org/4/x0490e/x0490e0b.htm"),
    "FAO56_C5_C8": Source(nom="FAO-56, stades de croissance et sensibilité au manque d'eau",
                          reference="Allen R. G., Pereira L. S., Raes D., Smith M., 1998. FAO Irrigation and drainage "
                                    "paper 56, chapitres 5 et 8, https://www.fao.org/4/x0490e/x0490e0e.htm"),
    "ZAGBAI2006": Source(nom="Zagbaï, Berti et Lebailly, 2006",
                         reference="Impact de la dynamique cotonnière sur le développement rural, région de Korhogo. "
                                   "Biotechnologie, Agronomie, Société et Environnement 10, 4, pages 325 à 334"),
    "YUSUF2009": Source(nom="Yusuf et collègues, 2009",
                        reference="Effect of crop rotation and nitrogen fertilization on yield and nitrogen efficiency "
                                  "in maize in the northern Guinea savanna of Nigeria. African Journal of Agricultural "
                                  "Research 4, 10, pages 913 à 921"),
    "GUENOT2014": Source(nom="Guenot et Huchet-Bourdon, 2014",
                         reference="Rôle du coton sur la filière maïs au Burkina Faso. Économie rurale 341, pages 107 "
                                   "à 119, DOI 10.4000/economierurale.4353"),
    "GOURO_VALL2010": Source(nom="Gouro et Vall, 2010",
                             reference="Restaurer la fertilité des sols et pérenniser les systèmes agropastoraux "
                                       "d'Afrique subsaharienne grâce à la fumure organique. Les dossiers d'Agropolis "
                                       "International 11, pages 23 à 25"),
    "CATTAN2001": Source(nom="Cattan et collègues, 2001",
                         reference="Rendement de l'arachide et du sorgho en rotation sous différents itinéraires "
                                   "techniques au Burkina Faso. Cahiers Agricultures 10, pages 159 à 172"),
    "FAO1995_SORGHO_MIL": Source(nom="FAO, 1995", reference="Sorghum and millets in human nutrition. FAO Food and "
                                                             "Nutrition Series 27, https://www.fao.org/4/t0818e/T0818E01.htm"),
    "GNAPI2025": Source(nom="Gnapi et collègues, CNRA, 2025",
                        reference="Scholars Academic Journal of Biosciences 13, 12, pages 1574 à 1580, DOI "
                                  "10.36347/sajb.2025.v13i12.002"),
    "EPPO_MSV": Source(nom="EPPO Global Database, Maize streak virus en Côte d'Ivoire",
                       reference="https://gd.eppo.int/taxon/MSV000/distribution/CI, présent d'après une information "
                                 "de 1993, sans détail, consulté le 14 novembre 2026"),
    "EPPO_XANTHO": Source(nom="EPPO Global Database, Xanthomonas citri pv. malvacearum en Côte d'Ivoire",
                          reference="https://gd.eppo.int/taxon/XANTMA/distribution/CI, présent d'après une "
                                    "information de 1996, sans détail, consulté le 14 novembre 2026"),
    "GEDIL2019": Source(nom="Gedil et Menkir, IITA, 2019",
                        reference="An integrated molecular and conventional breeding scheme for enhancing genetic "
                                  "gain in maize in Africa. Frontiers in Plant Science 10, 1430, introduction, DOI "
                                  "10.3389/fpls.2019.01430"),
    "SORO2024": Source(nom="Soro et collègues, Université Nangui Abrogoua, 2024",
                       reference="Amélioration de la production du maïs en Côte d'Ivoire par l'utilisation "
                                 "d'extraits de plantes contre les champignons pathogènes en milieu naturel. "
                                 "International Journal of Advanced Research 12, 4, pages 1228 à 1241, pages 1232 "
                                 "et 1240, https://zenodo.org/records/11384600"),
    "BANKOLE2023": Source(nom="Bankole et collègues, IITA, 2023",
                          reference="Variation in the morphology and effector profiles of Exserohilum turcicum "
                                    "isolates associated with the Northern Corn Leaf Blight of maize in Nigeria. BMC "
                                    "Plant Biology 23, 386, résumé, DOI 10.1186/s12870-023-04385-7"),
    "NWANOSIKE1997": Source(nom="Nwanosike, 1997",
                            reference="Studies on the Alternaria leaf spot of cotton induced by Alternaria "
                                      "macrospora Zimm. Mémoire de master, Ahmadu Bello University, Zaria, Nigeria, "
                                      "résumé, page viii"),
    "SILVIE2024": Source(nom="Silvie et Papierok, 2024",
                         reference="Les arthropodes du cotonnier. Éditions Quæ, ISBN 978-2-7592-4002-9, chapitre 6, "
                                   "section Résistance aux maladies transmises par les insectes"),
}


def source(codes: str) -> Source:
    """Source du contrat pour un code ou plusieurs codes séparés par une virgule et une espace."""
    elements = [SOURCES[code] for code in codes.split(", ")]
    if len(elements) == 1:
        return elements[0]
    return Source(nom=", ".join(e.nom for e in elements), reference=" ; ".join(e.reference for e in elements))
