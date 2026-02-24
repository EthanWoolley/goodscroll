import React, { useRef } from "react";
import {
  View,
  StyleSheet,
  Animated,
  PanResponder,
  Dimensions,
} from "react-native";
import { Card } from "../api/client";
import MultipleChoiceCard from "./MultipleChoiceCard";
import OpenEndedCard from "./OpenEndedCard";

const { height } = Dimensions.get("window");
const SWIPE_THRESHOLD = 80;

interface Props {
  card: Card;
  onAnswer: (answer: string) => void;
  onSkip: () => void;
}

export default function CardSwiper({ card, onAnswer, onSkip }: Props) {
  const translateY = useRef(new Animated.Value(0)).current;

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, gs) => Math.abs(gs.dy) > 10,
      onPanResponderMove: (_, gs) => {
        translateY.setValue(gs.dy);
      },
      onPanResponderRelease: (_, gs) => {
        if (gs.dy < -SWIPE_THRESHOLD) {
          // Swiped up — only meaningful for multiple choice with a selection;
          // handled via button tap instead for reliability
        }
        if (gs.dy > SWIPE_THRESHOLD) {
          Animated.timing(translateY, {
            toValue: height,
            duration: 250,
            useNativeDriver: true,
          }).start(() => {
            translateY.setValue(0);
            onSkip();
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

  return (
    <View style={styles.container}>
      <Animated.View
        style={{ transform: [{ translateY }] }}
        {...panResponder.panHandlers}
      >
        {card.type === "multiple_choice" ? (
          <MultipleChoiceCard card={card} onAnswer={onAnswer} onSkip={onSkip} />
        ) : (
          <OpenEndedCard card={card} onAnswer={onAnswer} onSkip={onSkip} />
        )}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
});
