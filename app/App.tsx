import React, { useEffect, useState } from "react";
import {
  View,
  ActivityIndicator,
  StyleSheet,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useFonts } from "expo-font";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { SafeAreaProvider } from "react-native-safe-area-context";
import HomeScreen from "./screens/HomeScreen";
import CreateProjectScreen from "./screens/CreateProjectScreen";
import FeedScreen from "./screens/FeedScreen";
import IntegratedFeedScreen from "./screens/IntegratedFeedScreen";
import WelcomeScreen from "./screens/WelcomeScreen";
import InterestsScreen from "./screens/InterestsScreen";
import FirstProjectPromptScreen from "./screens/FirstProjectPromptScreen";
import SettingsScreen from "./screens/SettingsScreen";
import ProjectContextScreen from "./screens/ProjectContextScreen";
import { colors, fontFamily } from "./theme";

export type RootStackParamList = {
  Onboarding: undefined;
  Main: undefined;
};

export type TabParamList = {
  Feed: undefined;
  Projects: undefined;
};

export type ProjectsStackParamList = {
  Home: undefined;
  CreateProject: undefined;
  Feed: { projectId: string };
  ProjectContext: { projectId: string };
  Settings: undefined;
};

export type OnboardingStackParamList = {
  Welcome: undefined;
  Interests: undefined;
  FirstProjectPrompt: undefined;
};

const RootStack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<TabParamList>();
const ProjectsStack = createNativeStackNavigator<ProjectsStackParamList>();
const OnboardingStack = createNativeStackNavigator<OnboardingStackParamList>();

const ONBOARDING_KEY = "has_seen_onboarding";

function OnboardingNavigator() {
  return (
    <OnboardingStack.Navigator
      screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }}
    >
      <OnboardingStack.Screen name="Welcome" component={WelcomeScreen} />
      <OnboardingStack.Screen name="Interests" component={InterestsScreen} />
      <OnboardingStack.Screen name="FirstProjectPrompt" component={FirstProjectPromptScreen} />
    </OnboardingStack.Navigator>
  );
}

function ProjectsNavigator() {
  return (
    <ProjectsStack.Navigator
      screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }}
    >
      <ProjectsStack.Screen name="Home" component={HomeScreen} />
      <ProjectsStack.Screen
        name="CreateProject"
        component={CreateProjectScreen}
        options={{ animation: "slide_from_bottom" }}
      />
      <ProjectsStack.Screen
        name="Feed"
        component={FeedScreen}
        options={{ animation: "slide_from_right" }}
      />
      <ProjectsStack.Screen
        name="ProjectContext"
        component={ProjectContextScreen}
      />
      <ProjectsStack.Screen name="Settings" component={SettingsScreen} />
    </ProjectsStack.Navigator>
  );
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border, borderTopWidth: 1 },
        tabBarActiveTintColor: colors.textPrimary,
        tabBarInactiveTintColor: colors.textSecondary,
        tabBarLabelStyle: { fontFamily },
      }}
    >
      <Tab.Screen name="Feed" component={IntegratedFeedScreen} />
      <Tab.Screen name="Projects" component={ProjectsNavigator} />
    </Tab.Navigator>
  );
}

export default function App() {
  const [fontsLoaded] = useFonts({
    "NectoMono-Regular": require("./assets/NectoMono-Regular.otf"),
  });

  const [ready, setReady] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(true);

  useEffect(() => {
    AsyncStorage.getItem(ONBOARDING_KEY).then((value) => {
      setShowOnboarding(value !== "true");
      setReady(true);
    });
  }, []);

  if (!ready || !fontsLoaded) {
    return (
      <SafeAreaProvider>
        <View style={styles.loading}>
          <ActivityIndicator size="large" color={colors.accent} />
        </View>
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <RootStack.Navigator
          initialRouteName={showOnboarding ? "Onboarding" : "Main"}
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: colors.background },
          }}
        >
          <RootStack.Screen name="Onboarding" component={OnboardingNavigator} />
          <RootStack.Screen name="Main" component={MainTabs} />
        </RootStack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.background,
  },
});
