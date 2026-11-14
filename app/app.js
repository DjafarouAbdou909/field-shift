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

function localiser() {
  if (!navigator.geolocation) { dire("La position n'est pas disponible sur ce téléphone. Choisissez votre zone.", demanderLieu); return; }
  dire("Je cherche votre position avec le GPS du téléphone, qui fonctionne sans connexion.");
  navigator.geolocation.getCurrentPosition((p) => {
    const ici = { lat: p.coords.latitude, lon: p.coords.longitude };
    const [id, km] = Object.entries(donnees.lieux)
      .map(([cle, l]) => [cle, distanceKm(ici, l)]).sort((a, b) => a[1] - b[1])[0];
    if (km > donnees.rayon_couverture_km) {
      dire(`Votre champ est à plus de ${donnees.rayon_couverture_km} km des zones que je connais. `
        + "Je ne peux pas encore vous conseiller pour votre zone. Vous pouvez consulter une zone proche.", demanderLieu);
    } else {
      choisirLieu(id);
    }
  }, () => dire("Je n'ai pas pu obtenir votre position. Choisissez votre zone.", demanderLieu),
  { enableHighAccuracy: true, timeout: 20000 });
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
  const lieu = donnees.lieux[etat.lieu];
  const r = lieu.resultats[priorite];
  const lignes = r.strategies.map((s) => {
    const egal = r.strategies.filter((t) => t.rang === s.rang).length > 1 ? ", à égalité" : "";
    return `${s.rang}${egal}. ${s.nom}${s.actuelle ? ", votre rotation actuelle" : ""}`;
  });
  dernierResume = `Pour ${lieu.nom}, avec la priorité ${donnees.priorites[priorite].toLowerCase()}, `
    + `voici les rotations comparées.\n${lignes.join("\n")}\n${r.stabilite}\n${donnees.avertissement}`;
  dire(dernierResume, actionsResultat);
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
