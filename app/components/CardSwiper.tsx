import React, { useRef } from "react";
import {
  View,
  StyleSheet,
  Animated,
  PanResponder,
  Dimensions,
} from "react-native";
import { type FeedCard, isRssCard } from "../api/client";
import type { WikipediaCardData } from "./WikipediaCard";
import MultipleChoiceCard from "./MultipleChoiceCard";
import OpenEndedCard from "./OpenEndedCard";
import RSSCard from "./RSSCard";
import WikipediaCard from "./WikipediaCard";

const { height } = Dimensions.get("window");
const SWIPE_THRESHOLD = 80;

export type SwipeableCard = FeedCard | (WikipediaCardData & { type?: "wikipedia" });

function isWikipediaCard(card: SwipeableCard): card is WikipediaCardData {
  return "source_term" in card && "extract" in card && !("question" in card);
}

interface Props {
  card: SwipeableCard;
  onSwipeUp: () => void;
  onSwipeDown: () => void;
  onAnswer: (answer: string) => void;
  onSkip: () => void;
  projectTitle?: string;
}

export default function CardSwiper({ card, onSwipeUp, onSwipeDown, onAnswer, onSkip, projectTitle }: Props) {
  const translateY = useRef(new Animated.Value(0)).current;

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, gs) => Math.abs(gs.dy) > 10,
      onPanResponderMove: (_, gs) => {
        translateY.setValue(gs.dy);
      },
      onPanResponderRelease: (_, gs) => {
        if (gs.dy < -SWIPE_THRESHOLD) {
          Animated.timing(translateY, {
            toValue: -height,
            duration: 250,
            useNativeDriver: true,
          }).start(() => {
            translateY.setValue(0);
            onSwipeUp();
          });
          return;
        }
        if (gs.dy > SWIPE_THRESHOLD) {
          Animated.timing(translateY, {
            toValue: height,
            duration: 250,
            useNativeDriver: true,
          }).start(() => {
            translateY.setValue(0);
            onSwipeDown();
          });
          return;
        }
        Animated.spring(translateY, {
          toValue: 0,
          useNativeDriver: true,
        }).start();
      },
    })
  ).current;

  const cardContent = isWikipediaCard(card) ? (
    <WikipediaCard card={card} onSkip={onSkip} />
  ) : isRssCard(card) ? (
    <RSSCard card={card} onSkip={onSkip} />
  ) : card.type === "multiple_choice" ? (
    <MultipleChoiceCard card={card} onAnswer={onAnswer} onSkip={onSkip} projectTitle={projectTitle} />
  ) : (
    <OpenEndedCard card={card} onAnswer={onAnswer} onSkip={onSkip} projectTitle={projectTitle} />
  );

  return (
    <View style={styles.container}>
      <Animated.View
        style={[styles.cardWrapper, { transform: [{ translateY }] }]}
        {...panResponder.panHandlers}
      >
        {cardContent}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    width: "100%",
  },
  cardWrapper: {
    flex: 1,
    width: "100%",
    minHeight: height,
    alignSelf: "stretch",
  },
});
