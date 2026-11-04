// Guarda o último estado enviado pelo simulador e o entrega ao site.
// O POST exige a chave em ESTADO_CHAVE; o GET é público e só devolve o que já foi validado.
import { getStore } from "@netlify/blobs";
import { timingSafeEqual } from "node:crypto";

const LIMITE_BYTES = 8192;
const TOPICO = /^casa\/(sala|cozinha|quarto|jardim|garagem|perimetro)\/(temp|umidade|luz|co|co2|fumaca|agua|vento|pressao|movimento|campainha|rfid)$/;
const TITULO = /^[A-Z ]{1,40}!?$/;
const LINHA_LCD = /^[A-Za-z0-9 !.,]{0,16}$/;
const COR = /^#[0-9a-f]{6}$/;
const CABECALHOS = { "Content-Type": "application/json", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" };

// O CDN responde por até 5 s: muitos visitantes não viram muitas chamadas à função.
const CACHE_CDN = { "Netlify-CDN-Cache-Control": "public, s-maxage=5" };

const responder = (corpo, status = 200, extra = {}) =>
  new Response(JSON.stringify(corpo), { status, headers: { ...CABECALHOS, ...extra } });

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

const inteiro = (v, max) => (Number.isInteger(v) && v >= 0 && v <= max ? v : null);

// Só passa o que o site sabe exibir, e tudo sai daqui em formato conhecido.
function limparResumo(dados) {
  const estado = limparEstado(dados.estado);
  const conectados = inteiro(dados.conectados, 50);
  const publicando = inteiro(dados.publicando, 20);
  const lcd = Array.isArray(dados.lcd) ? dados.lcd.slice(0, 2).map(String) : [];
  const valido = estado
    && TITULO.test(String(dados.titulo))
    && COR.test(String(dados.cor))
    && lcd.every((l) => LINHA_LCD.test(l))
    && (dados.modo === "casa" || dados.modo === "viagem")
    && conectados !== null && publicando !== null;
  if (!valido) return null;
  return { titulo: dados.titulo, cor: dados.cor, lcd, modo: dados.modo, conectados, publicando, estado };
}

export default async (req) => {
  const loja = getStore("casa");
  if (req.method === "GET") {
    const salvo = await loja.get("ultimo", { type: "json" });
    if (!salvo) return responder({ estado: null }, 200, CACHE_CDN);
    return responder({ ...salvo, idade_s: Math.round((Date.now() - salvo.recebido_ms) / 1000) }, 200, CACHE_CDN);
  }
  if (req.method !== "POST") return responder({ erro: "metodo" }, 405);

  const texto = await req.text();
  if (texto.length > LIMITE_BYTES) return responder({ erro: "grande" }, 413);
  let dados;
  try { dados = JSON.parse(texto); } catch { return responder({ erro: "json" }, 400); }
  if (!chaveConfere(dados.chave)) return responder({ erro: "chave" }, 401);
  const resumo = limparResumo(dados);
  if (!resumo) return responder({ erro: "resumo" }, 400);

  await loja.setJSON("ultimo", { ...resumo, recebido_ms: Date.now() });
  return responder({ ok: true, topicos: Object.keys(resumo.estado).length });
};

export const config = { path: "/api/estado" };
