import { api } from "@/lib/api";

export async function createDefaultOrganization(
  displayName: string,
  orgName: string,
) {
  const base = displayName
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "-")
    .slice(0, 24);
  const suffix = Math.random().toString(36).slice(2, 6);
  const slug = `${base}-${suffix}`;
  try {
    await api.post("/organizations/", { name: orgName, slug });
  } catch {
    // Non-bloquant — useEnsureOrganization retentera
  }
}
