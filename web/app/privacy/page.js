import Link from "next/link";

export const metadata = {
  title: "Privacy Policy | Content Factory",
  description: "Privacy Policy for Content Factory.",
};

const updatedAt = "May 9, 2026";

function Section({ title, children }) {
  return (
    <section style={{ display: "grid", gap: 12 }}>
      <h2
        style={{
          margin: 0,
          color: "var(--paper)",
          fontFamily: "var(--font-display)",
          fontSize: "clamp(24px, 4vw, 34px)",
          lineHeight: 1.05,
        }}
      >
        {title}
      </h2>
      <div
        style={{
          display: "grid",
          gap: 12,
          color: "var(--paper-soft)",
          fontFamily: "var(--font-sans)",
          fontSize: 16,
          lineHeight: 1.65,
        }}
      >
        {children}
      </div>
    </section>
  );
}

export default function PrivacyPage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: "var(--ink-0)",
        color: "var(--paper)",
        padding: "clamp(28px, 5vw, 64px)",
      }}
    >
      <div style={{ maxWidth: 900, margin: "0 auto", display: "grid", gap: 36 }}>
        <Link
          href="/"
          style={{
            width: "fit-content",
            color: "var(--paper-dim)",
            textDecoration: "none",
            font: "var(--t-caption)",
          }}
        >
          Content Factory
        </Link>

        <header style={{ display: "grid", gap: 14 }}>
          <p style={{ margin: 0, color: "var(--ember)", font: "var(--t-caption)" }}>
            PRIVACY POLICY
          </p>
          <h1
            style={{
              margin: 0,
              fontFamily: "var(--font-display)",
              fontSize: "clamp(44px, 9vw, 86px)",
              lineHeight: 0.95,
              letterSpacing: 0,
            }}
          >
            Content Factory Privacy
          </h1>
          <p
            style={{
              margin: 0,
              maxWidth: 720,
              color: "var(--paper-soft)",
              fontFamily: "var(--font-sans)",
              fontSize: 18,
              lineHeight: 1.6,
            }}
          >
            Last updated: {updatedAt}. This Privacy Policy explains how Content
            Factory collects, uses, stores, and shares information when you use
            the service.
          </p>
        </header>

        <Section title="1. Information we collect">
          <p>
            We collect account information such as your email address, user ID,
            authentication status, plan, credit balance, and product settings.
            We also collect project information you provide, including prompts,
            scripts, titles, generated media, captions, thumbnails, metadata,
            publishing selections, and files you upload or generate.
          </p>
          <p>
            When you connect a third-party platform such as YouTube or TikTok, we
            receive account identifiers, public profile information, access
            tokens, refresh tokens, scopes, and token expiration data needed to
            perform the actions you authorize.
          </p>
        </Section>

        <Section title="2. How we use information">
          <p>
            We use your information to authenticate you, create and manage
            projects, generate media, render videos, prepare publishing packages,
            connect creator accounts, upload or schedule content when requested,
            maintain credits, provide support, protect the service, and improve
            reliability.
          </p>
          <p>
            We do not sell your personal information. We do not use connected
            TikTok or YouTube accounts to publish content unless you explicitly
            initiate that workflow.
          </p>
        </Section>

        <Section title="3. Third-party services">
          <p>
            Content Factory uses trusted service providers for hosting,
            authentication, databases, storage, media processing, content
            generation, email or support, analytics, and publishing
            integrations. These providers process information only as needed to
            deliver the service.
          </p>
          <p>
            If you connect YouTube or TikTok, your use of those integrations is
            also governed by the respective platform terms and privacy policies.
          </p>
        </Section>

        <Section title="4. OAuth tokens and security">
          <p>
            Access and refresh tokens are stored in encrypted form where
            supported by the service backend. We use tokens only to call platform
            APIs for the connected account actions you request, such as reading
            account profile information, uploading videos, setting metadata, or
            delivering TikTok content to the creator inbox.
          </p>
          <p>
            No method of transmission or storage is perfectly secure, but we use
            reasonable administrative, technical, and organizational safeguards
            to protect account and project data.
          </p>
        </Section>

        <Section title="5. Retention">
          <p>
            We retain account, project, media, and publishing data for as long as
            needed to provide the service, comply with legal obligations, resolve
            disputes, prevent abuse, and maintain operational records. You may
            request deletion of account or project data by contacting us.
          </p>
        </Section>

        <Section title="6. Your choices">
          <p>
            You can choose what content to generate, what platform accounts to
            connect, and whether to upload or publish content. You may revoke
            access to connected platforms through Content Factory where
            available, through the platform account settings, or by contacting
            us.
          </p>
        </Section>

        <Section title="7. Children">
          <p>
            Content Factory is not intended for children under 13. We do not
            knowingly collect personal information from children under 13.
          </p>
        </Section>

        <Section title="8. Contact">
          <p>
            For privacy questions or data requests, contact us at{" "}
            <a href="mailto:admors@gmail.com" style={{ color: "var(--ember)" }}>
              admors@gmail.com
            </a>
            .
          </p>
        </Section>

        <footer
          style={{
            borderTop: "1px solid var(--rule-1)",
            paddingTop: 20,
            color: "var(--paper-dim)",
            font: "var(--t-caption)",
          }}
        >
          Content Factory
        </footer>
      </div>
    </main>
  );
}
