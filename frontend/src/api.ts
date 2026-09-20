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
