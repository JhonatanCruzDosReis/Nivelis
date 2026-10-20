import { Platform } from "react-native";
import { initializeApp } from "firebase/app";
import {
  initializeAuth,
  getAuth,
  // @ts-ignore — existe no bundle React Native mas falta no typing genérico
  getReactNativePersistence,
} from "firebase/auth";
import { getFirestore } from "firebase/firestore";
import AsyncStorage from "@react-native-async-storage/async-storage";

const firebaseConfig = {
  apiKey: "AIzaSyCLx3-qAOQs-5fEbjYhG9GqmCxbmVP-lVM",
  authDomain: "nivela-ad308.firebaseapp.com",
  databaseURL: "https://nivela-ad308-default-rtdb.firebaseio.com",
  projectId: "nivela-ad308",
  storageBucket: "nivela-ad308.firebasestorage.app",
  messagingSenderId: "770821114254",
  appId: "1:770821114254:web:83c956747de0f9f0a83cdf",
  measurementId: "G-05DTF5N3ZX",
};

const app = initializeApp(firebaseConfig);

// Cross-platform: getReactNativePersistence só existe no bundle RN.
// Em web, getAuth() usa localStorage automaticamente — funciona igual.
export const auth =
  Platform.OS === "web"
    ? getAuth(app)
    : initializeAuth(app, {
        persistence: getReactNativePersistence(AsyncStorage),
      });

export const db = getFirestore(app);