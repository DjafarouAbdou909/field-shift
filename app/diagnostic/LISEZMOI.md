# Diagnostic hors connexion

Ce dossier reçoit le modèle de diagnostic des feuilles de maïs, entraîné dans Google Colab avec `entrainement/diagnostic_mais_colab.ipynb`, et le moteur d'exécution ONNX Runtime Web.

1. Dans Colab, exécutez le notebook. Il télécharge `diagnostic.zip`, qui contient `modele.onnx` et `modele.json`.
2. Placez ces deux fichiers dans ce dossier.
3. Ajoutez le moteur d'exécution ONNX Runtime Web, `ort.min.js` et ses fichiers `.wasm` et `.mjs`, en version figée.
4. Listez dans `fichiers.json` tous les fichiers du dossier à garder sur le téléphone.

Tant que `modele.json` est absent, l'application ne propose pas le diagnostic.
