# masterofthenight.com — site vitrine

Site statique servi par un Worker Cloudflare (`masterofthenight-site`). Le jeu est ailleurs : dépôt `motn`, Worker `masterofthenight`, `game.masterofthenight.com`.

- `site/template.html` — la page, avec des `{{clés}}`.
- `site/i18n/<lang>.json` — les textes, une langue par fichier (fr, en, de, es, it, tr). **C'est ici qu'on modifie le contenu.**
- `site/build.py` — génère `public/<lang>/index.html`, les 404 et `sitemap.xml` : `python3 site/build.py`. Échoue si une clé manque dans une langue.
- `src/worker.js` — à la racine, redirige vers la langue du visiteur (cookie `lang`, sinon `Accept-Language`, sinon anglais) ; sert la 404 dans sa langue ; cache long sur polices et images.
- `public/` — ce qui est servi. Ne pas éditer `public/*/index.html` à la main : regénérer.

Déploiement : push sur `main`, puis build Workers (manuel via l'API tant que l'application GitHub de Cloudflare ne surveille pas ce dépôt).
