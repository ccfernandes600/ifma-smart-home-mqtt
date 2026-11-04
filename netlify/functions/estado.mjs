// Guarda o último estado enviado pelo simulador e o entrega ao site.
// O POST exige a chave em ESTADO_CHAVE; o GET é público e só devolve o que já foi validado.
import { getStore } from "@netlify/blobs";
import { timingSafeEqual } from "node:crypto";

const LIMITE_BYTES = 8192;
const TOPICO = /^casa\/(sala|cozinha|quarto|jardim|garagem|perimetro)\/(temp|umidade|luz|co|co2|fumaca|agua|vento|pressao|movimento|campainha|rfid)$/;
const CABECALHOS = { "Content-Type": "application/json", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" };

const responder = (corpo, status = 200) => new Response(JSON.stringify(corpo), { status, headers: CABECALHOS });

function chaveConfere(enviada) {
  const certa = Buffer.from(process.env.ESTADO_CHAVE || "");
  const recebida = Buffer.from(String(enviada || ""));
  return certa.length > 0 && certa.length === recebida.length && timingSafeEqual(certa, recebida);
}

function limparEstado(bruto) {
  if (!bruto || typeof bruto !== "object" || Array.isArray(bruto)) return null;
  const limpo = {};
  for (const [topico, valor] of Object.entries(bruto)) {
    if (TOPICO.test(topico) && typeof valor === "number" && Number.isFinite(valor)) limpo[topico] = valor;
  }
  return limpo;
}

export default async (req) => {
  const loja = getStore("casa");
  if (req.method === "GET") {
    const salvo = await loja.get("ultimo", { type: "json" });
    if (!salvo) return responder({ estado: null });
    return responder({ ...salvo, idade_s: Math.round((Date.now() - salvo.recebido_ms) / 1000) });
  }
  if (req.method !== "POST") return responder({ erro: "metodo" }, 405);

  const texto = await req.text();
  if (texto.length > LIMITE_BYTES) return responder({ erro: "grande" }, 413);
  let dados;
  try { dados = JSON.parse(texto); } catch { return responder({ erro: "json" }, 400); }
  if (!chaveConfere(dados.chave)) return responder({ erro: "chave" }, 401);
  const estado = limparEstado(dados.estado);
  if (!estado) return responder({ erro: "estado" }, 400);

  await loja.setJSON("ultimo", { estado, recebido_ms: Date.now() });
  return responder({ ok: true, topicos: Object.keys(estado).length });
};

export const config = { path: "/api/estado" };
