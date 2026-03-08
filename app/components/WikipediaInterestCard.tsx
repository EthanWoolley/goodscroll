import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  ScrollView,
  Platform,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { colors, fontFamily } from "../theme";

const { height } = Dimensions.get("window");

/** Bottom tab bar height so card actions stay above it on iOS */
const BOTTOM_NAV_INSET = Platform.OS === "ios" ? 56 : 0;

export interface WikipediaInterestCardData {
  id: string;
  wiki_interest_card_id: string;
  question: string;
  options: string[];
  parent_category?: string;
}

interface Props {
  card: WikipediaInterestCardData;
  onAnswer: (selected: string[]) => void;
  onSkip: () => void;
}

export default function WikipediaInterestCard({ card, onAnswer, onSkip }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const insets = useSafeAreaInsets();
  const bottomPadding = insets.bottom + BOTTOM_NAV_INSET;

  const toggle = (opt: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(opt)) next.delete(opt);
      else next.add(opt);
      return next;
    });
  };

  return (
    <View style={[styles.card, { maxHeight: height - bottomPadding }]}>
      <Text style={styles.label}>EXPLORE YOUR INTERESTS</Text>
      <Text style={styles.question}>{card.question}</Text>
      <Text style={styles.hint}>Select all that apply</Text>

      <ScrollView style={styles.optionsScroll} contentContainerStyle={styles.options}>
        {card.options.map((opt) => {
          const isSelected = selected.has(opt);
          return (
            <TouchableOpacity
              key={opt}
              style={[styles.option, isSelected && styles.optionSelected]}
              onPress={() => toggle(opt)}
            >
              <Text style={[styles.optionText, isSelected && styles.optionTextSelected]}>
                {opt}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      <View style={styles.actions}>
        <TouchableOpacity style={styles.skipBtn} onPress={onSkip}>
          <Text style={styles.skipText}>Skip</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.answerBtn, selected.size === 0 && styles.answerBtnDisabled]}
          disabled={selected.size === 0}
          onPress={() => onAnswer(Array.from(selected))}
        >
          <Text style={styles.answerText}>
            Confirm{selected.size > 0 ? ` (${selected.size})` : ""}
          </Text>
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
    marginBottom: 8,
    fontFamily,
  },
  hint: {
    fontSize: 13,
    color: colors.textSecondary,
    marginBottom: 20,
    fontFamily,
  },
  optionsScroll: {
    flex: 1,
    marginBottom: 28,
  },
  options: {
    gap: 10,
    paddingBottom: 12,
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
