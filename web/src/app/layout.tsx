import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="es">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        {children}
      </body>
    </html>
  );
}
