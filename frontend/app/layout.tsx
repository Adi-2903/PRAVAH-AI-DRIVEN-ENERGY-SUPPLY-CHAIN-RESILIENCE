import type {Metadata} from 'next';
import {Inter} from 'next/font/google';
import './globals.css'; // Global styles

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
});

export const metadata: Metadata = {
  title: 'Pravah | Energy Resilience',
  description: 'An AI-powered dashboard for energy supply chain resilience.',
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans" suppressHydrationWarning>{children}</body>
    </html>
  );
}
