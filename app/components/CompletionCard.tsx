import React from "react";
import { View, Text, TouchableOpacity, StyleSheet, Dimensions } from "react-native";

const { width } = Dimensions.get("window");

interface Props {
  onGoHome: () => void;
}

export default function CompletionCard({ onGoHome }: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.emoji}>✓</Text>
      <Text style={styles.title}>All caught up!</Text>
      <Text style={styles.message}>
        You've given enough context on this project. You can add more detail any
        time.
      </Text>
      <TouchableOpacity style={styles.button} onPress={onGoHome}>
        <Text style={styles.buttonText}>Back to Home</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    width: width - 40,
    backgroundColor: "#fff",
    borderRadius: 20,
    padding: 36,
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 5,
  },
  emoji: {
    fontSize: 40,
    fontWeight: 700,
    color: "#059669",
    marginBottom: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: 700,
    color: "#1a1a2e",
    marginBottom: 12,
  },
  message: {
    fontSize: 15,
    color: "#64748b",
    textAlign: "center",
    lineHeight: 22,
    marginBottom: 28,
  },
  button: {
    backgroundColor: "#8B5CF6",
    paddingVertical: 14,
    paddingHorizontal: 36,
    borderRadius: 12,
  },
  buttonText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: 600,
  },
});
