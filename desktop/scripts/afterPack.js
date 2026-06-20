// Assinatura ad-hoc do app no macOS (sem conta Apple Developer).
//
// Por quê: no Apple Silicon, um app SEM nenhuma assinatura aparece como
// "está danificado e não pode ser aberto" (bloqueio duro do Gatekeeper). Uma
// assinatura ad-hoc (identidade "-") faz o app rodar; o Gatekeeper passa a mostrar
// só "desenvolvedor não identificado", que o usuário resolve com botão-direito →
// Abrir. (A solução definitiva sem aviso nenhum é Developer ID + notarização, que
// exige conta Apple — adiado por decisão do dono.)
//
// Roda como hook afterPack do electron-builder. Só age no macOS; nas outras
// plataformas retorna sem fazer nada.

const { execFileSync } = require("child_process");
const path = require("path");

exports.default = async function afterPack(context) {
  if (context.electronPlatformName !== "darwin") return;

  const appName = context.packager.appInfo.productFilename; // "Medusa Clip"
  const appPath = path.join(context.appOutDir, `${appName}.app`);

  // --force: re-assina o que já tiver assinatura do toolchain.
  // --deep: assina frameworks/helpers embutidos. --sign -: identidade ad-hoc.
  execFileSync("codesign", ["--force", "--deep", "--sign", "-", appPath], {
    stdio: "inherit",
  });
  console.log(`[afterPack] ad-hoc assinado: ${appPath}`);
};
