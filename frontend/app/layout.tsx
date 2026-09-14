import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KnowYourCompany — Your career research desk",
  description: "Understand a company, inspect the evidence, and build a focused interview preparation brief.",
  openGraph: { title: "KnowYourCompany", description: "Public evidence. Personal direction.", type: "website" },
  robots: { index: false, follow: false },
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
