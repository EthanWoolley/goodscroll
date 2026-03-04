import React from "react";
import { View, Text, TouchableOpacity, StyleSheet, Dimensions } from "react-native";
import { colors, fontFamily } from "../theme";

const { height } = Dimensions.get("window");

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
    flex: 1,
    width: "100%",
    minHeight: height,
    backgroundColor: colors.surface,
    borderRadius: 0,
    padding: 36,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.border,
  },
  emoji: {
    fontSize: 40,
    fontWeight: "700",
    color: colors.textPrimary,
    marginBottom: 16,
    fontFamily,
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: colors.textPrimary,
    marginBottom: 12,
    fontFamily,
  },
  message: {
    fontSize: 15,
    color: colors.textSecondary,
    textAlign: "center",
    lineHeight: 22,
    marginBottom: 28,
    fontFamily,
  },
  button: {
    backgroundColor: colors.accent,
    paddingVertical: 14,
    paddingHorizontal: 36,
    borderRadius: 0,
    borderWidth: 1,
    borderColor: colors.border,
  },
  buttonText: {
    color: colors.background,
    fontSize: 15,
    fontWeight: "600",
    fontFamily,
  },
});
