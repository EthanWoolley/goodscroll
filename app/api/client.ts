const BASE_URL = "http://192.168.1.109:8000";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
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

export const api = {
  listProjects: () => request<Project[]>("/projects"),

  createProject: (data: {
    title: string;
    description: string;
    project_type: string;
    end_goal?: string;
    deadline?: string;
  }) =>
    request<ProjectCreateResponse>("/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getCards: (projectId: string) =>
    request<Card[]>(`/projects/${projectId}/cards`),

  submitAnswers: (
    projectId: string,
    answers: { card_id: string; answer: string }[]
  ) =>
    request<NextRoundResponse>(`/projects/${projectId}/answers`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),

  skipCard: (projectId: string, cardId: string) =>
    request<{ ok: boolean }>(
      `/projects/${projectId}/cards/${cardId}/skip`,
      { method: "PATCH" }
    ),
};
