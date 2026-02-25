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
import type { RootStackParamList } from "../App";
import { api, type RssFeed } from "../api/client";

const API_KEY_STORAGE_KEY = "anthropic_api_key";

type Props = NativeStackScreenProps<RootStackParamList, "Settings">;

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
            placeholderTextColor="#94a3b8"
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
              placeholderTextColor="#94a3b8"
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
  safe: { flex: 1, backgroundColor: "#f8fafc" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 12,
    gap: 16,
  },
  backText: { fontSize: 16, color: "#8B5CF6", fontWeight: 500 },
  title: { fontSize: 24, fontWeight: "700", color: "#1a1a2e" },
  scroll: { flex: 1 },
  content: { padding: 24, paddingBottom: 48 },
  section: { marginBottom: 32 },
  sectionTitle: {
    fontSize: 17,
    fontWeight: "600",
    color: "#1a1a2e",
    marginBottom: 12,
  },
  input: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#e2e8f0",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 15,
    color: "#1a1a2e",
  },
  urlInput: { flex: 1 },
  buttonRow: { flexDirection: "row", gap: 12, marginTop: 12 },
  primaryButton: {
    backgroundColor: "#8B5CF6",
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 12,
  },
  primaryButtonText: { fontSize: 15, fontWeight: 600, color: "#fff" },
  secondaryButton: {
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  secondaryButtonText: { fontSize: 15, fontWeight: 500, color: "#64748b" },
  note: {
    marginTop: 12,
    fontSize: 13,
    color: "#64748b",
    lineHeight: 18,
  },
  addRow: { flexDirection: "row", gap: 12, alignItems: "center", marginBottom: 12 },
  addButton: {
    backgroundColor: "#8B5CF6",
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 12,
  },
  addButtonText: { fontSize: 14, fontWeight: 600, color: "#fff" },
  feedRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: "#fff",
    borderRadius: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  feedUrl: { flex: 1, fontSize: 14, color: "#64748b", marginRight: 12 },
  deleteText: { fontSize: 14, color: "#dc2626", fontWeight: 500 },
  muted: { fontSize: 14, color: "#94a3b8", marginTop: 4 },
});
