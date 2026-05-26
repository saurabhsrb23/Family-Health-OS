import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { ActivityIndicator, View } from 'react-native';
import { useAuth } from '../context/AuthContext';

import LoginScreen from '../screens/LoginScreen';
import MemberListScreen from '../screens/MemberListScreen';
import ProgramOverviewScreen from '../screens/ProgramOverviewScreen';
import MealCaptureScreen from '../screens/MealCaptureScreen';
import NutritionResultScreen from '../screens/NutritionResultScreen';
import AdherenceDashboard from '../screens/AdherenceDashboard';

export type RootStackParamList = {
  Login: undefined;
  MemberList: undefined;
  ProgramOverview: { memberId: string; memberName: string; programId?: string };
  MealCapture: { memberId: string; programId?: string };
  NutritionResult: { memberId: string; mealId: string };
  AdherenceDashboard: { memberId: string; memberName: string };
};

const Stack = createStackNavigator<RootStackParamList>();

export default function AppNavigator() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color="#10B981" />
      </View>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{
          headerStyle: { backgroundColor: '#10B981' },
          headerTintColor: '#fff',
          headerTitleStyle: { fontWeight: 'bold' },
        }}
      >
        {!isAuthenticated ? (
          <Stack.Screen
            name="Login"
            component={LoginScreen}
            options={{ headerShown: false }}
          />
        ) : (
          <>
            <Stack.Screen
              name="MemberList"
              component={MemberListScreen}
              options={{ title: 'Family Members', headerLeft: () => null }}
            />
            <Stack.Screen
              name="ProgramOverview"
              component={ProgramOverviewScreen}
              options={({ route }) => ({ title: route.params.memberName })}
            />
            <Stack.Screen
              name="MealCapture"
              component={MealCaptureScreen}
              options={{ title: 'Log Meal' }}
            />
            <Stack.Screen
              name="NutritionResult"
              component={NutritionResultScreen}
              options={{ title: 'Nutrition Analysis' }}
            />
            <Stack.Screen
              name="AdherenceDashboard"
              component={AdherenceDashboard}
              options={{ title: 'Progress Dashboard' }}
            />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
