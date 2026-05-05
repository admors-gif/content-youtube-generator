export function getCreditCounts(profile) {
  const credits = profile?.credits || {};
  const rawIncluded = Math.max(0, Number(credits.included) || 0);
  const used = Math.max(0, Number(credits.used) || 0);
  const extra = Math.max(0, Number(credits.extra) || 0);
  const plan = (profile?.plan || "free").toLowerCase();
  const freeIncludedCap = Math.max(
    0,
    Number(process.env.NEXT_PUBLIC_FREE_INCLUDED_CREDITS) || 0,
  );
  const included = plan === "free" ? Math.min(rawIncluded, freeIncludedCap) : rawIncluded;
  const total = included + extra;
  const remaining = Math.max(0, total - used);

  return {
    included,
    used,
    extra,
    total,
    remaining,
  };
}
