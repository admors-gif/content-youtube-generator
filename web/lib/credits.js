export function getCreditCounts(profile) {
  const credits = profile?.credits || {};
  const included = Math.max(0, Number(credits.included) || 0);
  const used = Math.max(0, Number(credits.used) || 0);
  const extra = Math.max(0, Number(credits.extra) || 0);
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
