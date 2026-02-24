import React, { useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useFocusEffect } from "@react-navigation/native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useProjectStore } from "../store/useProjectStore";
import type { RootStackParamList } from "../App";

type Props = NativeStackScreenProps<RootStackParamList, "Home">;

export default function HomeScreen({ navigation }: Props) {
  const { projects, fetchProjects, loading } = useProjectStore();

  useFocusEffect(
    useCallback(() => {
      fetchProjects();
    }, [])
  );

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Text style={styles.title}>Scroll</Text>
        <Text style={styles.subtitle}>Your projects</Text>
      </View>

      <FlatList
        data={projects}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={fetchProjects} />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No projects yet.</Text>
            <Text style={styles.emptySubtext}>
              Create one to get started!
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() =>
              navigation.navigate("Feed", { projectId: item.id })
            }
          >
            <View style={styles.cardHeader}>
              <Text style={styles.cardTitle} numberOfLines={1}>
                {item.title}
              </Text>
              <View
                style={[
                  styles.badge,
                  item.project_type === "creating"
                    ? styles.badgeCreating
                    : styles.badgeLearning,
                ]}
              >
                <Text style={styles.badgeText}>
                  {item.project_type === "creating" ? "Creating" : "Learning"}
                </Text>
              </View>
            </View>
            <Text style={styles.cardDesc} numberOfLines={2}>
              {item.description}
            </Text>
          </TouchableOpacity>
        )}
      />

      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate("CreateProject")}
      >
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f8fafc" },
  header: { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 8 },
  title: { fontSize: 32, fontWeight: 800, color: "#1a1a2e" },
  subtitle: { fontSize: 14, color: "#94a3b8", marginTop: 4 },
  list: { padding: 20, paddingBottom: 100 },
  empty: { alignItems: "center", paddingTop: 60 },
  emptyText: { fontSize: 17, fontWeight: 600, color: "#64748b" },
  emptySubtext: { fontSize: 14, color: "#94a3b8", marginTop: 4 },
  card: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  cardTitle: { fontSize: 17, fontWeight: 600, color: "#1a1a2e", flex: 1 },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8, marginLeft: 8 },
  badgeCreating: { backgroundColor: "#f3f0ff" },
  badgeLearning: { backgroundColor: "#ecfdf5" },
  badgeText: { fontSize: 11, fontWeight: 700, color: "#8B5CF6" },
  cardDesc: { fontSize: 14, color: "#64748b", lineHeight: 20 },
  fab: {
    position: "absolute",
    right: 24,
    bottom: 40,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#8B5CF6",
    justifyContent: "center",
    alignItems: "center",
    shadowColor: "#8B5CF6",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  fabText: { fontSize: 28, color: "#fff", fontWeight: 500, marginTop: -2 },
});
