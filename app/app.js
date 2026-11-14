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

// Mode voix, pour les personnes qui ne lisent pas. Chaque question est lue, puis chaque
// réponse possible avec la couleur de son bouton. Un seul toucher choisit la réponse,
// et l'application confirme à voix haute ce qui a été choisi.
let modeVoix = false;
let dernierTexteDit = "";
let aConfirmer = "";
const COULEURS = [
  ["vert", "#2e7d32", "#ffffff"], ["orange", "#e65100", "#ffffff"], ["bleu", "#1565c0", "#ffffff"],
  ["violet", "#6a1b9a", "#ffffff"], ["rouge", "#c62828", "#ffffff"], ["marron", "#6d4c41", "#ffffff"],
  ["jaune", "#f9a825", "#1d1814"],
];

const SANS_VOIX = "Aucune voix française n'est installée sur ce téléphone. Installez-la dans les réglages, "
  + "rubrique synthèse vocale, ou faites enregistrer les messages par votre équipe.";

function voixFrancaise() {
  const voix = speechSynthesis.getVoices();
  return { connues: voix.length > 0, francaise: voix.find((v) => v.lang.toLowerCase().startsWith("fr")) };
}

// Retourne faux si le téléphone n'a certainement aucune voix française.
function parler(texte) {
  if (!("speechSynthesis" in window)) return false;
  const { connues, francaise } = voixFrancaise();
  if (connues && !francaise) return false;
  speechSynthesis.cancel();
  window.dernierePhraseLue = texte;
  const enonce = new SpeechSynthesisUtterance(texte);
  enonce.lang = "fr-FR";
  if (francaise) enonce.voice = francaise;
  speechSynthesis.speak(enonce);
  return true;
}

function afficherModeVoix() {
  boutonVoix.setAttribute("aria-pressed", String(modeVoix));
  boutonVoix.title = modeVoix ? "Mode voix activé" : "Activer le mode voix";
}

boutonVoix.addEventListener("click", () => {
  modeVoix = !modeVoix;
  try { localStorage.setItem("modeVoix", modeVoix ? "1" : "0"); } catch (e) { /* stockage indisponible */ }
  afficherModeVoix();
  if (modeVoix) parler("Mode voix activé. Écoutez les choix, puis touchez le bouton de la bonne couleur.");
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

function annonce(options) {
  return options.map(([libelle], i) => `${libelle}, touchez le bouton ${COULEURS[i % COULEURS.length][0]}.`).join(" ");
}

function proposer(options) {
  const boutons = options.map(([libelle, action, nomIcone], i) => {
    const [, fond, texte] = COULEURS[i % COULEURS.length];
    const bouton = document.createElement("button");
    bouton.type = "button";
    bouton.className = "colore";
    bouton.style.background = fond;
    bouton.style.color = texte;
    bouton.style.borderColor = fond;
    bouton.append(icone(nomIcone), libelle);
    bouton.addEventListener("click", () => {
      bulle(libelle, "agri");
      choix.replaceChildren();
      aConfirmer = modeVoix ? `Vous avez choisi ${libelle}. ` : "";
      action();
    });
    return bouton;
  });
  if (modeVoix) {
    const reecouter = document.createElement("button");
    reecouter.type = "button";
    reecouter.className = "reecouter";
    reecouter.append(icone("ecouter"), "Réécouter");
    reecouter.addEventListener("click", () => parler(`${dernierTexteDit}\n${annonce(options)}`));
    boutons.push(reecouter);
    parler(`${dernierTexteDit}\n${annonce(options)}`);
  }
  choix.replaceChildren(...boutons);
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
    dernierTexteDit = aConfirmer + texte;
    aConfirmer = "";
    if (modeVoix) parler(dernierTexteDit);
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
    + "Où se trouve votre champ ?", (b) => {
    const credit = document.createElement("div");
    credit.className = "discret";
    credit.textContent = "Sources, NASA POWER et GPM IMERG, FAO 56. Noms de lieux, GeoNames, licence CC BY 4.0.";
    b.appendChild(credit);
    demanderLieu();
  });
}

function demanderLieu() {
  const options = [["Utiliser ma position", localiser, "position"]];
  for (const [id, lieu] of Object.entries(donnees.lieux)) options.push([lieu.nom, () => choisirLieu(id), "village"]);
  options.push(["Message vocal pour mon conseiller", enregistrer, "micro"]);
  options.push(["Mes messages vocaux", mesNotes, "ecouter"]);
  if (ficheDiagnostic) options.push(["Photo d'une feuille de maïs", photographier, "pourquoi"]);
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
  if (!window.isSecureContext) { dire(MESSAGE_ADRESSE, demanderLieu); return; }
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
    if (erreur.code === 1) { echecPosition(erreur); return; }
    try { position = await chercherPosition(false); } catch (seconde) { echecPosition(seconde); return; }
  }
  const ici = { lat: position.coords.latitude, lon: position.coords.longitude };
  const precision = Math.round(position.coords.accuracy);
  const [id, km] = Object.entries(donnees.lieux)
    .map(([cle, l]) => [cle, distanceKm(ici, l)]).sort((a, b) => a[1] - b[1])[0];
  const ou = texteLieu(await nommer(ici), precision);
  const zones = Object.values(donnees.lieux).map((l) => l.nom).join(" et de ");
  if (km > donnees.rayon_couverture_km) {
    dire(`${ou} Je ne connais pas encore cette zone. Pour l'instant, je conseille seulement les champs `
      + `autour de ${zones}. Choisissez une zone pour voir ses conseils.`, demanderLieu);
    return;
  }
  dire(`${ou} Vous êtes dans la zone de ${donnees.lieux[id].nom}.`, () => choisirLieu(id));
}

