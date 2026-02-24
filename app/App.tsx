import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { SafeAreaProvider } from "react-native-safe-area-context";
import HomeScreen from "./screens/HomeScreen";
import CreateProjectScreen from "./screens/CreateProjectScreen";
import FeedScreen from "./screens/FeedScreen";

export type RootStackParamList = {
  Home: undefined;
  CreateProject: undefined;
  Feed: { projectId: string };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <SafeAreaProvider>
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Home"
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: "#f8fafc" },
        }}
      >
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
      </Stack.Navigator>
    </NavigationContainer>
    </SafeAreaProvider>
  );
}
