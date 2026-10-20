import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore"; // Adicionamos isso

const firebaseConfig = {
  apiKey: "AIzaSyCLx3-qAOQs-5fEbjYhG9GqmCxbmVP-lVM",
  authDomain: "nivela-ad308.firebaseapp.com",
  databaseURL: "https://nivela-ad308-default-rtdb.firebaseio.com",
  projectId: "nivela-ad308",
  storageBucket: "nivela-ad308.firebasestorage.app",
  messagingSenderId: "770821114254",
  appId: "1:770821114254:web:83c956747de0f9f0a83cdf",
  measurementId: "G-05DTF5N3ZX"
};

// Inicializa o Firebase
const app = initializeApp(firebaseConfig);

// Inicializa o Firestore e EXPORTA para o outro arquivo usar
export const db = getFirestore(app);