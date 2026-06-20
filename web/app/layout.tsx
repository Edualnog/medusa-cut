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
  title: "Medusa Clip — cortes especializados em gameplay, grátis e no seu PC",
  description:
    "O recortador especializado em gameplay: acha clutch, fail e clímax que ferramentas genéricas erram. Clips verticais 9:16 com legenda karaokê e enquadramento automático — grátis, com a sua própria chave de IA, processando tudo no seu PC.",
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
