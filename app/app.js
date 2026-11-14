// Conversation hors connexion. Tous les textes chiffrés viennent de
// donnees/recommandations.json, calculé par le moteur. Ce fichier n'en calcule aucun.

const fil = document.getElementById("fil");
const choix = document.getElementById("choix");
const etatReseau = document.getElementById("etat-reseau");
const NIVEAUX = { mesure: "Mesuré", calcule: "Calculé", hypothese: "Hypothèse" };
let donnees = null;
let dernierResume = "";
const etat = { lieu: null, priorite: null };

function bulle(texte, classe = "outil") {
  const element = document.createElement("div");
  element.className = `bulle ${classe}`;
  element.textContent = texte;
  fil.appendChild(element);
  fil.scrollTop = fil.scrollHeight;
  return element;
}

function preuve(parent, element) {
  const bloc = document.createElement("div");
  bloc.className = "preuve";
  const niveau = document.createElement("span");
  niveau.className = "niveau";
  niveau.textContent = NIVEAUX[element.niveau] || element.niveau;
  bloc.append(niveau, element.texte);
  const complement = [element.detail, element.source && `Source, ${element.source}.`].filter(Boolean).join(" ");
  if (complement) {
    const discret = document.createElement("div");
    discret.className = "discret";
    discret.textContent = complement;
    bloc.appendChild(discret);
  }
  parent.appendChild(bloc);
}

function proposer(options) {
  choix.replaceChildren(...options.map(([libelle, action]) => {
    const bouton = document.createElement("button");
    bouton.type = "button";
    bouton.textContent = libelle;
    bouton.addEventListener("click", () => { bulle(libelle, "agri"); choix.replaceChildren(); action(); });
    return bouton;
  }));
}

function dire(texte, ensuite) {
  const saisie = bulle("…", "saisie");
  setTimeout(() => { saisie.remove(); const b = bulle(texte); if (ensuite) ensuite(b); }, 450);
}

