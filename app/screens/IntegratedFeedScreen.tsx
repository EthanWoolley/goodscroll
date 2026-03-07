import React, { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  RefreshControl,
  ScrollView,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { SafeAreaView } from "react-native-safe-area-context";
import CardSwiper, { type SwipeableCard } from "../components/CardSwiper";
import {
  api,
  type FeedItem,
  isQuestionFeedItem,
  isRssFeedItem,
  isWikipediaFeedItem,
  isWikiInterestQuestionItem,
} from "../api/client";
import { colors, fontFamily } from "../theme";

function feedItemToSwipeableCard(item: FeedItem): SwipeableCard {
  if (item.source === "wikipedia_interest_question" && item.wiki_interest_card_id && item.options) {
    return {
      id: item.id,
      type: "wikipedia_interest_question" as const,
      wiki_interest_card_id: item.wiki_interest_card_id,
      question: item.question ?? "Which of these topics interest you most?",
      options: item.options.filter((o): o is string => o != null),
      parent_category: item.parent_category,
    };
  }
  if (item.source === "question" && item.project_id && item.type && item.question != null) {
    return {
      id: item.id,
      project_id: item.project_id,
      type: item.type as "multiple_choice" | "open_ended",
      question: item.question,
      options: item.options ?? null,
      status: item.status ?? "unanswered",
      round: item.round ?? 1,
      created_at: item.created_at ?? "",
    };
  }
  if (item.source === "rss") {
    return {
      id: item.id,
      type: "rss",
      title: item.title ?? "",
      source: item.feed_source ?? "",
      summary: item.summary ?? "",
      url: item.url ?? "",
      published_at: item.published_at ?? "",
      image_url: item.image_url,
    };
  }
  return {
    id: item.id,
    title: item.title ?? "",
    extract: item.extract ?? "",
    url: item.url ?? "",
    source_term: item.source_term ?? "",
    thumbnail_url: item.thumbnail_url,
  };
}

export default function IntegratedFeedScreen() {
  const [cards, setCards] = useState<FeedItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const loadFeed = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const key = await AsyncStorage.getItem("anthropic_api_key");
      const data = await api.getFeed({ anthropicKey: key ?? undefined });
      setCards(data);
      if (!isRefresh) setCurrentIndex(0);
    } catch (e: any) {
      Alert.alert("Error", e.message || "Failed to load feed");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadFeed();
  }, [loadFeed]);

  const currentItem = cards[currentIndex];
  const currentCard = currentItem ? feedItemToSwipeableCard(currentItem) : null;
  const previousCard =
    currentIndex > 0 && cards[currentIndex - 1] ? feedItemToSwipeableCard(cards[currentIndex - 1]) : null;
  const nextCard =
    currentIndex < cards.length - 1 && cards[currentIndex + 1]
      ? feedItemToSwipeableCard(cards[currentIndex + 1])
      : null;

  const advance = useCallback(() => {
    setCurrentIndex((i) => Math.min(i + 1, cards.length));
  }, [cards.length]);

  const removeAndAdvance = useCallback(() => {
    setCards((prev) => {
      const next = prev.filter((_, idx) => idx !== currentIndex);
      setCurrentIndex(next.length === 0 ? 0 : Math.min(currentIndex, next.length - 1));
      return next;
    });
  }, [currentIndex]);

  const requeueAndAdvance = useCallback(() => {
    setCards((prev) => {
      if (currentIndex >= prev.length) return prev;
      const copy = [...prev];
      const [removed] = copy.splice(currentIndex, 1);
      return [...copy, removed];
    });
  }, [currentIndex]);

  const handleAnswer = useCallback(
    async (answer: string) => {
      if (!currentItem || !currentCard) return;
      if (isQuestionFeedItem(currentItem) && currentItem.project_id) {
        if (answer === "") {
          removeAndAdvance();
          return;
        }
        setSubmitting(true);
        try {
          await api.submitAnswers(
            currentItem.project_id,
            [{ card_id: currentItem.id, answer }],
            { anthropicKey: (await AsyncStorage.getItem("anthropic_api_key")) ?? undefined }
          );
          removeAndAdvance();
        } catch (e: any) {
          Alert.alert("Error", e.message || "Failed to submit");
        } finally {
          setSubmitting(false);
        }
        return;
      }
      if (isRssFeedItem(currentItem) || isWikipediaFeedItem(currentItem)) {
        removeAndAdvance();
      }
    },
    [currentItem, currentCard, removeAndAdvance]
  );

  const handleMultiAnswer = useCallback(
    async (selected: string[]) => {
      if (!currentItem || !currentCard) return;
      if (isWikiInterestQuestionItem(currentItem) && currentItem.wiki_interest_card_id) {
        setSubmitting(true);
        try {
          await api.submitWikiInterestAnswer(currentItem.wiki_interest_card_id, selected);
          removeAndAdvance();
        } catch (e: any) {
          Alert.alert("Error", e.message || "Failed to submit");
        } finally {
          setSubmitting(false);
        }
      }
    },
    [currentItem, currentCard, removeAndAdvance]
  );

  const handleSkip = useCallback(async () => {
    if (!currentItem || !currentCard) return;
    if (isWikiInterestQuestionItem(currentItem) && currentItem.wiki_interest_card_id) {
      try {
        await api.skipWikiInterestCard(currentItem.wiki_interest_card_id);
      } catch {}
      removeAndAdvance();
      return;
    }
    if (isQuestionFeedItem(currentItem) && currentItem.project_id) {
      try {
        await api.skipCard(currentItem.project_id, currentItem.id);
      } catch {}
      removeAndAdvance();
      return;
    }
    if (isRssFeedItem(currentItem) || isWikipediaFeedItem(currentItem)) {
      requeueAndAdvance();
    }
  }, [currentItem, currentCard, removeAndAdvance, requeueAndAdvance]);

  const handleGoBack = useCallback(() => {
    setCurrentIndex((i) => Math.max(0, i - 1));
  }, []);

  const handleSwipeUp = useCallback(() => {
    if (!currentItem || !currentCard) return;
    if (isQuestionFeedItem(currentItem) || isWikiInterestQuestionItem(currentItem)) {
      handleSkip();
    } else {
      handleAnswer("");
    }
  }, [currentItem, currentCard, handleSkip, handleAnswer]);

  if (loading && cards.length === 0) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" color={colors.accent} />
        <Text style={styles.loadingText}>Loading feed...</Text>
      </SafeAreaView>
    );
  }

  if (submitting) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" color={colors.accent} />
        <Text style={styles.loadingText}>Submitting...</Text>
      </SafeAreaView>
    );
  }

  if (!currentCard || cards.length === 0) {
    return (
      <SafeAreaView style={styles.safe}>
        <ScrollView
          contentContainerStyle={styles.emptyScroll}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => loadFeed(true)} tintColor={colors.textPrimary} />
          }
        >
          <Text style={styles.emptyText}>No cards right now.</Text>
          <Text style={styles.emptySubtext}>Pull to refresh or add projects and RSS feeds.</Text>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.safe}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={Platform.OS === "ios" ? 60 : 0}
      >
        <CardSwiper
          key={currentCard.id}
          card={currentCard}
          previousCard={previousCard}
          nextCard={nextCard}
          onSwipeUp={handleSwipeUp}
          onSwipeDown={handleGoBack}
          onAnswer={handleAnswer}
          onMultiAnswer={handleMultiAnswer}
          onSkip={handleSkip}
          projectTitle={currentItem && isQuestionFeedItem(currentItem) ? currentItem.project_title : undefined}
        />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  centered: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: "center",
    alignItems: "center",
  },
  loadingText: { marginTop: 16, fontSize: 15, color: colors.textSecondary, fontFamily },
  emptyScroll: { flex: 1, justifyContent: "center", alignItems: "center", padding: 24 },
  emptyText: { fontSize: 18, color: colors.textPrimary, textAlign: "center", fontFamily },
  emptySubtext: { marginTop: 8, fontSize: 14, color: colors.textSecondary, textAlign: "center", fontFamily },
});
