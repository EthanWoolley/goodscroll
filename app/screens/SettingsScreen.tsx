import React, { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { SafeAreaView } from "react-native-safe-area-context";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { ProjectsStackParamList } from "../App";
import { api, type RssFeed } from "../api/client";
import { colors, fontFamily } from "../theme";

const API_KEY_STORAGE_KEY = "anthropic_api_key";

type Props = NativeStackScreenProps<ProjectsStackParamList, "Settings">;

export default function SettingsScreen({ navigation }: Props) {
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [hasStoredKey, setHasStoredKey] = useState(false);
  const [rssFeeds, setRssFeeds] = useState<RssFeed[]>([]);
  const [rssUrlInput, setRssUrlInput] = useState("");
  const [loadingFeeds, setLoadingFeeds] = useState(true);

  const loadStoredKey = useCallback(async () => {
    const key = await AsyncStorage.getItem(API_KEY_STORAGE_KEY);
    setHasStoredKey(!!key);
    setApiKeyInput("");
  }, []);

  const loadRssFeeds = useCallback(async () => {
    setLoadingFeeds(true);
    try {
      const feeds = await api.getRssFeeds();
      setRssFeeds(feeds);
    } catch {
      setRssFeeds([]);
    } finally {
      setLoadingFeeds(false);
    }
  }, []);

  useEffect(() => {
    loadStoredKey();
  }, [loadStoredKey]);

  useEffect(() => {
    loadRssFeeds();
  }, [loadRssFeeds]);

  const handleSaveApiKey = useCallback(async () => {
    const trimmed = apiKeyInput.trim();
    if (trimmed) {
      await AsyncStorage.setItem(API_KEY_STORAGE_KEY, trimmed);
      setHasStoredKey(true);
    }
  }, [apiKeyInput]);

  const handleClearApiKey = useCallback(async () => {
    await AsyncStorage.removeItem(API_KEY_STORAGE_KEY);
    setApiKeyInput("");
    setHasStoredKey(false);
  }, []);

  const handleAddRssFeed = useCallback(async () => {
    const url = rssUrlInput.trim();
    if (!url) return;
    try {
      const feed = await api.addRssFeed(url);
      setRssFeeds((prev) => [...prev, feed]);
      setRssUrlInput("");
    } catch (e: unknown) {
      Alert.alert("Error", (e as Error)?.message ?? "Failed to add feed");
    }
  }, [rssUrlInput]);

  const handleDeleteRssFeed = useCallback(async (id: string) => {
    try {
      await api.deleteRssFeed(id);
      setRssFeeds((prev) => prev.filter((f) => f.id !== id));
    } catch {
      // ignore
    }
  }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} hitSlop={12}>
          <Text style={styles.backText}>Back</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Settings</Text>
      </View>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>API Key</Text>
          <TextInput
            style={styles.input}
            value={apiKeyInput}
            onChangeText={setApiKeyInput}
            placeholder={
              hasStoredKey ? "Key saved (enter new to replace)" : "Enter your Anthropic API key"
            }
            placeholderTextColor={colors.textSecondary}
            secureTextEntry
            autoCapitalize="none"
            autoCorrect={false}
          />
          <View style={styles.buttonRow}>
            <TouchableOpacity style={styles.primaryButton} onPress={handleSaveApiKey}>
              <Text style={styles.primaryButtonText}>Save</Text>
            </TouchableOpacity>
            {hasStoredKey && (
              <TouchableOpacity style={styles.secondaryButton} onPress={handleClearApiKey}>
                <Text style={styles.secondaryButtonText}>Clear</Text>
              </TouchableOpacity>
            )}
          </View>
          <Text style={styles.note}>
            Your key is stored locally on this device and sent to the backend
            only when making AI requests.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>RSS Feeds</Text>
          <View style={styles.addRow}>
            <TextInput
              style={[styles.input, styles.urlInput]}
              value={rssUrlInput}
              onChangeText={setRssUrlInput}
              placeholder="Feed URL"
              placeholderTextColor={colors.textSecondary}
              autoCapitalize="none"
              autoCorrect={false}
            />
            <TouchableOpacity
              style={styles.addButton}
              onPress={handleAddRssFeed}
              disabled={!rssUrlInput.trim()}
            >
              <Text style={styles.addButtonText}>Add feed</Text>
            </TouchableOpacity>
          </View>
          {loadingFeeds ? (
            <Text style={styles.muted}>Loading feeds...</Text>
          ) : rssFeeds.length === 0 ? (
            <Text style={styles.muted}>No feeds added yet.</Text>
          ) : (
            rssFeeds.map((feed) => (
              <View key={feed.id} style={styles.feedRow}>
                <Text style={styles.feedUrl} numberOfLines={1}>
                  {feed.url}
                </Text>
                <TouchableOpacity
                  onPress={() => handleDeleteRssFeed(feed.id)}
                  hitSlop={8}
                >
                  <Text style={styles.deleteText}>Delete</Text>
                </TouchableOpacity>
              </View>
            ))
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 12,
    gap: 16,
  },
  backText: { fontSize: 16, color: colors.textPrimary, fontWeight: "500", fontFamily },
  title: { fontSize: 24, fontWeight: "700", color: colors.textPrimary, fontFamily },
  scroll: { flex: 1 },
  content: { padding: 24, paddingBottom: 48 },
  section: { marginBottom: 32 },
  sectionTitle: {
    fontSize: 17,
    fontWeight: "600",
    color: colors.textPrimary,
    marginBottom: 12,
    fontFamily,
  },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 0,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 15,
    color: colors.textPrimary,
    fontFamily,
  },
  urlInput: { flex: 1 },
  buttonRow: { flexDirection: "row", gap: 12, marginTop: 12 },
  primaryButton: {
    backgroundColor: colors.accent,
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 0,
    borderWidth: 1,
    borderColor: colors.border,
  },
  primaryButtonText: { fontSize: 15, fontWeight: "600", color: colors.background, fontFamily },
  secondaryButton: {
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 0,
    borderWidth: 1,
    borderColor: colors.border,
  },
  secondaryButtonText: { fontSize: 15, fontWeight: "500", color: colors.textPrimary, fontFamily },
  note: {
    marginTop: 12,
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 18,
    fontFamily,
  },
  addRow: { flexDirection: "row", gap: 12, alignItems: "center", marginBottom: 12 },
  addButton: {
    backgroundColor: colors.accent,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 0,
    borderWidth: 1,
    borderColor: colors.border,
  },
  addButtonText: { fontSize: 14, fontWeight: "600", color: colors.background, fontFamily },
  feedRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: colors.surface,
    borderRadius: 0,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  feedUrl: { flex: 1, fontSize: 14, color: colors.textSecondary, marginRight: 12, fontFamily },
  deleteText: { fontSize: 14, color: colors.destructive, fontWeight: "500", fontFamily },
  muted: { fontSize: 14, color: colors.textSecondary, marginTop: 4, fontFamily },
});
