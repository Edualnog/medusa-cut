import { redirect } from "next/navigation";

// Apoio ao Medusa Clip e so via GitHub Sponsors. Mantemos a rota /apoiar
// (links antigos + medusaclip.com/apoiar) redirecionando pra la.
const SPONSORS_URL = "https://github.com/sponsors/Edualnog";

export default function ApoiarPage() {
  redirect(SPONSORS_URL);
}
