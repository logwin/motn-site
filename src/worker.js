// Worker du site vitrine : choisit la langue, puis laisse les fichiers statiques faire le reste.
//
//  /            → redirige vers /<lang>/ : cookie « lang » s'il existe, sinon Accept-Language, sinon anglais.
//  /<lang>/     → page statique ; si le visiteur vient d'y arriver par le sélecteur (?lang=1), on mémorise
//                 son choix dans le cookie pour que la racine le respecte la prochaine fois.
//  autre chose  → fichiers statiques (polices, images, 404 de la langue détectée).

const LANGS = ["fr", "en", "de", "es", "it", "tr"];
const DEFAULT = "en";
const COOKIE = "lang";
const ONE_YEAR = 60 * 60 * 24 * 365;

function fromCookie(request) {
  const m = (request.headers.get("Cookie") || "").match(new RegExp(`(?:^|;\\s*)${COOKIE}=([a-z]{2})`));
  return m && LANGS.includes(m[1]) ? m[1] : null;
}

function fromAcceptLanguage(request) {
  const header = request.headers.get("Accept-Language") || "";
  const ranked = header.split(",").map((part, i) => {
    const [tag, ...params] = part.trim().split(";");
    const q = params.map(p => p.trim()).find(p => p.startsWith("q="));
    return { lang: tag.toLowerCase().split("-")[0], q: q ? parseFloat(q.slice(2)) : 1, i };
  }).filter(r => r.lang).sort((a, b) => b.q - a.q || a.i - b.i);
  const hit = ranked.find(r => LANGS.includes(r.lang));
  return hit ? hit.lang : null;
}

function langOfPath(pathname) {
  const m = pathname.match(/^\/([a-z]{2})(\/|$)/);
  return m && LANGS.includes(m[1]) ? m[1] : null;
}

// /stats/data.json : les totaux d'usage du jeu (fonction Supabase stats_usage, qui ne renvoie que des comptes),
// gardés 5 minutes dans le cache de Cloudflare pour que les visites ne frappent pas la base à chaque fois.
const STATS_TTL = 300;

async function statsData(request, env, ctx) {
  const cache = caches.default;
  const key = new Request(new URL("/stats/data.json", request.url).toString(), { method: "GET" });
  const hit = await cache.match(key);
  if (hit) return hit;
  let upstream;
  try {
    upstream = await fetch(`${env.SUPABASE_URL}/rest/v1/rpc/stats_usage`, {
      method: "POST",
      headers: { apikey: env.SUPABASE_KEY, "Content-Type": "application/json" },
      body: "{}",
    });
  } catch (e) {
    upstream = null;
  }
  if (!upstream || !upstream.ok) {
    return new Response('{"erreur":"statistiques indisponibles"}', {
      status: 502,
      headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
    });
  }
  const response = new Response(await upstream.text(), {
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": `public, max-age=${STATS_TTL}` },
  });
  ctx.waitUntil(cache.put(key, response.clone()));
  return response;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/stats/data.json" && request.method === "GET") {
      return statsData(request, env, ctx);
    }

    if (url.pathname === "/" || url.pathname === "/index.html") {
      const lang = fromCookie(request) || fromAcceptLanguage(request) || DEFAULT;
      return new Response(null, {
        status: 302,
        headers: { Location: `${url.origin}/${lang}/`, Vary: "Accept-Language, Cookie", "Cache-Control": "no-store" },
      });
    }

    const lang = langOfPath(url.pathname);

    // Choix explicite par le sélecteur : on mémorise, puis on sert l'adresse propre.
    if (lang && url.searchParams.has("lang")) {
      url.searchParams.delete("lang");
      return new Response(null, {
        status: 302,
        headers: {
          Location: url.toString(),
          "Set-Cookie": `${COOKIE}=${lang}; Path=/; Max-Age=${ONE_YEAR}; SameSite=Lax; Secure`,
        },
      });
    }

    const response = await env.ASSETS.fetch(request);

    // Pas de page à cette adresse : la 404 dans la langue du visiteur.
    if (response.status === 404 && request.method === "GET" && !url.pathname.includes(".")) {
      const l = lang || fromCookie(request) || fromAcceptLanguage(request) || DEFAULT;
      const page = await env.ASSETS.fetch(new Request(`${url.origin}/${l}/404`, { headers: request.headers })); // sans extension : html_handling redirigerait /404.html
      return new Response(page.body, { status: 404, headers: { "Content-Type": "text/html; charset=utf-8" } });
    }

    // Polices, images, icônes : nom stable, cache long.
    if (/\.(woff2|png|ico|svg)$/.test(url.pathname) && response.ok) {
      const r = new Response(response.body, response);
      r.headers.set("Cache-Control", "public, max-age=31536000, immutable");
      return r;
    }
    return response;
  },
};
