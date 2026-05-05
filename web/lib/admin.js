const DEFAULT_ADMIN_EMAILS = ["admors@gmail.com"];

export function getAdminEmails() {
  const configured = (process.env.NEXT_PUBLIC_ADMIN_EMAILS || "")
    .split(",")
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean);
  return new Set([...DEFAULT_ADMIN_EMAILS, ...configured]);
}

export function isAdminUser(user, profile) {
  const email = (profile?.email || user?.email || "").trim().toLowerCase();
  return !!email && getAdminEmails().has(email);
}
