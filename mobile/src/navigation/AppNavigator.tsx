import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { View, Text, StyleSheet } from 'react-native';
import { useAuth } from '../context/AuthContext';
import LoginScreen from '../screens/LoginScreen';
import MemberListScreen from '../screens/MemberListScreen';
import ProgramOverviewScreen from '../screens/ProgramOverviewScreen';
import MealCaptureScreen from '../screens/MealCaptureScreen';
import NutritionResultScreen from '../screens/NutritionResultScreen';
import AdherenceDashboard from '../screens/AdherenceDashboard';
import LoadingOverlay from '../components/LoadingOverlay';

export type RootStackParamList = {
  Login: undefined;
  Main: undefined;
  ProgramOverview: { memberId: string; memberName: string };
  MealCapture: { memberId: string };
  NutritionResult: { mealId: string; memberId: string };
};

export type TabParamList = {
  Members: undefined;
  Adherence: undefined;
};

const Stack = createStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<TabParamList>();

const TabIcon = ({ label, focused }: { label: string; focused: boolean }) => (
  <View style={styles.tabIcon}>
    <Text style={[styles.tabIconText, focused && styles.tabIconActive]}>
      {label === 'Members' ? '👨‍👩‍👧‍👦' : '📊'}
    </Text>
  </View>
);

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused }) => (
          <TabIcon label={route.name} focused={focused} />
        ),
        tabBarActiveTintColor: '#10B981',
        tabBarInactiveTintColor: '#9CA3AF',
        tabBarStyle: { backgroundColor: '#FFFFFF', borderTopColor: '#E5E7EB' },
        headerStyle: { backgroundColor: '#10B981' },
        headerTintColor: '#FFFFFF',
        headerTitleStyle: { fontWeight: '700' },
      })}
    >
      <Tab.Screen
        name="Members"
        component={MemberListScreen}
        options={{ title: 'Family Members' }}
      />
      <Tab.Screen
        name="Adherence"
        component={AdherenceDashboard}
        options={{ title: 'Dashboard' }}
      />
    </Tab.Navigator>
  );
}

export default function AppNavigator() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <LoadingOverlay />;

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {isAuthenticated ? (
          <>
            <Stack.Screen name="Main" component={MainTabs} />
            <Stack.Screen
              name="ProgramOverview"
              component={ProgramOverviewScreen}
              options={{
                headerShown: true,
                headerStyle: { backgroundColor: '#10B981' },
                headerTintColor: '#FFFFFF',
                headerTitleStyle: { fontWeight: '700' },
                title: 'Care Program',
              }}
            />
            <Stack.Screen
              name="MealCapture"
              component={MealCaptureScreen}
              options={{
                headerShown: true,
                headerStyle: { backgroundColor: '#10B981' },
                headerTintColor: '#FFFFFF',
                title: 'Log Meal',
              }}
            />
            <Stack.Screen
              name="NutritionResult"
              component={NutritionResultScreen}
              options={{
                headerShown: true,
                headerStyle: { backgroundColor: '#10B981' },
                headerTintColor: '#FFFFFF',
                title: 'Nutrition Analysis',
              }}
            />
          </>
        ) : (
          <Stack.Screen name="Login" component={LoginScreen} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  tabIcon: { alignItems: 'center', justifyContent: 'center' },
  tabIconText: { fontSize: 20 },
  tabIconActive: { transform: [{ scale: 1.1 }] },
});
