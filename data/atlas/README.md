# Atlas integrado em 10/09/2026

Dados selecionados de `eliel.html`, fornecido pelo usuário. SHA-256 do original em `atlas.json.meta.sha256`. Extração reproduzível: `python scripts/extract_atlas.py /caminho/eliel.html`. O script lê JSON; não executa o HTML/JavaScript recebido.

- 246 geometrias municipais: caminhos SVG absolutos convertidos para coordenadas latitude/longitude pela transformação linear definida no próprio artefato. Arredondamento a seis casas não melhora a precisão original.
- 17.402 polígonos: matrizes quantizadas UInt16 decodificadas no navegador, preservando anéis e a regra de preenchimento even-odd. IDs podem se repetir entre polígonos; não somar áreas como superfície territorial sem deduplicação/união espacial.
- 23 barragens: coordenadas e classificações do retrato fornecido. Data de extração não informada. Não é monitoramento de segurança em tempo real.
- CFEM municipal e anual, quantidade comercializada por substância, energia e coeficientes municipais, séries de produção beneficiada e investimento em pesquisa.
- Fontes declaradas no original: ANM, SIGBM, CCEE, Anuário Mineral Brasileiro. Não houve nova validação independente dessas fontes nesta integração.

Não se mistura este retrato com a importação MySQL: as coberturas diferem. CFEM 2026 vai até julho; CCEE do artefato vai de abril/2024 a junho/2026. Quantidades, ouro (kg), energia (GWh), coeficientes em kWh/t e ouro em MWh/kg permanecem distintos. Intensidades municipais são razões do artefato, não parâmetros validados por operação.

Do `rodrigo.zip` foram adaptados conceitos de navegação por território, filtros, mapa Leaflet e radar. Os cinco registros e curvas de cenários demonstrativos foram descartados. Não se apresenta projeção fictícia como dado observado.

Arquivos ficam fora de `public/`, servidos somente pelos endpoints autenticados `/api/atlas` e `/api/atlas/processes`. Dicionário de titulares, CPF/CNPJ e empresas individuais não foram incluídos no pacote de processos. Os dados selecionados estão versionados no repositório público por fazerem parte dos artefatos que o usuário autorizou integrar ao projeto; a autenticação do portal não torna o repositório privado.

Leaflet 1.9.4 é servido localmente, com licença em `public/vendor/leaflet/LICENSE`. Tiles de mapa-base OpenStreetMap são carregados sob demanda; sem cache offline ou download em lote. Os polígonos e indicadores locais permanecem utilizáveis caso os tiles falhem.

A camada CFEM usa por padrão o acumulado 2022–julho/2026 dos 246 municípios. O detalhamento anual do artefato contém apenas oito municípios; ausências anuais não são tratadas como zero. A soma dos valores municipais acumulados foi reconciliada com o total dos cinco anos: R$ 867.578.398,91.
