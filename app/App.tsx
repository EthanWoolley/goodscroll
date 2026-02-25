import React, { useEffect, useState } from "react";
import {
  View,
  ActivityIndicator,
  StyleSheet,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { SafeAreaProvider } from "react-native-safe-area-context";
import HomeScreen from "./screens/HomeScreen";
import CreateProjectScreen from "./screens/CreateProjectScreen";
import FeedScreen from "./screens/FeedScreen";
import WelcomeScreen from "./screens/WelcomeScreen";
import InterestsScreen from "./screens/InterestsScreen";
import FirstProjectPromptScreen from "./screens/FirstProjectPromptScreen";
import SettingsScreen from "./screens/SettingsScreen";

export type RootStackParamList = {
  Welcome: undefined;
  Interests: undefined;
  FirstProjectPrompt: undefined;
  Home: undefined;
  CreateProject: undefined;
  Feed: { projectId: string };
  Settings: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

const ONBOARDING_KEY = "has_seen_onboarding";

export default function App() {
  const [ready, setReady] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(true);

  useEffect(() => {
    AsyncStorage.getItem(ONBOARDING_KEY).then((value) => {
      setShowOnboarding(value !== "true");
      setReady(true);
    });
  }, []);

  if (!ready) {
    return (
      <SafeAreaProvider>
        <View style={styles.loading}>
          <ActivityIndicator size="large" color="#8B5CF6" />
        </View>
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <Stack.Navigator
          initialRouteName={showOnboarding ? "Welcome" : "Home"}
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: "#f8fafc" },
          }}
        >
          <Stack.Screen name="Welcome" component={WelcomeScreen} />
          <Stack.Screen name="Interests" component={InterestsScreen} />
          <Stack.Screen
            name="FirstProjectPrompt"
            component={FirstProjectPromptScreen}
          />
          <Stack.Screen name="Home" component={HomeScreen} />
          <Stack.Screen
            name="CreateProject"
            component={CreateProjectScreen}
            options={{ animation: "slide_from_bottom" }}
          />
          <Stack.Screen
            name="Feed"
            component={FeedScreen}
            options={{ animation: "slide_from_right" }}
          />
          <Stack.Screen name="Settings" component={SettingsScreen} />
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#f8fafc",
  },
});