// Nom de la localité la plus proche, d'après la liste GeoNames embarquée dans l'application.
let localites = null;

async function chargerLocalites() {
  if (localites) return localites;
  const enCache = window.caches ? await caches.match("donnees/localites.json") : null;
  localites = await (enCache || await fetch("donnees/localites.json")).json();
  return localites;
}

async function nommer(ici) {
  try {
    const { lieux } = await chargerLocalites();
    let meilleur = null;
    for (const [nom, lat, lon, region] of lieux) {
      const km = distanceKm(ici, { lat, lon });
      if (!meilleur || km < meilleur.km) meilleur = { nom, region, km };
    }
    return meilleur;
  } catch (e) {
    return null;
  }
}

function elision(prefixe, nom) {
  return /^[aeiouyéèêâîôûh]/i.test(nom) ? `${prefixe.slice(0, -1)}'${nom}` : `${prefixe} ${nom}`;
}

function texteLieu(lieu, precisionM) {
  if (!lieu) return "J'ai bien trouvé votre position.";
  const region = lieu.region && lieu.region !== lieu.nom ? `, ${lieu.region}` : "";
  const vers = precisionM > 2000 ? "environ " : "";
  if (lieu.km < 1.5) return `Vous êtes ${vers}à ${lieu.nom}${region}.`;
  return `Vous êtes ${vers}${elision("près de", lieu.nom)}${region}.`;
}

function echecPosition(erreur) {
  const technique = `Code ${erreur.code || "inconnu"}${erreur.message ? `, ${erreur.message}` : ""}.`;
  dire(`${MESSAGES_POSITION[erreur.code] || MESSAGES_POSITION[2]}\n${technique}`, () => proposer([
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
      ["Message vocal pour mon conseiller", enregistrer, "micro"], ["Recommencer", accueil, "recommencer"]]), "autre")],
  ]));
}

function demanderPriorite() {
  dire("Qu'est-ce qui compte le plus pour vous ?", () => proposer(
    Object.entries(donnees.priorites).map(([id, libelle]) => [libelle, () => resultat(id), id])));
}

function resultat(priorite) {
  etat.priorite = priorite;
  const r = donnees.lieux[etat.lieu].resultats[priorite];
  const alerte = donnees.lieux[etat.lieu].alerte;
  dernierResume = `${r.resume}\n${alerte}`;
  dire(r.resume, () => dire(alerte, actionsResultat));
}

function actionsResultat() {
  proposer([
    ["Pourquoi ?", pourquoi, "pourquoi"],
    ["Le climat de ma zone", climat, "climat"],
    ["Écouter", ecouter, "ecouter"],
    ["Envoyer le conseil à mon conseiller", () => partager(null), "envoyer"],
    ["Message vocal pour mon conseiller", enregistrer, "micro"],
    ["Mes messages vocaux", mesNotes, "ecouter"],
    ...(ficheDiagnostic ? [["Photo d'une feuille de maïs", photographier, "pourquoi"]] : []),
    ["Recommencer", accueil, "recommencer"],
  ]);
}

