import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import DateTimePicker from "@react-native-community/datetimepicker";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useProjectStore } from "../store/useProjectStore";
import type { RootStackParamList } from "../App";

type Props = NativeStackScreenProps<RootStackParamList, "CreateProject">;

export default function CreateProjectScreen({ navigation }: Props) {
  const { createProject, loading } = useProjectStore();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [projectType, setProjectType] = useState<"creating" | "learning">(
    "creating"
  );
  const [endGoal, setEndGoal] = useState("");
  const [noDeadline, setNoDeadline] = useState(true);
  const [deadline, setDeadline] = useState(new Date());
  const [showDatePicker, setShowDatePicker] = useState(false);

  const canSubmit = title.trim() && description.trim() && !loading;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    try {
      const projectId = await createProject({
        title: title.trim(),
        description: description.trim(),
        project_type: projectType,
        end_goal: endGoal.trim() || undefined,
        deadline: noDeadline ? undefined : deadline.toISOString().split("T")[0],
      });
      navigation.replace("Feed", { projectId });
    } catch (e: any) {
      Alert.alert("Error", e.message || "Failed to create project");
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.heading}>New Project</Text>

        <Text style={styles.label}>Title</Text>
        <TextInput
          style={styles.input}
          placeholder="What are you working on?"
          placeholderTextColor="#94a3b8"
          value={title}
          onChangeText={setTitle}
        />

        <Text style={styles.label}>Description</Text>
        <TextInput
          style={[styles.input, styles.multiline]}
          placeholder="Brain-dump everything about this project..."
          placeholderTextColor="#94a3b8"
          multiline
          textAlignVertical="top"
          value={description}
          onChangeText={setDescription}
        />

        <Text style={styles.label}>Project Type</Text>
        <View style={styles.toggle}>
          <TouchableOpacity
            style={[
              styles.toggleBtn,
              projectType === "creating" && styles.toggleActive,
            ]}
            onPress={() => setProjectType("creating")}
          >
            <Text
              style={[
                styles.toggleText,
                projectType === "creating" && styles.toggleTextActive,
              ]}
            >
              Creating
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[
              styles.toggleBtn,
              projectType === "learning" && styles.toggleActive,
            ]}
            onPress={() => setProjectType("learning")}
          >
            <Text
              style={[
                styles.toggleText,
                projectType === "learning" && styles.toggleTextActive,
              ]}
            >
              Learning
            </Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.label}>End Goal (optional)</Text>
        <TextInput
          style={styles.input}
          placeholder="What does done look like?"
          placeholderTextColor="#94a3b8"
          value={endGoal}
          onChangeText={setEndGoal}
        />

        <Text style={styles.label}>Deadline</Text>
        <View style={styles.deadlineRow}>
          <TouchableOpacity
            style={[styles.toggleBtn, styles.deadlineToggle, noDeadline && styles.toggleActive]}
            onPress={() => setNoDeadline(true)}
          >
            <Text style={[styles.toggleText, noDeadline && styles.toggleTextActive]}>
              Ongoing
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.toggleBtn, styles.deadlineToggle, !noDeadline && styles.toggleActive]}
            onPress={() => {
              setNoDeadline(false);
              setShowDatePicker(true);
            }}
          >
            <Text style={[styles.toggleText, !noDeadline && styles.toggleTextActive]}>
              {noDeadline
                ? "Set date"
                : deadline.toLocaleDateString()}
            </Text>
          </TouchableOpacity>
        </View>

        {showDatePicker && !noDeadline && (
          <DateTimePicker
            value={deadline}
            mode="date"
            minimumDate={new Date()}
            onChange={(_, d) => {
              setShowDatePicker(Platform.OS === "ios");
              if (d) setDeadline(d);
            }}
          />
        )}

        <TouchableOpacity
          style={[styles.submit, !canSubmit && styles.submitDisabled]}
          disabled={!canSubmit}
          onPress={handleSubmit}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.submitText}>Create & Generate Cards</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f8fafc" },
  scroll: { flex: 1 },
  content: { padding: 24, paddingBottom: 60 },
  heading: {
    fontSize: 28,
    fontWeight: 800,
    color: "#1a1a2e",
    marginBottom: 24,
  },
  label: {
    fontSize: 13,
    fontWeight: 600,
    color: "#64748b",
    marginBottom: 6,
    marginTop: 16,
  },
  input: {
    backgroundColor: "#fff",
    borderWidth: 1.5,
    borderColor: "#e2e8f0",
    borderRadius: 12,
    padding: 14,
    fontSize: 15,
    color: "#1e293b",
  },
  multiline: { minHeight: 120 },
  toggle: {
    flexDirection: "row",
    gap: 8,
  },
  toggleBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    backgroundColor: "#f1f5f9",
    alignItems: "center",
  },
  toggleActive: { backgroundColor: "#8B5CF6" },
  toggleText: { fontSize: 14, fontWeight: 600, color: "#64748b" },
  toggleTextActive: { color: "#fff" },
  deadlineRow: { flexDirection: "row", gap: 8 },
  deadlineToggle: { flex: 1 },
  submit: {
    marginTop: 32,
    backgroundColor: "#8B5CF6",
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: "center",
  },
  submitDisabled: { backgroundColor: "#d4d0f0" },
  submitText: { color: "#fff", fontSize: 16, fontWeight: 700 },
});
