export type FeedArticle = {
  id: number;
  title: string;
  url: string;
  source: string;
  language: string | null;
  summary: string | null;
  category: string | null;
  topics: string[] | null;
  published_at: string | null;
  score: number;
  ai_relevance: number;
  freshness_score: number;
  topic_match_score: number;
  reason: string;
};

export type ArticleDetails = {
  id: number;
  title: string;
  url: string;
  source: string;
  language: string | null;
  description: string | null;
  content: string | null;
  published_at: string | null;
  category: string | null;
  topics: string[] | null;
  summary: string | null;
  key_points: string[] | null;
  created_at: string;
};

export type FeedRequest = {
  topics: string[];
  languages: string[];
  max_articles: number;
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

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export async function fetchFeed(request: FeedRequest): Promise<FeedArticle[]> {
  const response = await fetch(`${API_URL}/feed`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error("Could not load personalized feed");
  }

  return response.json();
}

export async function fetchArticle(articleId: number): Promise<ArticleDetails> {
  const response = await fetch(`${API_URL}/articles/${articleId}`);

  if (!response.ok) {
    throw new Error("Could not load article details");
  }

  return response.json();
}

export async function fetchSources(): Promise<Source[]> {
  const response = await fetch(`${API_URL}/sources`);

  if (!response.ok) {
    throw new Error("Could not load sources");
  }

  return response.json();
}

export async function discoverSource(url: string): Promise<SourceDiscoverResult> {
  const response = await fetch(`${API_URL}/sources/discover`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    throw new Error("Could not discover source");
  }

  return response.json();
}

export async function createSource(source: SourceCreateInput): Promise<Source> {
  const response = await fetch(`${API_URL}/sources`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(source),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail ?? "Could not add source");
  }

  return response.json();
}

export async function updateSource(sourceId: number, updates: Partial<Source>): Promise<Source> {
  const response = await fetch(`${API_URL}/sources/${sourceId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(updates),
  });

  if (!response.ok) {
    throw new Error("Could not update source");
  }

  return response.json();
}

export async function deleteSource(sourceId: number): Promise<Source> {
  const response = await fetch(`${API_URL}/sources/${sourceId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Could not delete source");
  }

  return response.json();
}
