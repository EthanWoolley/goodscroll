import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
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

export default function OpenEndedCard({ card, onAnswer, onSkip, projectTitle }: Props) {
  const [text, setText] = useState("");

  return (
    <View style={styles.card}>
      <Text style={styles.label}>{projectTitle ?? "Question"}</Text>
      <Text style={styles.question}>{card.question}</Text>

      <TextInput
        style={styles.input}
        placeholder="Type your answer..."
        placeholderTextColor={colors.textSecondary}
        value={text}
        onChangeText={setText}
        returnKeyType="done"
        onSubmitEditing={() => {
          if (text.trim()) onAnswer(text.trim());
        }}
        blurOnSubmit
      />

      <View style={styles.actions}>
        <TouchableOpacity style={styles.skipBtn} onPress={onSkip}>
          <Text style={styles.skipText}>Skip</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[
            styles.answerBtn,
            !text.trim() && styles.answerBtnDisabled,
          ]}
          disabled={!text.trim()}
          onPress={() => onAnswer(text.trim())}
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
    marginBottom: 20,
    fontFamily,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 0,
    padding: 16,
    fontSize: 15,
    color: colors.textPrimary,
    minHeight: 52,
    backgroundColor: colors.background,
    marginBottom: 24,
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
