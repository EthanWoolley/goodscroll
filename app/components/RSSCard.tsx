import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Linking,
  Dimensions,
} from "react-native";
import type { RssCard } from "../api/client";

const { width } = Dimensions.get("window");
const CARD_WIDTH = width * 0.9;

interface Props {
  card: RssCard;
  onSkip: () => void;
}

export default function RSSCard({ card, onSkip }: Props) {
  const openArticle = () => {
    if (card.url) Linking.openURL(card.url);
  };

  return (
    <View style={[styles.card, { width: CARD_WIDTH }]}>
      <Text style={styles.source}>{card.source}</Text>
      <Text style={styles.title}>{card.title}</Text>
      {card.summary ? (
        <Text style={styles.summary} numberOfLines={4}>
          {card.summary}
        </Text>
      ) : null}
      <TouchableOpacity style={styles.openButton} onPress={openArticle}>
        <Text style={styles.openButtonText}>Open article</Text>
      </TouchableOpacity>
      <TouchableOpacity style={styles.skipHint} onPress={onSkip}>
        <Text style={styles.skipHintText}>Swipe down to skip</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 24,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 3,
  },
  source: {
    fontSize: 12,
    fontWeight: "600",
    color: "#8B5CF6",
    marginBottom: 8,
    textTransform: "uppercase",
  },
  title: {
    fontSize: 18,
    fontWeight: "700",
    color: "#1a1a2e",
    marginBottom: 12,
    lineHeight: 24,
  },
  summary: {
    fontSize: 14,
    color: "#64748b",
    lineHeight: 20,
    marginBottom: 20,
  },
  openButton: {
    backgroundColor: "#8B5CF6",
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
  },
  openButtonText: { fontSize: 15, fontWeight: 600, color: "#fff" },
  skipHint: { marginTop: 16, alignItems: "center" },
  skipHintText: { fontSize: 12, color: "#94a3b8" },
});
