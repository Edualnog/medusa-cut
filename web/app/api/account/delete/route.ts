// Exclusão de conta (server-side). Usa a service_role — que IGNORA a RLS — então
// SÓ pode rodar aqui no servidor (runtime nodejs), nunca no client/desktop.
// O desktop chama esta rota mandando o access_token do PRÓPRIO usuário; nós
// validamos o token, descobrimos o user id e apagamos apenas aquele usuário.
import { createClient } from "@supabase/supabase-js";

export const runtime = "nodejs";

export async function POST(req: Request) {
  const auth = req.headers.get("authorization") || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7).trim() : "";
  if (!token) {
    return Response.json({ error: "Token ausente." }, { status: 401 });
  }

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !serviceKey) {
    return Response.json({ error: "Servidor mal configurado." }, { status: 500 });
  }

  const admin = createClient(url, serviceKey, { auth: { persistSession: false } });

  // Valida o token e descobre de quem é a conta.
  const { data, error } = await admin.auth.getUser(token);
  if (error || !data?.user) {
    return Response.json({ error: "Sessão inválida." }, { status: 401 });
  }

  // Apaga somente o usuário dono do token.
  const { error: delError } = await admin.auth.admin.deleteUser(data.user.id);
  if (delError) {
    return Response.json({ error: delError.message }, { status: 500 });
  }

  return Response.json({ ok: true });
}
