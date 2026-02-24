import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
} from "react-native";
import { Card } from "../api/client";

const { width } = Dimensions.get("window");

interface Props {
  card: Card;
  onAnswer: (answer: string) => void;
  onSkip: () => void;
}

export default function MultipleChoiceCard({ card, onAnswer, onSkip }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <View style={styles.card}>
      <Text style={styles.label}>MULTIPLE CHOICE</Text>
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
    width: width - 40,
    backgroundColor: "#fff",
    borderRadius: 20,
    padding: 28,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 5,
  },
  label: {
    fontSize: 11,
    fontWeight: 700,
    color: "#8B5CF6",
    letterSpacing: 1.2,
    marginBottom: 16,
  },
  question: {
    fontSize: 20,
    fontWeight: 600,
    color: "#1a1a2e",
    lineHeight: 28,
    marginBottom: 24,
  },
  options: {
    gap: 10,
    marginBottom: 28,
  },
  option: {
    borderWidth: 1.5,
    borderColor: "#e2e8f0",
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 18,
    backgroundColor: "#fafafa",
  },
  optionSelected: {
    borderColor: "#8B5CF6",
    backgroundColor: "#f3f0ff",
  },
  optionText: {
    fontSize: 15,
    color: "#475569",
  },
  optionTextSelected: {
    color: "#8B5CF6",
    fontWeight: 600,
  },
  actions: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
  },
  skipBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    backgroundColor: "#f1f5f9",
    alignItems: "center",
  },
  skipText: {
    fontSize: 15,
    fontWeight: 600,
    color: "#94a3b8",
  },
  answerBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    backgroundColor: "#8B5CF6",
    alignItems: "center",
  },
  answerBtnDisabled: {
    backgroundColor: "#d4d0f0",
  },
  answerText: {
    fontSize: 15,
    fontWeight: 600,
    color: "#fff",
  },
});
