import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { RootStackParamList } from "../App";

type Props = NativeStackScreenProps<RootStackParamList, "Welcome">;

export default function WelcomeScreen({ navigation }: Props) {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        <Text style={styles.title}>Scroll</Text>
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
  safe: { flex: 1, backgroundColor: "#f8fafc" },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    justifyContent: "center",
  },
  title: { fontSize: 32, fontWeight: "800", color: "#1a1a2e" },
  description: {
    marginTop: 16,
    fontSize: 16,
    color: "#64748b",
    lineHeight: 24,
  },
  button: {
    marginTop: 40,
    backgroundColor: "#8B5CF6",
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
  },
  buttonText: { fontSize: 16, fontWeight: 600, color: "#fff" },
});
