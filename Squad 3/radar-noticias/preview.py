#!/usr/bin/env python3
"""Gera uma pagina HTML para olhar o que o radar coletou, antes de qualquer coisa
subir para o site. Nao consulta a rede e nao altera o banco: so le e escreve o HTML.

    py preview.py --db radar.sqlite --out preview.html
"""
import argparse
import html
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PAGINA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radar de noticias - MINERA Goias</title>
<style>
 :root {
   --fundo:#ffffff; --texto:#1a1a1a; --suave:#666; --linha:#e2e2e2;
   --caixa:#f7f7f8; --marca:#1f6f4a; --marca-fraca:#e6f2ec; --aviso:#8a5a00;
 }
 @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
   --fundo:#16181c; --texto:#e8e8ea; --suave:#9a9aa2; --linha:#2c2f36;
   --caixa:#1e2127; --marca:#5fbf8f; --marca-fraca:#1b3329; --aviso:#d6a54a;
 }}
 :root[data-theme="dark"] {
   --fundo:#16181c; --texto:#e8e8ea; --suave:#9a9aa2; --linha:#2c2f36;
   --caixa:#1e2127; --marca:#5fbf8f; --marca-fraca:#1b3329; --aviso:#d6a54a;
 }
 * { box-sizing:border-box }
 body { margin:0; background:var(--fundo); color:var(--texto); font:15px/1.5
        system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
 .env { max-width:1180px; margin:0 auto; padding:28px 16px 64px }
 h1 { font-size:22px; margin:0 0 4px }
 .sub { color:var(--suave); font-size:13px; margin-bottom:22px }
 .cartoes { display:flex; flex-wrap:wrap; gap:10px; margin-bottom:22px }
 .cartao { background:var(--caixa); border:1px solid var(--linha); border-radius:9px;
           padding:11px 15px; min-width:112px }
 .cartao b { display:block; font-size:21px; line-height:1.25 }
 .cartao span { color:var(--suave); font-size:12px }
 .aviso { background:var(--caixa); border-left:3px solid var(--aviso);
          padding:11px 14px; border-radius:0 7px 7px 0; font-size:13px;
          color:var(--suave); margin-bottom:22px }
 .filtros { display:flex; flex-wrap:wrap; gap:9px; align-items:center; margin-bottom:14px }
 select, input[type=search] { background:var(--fundo); color:var(--texto);
   border:1px solid var(--linha); border-radius:7px; padding:7px 9px; font-size:13px; font-family:inherit }
 input[type=search] { min-width:210px; flex:1 }
 label.chk { display:inline-flex; align-items:center; gap:6px; font-size:13px; color:var(--suave) }
 .conta { color:var(--suave); font-size:13px; margin-bottom:8px }
 table { width:100%; border-collapse:collapse; font-size:13.5px }
 th { text-align:left; font-weight:600; color:var(--suave); font-size:11.5px;
      text-transform:uppercase; letter-spacing:.04em; padding:8px 9px;
      border-bottom:1px solid var(--linha); position:sticky; top:0; background:var(--fundo) }
 td { padding:9px; border-bottom:1px solid var(--linha); vertical-align:top }
 tr:hover td { background:var(--caixa) }
 a { color:var(--marca); text-decoration:none }
 a:hover { text-decoration:underline }
 .data { color:var(--suave); white-space:nowrap; font-variant-numeric:tabular-nums }
 .veiculo { color:var(--suave); white-space:nowrap }
 .tag { display:inline-block; background:var(--marca-fraca); color:var(--marca);
        border-radius:5px; padding:1px 6px; font-size:11.5px; margin:1px 3px 1px 0; white-space:nowrap }
 .go { color:var(--marca); font-weight:600 }
 .goo { color:var(--suave); font-size:11.5px }
 .vazio { padding:36px; text-align:center; color:var(--suave) }
 @media (max-width:760px) { .esconde { display:none } .env { padding:18px 16px 48px } }
</style></head><body><div class="env">
<h1>Radar de noticias &middot; MINERA Goias</h1>
<div class="sub">__SUB__</div>
<div class="cartoes">__CARTOES__</div>
<div class="aviso">__AVISO__</div>
<div class="filtros">
  <input type="search" id="q" placeholder="buscar no titulo...">
  <select id="fsub"><option value="">todas as substancias</option>__OPTSUB__</select>
  <select id="fesc"><option value="">todos os escopos</option>__OPTESC__</select>
  <select id="ftem"><option value="">todos os temas</option>__OPTTEM__</select>
  <label class="chk"><input type="checkbox" id="fset" checked> so do setor</label>
  <label class="chk"><input type="checkbox" id="fgo"> so Goias</label>
  <label class="chk"><input type="checkbox" id="fdir"> so link direto</label>
</div>
<div class="conta" id="conta"></div>
<table><thead><tr>
  <th>Data</th><th>Titulo</th><th class="esconde">Veiculo</th>
  <th class="esconde">Substancias</th><th>Goias</th>
</tr></thead><tbody id="corpo"></tbody></table>
<div class="vazio" id="vazio" style="display:none">Nada com esses filtros.</div>
</div>
<script>
const DADOS = __DADOS__;
const $ = s => document.querySelector(s);
const esc = s => (s||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function desenha() {
  const q = $('#q').value.toLowerCase().trim();
  const sub = $('#fsub').value, escp = $('#fesc').value, tem = $('#ftem').value;
  const so_go = $('#fgo').checked, so_dir = $('#fdir').checked, so_set = $('#fset').checked;
  const vis = DADOS.filter(d =>
      (!q || d.t.toLowerCase().includes(q)) &&
      (!sub || d.c.includes(sub)) &&
      (!escp || d.e === escp) && (!tem || d.m === tem) &&
      (!so_set || d.s) && (!so_go || d.g) && (!so_dir || d.d));
  $('#conta').textContent = vis.length + ' de ' + DADOS.length + ' materias';
  $('#vazio').style.display = vis.length ? 'none' : 'block';
  $('#corpo').innerHTML = vis.slice(0, 600).map(d => `<tr>
    <td class="data">${esc(d.p)}</td>
    <td><a href="${esc(d.l)}" target="_blank" rel="noopener">${esc(d.t)}</a>
        ${d.d ? '' : '<div class="goo">via Google News</div>'}</td>
    <td class="esconde veiculo">${esc(d.f)}</td>
    <td class="esconde">${d.c.map(c => '<span class="tag">' + esc(c) + '</span>').join('')}</td>
    <td>${d.g ? '<span class="go">sim</span>' : ''}</td></tr>`).join('');
}
['#q','#fsub','#fesc','#ftem','#fset','#fgo','#fdir'].forEach(s =>
  $(s).addEventListener('input', desenha));
desenha();
</script></body></html>
"""


def gerar(db, out):
    conn = sqlite3.connect(f'file:{Path(db)}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    linhas = conn.execute('''
        SELECT i.item_id, i.title, i.link, i.published_at, i.first_seen, i.regional, i.setorial,
               s.name AS fonte, s.escopo, s.tema
        FROM news_items i LEFT JOIN news_sources s ON s.source_id = i.source_id
        ORDER BY (i.regional AND i.setorial) DESC, i.setorial DESC,
                 COALESCE(i.published_at, i.first_seen) DESC''').fetchall()
    subs = {}
    for r in conn.execute('SELECT item_id, commodity FROM news_item_commodities'):
        subs.setdefault(r['item_id'], []).append(r['commodity'])
    run = conn.execute('SELECT finished_at, status FROM news_runs WHERE finished_at IS NOT NULL '
                       'ORDER BY started_at DESC LIMIT 1').fetchone()
    fontes_ok = conn.execute("SELECT COUNT(*) FROM news_sources WHERE last_status='ok'").fetchone()[0]
    fontes = conn.execute('SELECT COUNT(*) FROM news_sources').fetchone()[0]
    conn.close()

    dados = []
    for r in linhas:
        data = (r['published_at'] or r['first_seen'] or '')[:10]
        dados.append({'t': r['title'], 'l': r['link'], 'p': data,
                      'f': r['fonte'] or '-', 'e': r['escopo'] or '-', 'm': r['tema'] or '-',
                      'g': 1 if r['regional'] else 0, 's': 1 if r['setorial'] else 0,
                      'd': 0 if ('news.google.com' in (r['link'] or '')
                                 or 'bing.com' in (r['link'] or '')) else 1,
                      'c': sorted(subs.get(r['item_id'], []))})

    regionais = sum(d['g'] for d in dados)
    setoriais = sum(d['s'] for d in dados)
    go_setor = sum(1 for d in dados if d['g'] and d['s'])
    diretos = sum(d['d'] for d in dados)
    todas_subs = sorted({c for d in dados for c in d['c']})
    # O funil, e nao um numero solto: "citam Goias" inclui policia e celebridade,
    # porque a marca regional so exige o nome do estado no texto.
    cartoes = [('coletadas', len(dados)), ('do setor', setoriais), ('citam Goias', regionais),
               ('Goias + setor', go_setor),
               ('link direto', diretos), ('fontes vivas', f'{fontes_ok}/{fontes}')]
    opt = lambda vals: ''.join(f'<option value="{html.escape(v)}">{html.escape(v)}</option>' for v in vals)

    pagina = (PAGINA
        .replace('__SUB__', html.escape(
            f"Ultima coleta: {(run['finished_at'] or '')[:19].replace('T', ' ') if run else '-'} UTC"
            f" ({run['status'] if run else '-'}) | pagina gerada em "
            f"{datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC"))
        .replace('__CARTOES__', ''.join(
            f'<div class="cartao"><b>{v}</b><span>{html.escape(k)}</span></div>' for k, v in cartoes))
        .replace('__AVISO__', html.escape(
            'O numero que vale para relatorio e "Goias + setor". "Citam Goias" sozinho nao serve: a '
            'marca regional so exige o nome do estado no texto, entao ela inclui policia, celebridade e '
            'futebol vindos do G1 Goias. "Do setor" exige substancia mineral ou termo de mineracao no '
            'texto; energia fica de fora dessa marca porque "energia" e "eletrica" sao palavras do '
            'cotidiano. O filtro "so do setor" ja vem ligado. Tudo aqui e verificavel: a materia existe, '
            'o link abre, a data e a que o veiculo declarou e a substancia esta escrita no texto. A '
            'leitura de alta/baixa do prototipo antigo esta desligada e nao aparece. "via Google News" '
            'indica link que passa por uma tela do Google antes de chegar ao veiculo.'))
        .replace('__OPTSUB__', opt(todas_subs))
        .replace('__OPTESC__', opt(sorted({d['e'] for d in dados})))
        .replace('__OPTTEM__', opt(sorted({d['m'] for d in dados})))
        .replace('__DADOS__', json.dumps(dados, ensure_ascii=False)))
    Path(out).write_text(pagina, encoding='utf-8')
    return len(dados), regionais, diretos, out


def main():
    p = argparse.ArgumentParser(description='Gera um HTML para conferir o que o radar coletou.')
    p.add_argument('--db', default='radar.sqlite')
    p.add_argument('--out', default='preview.html')
    a = p.parse_args()
    n, g, d, out = gerar(a.db, a.out)
    print(f'{n} materias ({g} de Goias, {d} com link direto) -> {out}')


if __name__ == '__main__':
    main()
