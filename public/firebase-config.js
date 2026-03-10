 // For Firebase JS SDK v7.20.0 and later, measurementId is optional
export const firebaseConfig = {
  apiKey: "AIzaSyBNPwtDTNkV0JXvIOZt36cze9WmPmE6TVE",
  authDomain: "travelwithnandu-25a27.firebaseapp.com",
  projectId: "travelwithnandu-25a27",
  storageBucket: "travelwithnandu-25a27.firebasestorage.app",
  messagingSenderId: "147821864034",
  appId: "1:147821864034:web:c5661cbae40af8df129d3b",
  measurementId: "G-NE50L4ZZJX"
};

// Remove malformed/stale persisted Auth entries that can trigger accounts:lookup 400.
export function cleanupStaleFirebaseAuthStorage() {
  const keyPrefix = `firebase:authUser:${firebaseConfig.apiKey}:`;
  const stores = [window.localStorage, window.sessionStorage];

  for (const store of stores) {
    if (!store) continue;
    for (let i = store.length - 1; i >= 0; i--) {
      const key = store.key(i);
      if (!key || !key.startsWith(keyPrefix)) continue;

      const raw = store.getItem(key);
      if (!raw) {
        store.removeItem(key);
        continue;
      }

      try {
        const parsed = JSON.parse(raw);
        const tokenManager = parsed?.stsTokenManager || {};
        const hasValidShape = typeof parsed?.uid === 'string'
          && typeof parsed?.apiKey === 'string'
          && parsed.apiKey === firebaseConfig.apiKey
          && typeof tokenManager?.refreshToken === 'string'
          && tokenManager.refreshToken.length > 0;

        if (!hasValidShape) {
          store.removeItem(key);
        }
      } catch {
        store.removeItem(key);
      }
    }
  }
}