import { create } from "zustand";
import { api, Card, Project } from "../api/client";

interface ProjectStore {
  projects: Project[];
  currentProjectId: string | null;
  cards: Card[];
  loading: boolean;

  fetchProjects: () => Promise<void>;
  createProject: (data: {
    title: string;
    description: string;
    project_type: string;
    end_goal?: string;
    deadline?: string;
  }) => Promise<string>;
  loadCards: (projectId: string) => Promise<void>;
  setCards: (cards: Card[]) => void;
  submitAnswers: (
    projectId: string,
    answers: { card_id: string; answer: string }[]
  ) => Promise<"continue" | "complete">;
  skipCard: (projectId: string, cardId: string) => Promise<void>;
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  projects: [],
  currentProjectId: null,
  cards: [],
  loading: false,

  fetchProjects: async () => {
    set({ loading: true });
    try {
      const projects = await api.listProjects();
      set({ projects });
    } finally {
      set({ loading: false });
    }
  },

  createProject: async (data) => {
    set({ loading: true });
    try {
      const res = await api.createProject(data);
      set((s) => ({
        projects: [res.project, ...s.projects],
        currentProjectId: res.project.id,
        cards: res.cards,
      }));
      return res.project.id;
    } finally {
      set({ loading: false });
    }
  },

  loadCards: async (projectId) => {
    set({ loading: true, currentProjectId: projectId });
    try {
      const cards = await api.getCards(projectId);
      set({ cards });
    } finally {
      set({ loading: false });
    }
  },

  setCards: (cards) => set({ cards }),

  submitAnswers: async (projectId, answers) => {
    set({ loading: true });
    try {
      const res = await api.submitAnswers(projectId, answers);
      set({ cards: res.cards });
      return res.status;
    } finally {
      set({ loading: false });
    }
  },

  skipCard: async (projectId, cardId) => {
    await api.skipCard(projectId, cardId);
  },
}));
