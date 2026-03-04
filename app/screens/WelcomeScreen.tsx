import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors, fontFamily } from "../theme";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { OnboardingStackParamList } from "../App";

type Props = NativeStackScreenProps<OnboardingStackParamList, "Welcome">;

export default function WelcomeScreen({ navigation }: Props) {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <Text style={styles.title}>goodscroll</Text>
        <Text style={styles.description}>
          Scroll through decisions, questions, and things worth knowing. Actually
          get things done.
        </Text>
        <TouchableOpacity
          style={styles.button}
          onPress={() => navigation.navigate("Interests")}
        >
          <Text style={styles.buttonText}>Get started</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    justifyContent: "center",
  },
  title: { fontSize: 32, fontWeight: "800", color: colors.textPrimary, fontFamily },
  description: {
    marginTop: 16,
    fontSize: 16,
    color: colors.textSecondary,
    lineHeight: 24,
    fontFamily,
  },
  button: {
    marginTop: 40,
    backgroundColor: colors.accent,
    paddingVertical: 16,
    borderRadius: 0,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.border,
  },
  buttonText: { fontSize: 16, fontWeight: "600", color: colors.background, fontFamily },
});
