import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { OnboardingStackParamList } from "../App";
import { api } from "../api/client";
import { colors, fontFamily } from "../theme";

const INTEREST_CATEGORIES = [
  "Technology",
  "Science",
  "History",
  "Design",
  "Business",
  "Psychology",
  "Philosophy",
  "Health",
  "Economics",
  "Space",
  "Politics",
  "Mathematics",
];

type Props = NativeStackScreenProps<OnboardingStackParamList, "Interests">;

export default function InterestsScreen({ navigation }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggle = useCallback((name: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }, []);

  const handleContinue = useCallback(async () => {
    if (selected.size === 0) return;
    const list = Array.from(selected);
    await AsyncStorage.setItem("user_interests", JSON.stringify(list));
    try {
      await api.postInterests(list);
    } catch (_) {}
    navigation.navigate("FirstProjectPrompt");
  }, [selected, navigation]);

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.title}>Pick your interests</Text>
      </View>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.grid}
        keyboardShouldPersistTaps="handled"
      >
        {INTEREST_CATEGORIES.map((name) => {
          const isSelected = selected.has(name);
          return (
            <TouchableOpacity
              key={name}
              style={[styles.tile, isSelected && styles.tileSelected]}
              onPress={() => toggle(name)}
            >
              <Text
                style={[styles.tileText, isSelected && styles.tileTextSelected]}
              >
                {name}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>
      <View style={styles.footer}>
        <TouchableOpacity
          style={[styles.button, selected.size === 0 && styles.buttonDisabled]}
          onPress={handleContinue}
          disabled={selected.size === 0}
        >
          <Text style={styles.buttonText}>Continue</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 8 },
  title: { fontSize: 24, fontWeight: "700", color: colors.textPrimary, fontFamily },
  scroll: { flex: 1 } as const,
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    padding: 20,
    gap: 12,
  },
  tile: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 0,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  tileSelected: {
    borderColor: colors.accent,
    backgroundColor: colors.surfaceRaised,
  },
  tileText: { fontSize: 14, fontWeight: "500", color: colors.textSecondary, fontFamily },
  tileTextSelected: { color: colors.accent },
  footer: { padding: 24, paddingBottom: 32 },
  button: {
    backgroundColor: colors.accent,
    paddingVertical: 16,
    borderRadius: 0,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.border,
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { fontSize: 16, fontWeight: "600", color: colors.background, fontFamily },
});
