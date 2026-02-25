import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import { api, type FeedCard, isRssCard, type Project } from "../api/client";

interface ProjectStore {
  projects: Project[];
  currentProjectId: string | null;
  cards: FeedCard[];
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
  setCards: (cards: FeedCard[]) => void;
  submitAnswers: (
    projectId: string,
    answers: { card_id: string; answer: string }[]
  ) => Promise<"continue" | "complete">;
  skipCard: (projectId: string, cardId: string) => Promise<void>;
}

function mergeFeedCards(
  projectCards: import("../api/client").Card[],
  rssCards: import("../api/client").RssCard[]
): FeedCard[] {
  return [...projectCards, ...rssCards];
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
      const key = await AsyncStorage.getItem("anthropic_api_key");
      const res = await api.createProject(data, {
        anthropicKey: key ?? undefined,
      });
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
      const [projectCards, rssCards] = await Promise.all([
        api.getCards(projectId),
        api.getRssCards(),
      ]);
      set({ cards: mergeFeedCards(projectCards, rssCards) });
    } catch {
      set({ cards: [] });
    } finally {
      set({ loading: false });
    }
  },

  setCards: (cards) => set({ cards }),

  submitAnswers: async (projectId, answers) => {
    set({ loading: true });
    try {
      const key = await AsyncStorage.getItem("anthropic_api_key");
      const res = await api.submitAnswers(projectId, answers, {
        anthropicKey: key ?? undefined,
      });
      const prevCards = get().cards;
      const rssCards = prevCards.filter(isRssCard);
      set({ cards: [...res.cards, ...rssCards] });
      return res.status;
    } finally {
      set({ loading: false });
    }
  },

  skipCard: async (projectId, cardId) => {
    await api.skipCard(projectId, cardId);
  },
}));
