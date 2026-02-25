import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { RootStackParamList } from "../App";

type Props = NativeStackScreenProps<RootStackParamList, "FirstProjectPrompt">;

export default function FirstProjectPromptScreen({ navigation }: Props) {
  const handleCreateProject = async () => {
    await AsyncStorage.setItem("has_seen_onboarding", "true");
    navigation.navigate("CreateProject");
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
  safe: { flex: 1, backgroundColor: "#f8fafc" },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    justifyContent: "center",
  },
  prompt: {
    fontSize: 18,
    color: "#64748b",
    lineHeight: 26,
    textAlign: "center",
  },
  button: {
    marginTop: 32,
    backgroundColor: "#8B5CF6",
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
  },
  buttonText: { fontSize: 16, fontWeight: 600, color: "#fff" },
});
