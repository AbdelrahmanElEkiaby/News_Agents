export type ArticleDetails = {
  id: number;
  source_id: number | null;
  title: string;
  url: string;
  source: string;
  language: string | null;
  description: string | null;
  content: string | null;
  published_at: string | null;
  category: string | null;
  topics: string[] | null;
  importance: string | null;
  importance_score: number | null;
  classification_confidence: number | null;
  summary: string | null;
  key_points: string[] | null;
  summary_status: string;
  summary_requested_at: string | null;
  summary_generated_at: string | null;
  created_at: string;
};

export type ArticleFetchResult = {
  fetched: number;
  saved: number;
  duplicates: number;
  content_updated: number;
  classified: number;
  summarized: number;
  ai_processing_started: boolean;
};

export type User = {
  id: number;
  name: string;
  email: string;
  created_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type Source = {
  id: number;
  name: string;
  website_url: string | null;
  feed_url: string | null;
  language: string;
  source_type: string;
  is_active: boolean;
  last_fetched_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
  created_at: string;
};

export type DiscoveredFeed = {
  title: string;
  feed_url: string;
  feed_type: string;
  discovery_method: string;
  item_count: number;
  latest_published_at: string | null;
  score: number;
};

export type SourceDiscoverResult = {
  website_url: string;
  feed_url: string | null;
  feed_found: boolean;
  message: string;
  feeds: DiscoveredFeed[];
  recommended_feed: string | null;
};

export type SourceCreateInput = {
  name: string;
  website_url: string | null;
  feed_url: string;
  language: string;
  source_type: "rss";
};

const API_URL = (
  import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");
const TOKEN_KEY = "news_agent_access_token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getStoredToken();
  const headers = new Headers(options.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    clearToken();
    window.dispatchEvent(new Event("auth:unauthorized"));
  }

  return response;
}

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  const errorData = await response.json().catch(() => null);
  return typeof errorData?.detail === "string" ? errorData.detail : fallback;
}

export async function registerUser(
  name: string,
  email: string,
  password: string,
): Promise<AuthResponse> {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Could not create account"));
  }

  return response.json();
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);

  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Could not log in"));
  }

  return response.json();
}

export async function fetchCurrentUser(): Promise<User> {
  const response = await authFetch("/auth/me");

  if (!response.ok) {
    throw new Error("Your session has expired");
  }

  return response.json();
}

export async function fetchArticles(): Promise<ArticleDetails[]> {
  const response = await authFetch("/articles");

  if (!response.ok) {
    throw new Error("Could not load saved articles");
  }

  return response.json();
}

export async function scanSources(): Promise<ArticleFetchResult> {
  const response = await authFetch("/articles/fetch", { method: "POST" });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Could not scan subscribed sources"));
  }

  return response.json();
}

export async function generateArticleSummary(articleId: number): Promise<ArticleDetails> {
  const response = await authFetch(`/articles/${articleId}/summary`, { method: "POST" });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Could not generate summary"));
  }

  return response.json();
}

export async function fetchSources(): Promise<Source[]> {
  const response = await authFetch("/sources");

  if (!response.ok) {
    throw new Error("Could not load sources");
  }

  return response.json();
}

export async function discoverSource(url: string): Promise<SourceDiscoverResult> {
  const response = await authFetch("/sources/discover", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    throw new Error("Could not discover source");
  }

  return response.json();
}

export async function createSource(source: SourceCreateInput): Promise<Source> {
  const response = await authFetch("/sources", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(source),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Could not add source"));
  }

  return response.json();
}

export async function updateSource(sourceId: number, updates: Partial<Source>): Promise<Source> {
  const response = await authFetch(`/sources/${sourceId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });

  if (!response.ok) {
    throw new Error("Could not update source");
  }

  return response.json();
}

export async function deleteSource(sourceId: number): Promise<Source> {
  const response = await authFetch(`/sources/${sourceId}`, { method: "DELETE" });

  if (!response.ok) {
    throw new Error("Could not delete source");
  }

  return response.json();
}

export async function fetchUserSources(): Promise<Source[]> {
  const response = await authFetch("/users/me/sources");

  if (!response.ok) {
    throw new Error("Could not load subscriptions");
  }

  return response.json();
}

export async function subscribeToSource(sourceId: number): Promise<void> {
  const response = await authFetch(`/users/me/sources/${sourceId}`, { method: "POST" });

  if (!response.ok) {
    throw new Error("Could not subscribe to source");
  }
}

export async function unsubscribeFromSource(sourceId: number): Promise<void> {
  const response = await authFetch(`/users/me/sources/${sourceId}`, { method: "DELETE" });

  if (!response.ok) {
    throw new Error("Could not unsubscribe from source");
  }
}
