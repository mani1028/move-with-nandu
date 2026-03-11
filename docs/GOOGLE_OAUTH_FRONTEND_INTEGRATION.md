<!-- Google OAuth Frontend Integration Snippet
   ═══════════════════════════════════════════════════════════════════════════
   Add this to public/app.html to enable Google Sign-In
   ═══════════════════════════════════════════════════════════════════════════
-->

<!-- 1. Add to <head> section (after other <script> imports) -->
<script src="https://accounts.google.com/gsi/client" async defer></script>

<!-- 2. Replace login form div with this HTML (in <body>) -->
<div id="google-login-section" style="display: none; text-align: center; margin: 2rem 0;">
    <!-- Google Sign-In Button -->
    <div id="g_id_onload"
         data-client_id="YOUR_GOOGLE_CLIENT_ID"
         data-callback="handleGoogleLogin"
         style="display: inline-block;">
    </div>
    <div class="g_id_signin" data-type="standard" data-size="large" data-theme="outline"></div>
    <p style="margin-top: 1rem; color: #64748b; font-size: 0.875rem;">or</p>
</div>

<!-- 3. Add this JavaScript handler to <script> section (in app.html) -->
<script>
// ─── GOOGLE OAUTH HANDLER ──────────────────────────────────────────────────

async function handleGoogleLogin(response) {
    const idToken = response.credential;
    if (!idToken) {
        showAuthError('login-error', '⚠️ Google Sign-In failed');
        return;
    }
    
    console.log('[GOOGLE] Received ID token, sending to backend...');
    setButtonLoading('btn-login', true);
    
    try {
        const data = await apiFetch('/api/auth/google/login', {
            method: 'POST',
            body: JSON.stringify({ id_token: idToken })
        });
        
        console.log('[GOOGLE] Login successful!');
        setToken(data.access_token);
        userData = data.user;
        localStorage.setItem('nandu_user', JSON.stringify(data.user));
        initUserUI();
    } catch(e) {
        console.error('[GOOGLE] Login error:', e);
        showAuthError('login-error', '⚠️ ' + e.message);
    } finally {
        setButtonLoading('btn-login', false, '<i data-lucide="log-in" class="h-4 w-4"></i> Login to My Account');
        lucide.createIcons();
    }
}

// Load Google client ID from backend and initialize
async function initGoogleOAuth() {
    try {
        const config = await apiFetch('/api/auth/google/userinfo');
        if (config.google_client_id) {
            console.log('[GOOGLE] OAuth configured, initializing...');
            const googleSection = document.getElementById('google-login-section');
            if (googleSection) googleSection.style.display = 'block';
            
            // Update client_id in the loader element
            const loader = document.getElementById('g_id_onload');
            if (loader) {
                loader.setAttribute('data-client_id', config.google_client_id);
            }
            
            // Re-initialize Google SDK
            if (window.google && google.accounts && google.accounts.id) {
                google.accounts.id.initialize({
                    client_id: config.google_client_id,
                    callback: handleGoogleLogin
                });
                google.accounts.id.renderButton(
                    document.querySelector('.g_id_signin'),
                    { theme: 'outline', size: 'large' }
                );
            }
        }
    } catch(e) {
        console.log('[GOOGLE] OAuth not configured:', e);
        // Google auth not available, hide button
        const googleSection = document.getElementById('google-login-section');
        if (googleSection) googleSection.style.display = 'none';
    }
}

// Call this during page init (add to existing init code)
// initGoogleOAuth();  // Uncomment when adding to app.html

// ─── ONE-TAP SIGN-IN (Optional) ────────────────────────────────────────────
// Uncomment to show auto pop-up on page load:
/*
async function enableOneTapSignIn() {
    try {
        const config = await apiFetch('/api/auth/google/userinfo');
        if (config.google_client_id && window.google) {
            google.accounts.id.initialize({
                client_id: config.google_client_id,
                callback: handleGoogleLogin
            });
            google.accounts.id.prompt();  // Shows One-Tap UI
        }
    } catch(e) {
        console.log('[GOOGLE] One-Tap not available');
    }
}
// Call during init:
// enableOneTapSignIn();
*/

</script>

<!-- 4. Integration Points in Existing App Logic ─────────────────────────────

   In registerWithEmail():
   - After setToken, userData assignment, and localStorage
   - Add: localStorage.setItem('google_linked', 'true');  // Optional
   
   In loginWithEmail():
   - Same as registerWithEmail()
   
   In page load (// ── INIT ── section):
   - After setting default date and splash screen
   - Add: initGoogleOAuth();
   
   In logout/reset:
   - localStorage.removeItem('google_linked');  // Optional
   
─────────────────────────────────────────────────────────────────────────────-->

<!-- Environment: Replace YOUR_GOOGLE_CLIENT_ID with actual ID ──────────────
   Get from: https://console.cloud.google.com/apis/credentials
   Or load dynamically from: /api/auth/google/userinfo endpoint
   ───────────────────────────────────────────────────────────────────────────-->
