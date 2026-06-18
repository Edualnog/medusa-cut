import { GetObjectCommand, PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

// Cloudflare R2 (S3-compativel). Credenciais SO no servidor.
function r2() {
  return new S3Client({
    region: "auto",
    endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: process.env.R2_ACCESS_KEY_ID!,
      secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
    },
  });
}

// Link assinado de leitura (preview/download) pra um objeto do bucket de clipes.
export async function signedClipUrl(key: string, expiresIn = 3600): Promise<string> {
  return getSignedUrl(
    r2(),
    new GetObjectCommand({ Bucket: process.env.R2_BUCKET, Key: key }),
    { expiresIn },
  );
}

// Link assinado de ESCRITA (upload direto do navegador pro R2, sem passar pela
// Vercel — evita limite de corpo serverless e aguenta arquivo grande).
export async function signedUploadUrl(
  key: string,
  contentType: string,
  expiresIn = 900,
): Promise<string> {
  return getSignedUrl(
    r2(),
    new PutObjectCommand({ Bucket: process.env.R2_BUCKET, Key: key, ContentType: contentType }),
    { expiresIn },
  );
}
