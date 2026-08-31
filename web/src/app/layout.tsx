import type { Metadata } from "next";
import { Spectral, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";

const spectral = Spectral({
  subsets: ["latin"],
  weight: ["400", "600"],
  style: ["normal", "italic"],
  variable: "--font-spectral",
  display: "swap",
});

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-ibm-plex-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Copiloto Normativo",
  description: "RAG sobre documentos regulatorios mexicanos",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={`${spectral.variable} ${ibmPlexSans.variable}`}>
      <body className="min-h-screen bg-papel font-sans text-tinta antialiased">
        {children}
      </body>
    </html>
  );
}
