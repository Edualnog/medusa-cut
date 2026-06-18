import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

export const runtime = "nodejs";

async function requireUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  return user;
}

// Lista os jobs do usuario (mais recentes primeiro).
export async function GET() {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const admin = createAdminClient();
  const { data } = await admin
    .from("jobs")
    .select("id, source_url, status, progress, stage, error, created_at")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(20);

  return NextResponse.json({ jobs: data ?? [] });
}

// Cria um job de corte (so se o usuario ja conectou a chave da OpenRouter).
export async function POST(req: Request) {
  const user = await requireUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const { url, options } = await req.json().catch(() => ({ url: undefined }));
  if (typeof url !== "string" || !/^https?:\/\/.+/.test(url.trim())) {
    return NextResponse.json({ error: "Cole um link de vídeo válido." }, { status: 400 });
  }

  const admin = createAdminClient();

  // exige a chave conectada (BYO key)
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

  const { data, error } = await admin
    .from("jobs")
    .insert({ user_id: user.id, source_url: url.trim(), options: options ?? {} })
    .select("id")
    .single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({ id: data.id });
}
