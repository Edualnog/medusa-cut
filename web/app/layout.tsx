import type { Metadata } from "next";
import { Press_Start_2P, VT323 } from "next/font/google";
import "./globals.css";

const pixel = Press_Start_2P({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-pixel",
  display: "swap",
});

const body = VT323({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Zorothax — clips de games perfeitos",
  description:
    "Transforme vídeos de games em clips verticais 9:16 com IA. Ganchos, legendas e enquadramento nível Opus Clip.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className={`${pixel.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}
