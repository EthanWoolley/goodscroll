import React, { useRef } from "react";
import {
  View,
  StyleSheet,
  Animated,
  PanResponder,
  Dimensions,
  Easing,
} from "react-native";
import { type FeedCard, isRssCard } from "../api/client";
import type { WikipediaCardData } from "./WikipediaCard";
import type { WikipediaInterestCardData } from "./WikipediaInterestCard";
import FlashcardCard from "./FlashcardCard";
import MultipleChoiceCard from "./MultipleChoiceCard";
import OpenEndedCard from "./OpenEndedCard";
import RSSCard from "./RSSCard";
import WikipediaCard from "./WikipediaCard";
import WikipediaInterestCard from "./WikipediaInterestCard";

const { height } = Dimensions.get("window");
const PAN_START_THRESHOLD = 6;
const DRAG_DISMISS_PERCENT = 0.27;
const MAX_DRAG_PERCENT = 0.9;
const SWIPE_VELOCITY_THRESHOLD = 0.65;
const OFFSCREEN_SNAP_DURATION = 180;

export type SwipeableCard =
  | FeedCard
  | (WikipediaCardData & { type?: "wikipedia" })
  | (WikipediaInterestCardData & { type: "wikipedia_interest_question" });

function isWikiInterestCard(card: SwipeableCard): card is WikipediaInterestCardData & { type: "wikipedia_interest_question" } {
  return "type" in card && card.type === "wikipedia_interest_question" && "wiki_interest_card_id" in card;
}

function isWikipediaCard(card: SwipeableCard): card is WikipediaCardData {
  return "source_term" in card && "extract" in card && !("question" in card);
}

interface Props {
  card: SwipeableCard;
  previousCard?: SwipeableCard | null;
  nextCard?: SwipeableCard | null;
  onSwipeUp: () => void;
  onSwipeDown: () => void;
  onAnswer: (answer: string) => void;
  onMultiAnswer?: (selected: string[]) => void;
  onSkip: () => void;
  projectTitle?: string;
}

export default function CardSwiper({
  card,
  previousCard,
  nextCard,
  onSwipeUp,
  onSwipeDown,
  onAnswer,
  onMultiAnswer,
  onSkip,
  projectTitle,
}: Props) {
  const translateY = useRef(new Animated.Value(0)).current;
  const distanceThreshold = height * DRAG_DISMISS_PERCENT;
  const maxDragDistance = height * MAX_DRAG_PERCENT;
  const previousCardTranslateY = translateY.interpolate({
    inputRange: [-height, 0, height],
    outputRange: [-2 * height, -height, 0],
    extrapolate: "clamp",
  });
  const nextCardTranslateY = translateY.interpolate({
    inputRange: [-height, 0, height],
    outputRange: [0, height, 2 * height],
    extrapolate: "clamp",
  });

  const animateToCardCenter = () => {
    Animated.spring(translateY, {
      toValue: 0,
      stiffness: 340,
      damping: 28,
      mass: 0.9,
      useNativeDriver: true,
    }).start();
  };

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, gs) => Math.abs(gs.dy) > PAN_START_THRESHOLD,
      onPanResponderMove: (_, gs) => {
        const clampedDrag = Math.max(-maxDragDistance, Math.min(maxDragDistance, gs.dy));
        translateY.setValue(clampedDrag);
      },
      onPanResponderRelease: (_, gs) => {
        const shouldSwipeUp =
          gs.dy <= -distanceThreshold || (gs.vy <= -SWIPE_VELOCITY_THRESHOLD && gs.dy < 0);
        const shouldSwipeDown =
          gs.dy >= distanceThreshold || (gs.vy >= SWIPE_VELOCITY_THRESHOLD && gs.dy > 0);

        if (shouldSwipeUp) {
          Animated.timing(translateY, {
            toValue: -height,
            duration: OFFSCREEN_SNAP_DURATION,
            easing: Easing.out(Easing.cubic),
            useNativeDriver: true,
          }).start(() => {
            onSwipeUp();
          });
          return;
        }
        if (shouldSwipeDown) {
          Animated.timing(translateY, {
            toValue: height,
            duration: OFFSCREEN_SNAP_DURATION,
            easing: Easing.out(Easing.cubic),
            useNativeDriver: true,
          }).start(() => {
            onSwipeDown();
          });
          return;
        }
        animateToCardCenter();
      },
      onPanResponderTerminate: animateToCardCenter,
    })
  ).current;

  const renderCardContent = (cardToRender: SwipeableCard) =>
    isWikiInterestCard(cardToRender) ? (
      <WikipediaInterestCard
        card={cardToRender}
        onAnswer={(sel) => onMultiAnswer?.(sel)}
        onSkip={onSkip}
      />
    ) : isWikipediaCard(cardToRender) ? (
      <WikipediaCard card={cardToRender} onSkip={onSkip} />
    ) : isRssCard(cardToRender) ? (
      <RSSCard card={cardToRender} onSkip={onSkip} />
    ) : cardToRender.type === "flashcard" ? (
      <FlashcardCard
        card={{
          id: cardToRender.id,
          project_id: cardToRender.project_id,
          type: "flashcard",
          question: cardToRender.question,
          answer: cardToRender.answer ?? "",
          topic: cardToRender.topic ?? null,
        }}
        onAnswer={(response) => onAnswer(response)}
        onSkip={onSkip}
        projectTitle={projectTitle}
      />
    ) : cardToRender.type === "multiple_choice" ? (
      <MultipleChoiceCard card={cardToRender} onAnswer={onAnswer} onSkip={onSkip} projectTitle={projectTitle} />
    ) : (
      <OpenEndedCard card={cardToRender} onAnswer={onAnswer} onSkip={onSkip} projectTitle={projectTitle} />
    );

  return (
    <View style={styles.container}>
      {previousCard ? (
        <Animated.View
          pointerEvents="none"
          style={[styles.adjacentCardWrapper, { transform: [{ translateY: previousCardTranslateY }] }]}
        >
          {renderCardContent(previousCard)}
        </Animated.View>
      ) : null}
      {nextCard ? (
        <Animated.View
          pointerEvents="none"
          style={[styles.adjacentCardWrapper, { transform: [{ translateY: nextCardTranslateY }] }]}
        >
          {renderCardContent(nextCard)}
        </Animated.View>
      ) : null}
      <Animated.View
        style={[styles.currentCardWrapper, { transform: [{ translateY }] }]}
        {...panResponder.panHandlers}
      >
        {renderCardContent(card)}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    width: "100%",
    overflow: "hidden",
  },
  adjacentCardWrapper: {
    ...StyleSheet.absoluteFillObject,
    width: "100%",
    minHeight: height,
    alignSelf: "stretch",
  },
  currentCardWrapper: {
    ...StyleSheet.absoluteFillObject,
    width: "100%",
    minHeight: height,
    alignSelf: "stretch",
  },
});
