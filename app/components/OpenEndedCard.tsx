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

const { width } = Dimensions.get("window");

interface Props {
  card: Card;
  onAnswer: (answer: string) => void;
  onSkip: () => void;
}

export default function OpenEndedCard({ card, onAnswer, onSkip }: Props) {
  const [text, setText] = useState("");

  return (
    <View style={styles.card}>
      <Text style={styles.label}>OPEN ENDED</Text>
      <Text style={styles.question}>{card.question}</Text>

      <TextInput
        style={styles.input}
        multiline
        placeholder="Type your answer..."
        placeholderTextColor="#94a3b8"
        value={text}
        onChangeText={setText}
        textAlignVertical="top"
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
    color: "#059669",
    letterSpacing: 1.2,
    marginBottom: 16,
  },
  question: {
    fontSize: 20,
    fontWeight: 600,
    color: "#1a1a2e",
    lineHeight: 28,
    marginBottom: 20,
  },
  input: {
    borderWidth: 1.5,
    borderColor: "#e2e8f0",
    borderRadius: 12,
    padding: 16,
    fontSize: 15,
    color: "#1e293b",
    minHeight: 120,
    backgroundColor: "#fafafa",
    marginBottom: 24,
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
    backgroundColor: "#059669",
    alignItems: "center",
  },
  answerBtnDisabled: {
    backgroundColor: "#a7f3d0",
  },
  answerText: {
    fontSize: 15,
    fontWeight: 600,
    color: "#fff",
  },
});
