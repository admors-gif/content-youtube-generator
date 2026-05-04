export function getApiBase() {
  return process.env.NEXT_PUBLIC_VPS_API_URL || "https://api.valtyk.com";
}

export async function authHeaders(user, headers = {}) {
  if (!user) throw new Error("Sesión no disponible");
  const token = await user.getIdToken();
  return {
    ...headers,
    Authorization: `Bearer ${token}`,
  };
}
