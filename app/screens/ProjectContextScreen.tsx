import React, { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  ScrollView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { ProjectsStackParamList } from "../App";
import { api } from "../api/client";
import { colors, fontFamily } from "../theme";

type Props = NativeStackScreenProps<ProjectsStackParamList, "ProjectContext">;

export default function ProjectContextScreen({ route, navigation }: Props) {
  const { projectId } = route.params;
  const [context, setContext] = useState("");
  const [projectTitle, setProjectTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getProjectContext(projectId);
      setContext(res.context);
      setProjectTitle(res.project_title ?? "Project");
    } catch (e: any) {
      Alert.alert("Error", e.message || "Failed to load context");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.putProjectContext(projectId, context);
      Alert.alert("Saved", "Context updated.");
    } catch (e: any) {
      Alert.alert("Error", e.message || "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    Alert.alert(
      "Reset context",
      "Regenerate context from your answers? This will remove your custom override.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Reset",
          style: "destructive",
          onPress: async () => {
            setSaving(true);
            try {
              await api.deleteProjectContextOverride(projectId);
              await load();
            } catch (e: any) {
              Alert.alert("Error", e.message || "Failed to reset");
            } finally {
              setSaving(false);
            }
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color="#ffffff" />
          <Text style={styles.loadingText}>Loading...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.title}>{projectTitle}</Text>
      </View>
      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        <TextInput
          style={styles.input}
          value={context}
          onChangeText={setContext}
          multiline
          placeholder="Q&A context..."
          placeholderTextColor={colors.textSecondary}
          editable={!saving}
        />
      </ScrollView>
      <View style={styles.actions}>
        <TouchableOpacity
          style={styles.primaryButton}
          onPress={handleSave}
          disabled={saving}
        >
          <Text style={styles.primaryButtonText}>{saving ? "Saving..." : "Save"}</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={handleReset}
          disabled={saving}
        >
          <Text style={styles.secondaryButtonText}>Reset</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  centered: { flex: 1, justifyContent: "center", alignItems: "center" },
  loadingText: { marginTop: 16, fontSize: 15, color: colors.textSecondary, fontFamily },
  header: { paddingHorizontal: 24, paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: colors.border },
  title: { fontSize: 18, fontWeight: "700", color: colors.textPrimary, fontFamily },
  scroll: { flex: 1 },
  scrollContent: { padding: 24, paddingBottom: 24 },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.textPrimary,
    fontSize: 14,
    fontFamily,
    minHeight: 300,
    padding: 16,
    textAlignVertical: "top",
  },
  actions: { flexDirection: "row", padding: 24, gap: 12, borderTopWidth: 1, borderTopColor: colors.border },
  primaryButton: {
    flex: 1,
    backgroundColor: colors.accent,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
  },
  primaryButtonText: { fontSize: 15, fontWeight: "600", color: colors.background, fontFamily },
  secondaryButton: {
    flex: 1,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
  },
  secondaryButtonText: { fontSize: 15, fontWeight: "600", color: colors.textPrimary, fontFamily },
});
