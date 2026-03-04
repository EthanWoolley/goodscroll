import React from "react";
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
  Linking,
  Dimensions,
} from "react-native";
import { colors, fontFamily } from "../theme";

const { height } = Dimensions.get("window");
const HEADER_IMAGE_HEIGHT = 200;

export interface WikipediaCardData {
  id: string;
  title: string;
  extract: string;
  url: string;
  source_term: string;
  thumbnail_url?: string;
}

interface Props {
  card: WikipediaCardData;
  onSkip: () => void;
}

export default function WikipediaCard({ card, onSkip }: Props) {
  const openArticle = () => {
    if (card.url) Linking.openURL(card.url);
  };

  return (
    <View style={styles.card}>
      {card.thumbnail_url ? (
        <Image
          source={{ uri: card.thumbnail_url }}
          style={styles.headerImage}
          resizeMode="cover"
        />
      ) : null}
      <View style={styles.content}>
        <Text style={styles.title}>{card.title}</Text>
        {card.extract ? (
          <Text style={styles.extract}>{card.extract}</Text>
        ) : null}
        <Text style={styles.sourceTerm}>via: {card.source_term}</Text>
        <TouchableOpacity style={styles.openButton} onPress={openArticle}>
          <Text style={styles.openButtonText}>Read more</Text>
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
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
  },
  headerImage: {
    width: "100%",
    height: HEADER_IMAGE_HEIGHT,
    backgroundColor: colors.border,
  },
  content: {
    flex: 1,
    padding: 24,
  },
  title: {
    fontSize: 18,
    fontWeight: "700",
    color: colors.textPrimary,
    marginBottom: 12,
    lineHeight: 24,
    fontFamily,
  },
  extract: {
    fontSize: 14,
    color: colors.textPrimary,
    lineHeight: 20,
    marginBottom: 12,
    fontFamily,
  },
  sourceTerm: {
    fontSize: 12,
    color: colors.textSecondary,
    marginBottom: 20,
    fontFamily,
  },
  openButton: {
    backgroundColor: colors.accent,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
  },
  openButtonText: { fontSize: 15, fontWeight: "600", color: colors.background, fontFamily },
});
