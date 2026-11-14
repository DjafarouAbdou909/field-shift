// Conversation hors connexion. Tous les textes chiffrés viennent de
// donnees/recommandations.json, calculé par le moteur. Ce fichier n'en calcule aucun.

const fil = document.getElementById("fil");
const choix = document.getElementById("choix");
const etatReseau = document.getElementById("etat-reseau");
const NIVEAUX = { mesure: "Mesuré", calcule: "Calculé", hypothese: "Hypothèse" };
let donnees = null;
let dernierResume = "";
const etat = { lieu: null, priorite: null };
const boutonVoix = document.getElementById("mode-voix");

// Pictogrammes des boutons, pour les personnes qui ne lisent pas.
const ICONES = {
  position: '<path d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z"/>',
  village: '<path d="M3 11 12 4l9 7v9h-6v-5H9v5H3z"/>',
  coton: '<circle cx="8" cy="10" r="3.5"/><circle cx="16" cy="10" r="3.5"/><circle cx="12" cy="6" r="3.5"/><path d="M11 13h2v9h-2z"/>',
  autre: '<circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/>',
  eau: '<path d="M12 2s-7 8-7 13a7 7 0 0 0 14 0c0-5-7-13-7-13z"/>',
  sol: '<path d="M2 18h20v4H2z"/><path d="M12 17V9m0 0c-4 0-6-3-6-6 4 0 6 3 6 6zm0 2c3 0 5-2 5-5-3 0-5 2-5 5z" fill="none" stroke="currentColor" stroke-width="2"/>',
  debouche: '<circle cx="12" cy="12" r="9"/><path d="M12 6v12M9 9h5a2 2 0 0 1 0 4h-4a2 2 0 0 0 0 4h5" fill="none" stroke="var(--bouton)" stroke-width="2"/>',
  pourquoi: '<circle cx="12" cy="12" r="10"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.7v1M12 18v.01" fill="none" stroke="var(--bouton)" stroke-width="2" stroke-linecap="round"/>',
  climat: '<path d="M7 15a5 5 0 1 1 9.6-2H17a3.5 3.5 0 0 1 0 7H7a3.5 3.5 0 0 1 0-7z"/>',
  ecouter: '<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M16 8a5 5 0 0 1 0 8M18.5 5.5a8.5 8.5 0 0 1 0 13" fill="none" stroke="currentColor" stroke-width="2"/>',
  recommencer: '<path d="M12 5V2L7 6l5 4V7a5 5 0 1 1-5 5H5a7 7 0 1 0 7-7z"/>',
  micro: '<path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3z"/><path d="M6 11a6 6 0 0 0 12 0M12 17v4" fill="none" stroke="currentColor" stroke-width="2"/>',
  arreter: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
  envoyer: '<path d="M3 20 21 12 3 4v6l12 2-12 2z"/>',
};

function icone(nom) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = ICONES[nom] || "";
  return svg;
}

// Mode voix. Chaque message est lu à voix haute, et un bouton se touche une fois pour
// entendre son nom, une seconde fois pour le choisir.
let modeVoix = false;
try { modeVoix = localStorage.getItem("modeVoix") === "1"; } catch (e) { /* stockage indisponible */ }

function parler(texte) {
  if (!("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  const voix = new SpeechSynthesisUtterance(texte);
  voix.lang = "fr-FR";
  speechSynthesis.speak(voix);
}

function afficherModeVoix() {
  boutonVoix.setAttribute("aria-pressed", String(modeVoix));
  boutonVoix.title = modeVoix ? "Mode voix activé" : "Activer le mode voix";
}

boutonVoix.addEventListener("click", () => {
  modeVoix = !modeVoix;
  try { localStorage.setItem("modeVoix", modeVoix ? "1" : "0"); } catch (e) { /* stockage indisponible */ }
  afficherModeVoix();
  if (modeVoix) parler("Mode voix activé. Touchez une image une fois pour entendre son nom, deux fois pour la choisir.");
  else if ("speechSynthesis" in window) speechSynthesis.cancel();
});

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
  choix.replaceChildren(...options.map(([libelle, action, nomIcone]) => {
    const bouton = document.createElement("button");
    bouton.type = "button";
    bouton.append(icone(nomIcone), libelle);
    bouton.addEventListener("click", () => {
      if (modeVoix && !bouton.classList.contains("entendu")) {
        choix.querySelectorAll(".entendu").forEach((b) => b.classList.remove("entendu"));
        bouton.classList.add("entendu");
        parler(libelle);
        return;
      }
      bulle(libelle, "agri");
      choix.replaceChildren();
      action();
    });
    return bouton;
  }));
}

function boutonRelire(element, texte) {
  const relire = document.createElement("button");
  relire.type = "button";
  relire.className = "relire";
  relire.title = "Écouter ce message";
  relire.append(icone("ecouter"));
  relire.addEventListener("click", () => parler(texte));
  element.appendChild(relire);
}

function dire(texte, ensuite) {
  const saisie = bulle("…", "saisie");
  setTimeout(() => {
    saisie.remove();
    const b = bulle(texte);
    boutonRelire(b, texte);
    if (modeVoix) parler(texte);
    if (ensuite) ensuite(b);
  }, 450);
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
  const options = [["Utiliser ma position", localiser, "position"]];
  for (const [id, lieu] of Object.entries(donnees.lieux)) options.push([lieu.nom, () => choisirLieu(id), "village"]);
  options.push(["Message vocal pour mon conseiller", enregistrer, "micro"]);
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
    ["Réessayer", localiser, "position"],
    ...Object.entries(donnees.lieux).map(([id, l]) => [l.nom, () => choisirLieu(id), "village"]),
  ]));
}

