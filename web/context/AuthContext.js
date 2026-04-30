"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { auth, db } from "@/lib/firebase";
import {
  onAuthStateChanged,
  signInWithPopup,
  GoogleAuthProvider,
  signOut as firebaseSignOut,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
} from "firebase/auth";
import { doc, getDoc, setDoc, onSnapshot, serverTimestamp } from "firebase/firestore";

const AuthContext = createContext({});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let unsubProfile = null;
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        setUser(firebaseUser);
        
        // Verificar si existe el perfil, si no crear uno
        const profileRef = doc(db, "users", firebaseUser.uid);
        const profileDoc = await getDoc(profileRef);
        if (!profileDoc.exists()) {
          const newProfile = {
            uid: firebaseUser.uid,
            email: firebaseUser.email,
            displayName: firebaseUser.displayName || firebaseUser.email.split("@")[0],
            photoURL: firebaseUser.photoURL || null,
            plan: "free",
            credits: { included: 1, used: 0, extra: 0 },
            totalVideosCreated: 0,
            createdAt: serverTimestamp(),
            lastActive: serverTimestamp(),
          };
          await setDoc(profileRef, newProfile);
        }
        
        // Escuchar cambios en tiempo real (créditos, plan, etc.)
        unsubProfile = onSnapshot(profileRef, (snap) => {
          if (snap.exists()) {
            setProfile(snap.data());
          }
        });
      } else {
        setUser(null);
        setProfile(null);
        if (unsubProfile) unsubProfile();
      }
      setLoading(false);
    });
    return () => {
      unsubscribe();
      if (unsubProfile) unsubProfile();
    };
  }, []);

  const signInWithGoogle = async () => {
    const provider = new GoogleAuthProvider();
    return signInWithPopup(auth, provider);
  };

  const signUpWithEmail = async (email, password, displayName) => {
    const cred = await createUserWithEmailAndPassword(auth, email, password);
    const newProfile = {
      uid: cred.user.uid,
      email,
      displayName,
      photoURL: null,
      plan: "free",
      credits: { included: 1, used: 0, extra: 0 },
      totalVideosCreated: 0,
      createdAt: serverTimestamp(),
      lastActive: serverTimestamp(),
    };
    await setDoc(doc(db, "users", cred.user.uid), newProfile);
    return cred;
  };

  const signInWithEmail = (email, password) => {
    return signInWithEmailAndPassword(auth, email, password);
  };

  const signOut = () => firebaseSignOut(auth);

  return (
    <AuthContext.Provider
      value={{ user, profile, loading, signInWithGoogle, signUpWithEmail, signInWithEmail, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
