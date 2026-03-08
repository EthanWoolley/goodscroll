import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  ScrollView,
} from "react-native";
import { colors, fontFamily } from "../theme";

const { height } = Dimensions.get("window");

export type FlashcardResponse = "knew" | "partly" | "didnt_know";

export interface FlashcardCardData {
  id: string;
  project_id: string;
  type: "flashcard";
  question: string;
  answer: string;
  topic?: string | null;
}

interface Props {
  card: FlashcardCardData;
  onAnswer: (response: FlashcardResponse) => void;
  onSkip: () => void;
  projectTitle?: string;
}

export default function FlashcardCard({ card, onAnswer, onSkip, projectTitle }: Props) {
  const [revealed, setRevealed] = useState(false);

  return (
    <View style={styles.card}>
      <Text style={styles.label}>{projectTitle ?? "Flashcard"}</Text>
      {card.topic ? (
        <Text style={styles.topic}>{card.topic}</Text>
      ) : null}
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.question}>{card.question}</Text>
        {revealed ? (
          <>
            <View style={styles.answerBlock}>
              <Text style={styles.answerLabel}>Answer</Text>
              <Text style={styles.answer}>{card.answer}</Text>
            </View>
            <Text style={styles.assessmentLabel}>How well did you know it?</Text>
            <View style={styles.assessmentButtons}>
              <TouchableOpacity
                style={[styles.assessmentBtn, styles.knewBtn]}
                onPress={() => onAnswer("knew")}
              >
                <Text style={styles.assessmentBtnText}>Knew it</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.assessmentBtn, styles.partlyBtn]}
                onPress={() => onAnswer("partly")}
              >
                <Text style={styles.assessmentBtnText}>Partly</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.assessmentBtn, styles.didntKnowBtn]}
                onPress={() => onAnswer("didnt_know")}
              >
                <Text style={styles.assessmentBtnText}>Didn't know</Text>
              </TouchableOpacity>
            </View>
          </>
        ) : (
          <TouchableOpacity
            style={styles.revealBtn}
            onPress={() => setRevealed(true)}
          >
            <Text style={styles.revealText}>Reveal</Text>
          </TouchableOpacity>
        )}
      </ScrollView>
      {!revealed && (
        <View style={styles.actions}>
          <TouchableOpacity style={styles.skipBtn} onPress={onSkip}>
            <Text style={styles.skipText}>Skip</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    width: "100%",
    minHeight: height,
    backgroundColor: colors.surface,
    borderRadius: 0,
    padding: 28,
    borderWidth: 1,
    borderColor: colors.border,
  },
  label: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.textSecondary,
    letterSpacing: 1.2,
    marginBottom: 8,
    fontFamily,
  },
  topic: {
    fontSize: 13,
    color: colors.textSecondary,
    marginBottom: 12,
    fontFamily,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 24,
  },
  question: {
    fontSize: 20,
    fontWeight: "600",
    color: colors.textPrimary,
    lineHeight: 28,
    marginBottom: 24,
    fontFamily,
  },
  revealBtn: {
    paddingVertical: 14,
    paddingHorizontal: 24,
    alignSelf: "flex-start",
    backgroundColor: colors.accent,
    borderWidth: 1,
    borderColor: colors.border,
  },
  revealText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.background,
    fontFamily,
  },
  answerBlock: {
    marginBottom: 24,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  answerLabel: {
    fontSize: 11,
    fontWeight: "700",
    color: colors.textSecondary,
    letterSpacing: 1.2,
    marginBottom: 8,
    fontFamily,
  },
  answer: {
    fontSize: 17,
    color: colors.textPrimary,
    lineHeight: 24,
    fontFamily,
  },
  assessmentLabel: {
    fontSize: 13,
    color: colors.textSecondary,
    marginBottom: 12,
    fontFamily,
  },
  assessmentButtons: {
    gap: 10,
  },
  assessmentBtn: {
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderWidth: 1,
    borderColor: colors.border,
  },
  knewBtn: {
    backgroundColor: colors.surfaceRaised,
  },
  partlyBtn: {
    backgroundColor: colors.surfaceRaised,
  },
  didntKnowBtn: {
    backgroundColor: colors.surfaceRaised,
  },
  assessmentBtnText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.textPrimary,
    fontFamily,
  },
  actions: {
    flexDirection: "row",
    justifyContent: "flex-start",
    marginTop: "auto",
  },
  skipBtn: {
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 0,
    backgroundColor: colors.surfaceRaised,
    borderWidth: 1,
    borderColor: colors.border,
  },
  skipText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.textSecondary,
    fontFamily,
  },
});
