import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Predição Brasileirão",
  description: "Predição de estatísticas de partidas do Brasileirão Série A",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
