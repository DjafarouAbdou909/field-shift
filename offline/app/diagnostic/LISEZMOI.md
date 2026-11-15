# Diagnostic hors connexion

Ce dossier reçoit le modèle de diagnostic des feuilles de maïs, entraîné dans Google Colab avec `entrainement/diagnostic_mais_colab.ipynb`, et le moteur d'exécution ONNX Runtime Web.

1. Dans Colab, exécutez le notebook. Il télécharge `diagnostic.zip`, qui contient `modele.onnx` et `modele.json`.
2. Placez ces deux fichiers dans ce dossier.
3. Le moteur d'exécution ONNX Runtime Web 1.20.1 est déjà présent, `ort.wasm.min.js`, `ort-wasm-simd-threaded.wasm` et `ort-wasm-simd-threaded.mjs`, vérifiés contre les empreintes publiées par jsDelivr.
4. Listez dans `fichiers.json` tous les fichiers du dossier à garder sur le téléphone.

Tant que `modele.json` est absent, l'application ne propose pas le diagnostic.
