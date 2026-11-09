#!/usr/bin/env python3
"""Génère public/<lang>/index.html à partir de site/template.html et site/i18n/<lang>.json.

    python3 site/build.py

Les textes se modifient dans les JSON, jamais dans public/. Les clés manquantes font échouer
la génération : une page à moitié traduite ne doit pas partir en ligne.
"""
import json, re, sys, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT.parent / "public"
LANGS = ["fr", "en", "de", "es", "it", "tr"]   # l'ordre est celui du sélecteur
DEFAULT = "en"                                   # x-default pour les moteurs de recherche
BASE = "https://masterofthenight.com"

template = (ROOT / "template.html").read_text(encoding="utf-8")
texts = {l: json.loads((ROOT / "i18n" / f"{l}.json").read_text(encoding="utf-8")) for l in LANGS}
keys = set(re.findall(r"\{\{(\w+)\}\}", template)) - {"lang", "alternates", "lang_links"}

alternates = "\n".join(f'<link rel="alternate" hreflang="{l}" href="{BASE}/{l}/">' for l in LANGS)
alternates += f'\n<link rel="alternate" hreflang="x-default" href="{BASE}/{DEFAULT}/">'

errors = []
for lang in LANGS:
    t = dict(texts[lang])
    missing = sorted(k for k in keys if k not in t)
    if missing:
        errors.append(f"{lang}: clés manquantes {missing}")
        continue
    t["table_i18n"] = html.escape(json.dumps(t["table_i18n"], ensure_ascii=False), quote=True)
    links = "".join(
        f'<li><a href="/{l}/?lang=1" lang="{l}" hreflang="{l}"{" aria-current=\"page\"" if l == lang else ""}>{texts[l]["_name"]}</a></li>'
        for l in LANGS)
    page = template
    page = page.replace("{{lang}}", lang).replace("{{alternates}}", alternates).replace("{{lang_links}}", links)
    page = re.sub(r"\{\{(\w+)\}\}", lambda m: t[m.group(1)], page)
    out = PUBLIC / lang / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"{out.relative_to(PUBLIC.parent)}  {len(page):,} o")

# 404 par langue
NF = {
    "fr": ("Cette page n'existe pas", "Le soleil s'est levé dessus.", "Retour à l'accueil", "lancer le jeu"),
    "en": ("This page does not exist", "The sun rose on it.", "Back to the home page", "launch the game"),
    "de": ("Diese Seite gibt es nicht", "Die Sonne ist darüber aufgegangen.", "Zurück zur Startseite", "das Spiel starten"),
    "es": ("Esta página no existe", "Le salió el sol encima.", "Volver al inicio", "lanzar el juego"),
    "it": ("Questa pagina non esiste", "Il sole è sorto sopra di lei.", "Torna alla pagina iniziale", "avvia il gioco"),
    "tr": ("Bu sayfa yok", "Üzerine güneş doğdu.", "Ana sayfaya dön", "oyunu başlat"),
}
for l, (h, sub, back, play) in NF.items():
    (PUBLIC / l / "404.html").write_text(f"""<!DOCTYPE html>
<html lang="{l}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h} — Master of the Night</title><meta name="robots" content="noindex">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>@font-face{{font-family:"Cormorant Garamond";src:url(/fonts/cormorant.woff2) format("woff2");font-weight:300 700}}
html,body{{margin:0;height:100%;background:#08080a;color:#ddd6c6;font:17px/1.6 system-ui,sans-serif}}
main{{min-height:100%;display:grid;place-items:center;text-align:center;padding:20px}}
h1{{font-family:"Cormorant Garamond",Georgia,serif;font-weight:400;font-size:3rem;margin:0 0 .5rem;color:#e7c56b}}a{{color:#e7c56b}}</style></head>
<body><main><div><h1>{h}</h1><p>{sub} <a href="/{l}/">{back}</a> · <a href="https://game.masterofthenight.com/">{play}</a>.</p></div></main></body></html>
""", encoding="utf-8")

# sitemap : une entrée par langue, avec les alternates
urls = []
for l in LANGS:
    alts = "".join(f'<xhtml:link rel="alternate" hreflang="{a}" href="{BASE}/{a}/"/>' for a in LANGS)
    alts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{BASE}/{DEFAULT}/"/>'
    urls.append(f"  <url><loc>{BASE}/{l}/</loc>{alts}<changefreq>weekly</changefreq><priority>1.0</priority></url>")
urls.append(f"  <url><loc>https://game.masterofthenight.com/</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>")
(PUBLIC / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
