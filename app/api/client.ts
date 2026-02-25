const BASE_URL = "http://192.168.1.109:8000";

export interface RequestOptions extends RequestInit {
  anthropicKey?: string;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { anthropicKey, ...fetchOptions } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchOptions.headers as Record<string, string>),
  };
  if (anthropicKey && anthropicKey.trim()) {
    headers["X-Anthropic-Key"] = anthropicKey.trim();
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    ...fetchOptions,
    headers,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export interface Project {
  id: string;
  title: string;
  description: string;
  project_type: string;
  end_goal: string | null;
  deadline: string | null;
  created_at: string;
}

export interface Card {
  id: string;
  project_id: string;
  type: "multiple_choice" | "open_ended";
  question: string;
  options: string[] | null;
  status: string;
  round: number;
  created_at: string;
}

export interface ProjectCreateResponse {
  project: Project;
  cards: Card[];
}

export interface NextRoundResponse {
  status: "continue" | "complete";
  cards: Card[];
}

export interface RssFeed {
  id: string;
  url: string;
  created_at: string;
}

export interface RssCard {
  id: string;
  type: "rss";
  title: string;
  source: string;
  summary: string;
  url: string;
  published_at: string;
}

export type FeedCard = Card | RssCard;

export function isRssCard(card: FeedCard): card is RssCard {
  return card.type === "rss";
}

export const api = {
  listProjects: () => request<Project[]>("/projects"),

  createProject: (
    data: {
      title: string;
      description: string;
      project_type: string;
      end_goal?: string;
      deadline?: string;
    },
    options?: { anthropicKey?: string }
  ) =>
    request<ProjectCreateResponse>("/projects", {
      method: "POST",
      body: JSON.stringify(data),
      ...options,
    }),

  getCards: (projectId: string) =>
    request<Card[]>(`/projects/${projectId}/cards`),

  submitAnswers: (
    projectId: string,
    answers: { card_id: string; answer: string }[],
    options?: { anthropicKey?: string }
  ) =>
    request<NextRoundResponse>(`/projects/${projectId}/answers`, {
      method: "POST",
      body: JSON.stringify({ answers }),
      ...options,
    }),

  skipCard: (projectId: string, cardId: string) =>
    request<{ ok: boolean }>(
      `/projects/${projectId}/cards/${cardId}/skip`,
      { method: "PATCH" }
    ),

  postInterests: (interests: string[]) =>
    request<{ ok: boolean }>("/users/interests", {
      method: "POST",
      body: JSON.stringify({ interests }),
    }),

  getRssFeeds: () => request<RssFeed[]>("/rss/feeds"),

  addRssFeed: (url: string) =>
    request<RssFeed>("/rss/feeds", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  deleteRssFeed: (id: string) =>
    request<{ ok: boolean }>(`/rss/feeds/${id}`, { method: "DELETE" }),

  getRssCards: () => request<RssCard[]>("/rss/cards"),
};
