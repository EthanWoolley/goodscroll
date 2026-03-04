import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
} from "react-native";
import { Card } from "../api/client";
import { colors, fontFamily } from "../theme";

const { height } = Dimensions.get("window");

interface Props {
  card: Card;
  onAnswer: (answer: string) => void;
  onSkip: () => void;
  projectTitle?: string;
}

export default function MultipleChoiceCard({ card, onAnswer, onSkip, projectTitle }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <View style={styles.card}>
      <Text style={styles.label}>{projectTitle ?? "Question"}</Text>
      <Text style={styles.question}>{card.question}</Text>

      <View style={styles.options}>
        {card.options?.map((opt) => (
          <TouchableOpacity
            key={opt}
            style={[styles.option, selected === opt && styles.optionSelected]}
            onPress={() => setSelected(opt)}
          >
            <Text
              style={[
                styles.optionText,
                selected === opt && styles.optionTextSelected,
              ]}
            >
              {opt}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.actions}>
        <TouchableOpacity style={styles.skipBtn} onPress={onSkip}>
          <Text style={styles.skipText}>Skip</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.answerBtn, !selected && styles.answerBtnDisabled]}
          disabled={!selected}
          onPress={() => selected && onAnswer(selected)}
        >
          <Text style={styles.answerText}>Answer</Text>
        </TouchableOpacity>
      </View>
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
    marginBottom: 16,
    fontFamily,
  },
  question: {
    fontSize: 20,
    fontWeight: "600",
    color: colors.textPrimary,
    lineHeight: 28,
    marginBottom: 24,
    fontFamily,
  },
  options: {
    gap: 10,
    marginBottom: 28,
  },
  option: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 0,
    paddingVertical: 14,
    paddingHorizontal: 18,
    backgroundColor: colors.background,
  },
  optionSelected: {
    borderColor: colors.accent,
    backgroundColor: colors.surfaceRaised,
  },
  optionText: {
    fontSize: 15,
    color: colors.textSecondary,
    fontFamily,
  },
  optionTextSelected: {
    color: colors.accent,
    fontWeight: "600",
    fontFamily,
  },
  actions: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
  },
  skipBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 0,
    backgroundColor: colors.surfaceRaised,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
  },
  skipText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.textSecondary,
    fontFamily,
  },
  answerBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 0,
    backgroundColor: colors.accent,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
  },
  answerBtnDisabled: {
    backgroundColor: colors.surfaceRaised,
  },
  answerText: {
    fontSize: 15,
    fontWeight: "600",
    color: colors.background,
    fontFamily,
  },
});
