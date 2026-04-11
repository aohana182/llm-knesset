import { useState } from 'react';
import { signInWithGoogle } from '../firebase';
import './LoginPage.css';

function GoogleButton({ onClick, loading }) {
  return (
    <button onClick={onClick} disabled={loading} className="google-btn">
      {loading ? (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="spin">
          <circle cx="12" cy="12" r="10" strokeOpacity="0.25"/>
          <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round"/>
        </svg>
      ) : (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
        </svg>
      )}
      {loading ? 'Signing in…' : 'Sign in with Google'}
    </button>
  );
}

export default function LoginPage({ authError, onSignIn }) {
  const [signingIn, setSigningIn] = useState(false);
  const [signInError, setSignInError] = useState(null);

  async function handleSignIn() {
    setSigningIn(true);
    setSignInError(null);
    try {
      const idToken = await signInWithGoogle();
      const resp = await fetch('/auth/firebase', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ id_token: idToken }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Sign-in failed');
      }
      if (onSignIn) onSignIn();
    } catch (e) {
      if (e.code === 'auth/popup-closed-by-user' || e.code === 'auth/cancelled-popup-request') {
        setSignInError(null);
      } else {
        setSignInError(e.message || 'Sign-in failed. Please try again.');
      }
    } finally {
      setSigningIn(false);
    }
  }

  return (
    <div className="landing">

      {/* ── Nav ───────────────────────────────────────────────── */}
      <nav className="landing-nav">
        <div className="nav-logo">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4a7fc1" strokeWidth="1.6">
            <circle cx="12" cy="12" r="10"/>
            <circle cx="6.5" cy="12" r="1.4" fill="#4a7fc1" stroke="none"/>
            <circle cx="17.5" cy="12" r="1.4" fill="#4a7fc1" stroke="none"/>
            <circle cx="12" cy="6.5" r="1.4" fill="#4a7fc1" stroke="none"/>
            <circle cx="12" cy="17.5" r="1.4" fill="#4a7fc1" stroke="none"/>
            <line x1="6.5" y1="12" x2="17.5" y2="12" stroke="#4a7fc1" strokeWidth="1"/>
            <line x1="12" y1="6.5" x2="12" y2="17.5" stroke="#4a7fc1" strokeWidth="1"/>
          </svg>
          <span>LLM Knesset</span>
        </div>
        <GoogleButton onClick={handleSignIn} loading={signingIn} />
      </nav>

      {/* ── Hero ──────────────────────────────────────────────── */}
      <section className="hero">
        <div className="hero-inner">
          <div className="hero-badge">Multi-model deliberation</div>
          <h1 className="hero-title">
            Stop trusting one AI.<br/>
            <span className="hero-accent">Ask the whole council.</span>
          </h1>
          <p className="hero-sub">
            LLM Knesset sends your question to multiple AI models simultaneously,
            has them critique and rank each other's answers, then synthesizes the best
            response — giving you the collective wisdom of the world's top models.
          </p>

          {(authError || signInError) && (
            <div className="auth-error">
              {signInError || (authError === 'unverified_email' ? 'Your Google account email must be verified.' : 'Sign-in failed. Please try again.')}
            </div>
          )}

          <GoogleButton onClick={handleSignIn} loading={signingIn} />

          <p className="hero-note">Free to use — bring your own OpenRouter API key</p>
        </div>

      </section>

      {/* ── How it works ──────────────────────────────────────── */}
      <section className="how-section">
        <div className="section-inner">
          <h2 className="section-heading">How it works</h2>
          <p className="section-sub">Three deliberate stages, modeled on how expert panels reach consensus.</p>

          <div className="steps">
            <div className="step">
              <div className="step-num">1</div>
              <div className="step-body">
                <div className="step-icon">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                    <circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                  </svg>
                </div>
                <h3>Independent responses</h3>
                <p>Each model answers your question in isolation — no groupthink, no anchoring to what others said first.</p>
              </div>
            </div>

            <div className="step-connector">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </div>

            <div className="step">
              <div className="step-num">2</div>
              <div className="step-body">
                <div className="step-icon">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="M9 11l3 3L22 4"/>
                    <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
                  </svg>
                </div>
                <h3>Anonymous peer review</h3>
                <p>Models read and rank each other's responses — but without knowing who wrote what, eliminating brand bias.</p>
              </div>
            </div>

            <div className="step-connector">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </div>

            <div className="step">
              <div className="step-num">3</div>
              <div className="step-body">
                <div className="step-icon">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                  </svg>
                </div>
                <h3>Chairman synthesis</h3>
                <p>A designated chairman model reads all responses and rankings, then writes a final answer that draws on the best of everything.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Why use it ────────────────────────────────────────── */}
      <section className="why-section">
        <div className="section-inner">
          <h2 className="section-heading">Why people use it</h2>
          <p className="section-sub">One AI can be confidently wrong. A deliberating council is much harder to fool.</p>

          <div className="cards">
            <div className="card">
              <div className="card-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.35-4.35"/>
                  <path d="M11 8v6M8 11h6"/>
                </svg>
              </div>
              <h3>Catch hallucinations</h3>
              <p>When multiple models disagree on a fact, they often cancel each other's errors out. Consensus builds confidence.</p>
            </div>

            <div className="card">
              <div className="card-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M12 20h9"/>
                  <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                </svg>
              </div>
              <h3>Better writing & reasoning</h3>
              <p>Each model has different strengths. The synthesis step picks the best structure, phrasing, and logic from all of them.</p>
            </div>

            <div className="card">
              <div className="card-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                </svg>
              </div>
              <h3>Research & learning</h3>
              <p>Compare how different frontier models reason about complex topics. See where they agree, and where they diverge.</p>
            </div>

            <div className="card">
              <div className="card-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <rect x="3" y="11" width="18" height="10" rx="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
              </div>
              <h3>No vendor lock-in</h3>
              <p>Runs on OpenRouter, so you have access to every major model in one place. Pick your own council, swap models anytime.</p>
            </div>

            <div className="card">
              <div className="card-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
              </div>
              <h3>Private per-user history</h3>
              <p>Every conversation is tied to your Google account. Your questions and answers are never shared with other users.</p>
            </div>

            <div className="card">
              <div className="card-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                </svg>
              </div>
              <h3>Full transparency</h3>
              <p>You can read every individual model's raw response and ranking rationale — nothing is hidden behind a black box.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── FAQ ───────────────────────────────────────────────── */}
      <section className="faq-section">
        <div className="section-inner">
          <h2 className="section-heading">Frequently asked questions</h2>
          <p className="section-sub">Everything you need to know before getting started.</p>

          <div className="faq-list">
            {[
              {
                q: 'What is LLM Knesset?',
                a: 'LLM Knesset is a multi-model AI deliberation platform. Instead of querying a single AI model, it sends your question to multiple frontier models simultaneously — from providers such as OpenAI, Anthropic, Google, and xAI — has them anonymously critique and rank each other\'s responses, then uses a designated chairman model to synthesize the best final answer.',
              },
              {
                q: 'How does the three-stage deliberation process work?',
                a: 'Stage 1 — each model answers your question in complete isolation. Stage 2 — all models receive the responses with model identities hidden, and rank them from best to worst (no brand favoritism). Stage 3 — a chairman model reads all responses and rankings, then writes a comprehensive final answer drawing on the best insights from all models.',
              },
              {
                q: 'Which AI models does LLM Knesset use?',
                a: 'LLM Knesset integrates with OpenRouter, giving access to over 300 frontier models from providers including OpenAI, Anthropic, Google, xAI, Meta, Mistral, and many others. Each user can configure exactly which models form their council and which acts as chairman.',
              },
              {
                q: 'How does it reduce hallucinations and bias?',
                a: 'Two mechanisms: anonymous peer review hides model identities so models cannot favor well-known providers; and multi-model consensus means that when independent models agree on a fact, confidence is much higher. When models disagree, the synthesis step surfaces the uncertainty explicitly.',
              },
              {
                q: 'Is it free to use?',
                a: 'Yes — LLM Knesset is free to use. You just need a Google account to sign in and your own OpenRouter API key to pay for model inference. Many models on OpenRouter are very affordable or free.',
              },
              {
                q: 'Are my conversations private?',
                a: 'Yes. Every conversation is tied to your Google account and is never visible to other users. Conversations are stored per-user and are only accessible after you authenticate.',
              },
            ].map(({ q, a }) => (
              <details key={q} className="faq-item">
                <summary className="faq-q">{q}</summary>
                <p className="faq-a">{a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────────────── */}
      <section className="cta-section">
        <div className="cta-inner">
          <h2>Ready to consult the Knesset?</h2>
          <p>Sign in with your Google account to get started. Bring your OpenRouter API key.</p>
          <GoogleButton onClick={handleSignIn} loading={signingIn} />
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────── */}
      <footer className="landing-footer">
        <div className="nav-logo" style={{ justifyContent: 'center' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.6">
            <circle cx="12" cy="12" r="10"/>
            <circle cx="6.5" cy="12" r="1.2" fill="#94a3b8" stroke="none"/>
            <circle cx="17.5" cy="12" r="1.2" fill="#94a3b8" stroke="none"/>
            <circle cx="12" cy="6.5" r="1.2" fill="#94a3b8" stroke="none"/>
            <circle cx="12" cy="17.5" r="1.2" fill="#94a3b8" stroke="none"/>
          </svg>
          <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>LLM Knesset</span>
        </div>
      </footer>

    </div>
  );
}
