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
import WorkoutLogScreen from '../screens/WorkoutLogScreen';
import ClinicalLogScreen from '../screens/ClinicalLogScreen';
import AddMemberScreen from '../screens/AddMemberScreen';
import CreateProgramScreen from '../screens/CreateProgramScreen';
import ConfigureComponentsScreen from '../screens/ConfigureComponentsScreen';
import EnrollmentSuccessScreen from '../screens/EnrollmentSuccessScreen';

export type RootStackParamList = {
  Login: undefined;
  MemberList: undefined;
  ProgramOverview: { memberId: string; memberName: string; programId?: string };
  MealCapture: { memberId: string; memberName: string; programId?: string };
  NutritionResult: { memberId: string; mealId: string; memberName: string };
  AdherenceDashboard: { memberId: string; memberName: string };
  WorkoutLog: { memberId: string; memberName: string; programId: string };
  ClinicalLog: { memberId: string; memberName: string; programId: string };
  AddMember: undefined;
  CreateProgram: { memberId: string; memberName: string };
  ConfigureComponents: {
    memberId: string;
    memberName: string;
    programTitle: string;
    startDate: string;
  };
  EnrollmentSuccess: {
    memberName: string;
    programTitle: string;
  };
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
            <Stack.Screen
              name="WorkoutLog"
              component={WorkoutLogScreen}
              options={{ title: 'Log Workout' }}
            />
            <Stack.Screen
              name="ClinicalLog"
              component={ClinicalLogScreen}
              options={{ title: 'Log Measurement' }}
            />
            <Stack.Screen
              name="AddMember"
              component={AddMemberScreen}
              options={{ title: 'Add Family Member' }}
            />
            <Stack.Screen
              name="CreateProgram"
              component={CreateProgramScreen}
              options={{ title: 'Create Program' }}
            />
            <Stack.Screen
              name="ConfigureComponents"
              component={ConfigureComponentsScreen}
              options={{ title: 'Configure Program' }}
            />
            <Stack.Screen
              name="EnrollmentSuccess"
              component={EnrollmentSuccessScreen}
              options={{ title: 'Enrolled!', headerLeft: () => null }}
            />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
