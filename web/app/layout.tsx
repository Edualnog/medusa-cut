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
  title: "Medusa Clip — cortes de gameplay no seu PC",
  description:
    "Transforme gameplays em clips verticais 9:16 com IA, legenda e enquadramento automático, processando tudo localmente.",
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
