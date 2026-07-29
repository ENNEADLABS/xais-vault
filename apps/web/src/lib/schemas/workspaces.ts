import { z } from "zod";

export const workspaceCreateSchema = z.object({
  name: z.string().min(1),
  emoji: z.string(),
  description: z.string().optional(),
  workspaceType: z.string().optional(),
  sector: z.string().optional(),
  targetCompany: z.string().optional(),
});

export const generateDeliverableSchema = z.object({
  type: z.enum(["executive_summary", "investment_memo", "dd_report"]),
  name: z.string().min(1),
});

export type WorkspaceCreateFormData = z.infer<typeof workspaceCreateSchema>;
export type GenerateDeliverableFormData = z.infer<typeof generateDeliverableSchema>;
