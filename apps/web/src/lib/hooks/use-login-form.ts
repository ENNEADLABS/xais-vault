"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "@/i18n/navigation";
import { createClient } from "@/lib/supabase/client";
import { loginSchema, magicLinkSchema, type LoginFormData, type MagicLinkFormData } from "@/lib/schemas/auth";

export type LoginMode = "password" | "magic-link";

export function useLoginForm() {
  const router = useRouter();
  const supabase = createClient();

  const [mode, setMode] = useState<LoginMode>("password");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [magicLinkSent, setMagicLinkSent] = useState(false);

  const passwordForm = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const magicLinkForm = useForm<MagicLinkFormData>({
    resolver: zodResolver(magicLinkSchema),
    defaultValues: { email: "" },
  });

  async function handlePasswordLogin(data: LoginFormData) {
    setLoading(true);
    setError(null);

    const { error: authError } = await supabase.auth.signInWithPassword({
      email: data.email,
      password: data.password,
    });

    if (authError) {
      setError(authError.message);
      setLoading(false);
      return;
    }

    router.push("/workspaces");
    router.refresh();
  }

  async function handleMagicLink(data: MagicLinkFormData) {
    setLoading(true);
    setError(null);

    const { error: authError } = await supabase.auth.signInWithOtp({
      email: data.email,
      options: { emailRedirectTo: `${window.location.origin}/callback` },
    });

    if (authError) {
      setError(authError.message);
      setLoading(false);
      return;
    }

    setMagicLinkSent(true);
    setLoading(false);
  }

  return {
    mode,
    setMode,
    passwordForm,
    magicLinkForm,
    loading,
    error,
    magicLinkSent,
    handlePasswordLogin,
    handleMagicLink,
  };
}
