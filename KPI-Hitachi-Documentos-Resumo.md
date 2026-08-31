# KPI Hitachi - Blocos de Codigo para Importacao e Gestao de Documentos

Este arquivo foi montado para reaproveitamento direto em outro projeto.

Ele contem:

- HTML dos campos de upload
- CSS dos botoes de documento
- funcoes JavaScript para:
  - ler ZIP de holerite
  - ler multiplos PDFs de comprovante de pagamento
  - ler multiplos PDFs de comprovante de adiantamento
  - detectar assinatura digital no holerite
  - cruzar o nome do colaborador com a lista do mes
  - abrir documento salvo
  - excluir documento individual por colaborador
  - importar sem apagar o que ja foi localizado

## 1. HTML - area de upload

```html
<section class="card pad" style="margin-bottom:14px">
  <div class="chead">
    <span class="ti2">Importar documentos dos colaboradores</span>
    <span class="eyebrow">Vinculo automatico</span>
  </div>

  <div class="import-doc-grid">
    <label>Arquivo holerite (ZIP)
      <input id="hitachiDocsZip" type="file" accept=".zip,application/zip">
    </label>

    <label>Comprovantes de pagamento (1 ou mais PDFs)
      <input id="hitachiDocsPagamento" type="file" accept="application/pdf" multiple>
    </label>

    <label>Comprovantes de adiantamento (1 ou mais PDFs)
      <input id="hitachiDocsAdiantamento" type="file" accept="application/pdf" multiple>
    </label>

    <button class="soft" type="button" id="hitachiDocsImport">
      <span data-icon="folder"></span>Importar documentos
    </button>
  </div>

  <div class="import-help">
    <b>Como o portal vai conferir</b>
    O ZIP de holerites sera cruzado pelo nome do colaborador e o sistema vai verificar se o PDF tem assinatura digital.
    Os comprovantes em PDF serao lidos por pagina para localizar o nome de cada colaborador e atualizar os status automaticamente.
    Voce pode selecionar varios PDFs nos dois campos de comprovantes.
  </div>

  <div class="upload-note" id="hitachiDocsSummary">
    Carregue o ZIP de holerites e os PDFs de comprovantes para atualizar os status do mes selecionado.
  </div>
</section>
```

## 2. CSS - botoes e bloco de documentos

```css
.docmeta {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}

.docline {
  display: grid;
  gap: 6px;
}

.docmeta small {
  font-size: 10px;
  color: var(--mut);
  line-height: 1.35;
}

.doc-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.doc-open {
  display: inline-flex;
}

.doc-open-btn {
  border: 1px solid #d7e3ff;
  background: #eef4ff;
  color: #1d4ed8;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  box-shadow: 0 1px 2px rgba(29, 78, 216, 0.08);
}

.doc-open-btn:hover {
  background: #e2edff;
  border-color: #bfd2ff;
}

.doc-delete-btn {
  border: 1px solid rgba(210, 59, 59, 0.18);
  background: #fff5f5;
  color: var(--red);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  box-shadow: 0 1px 2px rgba(210, 59, 59, 0.05);
}

.doc-delete-btn:hover {
  background: #ffeceb;
  border-color: rgba(210, 59, 59, 0.28);
}
```

## 3. Dependencias usadas no navegador

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
```

## 4. Funcoes base para leitura de PDF

```js
async function readPdfPages(file) {
  if (!window.pdfjsLib) throw new Error('Leitor de PDF indisponivel no navegador.');
  pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
  const buffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: buffer }).promise;
  const pages = [];

  for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
    const page = await pdf.getPage(pageNumber);
    const content = await page.getTextContent();
    const text = content.items.map(item => item.str).join('\n');
    pages.push({ pageNumber, text });
  }

  return pages;
}

function binaryPdfText(buffer) {
  return new TextDecoder('latin1').decode(buffer);
}

