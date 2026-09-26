export interface FieldConflict { draftId: string; field: string; remote: unknown }
const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);
/** Three-way content merge. Provenance/revision always come from the remote row. */
export function mergeDraftContent(draftId: string, base: Record<string, unknown>, local: Record<string, unknown>, remote: Record<string, unknown>) {
  const content = { ...remote };
  const conflicts: FieldConflict[] = [];
  for (const field of new Set([...Object.keys(base), ...Object.keys(local), ...Object.keys(remote)])) {
    if (same(local[field], base[field])) continue;
    if (!same(remote[field], base[field]) && !same(remote[field], local[field])) {
      conflicts.push({ draftId, field, remote: remote[field] });
    }
    if (field in local) content[field] = local[field]; else delete content[field];
  }
  return { content, conflicts };
}
