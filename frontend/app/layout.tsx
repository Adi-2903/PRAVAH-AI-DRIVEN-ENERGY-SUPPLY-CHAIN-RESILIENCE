import type {Metadata} from 'next';
import {Inter, JetBrains_Mono, Playfair_Display} from 'next/font/google';
import './globals.css'; // Global styles

// Self-hosted via next/font (build-time fetch, served from the app) so the UI
// keeps its typography even if the venue internet drops — no runtime CDN call.
const inter = Inter({subsets: ['latin'], variable: '--font-inter', display: 'swap'});
const jetbrainsMono = JetBrains_Mono({subsets: ['latin'], variable: '--font-jbmono', display: 'swap'});
const playfair = Playfair_Display({subsets: ['latin'], variable: '--font-playfair', display: 'swap'});

export const metadata: Metadata = {
  title: 'Pravah | Energy Resilience',
  description: 'An AI-powered dashboard for energy supply chain resilience.',
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable} ${playfair.variable}`}>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
