export function getApiBase() {
  return process.env.NEXT_PUBLIC_VPS_API_URL || "https://api.valtyk.com";
}

export async function authHeaders(user, headers = {}, options = {}) {
  if (!user) throw new Error("Sesión no disponible");
  const token = await user.getIdToken(Boolean(options.forceRefresh));
  return {
    ...headers,
    Authorization: `Bearer ${token}`,
  };
}

async function responseLooksLikeExpiredAuth(res) {
  if (res.status !== 401) return false;
  try {
    const data = await res.clone().json();
    const detail = String(data.detail || data.error || "").toLowerCase();
    return detail.includes("invalid auth token") || detail.includes("expired") || detail.includes("auth token");
  } catch {
    return true;
  }
}

export async function authedFetch(user, url, options = {}) {
  const { headers = {}, ...rest } = options;
  const first = await fetch(url, {
    ...rest,
    headers: await authHeaders(user, headers),
  });

  if (!(await responseLooksLikeExpiredAuth(first))) {
    return first;
  }

  return fetch(url, {
    ...rest,
    headers: await authHeaders(user, headers, { forceRefresh: true }),
  });
}
