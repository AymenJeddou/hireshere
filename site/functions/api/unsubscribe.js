// One-click unsubscribe from digest emails. The link carries HMAC-SHA256(email) made with
// UNSUBSCRIBE_SECRET (see pipeline/alerts.py), so nobody can unsubscribe someone else.
async function remove(request, env) {
  const url = new URL(request.url);
  const email = url.searchParams.get("e") || "";
  const token = url.searchParams.get("t") || "";
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(env.UNSUBSCRIBE_SECRET), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(email)));
  const expected = [...sig].map((b) => b.toString(16).padStart(2, "0")).join("");
  if (!email || token !== expected) return false;
  await env.DB.prepare("DELETE FROM subscribers WHERE email = ?").bind(email).run();
  return true;
}

const page = (ok) =>
  new Response(
    `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>HiresHere</title>
<body style="font-family:system-ui;max-width:560px;margin:15vh auto;padding:0 16px;color:#14223a">
<h1 style="font-size:22px">${ok ? "You are unsubscribed" : "This link is not valid"}</h1>
<p>${ok ? "You will not receive any more HiresHere emails. / Vous ne recevrez plus d’e-mails de HiresHere." : "Use the unsubscribe link from your latest email. / Utilisez le lien de votre dernier e-mail."}</p>
<p><a href="/" style="color:#1d5bc7">hireshere.app</a></p>`,
    { status: ok ? 200 : 400, headers: { "content-type": "text/html; charset=utf-8" } },
  );

// GET from the email link, POST from mail clients' one-click button (RFC 8058).
export const onRequestGet = async ({ request, env }) => page(await remove(request, env));
export const onRequestPost = async ({ request, env }) => new Response(null, { status: (await remove(request, env)) ? 200 : 400 });