function distanceKm(a, b) {
  const r = (x) => (x * Math.PI) / 180;
  const h = Math.sin(r(b.lat - a.lat) / 2) ** 2
    + Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(r(b.lon - a.lon) / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

function accueil() {
  etat.lieu = etat.priorite = null;
  dire("Bonjour. Je compare des rotations de cultures pour votre zone, à partir de données satellites "
    + "de la NASA sur le climat de " + donnees.periode + ".\n"
    + "Je fonctionne sans connexion, et aucune donnée ne quitte votre téléphone.\n"
    + "Où se trouve votre champ ?", demanderLieu);
}

function demanderLieu() {
  const options = [["Utiliser ma position", localiser]];
  for (const [id, lieu] of Object.entries(donnees.lieux)) options.push([lieu.nom, () => choisirLieu(id)]);
  proposer(options);
}

// Sans connexion, le GPS ne reçoit pas l'aide du réseau et sa première position peut
// prendre une à plusieurs minutes. La position est donc suivie jusqu'à atteindre la
// précision voulue, et la meilleure obtenue est gardée.
const PRECISION_VISEE_M = 100;
const DUREE_MAX_MS = 120000;
const MESSAGES_POSITION = {
  1: "La localisation est refusée. Autorisez-la dans les réglages du téléphone, puis réessayez.",
  2: "Position introuvable. Activez la localisation du téléphone, de préférence en extérieur, puis réessayez.",
  3: "Le GPS n'a pas trouvé de position à temps. Mettez-vous à découvert, puis réessayez.",
};

function chercherPosition(precise) {
  return new Promise((resoudre, rejeter) => {
    let meilleure = null;
    const fin = (position) => {
      navigator.geolocation.clearWatch(suivi);
      clearTimeout(minuteur);
      position ? resoudre(position) : rejeter({ code: 3 });
    };
    const suivi = navigator.geolocation.watchPosition((p) => {
      if (!meilleure || p.coords.accuracy < meilleure.coords.accuracy) meilleure = p;
      if (p.coords.accuracy <= PRECISION_VISEE_M) fin(meilleure);
    }, (erreur) => {
      if (erreur.code === 1 || !meilleure) { navigator.geolocation.clearWatch(suivi); clearTimeout(minuteur); rejeter(erreur); }
    }, { enableHighAccuracy: precise, maximumAge: 0, timeout: DUREE_MAX_MS });
    const minuteur = setTimeout(() => fin(meilleure), DUREE_MAX_MS);
  });
}

async function localiser() {
  if (!navigator.geolocation) {
    dire("La localisation n'est pas disponible sur ce téléphone. Choisissez votre zone.", demanderLieu);
    return;
  }
  dire("Je cherche votre position avec le GPS du téléphone, qui fonctionne sans connexion. "
    + "Sans réseau, cela peut prendre une ou deux minutes. Restez de préférence à découvert.");
  let position;
  try {
    position = await chercherPosition(true);
  } catch (erreur) {
    if (erreur.code === 1) { echecPosition(erreur.code); return; }
    try { position = await chercherPosition(false); } catch (seconde) { echecPosition(seconde.code); return; }
  }
  const ici = { lat: position.coords.latitude, lon: position.coords.longitude };
  const precision = Math.round(position.coords.accuracy);
  const [id, km] = Object.entries(donnees.lieux)
    .map(([cle, l]) => [cle, distanceKm(ici, l)]).sort((a, b) => a[1] - b[1])[0];
  const coordonnees = `${ici.lat.toFixed(5)}, ${ici.lon.toFixed(5)}`;
  const precisionTexte = precision <= 1000 ? `à ${precision} m près` : `à environ ${Math.round(precision / 1000)} km près`;
  if (km > donnees.rayon_couverture_km) {
    dire(`Position trouvée ${precisionTexte}, ${coordonnees}. Votre champ est à ${Math.round(km)} km de `
      + `${donnees.lieux[id].nom}, au-delà des ${donnees.rayon_couverture_km} km que je couvre. `
      + "Je ne peux pas encore vous conseiller pour votre zone.", demanderLieu);
    return;
  }
  dire(`Position trouvée ${precisionTexte}, ${coordonnees}, à ${Math.round(km)} km de ${donnees.lieux[id].nom}.`,
    () => choisirLieu(id));
}

function echecPosition(code) {
  dire(MESSAGES_POSITION[code] || MESSAGES_POSITION[2], () => proposer([
    ["Réessayer", localiser],
    ...Object.entries(donnees.lieux).map(([id, l]) => [l.nom, () => choisirLieu(id)]),
  ]));
}

function choisirLieu(id) {
  etat.lieu = id;
  dire(`Zone de ${donnees.lieux[id].nom}. Que cultivez-vous en ce moment ?`, () => proposer([
    ["Coton puis maïs", demanderPriorite],
    ["Autre chose", () => dire("Pour l'instant, je ne compare que des rotations à partir de coton puis maïs. "
      + "Votre conseiller ANADER pourra vous aider pour votre cas.", () => proposer([["Recommencer", accueil]]))],
  ]));
}

function demanderPriorite() {
  dire("Qu'est-ce qui compte le plus pour vous ?", () => proposer(
    Object.entries(donnees.priorites).map(([id, libelle]) => [libelle, () => resultat(id)])));
}

function resultat(priorite) {
  etat.priorite = priorite;
  const r = donnees.lieux[etat.lieu].resultats[priorite];
  dernierResume = r.resume;
  dire(r.resume, actionsResultat);
}

function actionsResultat() {
  proposer([
    ["Pourquoi ?", pourquoi],
    ["Le climat de ma zone", climat],
    ["Écouter", ecouter],
    ["Recommencer", accueil],
  ]);
}

function pourquoi() {
  const r = donnees.lieux[etat.lieu].resultats[etat.priorite];
  let delai = 0;
  for (const s of r.strategies) {
    setTimeout(() => dire(`${s.nom}`, (b) => s.explications.forEach((e) => preuve(b, e))), delai);
    delai += 500;
  }
  setTimeout(actionsResultat, delai + 500);
}

function climat() {
  const lieu = donnees.lieux[etat.lieu];
  dire(`Climat de ${lieu.nom} de ${donnees.periode}.`, (b) => {
    lieu.indicateurs.forEach((e) => preuve(b, e));
    actionsResultat();
  });
}

function ecouter() {
  const r = donnees.lieux[etat.lieu].resultats[etat.priorite];
  if (r.audio) {
    new Audio(r.audio).play().catch(() => dire("La lecture de l'enregistrement a échoué.", actionsResultat));
    actionsResultat();
    return;
  }
  if (!("speechSynthesis" in window)) {
    dire("La lecture à voix haute n'est pas disponible sur ce téléphone.", actionsResultat);
    return;
  }
  const voix = new SpeechSynthesisUtterance(dernierResume);
  voix.lang = "fr-FR";
  voix.onerror = () => dire("La lecture à voix haute a échoué. Une voix française doit être installée sur le téléphone.", actionsResultat);
  speechSynthesis.cancel();
  speechSynthesis.speak(voix);
  actionsResultat();
}

function afficherReseau() {
  etatReseau.textContent = navigator.onLine
    ? "Connexion disponible, tout fonctionne aussi sans"
    : "Hors connexion, tout fonctionne";
}

async function demarrer() {
  afficherReseau();
  addEventListener("online", afficherReseau);
  addEventListener("offline", afficherReseau);
  if ("serviceWorker" in navigator) {
    try { await navigator.serviceWorker.register("sw.js"); } catch (e) { /* le site reste utilisable en ligne */ }
  }
  try {
    const reponse = await fetch("donnees/recommandations.json");
    donnees = await reponse.json();
  } catch (e) {
    bulle("Les données ne sont pas encore installées. Ouvrez l'application une première fois avec une connexion.");
    return;
  }
  accueil();
}

demarrer();
