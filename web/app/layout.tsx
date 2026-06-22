import type { Metadata } from "next";
import { Press_Start_2P, VT323 } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
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

const TITLE = "Medusa Clip — cortes especializados em gameplay, grátis e no seu PC";
const DESCRIPTION =
  "O recortador especializado em gameplay: acha clutch, fail e clímax que ferramentas genéricas erram. Clips verticais 9:16 com legenda karaokê e enquadramento automático — grátis, com a sua própria chave de IA, processando tudo no seu PC.";
const OG_IMAGE = {
  url: "/og.png",
  width: 1200,
  height: 630,
  alt: "Medusa Clip — feito pra gameplay, seus melhores clips no seu PC",
};

export const metadata: Metadata = {
  metadataBase: new URL("https://medusaclip.com"),
  title: TITLE,
  description: DESCRIPTION,
  openGraph: {
    type: "website",
    siteName: "Medusa Clip",
    locale: "pt_BR",
    url: "https://medusaclip.com",
    title: TITLE,
    description: DESCRIPTION,
    images: [OG_IMAGE],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
    images: [OG_IMAGE.url],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className={`${pixel.variable} ${body.variable}`}>
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