function pdfHasDigitalSignature(buffer) {
  const text = binaryPdfText(buffer);
  return /\/FT\s*\/Sig|\/Type\s*\/Sig|Assinatura Digital/i.test(text);
}
```

## 5. Funcoes para localizar nome do colaborador

```js
function extractPagamentoName(text) {
  const normalized = stripAccents(text || '');
  const lineMatch = normalized.match(/Nome\:\s*([^\n\r]+)/i);

  if (lineMatch && lineMatch[1]) {
    return lineMatch[1]
      .replace(/\s+(Ag\S+ncia|Conta corrente|Valor)\:.*$/i, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  const flat = normalized.replace(/\s+/g, ' ');
  const match = flat.match(/Nome\:\s*([A-Z\s'`.\-]{6,}?)\s+(Ag\S+ncia|Conta corrente|Valor)\:/i);
  if (!match) return '';

  return (match[1] || '').replace(/\s+/g, ' ').trim();
}

function extractAdiantamentoName(text) {
  const normalized = stripAccents(text || '');

  const direct = normalized.match(/Nome do Funcionario[\s\S]{0,120}?\n?(\d+\s+)?([A-Z][A-Z\s'`.\-]{6,})\s+\d{5,}/i);
  if (direct && direct[2]) return direct[2].replace(/\s+/g, ' ').trim();

  const fallback = normalized.match(/Mensalista[\s\S]{0,120}?(\d{3,5})\s+([A-Z][A-Z\s'`.\-]{6,})\s+\d{5,}/i);
  if (fallback && fallback[2]) return fallback[2].replace(/\s+/g, ' ').trim();

  const lineMatch = normalized.match(/Nome(?:\s+do\s+Funcionario)?\s*[:\-]\s*([^\n\r]+)/i);
  if (lineMatch && lineMatch[1]) {
    return lineMatch[1]
      .replace(/\s+(Matricula|CPF|Setor|Departamento|Conta|Agencia)\b.*$/i, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  return '';
}

function detectCollaboratorFromPageText(text, rows) {
  const normalizedText = norm((text || '').replace(/\s+/g, ' '));
  if (!normalizedText) return '';

  const candidates = rows
    .map(row => row.colaborador)
    .filter(Boolean)
    .sort((a, b) => norm(b).length - norm(a).length);

  for (const name of candidates) {
    if (normalizedText.includes(norm(name))) return name;
  }

  return '';
}
```

## 6. Armazenamento local dos PDFs no navegador

```js
const HITACHI_DOC_DB = 'portal-mse-hitachi-docs';
const HITACHI_DOC_STORE = 'documents';

function openHitachiDocDatabase() {
  return new Promise((resolve, reject) => {
    if (!window.indexedDB) {
      reject(new Error('Armazenamento local de documentos indisponivel neste navegador.'));
      return;
    }

    const request = window.indexedDB.open(HITACHI_DOC_DB, 1);

    request.onupgradeneeded = event => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(HITACHI_DOC_STORE)) {
        db.createObjectStore(HITACHI_DOC_STORE, { keyPath: 'key' });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error('Nao foi possivel abrir o armazenamento local.'));
  });
}

async function saveHitachiDocumentBlob(key, blob, meta = {}) {
  const db = await openHitachiDocDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(HITACHI_DOC_STORE, 'readwrite');
    tx.objectStore(HITACHI_DOC_STORE).put({
      key,
      blob,
      fileName: meta.fileName || '',
      pageNumber: meta.pageNumber ?? null,
      savedAt: new Date().toISOString()
    });
    tx.oncomplete = () => resolve(key);
    tx.onerror = () => reject(tx.error || new Error('Nao foi possivel salvar o documento localmente.'));
  });
}

async function getHitachiDocumentBlob(key) {
  const db = await openHitachiDocDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(HITACHI_DOC_STORE, 'readonly');
    const request = tx.objectStore(HITACHI_DOC_STORE).get(key);
    request.onsuccess = () => resolve(request.result || null);
    request.onerror = () => reject(request.error || new Error('Nao foi possivel abrir o documento local.'));
  });
}
```

## 7. Abrir documento salvo

```js
async function openStoredHitachiDocument(storageKey, pageNumber = null) {
  if (!storageKey) {
    alert('Nenhum documento foi salvo para este item.');
    return;
  }

  try {
    const stored = await getHitachiDocumentBlob(storageKey);
    if (!stored || !stored.blob) {
      alert('Este documento nao esta salvo neste navegador. Importe o arquivo novamente para abrir aqui.');
      return;
    }

    const url = URL.createObjectURL(stored.blob);
    const suffix = pageNumber ? `#page=${pageNumber}` : '';
    window.open(`${url}${suffix}`, '_blank', 'noopener');
    window.setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (error) {
    console.error(error);
    alert('Nao foi possivel abrir o documento agora.');
  }
}

window.openStoredHitachiDocument = openStoredHitachiDocument;
```

## 8. Excluir documento individual por colaborador

```js
async function removeHitachiDocument(id, docType) {
  const item = hitachiCollaborators.find(entry => entry.id === id);
  if (!item) return;

  const labels = {
    holerite: 'holerite',
    comprovantePagamento: 'comprovante de pagamento',
    comprovanteAdiantamento: 'comprovante de adiantamento'
  };

  const confirmed = window.confirm(`Excluir o ${labels[docType] || 'documento'} vinculado apenas deste colaborador?`);
  if (!confirmed) return;

  const payload = { ...item };

  if (docType === 'holerite') {
    payload.holerite = payload.situacao === 'Ativo' ? 'PENDENTE' : 'N/A';
    payload.holeriteArquivo = '';
    payload.holeriteStorageKey = '';
  }

  if (docType === 'comprovantePagamento') {
    payload.comprovantePagamento = 'PENDENTE';
    payload.comprovantePagamentoArquivo = '';
    payload.comprovantePagamentoStorageKey = '';
    payload.comprovantePagamentoPage = null;
  }

  if (docType === 'comprovanteAdiantamento') {
    payload.comprovanteAdiantamento = 'PENDENTE';
    payload.comprovanteAdiantamentoArquivo = '';
    payload.comprovanteAdiantamentoStorageKey = '';
    payload.comprovanteAdiantamentoPage = null;
  }

  await saveHitachiCollaborator(payload);
}

window.removeHitachiDocument = removeHitachiDocument;
```

## 9. Importacao de documentos sem apagar os que ja existem

### Regra aplicada

Quando um novo lote e importado:

- o sistema localiza os documentos novos
- atualiza apenas os documentos encontrados no novo lote
- preserva os documentos que ja estavam vinculados no colaborador

### Funcao principal de importacao

```js
async function importHitachiDocumentFiles() {
  const zipInput = document.getElementById('hitachiDocsZip');
  const pagamentoInput = document.getElementById('hitachiDocsPagamento');
  const adiantamentoInput = document.getElementById('hitachiDocsAdiantamento');
  const summaryBox = document.getElementById('hitachiDocsSummary');
  const monthKey = currentHitachiMonth();
  const rows = hitachiRowsForMonth(monthKey);

  if (!rows.length) {
    summaryBox.textContent = 'Nao ha colaboradores cadastrados nesse mes para vincular os documentos.';
    return;
  }

  const holeriteZip = zipInput.files && zipInput.files[0];
  const pagamentoFiles = [...(pagamentoInput.files || [])];
  const adiantamentoFiles = [...(adiantamentoInput.files || [])];

  if (!holeriteZip && !pagamentoFiles.length && !adiantamentoFiles.length) {
    summaryBox.textContent = 'Selecione ao menos um ZIP ou PDF para importar os documentos.';
    return;
  }

  summaryBox.textContent = 'Lendo documentos e localizando os colaboradores...';

  try {
    const docsByName = new Map();

    const ensureDocEntry = key => {
      if (!docsByName.has(key)) {
        docsByName.set(key, {
          holerite: null,
          comprovantePagamento: null,
          comprovanteAdiantamento: null
        });
      }
      return docsByName.get(key);
    };

    const docStorageCache = new Map();

    const ensureUploadedPdfStorage = async file => {
      const cacheKey = `${monthKey}|${file.name}|${file.size}|${file.lastModified || 0}`;
      if (docStorageCache.has(cacheKey)) return docStorageCache.get(cacheKey);

      const storageKey = `hitachi|${monthKey}|arquivo|${normalizePersonName(file.name) || file.name}`;
      await saveHitachiDocumentBlob(storageKey, file, { fileName: file.name });
      docStorageCache.set(cacheKey, storageKey);
      return storageKey;
    };

    if (holeriteZip) {
      if (!window.JSZip) throw new Error('Leitor de ZIP indisponivel no navegador.');

      const zip = await JSZip.loadAsync(await holeriteZip.arrayBuffer());
      const pdfEntries = Object.values(zip.files).filter(entry =>
        !entry.dir &&
        entry.name.toLowerCase().endsWith('.pdf') &&
        entry.name.toLowerCase().includes('holerite')
      );

      for (const entry of pdfEntries) {
        const folderName = entry.name.split('/')[0] || '';
        const collaboratorName = folderName.trim();
        const key = normalizePersonName(collaboratorName);
        if (!key) continue;

        const buffer = await entry.async('uint8array');
        const signed = pdfHasDigitalSignature(buffer);
        const docs = ensureDocEntry(key);

        docs.holerite = {
          status: signed ? 'OK' : 'PENDENTE',
          label: `${entry.name}${signed ? ' | assinado' : ' | sem assinatura digital'}`
        };

        if (signed) {
          const blob = new Blob([buffer], { type: 'application/pdf' });
          const storageKey = `hitachi|${monthKey}|${key}|holerite`;
          await saveHitachiDocumentBlob(storageKey, blob, { fileName: entry.name });
          docs.holerite.storageKey = storageKey;
        }
      }
    }

    for (const file of pagamentoFiles) {
      const storageKey = await ensureUploadedPdfStorage(file);
      const pages = await readPdfPages(file);

      pages.forEach(page => {
        const collaboratorName = extractPagamentoName(page.text) || detectCollaboratorFromPageText(page.text, rows);
        const key = normalizePersonName(collaboratorName);
        if (!key) return;

        ensureDocEntry(key).comprovantePagamento = {
          status: 'OK',
          label: `${file.name} | pagina ${page.pageNumber}`,
          storageKey,
          pageNumber: page.pageNumber
        };
      });
    }

    for (const file of adiantamentoFiles) {
      const storageKey = await ensureUploadedPdfStorage(file);
      const pages = await readPdfPages(file);

      pages.forEach(page => {
        const collaboratorName = extractAdiantamentoName(page.text) || detectCollaboratorFromPageText(page.text, rows);
        const key = normalizePersonName(collaboratorName);
        if (!key) return;

        ensureDocEntry(key).comprovanteAdiantamento = {
          status: 'OK',
          label: `${file.name} | pagina ${page.pageNumber}`,
          storageKey,
          pageNumber: page.pageNumber
        };
      });
    }

    const payloads = rows.map(row => {
      const key = normalizePersonName(row.colaborador);
      const docs = docsByName.get(key) || {};

      return {
        ...row,
        holerite: docs.holerite ? docs.holerite.status : (row.holerite || 'PENDENTE'),
        comprovantePagamento: docs.comprovantePagamento ? docs.comprovantePagamento.status : (row.comprovantePagamento || 'PENDENTE'),
        comprovanteAdiantamento: docs.comprovanteAdiantamento ? docs.comprovanteAdiantamento.status : (row.comprovanteAdiantamento || 'PENDENTE'),
        holeriteArquivo: docs.holerite ? docs.holerite.label : (row.holeriteArquivo || ''),
        comprovantePagamentoArquivo: docs.comprovantePagamento ? docs.comprovantePagamento.label : (row.comprovantePagamentoArquivo || ''),
        comprovanteAdiantamentoArquivo: docs.comprovanteAdiantamento ? docs.comprovanteAdiantamento.label : (row.comprovanteAdiantamentoArquivo || ''),
        holeriteStorageKey: docs.holerite && docs.holerite.status === 'OK' ? (docs.holerite.storageKey || '') : (row.holeriteStorageKey || ''),
        comprovantePagamentoStorageKey: docs.comprovantePagamento ? (docs.comprovantePagamento.storageKey || '') : (row.comprovantePagamentoStorageKey || ''),
        comprovantePagamentoPage: docs.comprovantePagamento ? (docs.comprovantePagamento.pageNumber ?? null) : (row.comprovantePagamentoPage ?? null),
        comprovanteAdiantamentoStorageKey: docs.comprovanteAdiantamento ? (docs.comprovanteAdiantamento.storageKey || '') : (row.comprovanteAdiantamentoStorageKey || ''),
        comprovanteAdiantamentoPage: docs.comprovanteAdiantamento ? (docs.comprovanteAdiantamento.pageNumber ?? null) : (row.comprovanteAdiantamentoPage ?? null)
      };
    });

    await saveHitachiDocsBatch(payloads);

    const okHolerite = payloads.filter(item => item.holerite === 'OK').length;
    const okPagamento = payloads.filter(item => item.comprovantePagamento === 'OK').length;
    const okAdiantamento = payloads.filter(item => item.comprovanteAdiantamento === 'OK').length;

    summaryBox.textContent = `Documentos processados em ${monthLabel(monthKey)}: ${okHolerite}/${payloads.length} holerite(s) OK, ${okPagamento}/${payloads.length} comprovante(s) de pagamento OK e ${okAdiantamento}/${payloads.length} comprovante(s) de adiantamento OK.`;

    zipInput.value = '';
    pagamentoInput.value = '';
    adiantamentoInput.value = '';
  } catch (error) {
    console.error(error);
    summaryBox.textContent = 'Nao foi possivel processar os documentos agora. Confira os arquivos e tente novamente.';
  }
}
```

## 10. Renderizacao dos botoes Abrir / Excluir documento

```js
function renderHitachiDocumentLine(label, fileLabel, storageKey, pageNumber = null, options = {}) {
  if (!fileLabel) return '';

  const requireOk = !!options.requireOk;
  const status = options.status || '';
  const rowId = options.rowId;
  const docType = options.docType || '';
  const canOpen = !!storageKey && (!requireOk || status === 'OK');

  const openButton = canOpen
    ? `<button class="doc-open-btn" type="button" onclick='openStoredHitachiDocument(${JSON.stringify(storageKey)}, ${pageNumber == null ? 'null' : Number(pageNumber)})'>Abrir documento</button>`
    : '';

  const deleteButton = rowId && docType
    ? `<button class="doc-delete-btn" type="button" onclick="removeHitachiDocument(${Number(rowId)}, '${docType}')">Excluir documento</button>`
    : '';

  const actions = openButton || deleteButton
    ? `<span class="doc-actions">${openButton ? `<span class="doc-open">${openButton}</span>` : ''}${deleteButton}</span>`
    : '';

  return `<div class="docline"><small>${label}: ${fileLabel}</small>${actions}</div>`;
}
```

## 11. Exemplo de uso na tabela do colaborador

```js
${renderHitachiDocumentLine('Holerite', row.holeriteArquivo, row.holeriteStorageKey, null, {
  requireOk: true,
  status: row.holerite,
  rowId: row.id,
  docType: 'holerite'
})}

${renderHitachiDocumentLine('Comprovante pgto', row.comprovantePagamentoArquivo, row.comprovantePagamentoStorageKey, row.comprovantePagamentoPage, {
  rowId: row.id,
  docType: 'comprovantePagamento'
})}

${renderHitachiDocumentLine('Comprovante adiant.', row.comprovanteAdiantamentoArquivo, row.comprovanteAdiantamentoStorageKey, row.comprovanteAdiantamentoPage, {
  rowId: row.id,
  docType: 'comprovanteAdiantamento'
})}
```

## 12. Funcoes auxiliares esperadas no projeto

Estas funcoes/estruturas precisam existir no projeto de destino:

```js
function stripAccents(value) { /* remove acentos */ }
function norm(value) { /* normaliza para comparacao */ }
function normalizePersonName(value) { /* normaliza nome da pessoa */ }
function monthLabel(monthKey) { /* formata yyyy-mm para texto */ }
function currentHitachiMonth() { /* devolve o mes atual */ }
function hitachiRowsForMonth(monthKey) { /* devolve colaboradores do mes */ }
async function saveHitachiDocsBatch(items) { /* salva lista atualizada */ }
async function saveHitachiCollaborator(payload) { /* salva um colaborador */ }
```

## 13. Arquivo de origem no projeto atual

Caso ela queira comparar com a implementacao completa, o arquivo base atual esta em:

- [controle-internet.html](C:\Users\notebook\Documents\Conferencia Cartão\TESTE-PORTAL\controle-internet.html)