function pourquoi() {
  const r = donnees.lieux[etat.lieu].resultats[etat.priorite];
  bulle(r.detail);
  let delai = 300;
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
  if (!parler(dernierResume)) { dire(SANS_VOIX, actionsResultat); return; }
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

// Le navigateur bloque le GPS et le micro sur une adresse non sécurisée, sans même
// afficher la demande d'autorisation. Seules les adresses https et localhost sont sûres.
const MESSAGE_ADRESSE = "Cette adresse n'est pas sécurisée, et le navigateur bloque la position et le micro "
  + "sans demander d'autorisation. Ouvrez l'application par une adresse https, ou par localhost sur un ordinateur.";

function suite() {
  if (etat.priorite) actionsResultat(); else demanderLieu();
}

async function enregistrer() {
  if (!window.isSecureContext) { dire(MESSAGE_ADRESSE, suite); return; }
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
  const format = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus", "audio/webm"].find((f) =>
    MediaRecorder.isTypeSupported(f) && document.createElement("audio").canPlayType(f.split(";")[0]) !== "");
  const enregistreur = format ? new MediaRecorder(flux, { mimeType: format }) : new MediaRecorder(flux);
  enregistreur.ondataavailable = (e) => { if (e.data.size) morceaux.push(e.data); };
  enregistreur.onstop = async () => {
    flux.getTracks().forEach((piste) => piste.stop());
    const note = new Blob(morceaux, { type: enregistreur.mimeType || "audio/webm" });
    lecteurNote(bulle("Mon message vocal", "agri"), note);
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

// Lecture par un bouton, qui affiche l'erreur exacte si le téléphone ne peut pas lire la note.
function lecteurNote(parent, note) {
  const bouton = document.createElement("button");
  bouton.type = "button";
  bouton.className = "lire-note";
  bouton.append(icone("ecouter"), "Écouter");
  bouton.addEventListener("click", () => {
    const audio = new Audio(URL.createObjectURL(note));
    audio.onerror = () => dire(`Ce téléphone ne peut pas lire ce message, format ${note.type || "inconnu"}, `
      + `erreur ${audio.error ? audio.error.code : "inconnue"}. Vous pouvez l'envoyer à votre conseiller.`);
    audio.play().catch((e) => dire(`La lecture n'a pas démarré, ${e.name}. Touchez à nouveau Écouter.`));
  });
  parent.appendChild(document.createElement("br"));
  parent.appendChild(bouton);
}

async function lireNotes() {
  const db = await base();
  return new Promise((resoudre, rejeter) => {
    const requete = db.transaction("notes").objectStore("notes").getAll();
    requete.onsuccess = () => resoudre(requete.result);
    requete.onerror = () => rejeter(requete.error);
  });
}

async function mesNotes() {
  let notes = [];
  try { notes = await lireNotes(); } catch (e) { /* base indisponible */ }
  if (!notes.length) { dire("Vous n'avez encore aucun message vocal.", suite); return; }
  dire(`Vous avez ${notes.length} message${notes.length > 1 ? "s" : ""} vocal${notes.length > 1 ? "aux" : ""}.`, () => {
    notes.forEach((n) => {
      const quand = new Date(n.date).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
      lecteurNote(bulle(`Message du ${quand}`, "agri"), n.audio);
    });
    proposer([["Envoyer le dernier à mon conseiller", () => partager(notes[notes.length - 1].audio), "envoyer"],
              ["Continuer", suite, "recommencer"]]);
  });
}

// Résumé de l'échange, envoyé au conseiller avec l'accord de l'agriculteur.
function resumeEchange() {
  const lignes = ["Message envoyé depuis l'application Conseil Rotation."];
  if (etat.lieu) lignes.push(`Zone, ${donnees.lieux[etat.lieu].nom}.`);
  if (etat.priorite) {
    lignes.push(`Priorité, ${donnees.priorites[etat.priorite].toLowerCase()}.`);
    lignes.push(`Conseil reçu.\n${donnees.lieux[etat.lieu].resultats[etat.priorite].resume}`);
  }
  return lignes.join("\n");
}

// Chrome sur Android ne partage un fichier audio que si son extension et son type sont reconnus.
const EXTENSIONS_AUDIO = { "audio/webm": "weba", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/mpeg": "mp3" };

function fichierAudio(note) {
  const type = (note.type || "audio/webm").split(";")[0];
  return new File([note], `message-vocal.${EXTENSIONS_AUDIO[type] || "weba"}`, { type });
}

function telechargerNote(fichier) {
  const lien = document.createElement("a");
  lien.href = URL.createObjectURL(fichier);
  lien.download = fichier.name;
  document.body.appendChild(lien);
  lien.click();
  lien.remove();
}

async function partager(note) {
  const texte = resumeEchange();
  const fichier = note ? fichierAudio(note) : null;
  try {
    if (fichier && navigator.canShare && navigator.canShare({ files: [fichier] })) {
      await navigator.share({ files: [fichier], text: texte, title: "Message pour mon conseiller" });
      suite();
      return;
    }
    if (navigator.share) {
      await navigator.share({ text: texte, title: "Message pour mon conseiller" });
      if (fichier) {
        telechargerNote(fichier);
        dire("Le résumé est envoyé. Le message vocal est enregistré dans les téléchargements du téléphone. "
          + "Envoyez-le aussi à votre conseiller, par exemple par WhatsApp.", suite);
        return;
      }
      suite();
      return;
    }
  } catch (e) {
    if (e.name === "AbortError") { suite(); return; }
  }
  if (fichier) telechargerNote(fichier);
  dire("Le partage direct n'est pas disponible sur ce téléphone. "
    + (fichier ? "Le message vocal est enregistré dans les téléchargements. " : "")
    + "Envoyez-le à votre conseiller par WhatsApp, ou faites-lui écouter.", suite);
}

// Vrai quand l'application et ses recommandations sont dans le cache du téléphone.
let pretHorsLigne = false;

async function verifierHorsLigne() {
  if (!("serviceWorker" in navigator) || !window.caches) return;
  await navigator.serviceWorker.ready;
  for (const cle of await caches.keys()) {
    const cache = await caches.open(cle);
    if (await cache.match("donnees/recommandations.json") && await cache.match("app.js")) pretHorsLigne = true;
  }
  afficherReseau();
}

// Diagnostic d'une photo de feuille de maïs, sans connexion. Le modèle et son moteur
// d'exécution sont dans app/diagnostic. Sans eux, l'option n'est pas proposée.
const DOSSIER_DIAGNOSTIC = "diagnostic/";
let ficheDiagnostic;
let sessionDiagnostic = null;
const MESSAGES_DIAGNOSTIC = {
  saine: "Je ne reconnais sur cette feuille aucune des maladies que je connais. Si la plante va mal, "
    + "montrez-la à votre conseiller ANADER.",
  striure: "Maladie possible, la striure du maïs. À faire confirmer par votre conseiller ANADER. "
    + "Je ne propose aucun traitement.",
  helminthosporiose_nord: "Maladie possible, l'helminthosporiose du maïs. À faire confirmer par votre "
    + "conseiller ANADER. Je ne propose aucun traitement.",
  pas_de_feuille: "Je ne vois pas de feuille sur cette photo. Prenez en photo une seule feuille de maïs, de près, "
    + "à la lumière du jour.",
  inconnu: "Je ne reconnais pas bien cette photo. Prenez une photo nette d'une seule feuille de maïs, à la "
    + "lumière du jour, ou montrez la plante à votre conseiller ANADER.",
};

async function chargerFicheDiagnostic() {
  if (ficheDiagnostic !== undefined) return ficheDiagnostic;
  try {
    const enCache = window.caches ? await caches.match(DOSSIER_DIAGNOSTIC + "modele.json") : null;
    const reponse = enCache || await fetch(DOSSIER_DIAGNOSTIC + "modele.json");
    ficheDiagnostic = reponse.ok ? await reponse.json() : null;
  } catch (e) {
    ficheDiagnostic = null;
  }
  return ficheDiagnostic;
}

function chargerScript(adresse) {
  return new Promise((resoudre, rejeter) => {
    const script = document.createElement("script");
    script.src = adresse;
    script.onload = resoudre;
    script.onerror = rejeter;
    document.head.appendChild(script);
  });
}

async function session() {
  if (sessionDiagnostic) return sessionDiagnostic;
  if (!window.ort) await chargerScript(DOSSIER_DIAGNOSTIC + "ort.wasm.min.js");
  ort.env.wasm.wasmPaths = new URL(DOSSIER_DIAGNOSTIC, location.href).href;
  ort.env.wasm.numThreads = 1;
  sessionDiagnostic = await ort.InferenceSession.create(DOSSIER_DIAGNOSTIC + "modele.onnx",
    { executionProviders: ["wasm"] });
  return sessionDiagnostic;
}

// Le modèle n'a appris que sur des feuilles et peut se tromper avec assurance sur autre chose,
// un mur ou le sol par exemple. Ce contrôle, ajouté après les tests de fiabilité et non mesuré
// par eux, refuse une photo où moins de 15 % des pixels ont une teinte de végétation.
const PART_VEGETATION_MIN = 0.15;

function partVegetation(pixels) {
  let vegetation = 0;
  for (let i = 0; i < pixels.length; i += 4) {
    const r = pixels[i], g = pixels[i + 1], b = pixels[i + 2];
    if (g >= 0.9 * r && g > b + 10) vegetation++;
  }
  return vegetation / (pixels.length / 4);
}

// Même préparation que l'évaluation de l'entraînement, petit côté à 256, centre de 224, normalisation.
function tenseurImage(image, fiche) {
  const echelle = fiche.redimension / Math.min(image.width, image.height);
  const largeur = Math.round(image.width * echelle), hauteur = Math.round(image.height * echelle);
  const canevas = document.createElement("canvas");
  canevas.width = canevas.height = fiche.taille;
  const contexte = canevas.getContext("2d");
  contexte.drawImage(image, (fiche.taille - largeur) / 2, (fiche.taille - hauteur) / 2, largeur, hauteur);
  const pixels = contexte.getImageData(0, 0, fiche.taille, fiche.taille).data;
  if (partVegetation(pixels) < PART_VEGETATION_MIN) return null;
  const n = fiche.taille * fiche.taille;
  const donneesTenseur = new Float32Array(3 * n);
  for (let i = 0; i < n; i++) {
    for (let c = 0; c < 3; c++) {
      donneesTenseur[c * n + i] = (pixels[4 * i + c] / 255 - fiche.moyenne[c]) / fiche.ecart_type[c];
    }
  }
  return new ort.Tensor("float32", donneesTenseur, [1, 3, fiche.taille, fiche.taille]);
}

// Fiabilité mesurée lors de l'entraînement, lue dans la fiche du modèle, jamais écrite ici.
function detailFiabilite(fiche, classe) {
  const f = fiche.fiabilite || {};
  const sur100 = (x) => Math.round(100 * x);
  const lignes = [];
  if (classe === "striure" && f.test_independant_striure) {
    lignes.push(`Testé sur ${f.test_independant_striure.images} photos du Ghana, un pays que je n'ai pas vu en apprenant. `
      + `Quand je dis striure, j'ai raison ${sur100(f.test_independant_striure.precision)} fois sur 100.`);
  }
  if (classe === "saine" && f.test_independant_saine) {
    lignes.push(`Au Ghana, quand je ne reconnais aucune maladie, j'ai raison ${sur100(f.test_independant_saine.precision)} `
      + "fois sur 100. Mais je réponds souvent que je ne sais pas.");
  }
  if (classe === "helminthosporiose_nord") {
    lignes.push("Cette maladie n'a été testée que sur des photos de la même source que mon apprentissage, en Ouganda. "
      + "Ma fiabilité réelle est inconnue.");
  }
  const necrose = f.hors_liste_necrose_letale;
  if (necrose && classe !== "inconnu" && classe !== "saine") {
    lignes.push(`Je confonds la nécrose létale du maïs avec une maladie connue ${sur100(necrose.part_maladie_connue)} `
      + "fois sur 100.");
  }
  lignes.push("Photos d'Afrique de l'Est, d'Afrique australe et du Ghana, pas de Côte d'Ivoire. Ce diagnostic ne vient pas de la NASA.");
  return lignes.join(" ");
}

function photographier() {
  const champ = document.createElement("input");
  champ.type = "file";
  champ.accept = "image/*";
  champ.capture = "environment";
  champ.addEventListener("change", () => champ.files[0] ? analyser(champ.files[0]) : suite());
  champ.click();
}

async function analyser(fichier) {
  const fiche = await chargerFicheDiagnostic();
  const image = await createImageBitmap(fichier);
  const apercu = document.createElement("img");
  apercu.src = URL.createObjectURL(fichier);
  apercu.alt = "Photo envoyée";
  apercu.className = "photo";
  bulle("", "agri").appendChild(apercu);
  try {
    const modele = await session();
    const entree = tenseurImage(image, fiche);
    if (!entree) { dire(MESSAGES_DIAGNOSTIC.pas_de_feuille, suite); return; }
    const sortie = (await modele.run({ [modele.inputNames[0]]: entree }))[modele.outputNames[0]].data;
    const maximum = Math.max(...sortie);
    const exp = Array.from(sortie, (v) => Math.exp(v - maximum));
    const somme = exp.reduce((a, b) => a + b, 0);
    const probabilites = exp.map((v) => v / somme);
    const meilleure = probabilites.indexOf(Math.max(...probabilites));
    const classe = probabilites[meilleure] >= fiche.seuil ? fiche.classes[meilleure] : "inconnu";
    dire(MESSAGES_DIAGNOSTIC[classe] || MESSAGES_DIAGNOSTIC.inconnu, (b) => {
      const detail = document.createElement("div");
      detail.className = "discret";
      detail.textContent = detailFiabilite(fiche, classe);
      b.appendChild(detail);
      suite();
    });
  } catch (e) {
    dire(`Le diagnostic n'a pas pu tourner sur ce téléphone.\nDétail technique, ${e && e.message ? e.message : e}.`, suite);
  }
}

function afficherReseau() {
  if (!navigator.onLine) etatReseau.textContent = pretHorsLigne || donnees ? "Hors connexion, tout fonctionne" : "Hors connexion";
  else if (!window.isSecureContext) etatReseau.textContent = "Adresse non sécurisée, mode hors connexion impossible";
  else etatReseau.textContent = pretHorsLigne ? "Prête à fonctionner sans connexion"
    : "Préparation du mode hors connexion, gardez la connexion";
}

// Les recommandations sont lues dans le cache si elles y sont, sans attendre le réseau.
async function chargerDonnees() {
  if (window.caches) {
    const enCache = await caches.match("donnees/recommandations.json", { ignoreSearch: true });
    if (enCache) return enCache.json();
  }
  const reponse = await fetch("donnees/recommandations.json");
  return reponse.json();
}

async function demarrer() {
  afficherModeVoix();
  afficherReseau();
  addEventListener("online", afficherReseau);
  addEventListener("offline", afficherReseau);
  // Le démarrage n'attend jamais le réseau. L'enregistrement se fait en arrière-plan.
  if ("serviceWorker" in navigator) {
    // Quand une nouvelle version prend le relais, la page se recharge une fois pour l'afficher.
    const avaitUneVersion = !!navigator.serviceWorker.controller;
    let recharge = false;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (avaitUneVersion && !recharge) { recharge = true; location.reload(); }
    });
    navigator.serviceWorker.register("sw.js").catch(() => { /* le site reste utilisable en ligne */ });
    verifierHorsLigne();
  }
  if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
  try {
    donnees = await chargerDonnees();
  } catch (e) {
    bulle("Les données ne sont pas encore installées. Ouvrez l'application une première fois avec une connexion.");
    return;
  }
  await chargerFicheDiagnostic();
  ecranDemarrage();
}

// Premier écran. Le téléphone n'accepte de parler qu'après un premier toucher.
function ecranDemarrage() {
  const ecran = document.getElementById("demarrage");
  const lancer = (avecVoix) => {
    modeVoix = avecVoix;
    afficherModeVoix();
    ecran.hidden = true;
    if (avecVoix) parler("Bonjour.");
    accueil();
  };
  document.getElementById("commencer-voix").addEventListener("click", () => lancer(true), { once: true });
  document.getElementById("commencer-texte").addEventListener("click", () => lancer(false), { once: true });
  ecran.hidden = false;
}

demarrer();
