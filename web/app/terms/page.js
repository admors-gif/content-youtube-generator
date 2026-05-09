import Link from "next/link";

export const metadata = {
  title: "Terms of Service | Content Factory",
  description: "Terms of Service for Content Factory.",
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

export default function TermsPage() {
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
            TERMS OF SERVICE
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
            Content Factory Terms
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
            Last updated: {updatedAt}. These Terms govern access to and use of
            Content Factory, a web application for generating, organizing, and
            publishing creator media assets.
          </p>
        </header>

        <Section title="1. Use of the service">
          <p>
            Content Factory helps users create scripts, images, audio, videos,
            captions, thumbnails, and publishing packages for platforms such as
            YouTube and TikTok. You are responsible for the topics, instructions,
            files, accounts, and publication decisions you submit through the
            service.
          </p>
          <p>
            You agree to use Content Factory only for lawful purposes and in
            accordance with applicable platform rules, intellectual property
            rights, privacy laws, and content policies.
          </p>
        </Section>

        <Section title="2. Accounts and connected platforms">
          <p>
            Some features allow you to connect external creator accounts through
            OAuth, including YouTube and TikTok. We use these connections only to
            perform actions you request, such as preparing metadata, uploading
            videos, setting thumbnails, scheduling content where supported, or
            sending TikTok-ready videos to the creator inbox for final review.
          </p>
          <p>
            You may disconnect connected accounts where the product interface or
            the external platform allows it. You must not connect accounts that
            you do not own or are not authorized to manage.
          </p>
        </Section>

        <Section title="3. User content">
          <p>
            You retain ownership of content you provide and the media generated
            for your projects, subject to any third-party rights, licenses, or
            platform terms that may apply. By using the service, you grant
            Content Factory permission to process, store, render, package, and
            transmit your content solely to provide the requested functionality.
          </p>
          <p>
            You are responsible for reviewing generated output before publishing.
            Generated content may contain mistakes, omissions, or visual/audio
            artifacts, and should not be treated as professional legal, medical,
            financial, or therapeutic advice.
          </p>
        </Section>

        <Section title="4. Publishing and review">
          <p>
            Content Factory is designed to keep creators in control. YouTube
            uploads may be created as private or scheduled according to your
            settings. TikTok upload features use creator authorization and may
            deliver content to TikTok as a draft or inbox item that the creator
            must review and complete inside TikTok.
          </p>
          <p>
            You are responsible for the final publication, privacy settings,
            disclosures, captions, hashtags, and compliance choices for each
            platform.
          </p>
        </Section>

        <Section title="5. Prohibited conduct">
          <p>
            You may not use Content Factory to infringe rights, impersonate
            others, upload malicious files, bypass platform review, manipulate
            accounts, publish unlawful content, or attempt to access data or
            systems without authorization.
          </p>
        </Section>

        <Section title="6. Availability and changes">
          <p>
            We may update, suspend, or discontinue features as the product,
            provider APIs, or platform requirements change. We do not guarantee
            uninterrupted availability, exact publishing outcomes, platform
            approval, or continued access to third-party APIs.
          </p>
        </Section>

        <Section title="7. Limitation of liability">
          <p>
            To the maximum extent permitted by law, Content Factory is provided
            on an &quot;as is&quot; and &quot;as available&quot; basis. We are not liable for lost
            revenue, account restrictions, platform decisions, generated content
            errors, or indirect damages arising from use of the service.
          </p>
        </Section>

        <Section title="8. Contact">
          <p>
            For questions about these Terms, contact us at{" "}
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
