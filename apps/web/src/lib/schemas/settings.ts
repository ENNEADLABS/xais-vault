import { z } from "zod";

export const profileSchema = z.object({
  displayName: z.string().min(1),
  avatarUrl: z.string().optional(),
});

export const organizationSchema = z.object({
  name: z.string().min(1),
});

export const inviteMemberSchema = z.object({
  email: z.string().email(),
  role: z.enum(["admin", "analyst", "viewer"]),
});

export const createWebhookSchema = z.object({
  url: z.string().url(),
  events: z.array(z.string()).min(1),
  isActive: z.boolean(),
});

export const createApiKeySchema = z.object({
  name: z.string().min(1),
  rpmLimit: z.number().min(1),
  rpdLimit: z.number().min(1),
});

export const deleteOrgSchema = z.object({
  confirmName: z.string().min(1),
});

export type ProfileFormData = z.infer<typeof profileSchema>;
export type OrganizationFormData = z.infer<typeof organizationSchema>;
export type InviteMemberFormData = z.infer<typeof inviteMemberSchema>;
export type CreateWebhookFormData = z.infer<typeof createWebhookSchema>;
export type CreateApiKeyFormData = z.infer<typeof createApiKeySchema>;
export type DeleteOrgFormData = z.infer<typeof deleteOrgSchema>;