function choisirLieu(id) {
  etat.lieu = id;
  dire(`Zone de ${donnees.lieux[id].nom}. Que cultivez-vous en ce moment ?`, () => proposer([
    ["Coton puis maïs", demanderPriorite, "coton"],
    ["Autre chose", () => dire("Pour l'instant, je ne compare que des rotations à partir de coton puis maïs. "
      + "Laissez un message vocal à votre conseiller ANADER pour votre cas.", () => proposer([
      ["Message vocal pour mon conseiller", enregistrer, "micro"], ["Recommencer", accueil, "recommencer"]]))],
  ]));
}

function demanderPriorite() {
  dire("Qu'est-ce qui compte le plus pour vous ?", () => proposer(
    Object.entries(donnees.priorites).map(([id, libelle]) => [libelle, () => resultat(id), id])));
}

function resultat(priorite) {
  etat.priorite = priorite;
  const r = donnees.lieux[etat.lieu].resultats[priorite];
  dernierResume = r.resume;
  dire(r.resume, actionsResultat);
}

function actionsResultat() {
  proposer([
    ["Pourquoi ?", pourquoi, "pourquoi"],
    ["Le climat de ma zone", climat, "climat"],
    ["Écouter", ecouter, "ecouter"],
    ["Message vocal pour mon conseiller", enregistrer, "micro"],
    ["Recommencer", accueil, "recommencer"],
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

// Notes vocales. Elles sont enregistrées et gardées sur le téléphone, sans réseau.
// L'application ne les interprète pas, elles sont destinées au conseiller.
function base() {
  return new Promise((resoudre, rejeter) => {
    const ouverture = indexedDB.open("notes-vocales", 1);
    ouverture.onupgradeneeded = () => ouverture.result.createObjectStore("notes", { autoIncrement: true });
    ouverture.onsuccess = () => resoudre(ouverture.result);
    ouverture.onerror = () => rejeter(ouverture.error);
  });
}

async function garderNote(note) {
  const db = await base();
  await new Promise((resoudre, rejeter) => {
    const transaction = db.transaction("notes", "readwrite");
    transaction.objectStore("notes").add(note);
    transaction.oncomplete = resoudre;
    transaction.onerror = () => rejeter(transaction.error);
  });
}

function suite() {
  if (etat.priorite) actionsResultat(); else demanderLieu();
}

async function enregistrer() {
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    dire("L'enregistrement de la voix n'est pas disponible sur ce téléphone.", suite);
    return;
  }
  let flux;
  try {
    flux = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (e) {
    dire("Le micro est refusé. Autorisez-le dans les réglages du téléphone, puis réessayez.", suite);
    return;
  }
  const morceaux = [];
  const enregistreur = new MediaRecorder(flux);
  enregistreur.ondataavailable = (e) => { if (e.data.size) morceaux.push(e.data); };
  enregistreur.onstop = async () => {
    flux.getTracks().forEach((piste) => piste.stop());
    const note = new Blob(morceaux, { type: enregistreur.mimeType || "audio/webm" });
    const lecteur = document.createElement("audio");
    lecteur.controls = true;
    lecteur.src = URL.createObjectURL(note);
    bulle("", "agri").appendChild(lecteur);
    try {
      await garderNote({ date: new Date().toISOString(), lieu: etat.lieu, audio: note });
    } catch (e) {
      dire("Le message n'a pas pu être gardé sur le téléphone.", suite);
      return;
    }
    dire("Votre message est gardé sur le téléphone, même sans réseau. Vous pouvez l'envoyer à votre "
      + "conseiller dès que vous avez du réseau, ou le lui faire écouter.", () => proposer([
      ["Envoyer à mon conseiller", () => partager(note), "envoyer"],
      ["Continuer", suite, "recommencer"],
    ]));
  };
  enregistreur.start();
  dire("Je vous écoute. Parlez dans votre langue, puis touchez le carré pour arrêter.", () => proposer([
    ["Arrêter l'enregistrement", () => enregistreur.stop(), "arreter"],
  ]));
}

async function partager(note) {
  const extension = note.type.includes("ogg") ? "ogg" : note.type.includes("mp4") ? "m4a" : "webm";
  const fichier = new File([note], `message-vocal.${extension}`, { type: note.type });
  if (navigator.canShare && navigator.canShare({ files: [fichier] })) {
    try {
      await navigator.share({ files: [fichier], title: "Message vocal pour mon conseiller" });
    } catch (e) { /* partage annulé */ }
    suite();
  } else {
    dire("Le partage n'est pas disponible sur ce téléphone. Faites écouter le message à votre conseiller.", suite);
  }
}

function afficherReseau() {
  etatReseau.textContent = navigator.onLine
    ? "Connexion disponible, tout fonctionne aussi sans"
    : "Hors connexion, tout fonctionne";
}

async function demarrer() {
  afficherModeVoix();
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
