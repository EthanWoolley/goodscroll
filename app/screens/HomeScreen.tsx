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
import type { ProjectsStackParamList } from "../App";
import { colors, fontFamily } from "../theme";

type Props = NativeStackScreenProps<ProjectsStackParamList, "Home">;

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
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>Scroll</Text>
            <Text style={styles.subtitle}>Your projects</Text>
          </View>
          <TouchableOpacity
            onPress={() => navigation.navigate("Settings")}
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          >
            <Text style={styles.settingsLink}>Settings</Text>
          </TouchableOpacity>
        </View>
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
  safe: { flex: 1, backgroundColor: colors.background },
  header: { paddingHorizontal: 24, paddingTop: 16, paddingBottom: 8 },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  title: { fontSize: 32, fontWeight: "800", color: colors.textPrimary, fontFamily },
  subtitle: { fontSize: 14, color: colors.textSecondary, marginTop: 4, fontFamily },
  settingsLink: { fontSize: 15, color: colors.textPrimary, fontWeight: "500", fontFamily },
  list: { padding: 20, paddingBottom: 100 },
  empty: { alignItems: "center", paddingTop: 60 },
  emptyText: { fontSize: 17, fontWeight: "600", color: colors.textSecondary, fontFamily },
  emptySubtext: { fontSize: 14, color: colors.textSecondary, marginTop: 4, fontFamily },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 0,
    padding: 20,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  cardTitle: { fontSize: 17, fontWeight: "600", color: colors.textPrimary, flex: 1, fontFamily },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 0, marginLeft: 8, borderWidth: 1, borderColor: colors.border },
  badgeCreating: { backgroundColor: colors.surfaceRaised },
  badgeLearning: { backgroundColor: colors.surfaceRaised },
  badgeText: { fontSize: 11, fontWeight: "700", color: colors.textPrimary, fontFamily },
  cardDesc: { fontSize: 14, color: colors.textSecondary, lineHeight: 20, fontFamily },
  fab: {
    position: "absolute",
    right: 24,
    bottom: 40,
    width: 56,
    height: 56,
    borderRadius: 0,
    backgroundColor: colors.accent,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.border,
  },
  fabText: { fontSize: 28, color: colors.background, fontWeight: "500", marginTop: -2, fontFamily },
});
