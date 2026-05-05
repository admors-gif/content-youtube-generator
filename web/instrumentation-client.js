import * as Sentry from "@sentry/nextjs";
import { getSentryBaseOptions, getSentryDsn } from "./lib/sentryConfig";

if (getSentryDsn()) {
  Sentry.init({
    ...getSentryBaseOptions(),
  });
}

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
