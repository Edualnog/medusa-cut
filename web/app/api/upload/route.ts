import { NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { signedUploadUrl } from "@/lib/r2";

export const runtime = "nodejs";

const MAX_BYTES = 2 * 1024 * 1024 * 1024; // 2 GB
const OK_TYPES = new Set(["video/mp4", "video/quicktime", "video/webm", "video/x-matroska"]);

// Devolve uma URL assinada pra subir o video direto no R2. O worker depois baixa
// dessa chave (jobs source_kind='upload').
export async function POST(req: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { contentType, size } = await req.json().catch(() => ({}));
  if (typeof contentType !== "string" || !OK_TYPES.has(contentType)) {
    return NextResponse.json({ error: "Formato não suportado (use MP4/MOV/WEBM/MKV)." }, { status: 400 });
  }
  if (typeof size !== "number" || size <= 0 || size > MAX_BYTES) {
    return NextResponse.json({ error: "Arquivo muito grande (máx 2 GB)." }, { status: 400 });
  }

  // exige a chave conectada (BYO key) — mesma regra do job
  const admin = createAdminClient();
  const { data: keyRow } = await admin
    .from("user_api_keys")
    .select("user_id")
    .eq("user_id", user.id)
    .maybeSingle();
  if (!keyRow) {
    return NextResponse.json(
      { error: "Conecte sua chave da OpenRouter primeiro (aba Chaves API)." },
      { status: 400 },
    );
  }

  const ext = contentType === "video/quicktime" ? "mov" : contentType.split("/")[1] || "mp4";
  const key = `uploads/${user.id}/${randomUUID()}.${ext}`;
  const uploadUrl = await signedUploadUrl(key, contentType);

  return NextResponse.json({ uploadUrl, key });
}
