import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
});

export const magicLinkSchema = z.object({
  email: z.string().email(),
});

export const signupSchema = z
  .object({
    fullName: z.string().optional(),
    email: z.string().email(),
    password: z.string().min(6),
    confirmPassword: z.string().min(6),
  })
  .refine((data) => data.password === data.confirmPassword, {
    path: ["confirmPassword"],
    message: "passwords_dont_match",
  });

export type LoginFormData = z.infer<typeof loginSchema>;
export type MagicLinkFormData = z.infer<typeof magicLinkSchema>;
export type SignupFormData = z.infer<typeof signupSchema>;
