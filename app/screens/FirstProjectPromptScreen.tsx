import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { colors, fontFamily } from "../theme";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { OnboardingStackParamList } from "../App";

type Props = NativeStackScreenProps<OnboardingStackParamList, "FirstProjectPrompt">;

export default function FirstProjectPromptScreen({ navigation }: Props) {
  const handleCreateProject = async () => {
    await AsyncStorage.setItem("has_seen_onboarding", "true");
    (navigation.getParent() as any)?.replace("Main");
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <Text style={styles.prompt}>
          Now create your first project to get started.
        </Text>
        <TouchableOpacity style={styles.button} onPress={handleCreateProject}>
          <Text style={styles.buttonText}>Create project</Text>
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
  prompt: {
    fontSize: 18,
    color: colors.textSecondary,
    lineHeight: 26,
    textAlign: "center",
    fontFamily,
  },
  button: {
    marginTop: 32,
    backgroundColor: colors.accent,
    paddingVertical: 16,
    borderRadius: 0,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.border,
  },
  buttonText: { fontSize: 16, fontWeight: "600", color: colors.background, fontFamily },
});
