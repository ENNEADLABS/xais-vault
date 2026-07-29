import { createClient } from "./supabase/client";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ApiError {
  error: { code: number; message: string };
}

export interface ApiResponse<T> {
  data: T | null;
  usage?: {
    input_tokens: number;
    output_tokens: number;
    cost_usd: number;
    model_used: string;
  } | null;
  meta?: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

class VaultApiClient {
  private organizationId: string | null = null;

  setOrganizationId(id: string | null) {
    this.organizationId = id;
  }

  private async getHeaders(): Promise<HeadersInit> {
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    if (session?.access_token) {
      headers["Authorization"] = `Bearer ${session.access_token}`;
    }

    if (this.organizationId) {
      headers["X-Organization-ID"] = this.organizationId;
    }

    return headers;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const headers = await this.getHeaders();
    const res = await fetch(`${API_URL}/api/v2${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!res.ok) {
      const errorBody = (await res.json().catch(() => ({
        error: { code: res.status, message: res.statusText },
      }))) as ApiError;
      throw errorBody;
    }

    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  }

  get<T>(path: string) {
    return this.request<T>("GET", path);
  }
  post<T>(path: string, body?: unknown) {
    return this.request<T>("POST", path, body);
  }
  patch<T>(path: string, body: unknown) {
    return this.request<T>("PATCH", path, body);
  }
  delete(path: string) {
    return this.request<void>("DELETE", path);
  }

  async upload<T>(path: string, formData: FormData): Promise<T> {
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    const headers: HeadersInit = {};
    if (session?.access_token) {
      headers["Authorization"] = `Bearer ${session.access_token}`;
    }
    if (this.organizationId) {
      headers["X-Organization-ID"] = this.organizationId;
    }

    const res = await fetch(`${API_URL}/api/v2${path}`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!res.ok) {
      const errorBody = (await res.json().catch(() => ({
        error: { code: res.status, message: res.statusText },
      }))) as ApiError;
      throw errorBody;
    }

    return res.json() as Promise<T>;
  }

  buildUrl(path: string): string {
    return `${API_URL}/api/v2${path}`;
  }
}

export const api = new VaultApiClient();
