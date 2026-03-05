import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  TouchableOpacity,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useProjectStore } from "../store/useProjectStore";
import CardSwiper from "../components/CardSwiper";
import CompletionCard from "../components/CompletionCard";
import type { ProjectsStackParamList } from "../App";
import type { FeedCard } from "../api/client";
import { isRssCard } from "../api/client";
import { colors, fontFamily } from "../theme";

type Props = NativeStackScreenProps<ProjectsStackParamList, "Feed">;

export default function FeedScreen({ route, navigation }: Props) {
  const { projectId } = route.params;
  const { cards, loadCards, submitAnswers, skipCard, loading, projects, fetchProjects } =
    useProjectStore();

  const projectTitle = projects.find((p) => p.id === projectId)?.title;

  const [localCards, setLocalCards] = useState<FeedCard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const answeredRef = useRef<{ card_id: string; answer: string }[]>([]);

  useEffect(() => {
    fetchProjects();
    loadCards(projectId);
  }, [projectId, fetchProjects, loadCards]);

  useEffect(() => {
    setLocalCards(cards);
    setCurrentIndex(0);
    answeredRef.current = [];
  }, [cards]);

  const currentCard: FeedCard | undefined = localCards[currentIndex];
  const previousCard: FeedCard | undefined = currentIndex > 0 ? localCards[currentIndex - 1] : undefined;
  const nextCard: FeedCard | undefined =
    currentIndex < localCards.length - 1 ? localCards[currentIndex + 1] : undefined;
  const isLastCard = currentIndex >= localCards.length - 1;

  const handleAnswer = useCallback(
    async (answer: string) => {
      if (!currentCard) return;
      if (isRssCard(currentCard)) {
        setCurrentIndex((i) => i + 1);
        return;
      }
      if (answer === "") {
        try {
          await skipCard(projectId, currentCard.id);
        } catch {}
        if (isLastCard) {
          if (answeredRef.current.length > 0) {
            await flushAnswers();
          } else {
            await loadCards(projectId);
          }
        } else {
          setCurrentIndex((i) => i + 1);
        }
        return;
      }
      answeredRef.current.push({ card_id: currentCard.id, answer });
      if (isLastCard) {
        await flushAnswers();
      } else {
        setCurrentIndex((i) => i + 1);
      }
    },
    [currentCard, isLastCard, projectId, skipCard, loadCards]
  );

  const handleSkip = useCallback(async () => {
    if (!currentCard) return;
    if (isRssCard(currentCard)) {
      setLocalCards((prev) => {
        const next = [...prev];
        const [removed] = next.splice(currentIndex, 1);
        next.push(removed);
        return next;
      });
      return;
    }
    try {
      await skipCard(projectId, currentCard.id);
    } catch {}

    if (isLastCard) {
      if (answeredRef.current.length > 0) {
        await flushAnswers();
      } else {
        await loadCards(projectId);
      }
    } else {
      setCurrentIndex((i) => i + 1);
    }
  }, [currentCard, isLastCard, projectId, currentIndex]);

  const handleGoBack = useCallback(() => {
    setCurrentIndex((i) => Math.max(0, i - 1));
  }, []);

  const handleSwipeUp = useCallback(() => {
    if (isRssCard(currentCard)) {
      handleAnswer("");
    } else {
      handleSkip();
    }
  }, [currentCard, handleAnswer, handleSkip]);

  const flushAnswers = async () => {
    if (answeredRef.current.length === 0) return;
    setSubmitting(true);
    try {
      const status = await submitAnswers(projectId, answeredRef.current);
      answeredRef.current = [];
      if (status === "complete") {
        setIsComplete(true);
      }
    } catch (e: any) {
      Alert.alert("Error", e.message || "Failed to submit answers");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading && localCards.length === 0) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" color={colors.accent} />
        <Text style={styles.loadingText}>Loading cards...</Text>
      </SafeAreaView>
    );
  }

  if (submitting) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" color={colors.accent} />
        <Text style={styles.loadingText}>Generating next round...</Text>
      </SafeAreaView>
    );
  }

  if (isComplete) {
    return (
      <SafeAreaView style={styles.centered}>
        <CompletionCard onGoHome={() => navigation.navigate("Home")} />
      </SafeAreaView>
    );
  }

  if (!currentCard) {
    return (
      <SafeAreaView style={styles.centered}>
        <CompletionCard onGoHome={() => navigation.navigate("Home")} />
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
        <View style={styles.headerRow}>
          <View style={styles.spacer} />
          <TouchableOpacity
            onPress={() => navigation.navigate("ProjectContext", { projectId })}
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          >
            <Text style={styles.contextLink}>View context</Text>
          </TouchableOpacity>
        </View>
        <CardSwiper
          key={currentCard.id}
          card={currentCard}
          previousCard={previousCard}
          nextCard={nextCard}
          onSwipeUp={handleSwipeUp}
          onSwipeDown={handleGoBack}
          onAnswer={handleAnswer}
          onSkip={handleSkip}
          projectTitle={projectTitle}
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
  loadingText: {
    marginTop: 16,
    fontSize: 15,
    color: colors.textSecondary,
    fontFamily,
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingTop: 12,
  },
  spacer: {
    flex: 1,
  },
  contextLink: {
    fontSize: 14,
    color: colors.textSecondary,
    fontFamily,
  },
});
