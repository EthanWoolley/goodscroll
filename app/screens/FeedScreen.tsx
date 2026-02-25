import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useProjectStore } from "../store/useProjectStore";
import CardSwiper from "../components/CardSwiper";
import CompletionCard from "../components/CompletionCard";
import type { RootStackParamList } from "../App";
import type { FeedCard } from "../api/client";
import { isRssCard } from "../api/client";

type Props = NativeStackScreenProps<RootStackParamList, "Feed">;

export default function FeedScreen({ route, navigation }: Props) {
  const { projectId } = route.params;
  const { cards, loadCards, submitAnswers, skipCard, loading } =
    useProjectStore();

  const [localCards, setLocalCards] = useState<FeedCard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const answeredRef = useRef<{ card_id: string; answer: string }[]>([]);

  useEffect(() => {
    loadCards(projectId);
  }, [projectId]);

  useEffect(() => {
    setLocalCards(cards);
    setCurrentIndex(0);
    answeredRef.current = [];
  }, [cards]);

  const currentCard: FeedCard | undefined = localCards[currentIndex];
  const isLastCard = currentIndex >= localCards.length - 1;

  const handleAnswer = useCallback(
    async (answer: string) => {
      if (!currentCard || isRssCard(currentCard)) return;
      answeredRef.current.push({ card_id: currentCard.id, answer });

      if (isLastCard) {
        await flushAnswers();
      } else {
        setCurrentIndex((i) => i + 1);
      }
    },
    [currentCard, isLastCard]
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
        <ActivityIndicator size="large" color="#8B5CF6" />
        <Text style={styles.loadingText}>Loading cards...</Text>
      </SafeAreaView>
    );
  }

  if (submitting) {
    return (
      <SafeAreaView style={styles.centered}>
        <ActivityIndicator size="large" color="#8B5CF6" />
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
        <View style={styles.progress}>
          <Text style={styles.progressText}>
            {currentIndex + 1} / {localCards.length}
          </Text>
        </View>
        <CardSwiper
          key={currentCard.id}
          card={currentCard}
          onAnswer={handleAnswer}
          onSkip={handleSkip}
        />
        <View style={styles.hint}>
          <Text style={styles.hintText}>Swipe up to skip</Text>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f8fafc" },
  centered: {
    flex: 1,
    backgroundColor: "#f8fafc",
    justifyContent: "center",
    alignItems: "center",
  },
  loadingText: {
    marginTop: 16,
    fontSize: 15,
    color: "#64748b",
  },
  progress: {
    paddingHorizontal: 24,
    paddingTop: 12,
    alignItems: "center",
  },
  progressText: {
    fontSize: 13,
    fontWeight: 600,
    color: "#94a3b8",
  },
  hint: {
    paddingBottom: 24,
    alignItems: "center",
  },
  hintText: {
    fontSize: 12,
    color: "#cbd5e1",
  },
});
