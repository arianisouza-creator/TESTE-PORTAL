# Modulo Gestao Documental - KPI Hitachi

Arquivo de origem: controle-internet.html

Este arquivo contem somente o codigo do modulo de Gestao Documental / KPI Hitachi, separado por blocos.

## 1. HTML principal do modulo

`html
      <section class="module" id="moduleHitachi">
        <div class="subrow2">
          <button class="sidetoggle" type="button" title="Recolher menu" aria-label="Recolher menu" data-icon="menu"></button>
          <span class="ico" data-icon="barChart3"></span>
          <span class="lab">
            <b>KPI Hitachi</b>
            <small>Gestao documental mensal</small>
          </span>
        </div>

        <div class="monthbar">
          <div class="search"><span data-icon="search"></span><input id="hq" placeholder="Buscar por colaborador, empresa ou situacao..."></div>
          <div class="selectbox"><span data-icon="calendar"></span><input id="hMonthPicker" type="month"></div>
          <button class="danger" id="resetHitachi"><span data-icon="trash"></span>Zerar mes</button>
          <button class="ghost" id="openHitachiPendencias"><span data-icon="mail"></span>Enviar pendencias</button>
        </div>

        <div class="topmenu">
          <button class="toplink on" data-h-view="overview">Visao Geral</button>
          <button class="toplink" data-h-view="cadastro">Cadastro</button>
        </div>

        <div class="view on" id="hview-overview">
          <div class="hero">
            <h1 id="hPageTitle">KPI Hitachi</h1>
            <p id="hPageSubtitle">Controle mensal de documentacao de colaboradores e documentos da empresa.</p>
          </div>

          <div class="toolbar">
            <div class="seg" aria-label="Filtros Hitachi">
              <button class="on" data-h-filter="todos">Todos</button>
              <button data-h-filter="ok">OK</button>
              <button data-h-filter="pendente">Pendentes</button>
              <button data-h-filter="rescindidos">Rescindidos</button>
            </div>
            <div class="eyebrow" id="hCountLabel">0 colaboradores no mes</div>
          </div>

          <section class="kpis" style="grid-template-columns:repeat(4,1fr)">
            <div class="kpi">
              <div class="ktop"><div class="kicon blue" data-icon="users"></div><div class="klabel">Colaboradores</div></div>
              <div class="kvalue" id="hCollaborators">0</div>
              <div class="kmeta">Cadastros no mes</div>
            </div>
            <div class="kpi">
              <div class="ktop"><div class="kicon green" data-icon="badgeCheck"></div><div class="klabel">Documentos OK</div></div>
              <div class="kvalue" id="hOkPct">0%</div>
              <div class="kmeta">Percentual validado</div>
            </div>
            <div class="kpi">
              <div class="ktop"><div class="kicon blue" data-icon="alertCircle"></div><div class="klabel">Pendencias</div></div>
              <div class="kvalue" id="hPendings">0</div>
              <div class="kmeta">Itens pendentes</div>
            </div>
            <div class="kpi">
              <div class="ktop"><div class="kicon slate" data-icon="files"></div><div class="klabel">Docs empresa</div></div>
              <div class="kvalue" id="hCompanyDocs">0</div>
              <div class="kmeta">Registros mensais</div>
            </div>
          </section>

          <section class="dashgrid" style="grid-template-columns:1.35fr .95fr .95fr">
            <article class="card pad">
              <div class="chead"><span class="ti2">Proporcao de documentos</span><span class="eyebrow">Mes selecionado</span></div>
              <div class="donut-wrap">
                <div class="donut" id="hDonut">
                  <div class="donut-hole"><div><b id="hDonutPct">0%</b><div class="eyebrow">OK</div></div></div>
                </div>
                <div class="legend" id="hLegend"></div>
              </div>
            </article>

            <article class="card pad">
              <div class="chead"><span class="ti2">Evolucao mensal</span><span class="eyebrow">Historico</span></div>
              <div class="list" id="hEvolution"></div>
            </article>

            <article class="card pad">
              <div class="chead"><span class="ti2">Volume de docs</span><span class="eyebrow">Postados</span></div>
              <div class="bars" id="hVolumeBars"></div>
            </article>
          </section>

          <div class="cred-grid" style="margin-bottom:16px">
            <section class="card pad">
              <div class="chead"><span class="ti2">MSE Engenharia</span><span class="eyebrow">Resumo da empresa</span></div>
              <div class="cred-list" id="hEngineeringCard"></div>
            </section>
            <section class="card pad">
              <div class="chead"><span class="ti2">MSE Service</span><span class="eyebrow">Resumo da empresa</span></div>
              <div class="cred-list" id="hServiceCard"></div>
            </section>
          </div>

          <section class="card table-card" style="margin-bottom:16px">
            <div class="pad">
              <div class="chead"><span class="ti2">Colaboradores do mes</span><span class="eyebrow" id="hFootCount">0 registros</span></div>
            </div>
            <div style="overflow:auto">
              <table>
                <thead>
                  <tr>
                    <th>Colaborador</th>
                    <th>Empresa</th>
                    <th>Situacao</th>
                    <th>Holerite</th>
                    <th>Comprovante</th>
                    <th>Adiantamento</th>
                    <th>Kit rescisao</th>
                    <th>Acoes</th>
                  </tr>
                </thead>
                <tbody id="hRows"></tbody>
              </table>
            </div>
          </section>

          <section class="card table-card">
            <div class="pad">
              <div class="chead"><span class="ti2">Documentos da empresa</span><span class="eyebrow">Status mensal</span></div>
            </div>
            <div style="overflow:auto">
              <table>
                <thead>
                  <tr>
                    <th>Empresa</th>
                    <th>Documento</th>
                    <th>Status</th>
                    <th>Acoes</th>
                  </tr>
                </thead>
                <tbody id="hCompanyRows"></tbody>
              </table>
            </div>
          </section>
        </div>

        <div class="view" id="hview-cadastro">
          <div id="hCadastroContent">
            <div class="hero" style="margin-bottom:14px">
              <h1>Cadastro KPI Hitachi</h1>
              <p>Cadastre os colaboradores, situacoes especiais e documentos mensais que alimentam o dashboard do cliente.</p>
            </div>

            <section class="card pad">
              <div class="chead"><span class="ti2">Novo colaborador</span><span class="eyebrow">Competencia mensal</span></div>
              <form id="hitachiForm" class="formgrid">
                <label>Competencia<input name="monthKey" type="month" required></label>
                <label>Empresa
                  <select name="empresa" required>
                    <option value="MSE ENGENHARIA">MSE ENGENHARIA</option>
                    <option value="MSE SERVICE">MSE SERVICE</option>
                  </select>
                </label>
                <label style="grid-column:1 / -1">Colaborador<input name="colaborador" required placeholder="Nome do colaborador"></label>
                <label>Situacao
                  <select name="situacao">
                    <option value="Ativo">Ativo</option>
                    <option value="Rescindido">Rescindido</option>
                    <option value="Demitido">Demitido</option>
                    <option value="Transferido">Transferido</option>
                  </select>
                </label>
                <label>Holerite
                  <select name="holerite">
                    <option value="OK">OK</option>
                    <option value="PENDENTE">PENDENTE</option>
                    <option value="N/A">N/A</option>
                  </select>
                </label>
                <label>Comprovante de pagamento
                  <select name="comprovantePagamento">
                    <option value="OK">OK</option>
                    <option value="PENDENTE">PENDENTE</option>
                    <option value="N/A">N/A</option>
                  </select>
                </label>
                <label>Comprovante de adiantamento
                  <select name="comprovanteAdiantamento">
                    <option value="OK">OK</option>
                    <option value="PENDENTE">PENDENTE</option>
                    <option value="N/A">N/A</option>
                  </select>
                </label>
                <label>Kit rescisao
                  <select name="kitRescisao">
                    <option value="N/A">N/A</option>
                    <option value="OK">OK</option>
                    <option value="PENDENTE">PENDENTE</option>
                  </select>
                </label>
                <div style="grid-column:1 / -1;display:flex;justify-content:flex-end;gap:10px">
                  <button class="ghost" type="button" id="cancelHitachiEdit" style="display:none">Cancelar edicao</button>
                  <button class="primary" type="submit" id="saveHitachiBtn"><span data-icon="plus"></span>Salvar colaborador</button>
                </div>
              </form>
            </section>

            <section class="card pad" style="margin-top:14px">
              <div class="chead"><span class="ti2">Documentos da empresa</span><span class="eyebrow">Competencia mensal</span></div>
              <form id="hitachiCompanyForm" class="formgrid">
                <label>Competencia<input name="monthKey" type="month" required></label>
                <label>Empresa
                  <select name="empresa" required>
                    <option value="MSE ENGENHARIA">MSE ENGENHARIA</option>
                    <option value="MSE SERVICE">MSE SERVICE</option>
                  </select>
                </label>
                <label>Documento
                  <select name="documento" required>
                    <option value="FOLHA DE PAGAMENTO">FOLHA DE PAGAMENTO</option>
                    <option value="DCTFWEB">DCTFWEB</option>
                    <option value="FGTS DIGITAL + GUIA E COMPROVANTE">FGTS DIGITAL + GUIA E COMPROVANTE</option>
                    <option value="INSS">INSS</option>
                  </select>
                </label>
                <label>Status
                  <select name="status" required>
                    <option value="OK">OK</option>
                    <option value="PENDENTE">PENDENTE</option>
                    <option value="N/A">N/A</option>
                  </select>
                </label>
                <div style="grid-column:1 / -1;display:flex;justify-content:flex-end;gap:10px">
                  <button class="ghost" type="button" id="cancelHitachiCompanyEdit" style="display:none">Cancelar edicao</button>
                  <button class="primary" type="submit" id="saveHitachiCompanyBtn"><span data-icon="plus"></span>Salvar documento</button>
                </div>
              </form>
            </section>

            <div class="cred-grid" style="margin-top:14px">
              <section class="card pad">
                <div class="chead"><span class="ti2">Colaboradores cadastrados</span><span class="eyebrow" id="hCadastroCount">0 registros</span></div>
                <div class="cred-list" id="hCadastroList"></div>
              </section>
              <section class="card pad">
                <div class="chead"><span class="ti2">Docs da empresa cadastrados</span><span class="eyebrow" id="hCompanyCadastroCount">0 registros</span></div>
                <div class="cred-list" id="hCompanyCadastroList"></div>
              </section>
            </div>
          </div>
        </div>
      </section>
`

## 2. Modais do modulo

`html
  <div class="modal" id="hitachiEditModal" role="dialog" aria-modal="true" aria-labelledby="hitachiEditModalTitle">
    <div class="dialog">
      <div class="chead"><span class="ti2" id="hitachiEditModalTitle">Editar colaborador</span><button class="rowact" type="button" id="closeHitachiEditModal" aria-label="Fechar" data-icon="close"></button></div>
      <form id="hitachiEditForm" class="formgrid">
        <label>Competencia<input name="monthKey" type="month" required></label>
        <label>Empresa
          <select name="empresa" required>
            <option value="MSE ENGENHARIA">MSE ENGENHARIA</option>
            <option value="MSE SERVICE">MSE SERVICE</option>
          </select>
        </label>
        <label style="grid-column:1 / -1">Colaborador<input name="colaborador" required></label>
        <label>Situacao
          <select name="situacao">
            <option value="Ativo">Ativo</option>
            <option value="Rescindido">Rescindido</option>
            <option value="Demitido">Demitido</option>
            <option value="Transferido">Transferido</option>
          </select>
        </label>
        <label>Holerite
          <select name="holerite">
            <option value="OK">OK</option>
            <option value="PENDENTE">PENDENTE</option>
            <option value="N/A">N/A</option>
          </select>
        </label>
        <label>Comprovante de pagamento
          <select name="comprovantePagamento">
            <option value="OK">OK</option>
            <option value="PENDENTE">PENDENTE</option>
            <option value="N/A">N/A</option>
          </select>
        </label>
        <label>Comprovante de adiantamento
          <select name="comprovanteAdiantamento">
            <option value="OK">OK</option>
            <option value="PENDENTE">PENDENTE</option>
            <option value="N/A">N/A</option>
          </select>
        </label>
        <label>Kit rescisao
          <select name="kitRescisao">
            <option value="N/A">N/A</option>
            <option value="OK">OK</option>
            <option value="PENDENTE">PENDENTE</option>
          </select>
        </label>
        <footer style="grid-column:1 / -1">
          <button class="ghost" type="button" id="cancelHitachiEditModal">Cancelar</button>
          <button class="primary" type="submit"><span data-icon="save"></span>Salvar alteracoes</button>
        </footer>
      </form>
    </div>
  </div>

  <div class="modal" id="hitachiCompanyModal" role="dialog" aria-modal="true" aria-labelledby="hitachiCompanyModalTitle">
    <div class="dialog">
      <div class="chead"><span class="ti2" id="hitachiCompanyModalTitle">Editar documento da empresa</span><button class="rowact" type="button" id="closeHitachiCompanyModal" aria-label="Fechar" data-icon="close"></button></div>
      <form id="hitachiCompanyEditForm" class="formgrid">
        <label>Competencia<input name="monthKey" type="month" required></label>
        <label>Empresa
          <select name="empresa" required>
            <option value="MSE ENGENHARIA">MSE ENGENHARIA</option>
            <option value="MSE SERVICE">MSE SERVICE</option>
          </select>
        </label>
        <label>Documento
          <select name="documento" required>
            <option value="FOLHA DE PAGAMENTO">FOLHA DE PAGAMENTO</option>
            <option value="DCTFWEB">DCTFWEB</option>
            <option value="FGTS DIGITAL + GUIA E COMPROVANTE">FGTS DIGITAL + GUIA E COMPROVANTE</option>
            <option value="INSS">INSS</option>
          </select>
        </label>
        <label>Status
          <select name="status">
            <option value="OK">OK</option>
            <option value="PENDENTE">PENDENTE</option>
            <option value="N/A">N/A</option>
          </select>
        </label>
        <footer style="grid-column:1 / -1">
          <button class="ghost" type="button" id="cancelHitachiCompanyModal">Cancelar</button>
          <button class="primary" type="submit"><span data-icon="save"></span>Salvar alteracoes</button>
        </footer>
      </form>
    </div>
  </div>

  <div class="modal" id="hitachiPendenciasModal" role="dialog" aria-modal="true" aria-labelledby="hitachiPendenciasTitle">
    <div class="dialog wide">
      <div class="chead"><span class="ti2" id="hitachiPendenciasTitle">Enviar pendencias do mes</span><button class="rowact" type="button" id="closeHitachiPendenciasModal" aria-label="Fechar" data-icon="close"></button></div>
      <div class="formgrid">
        <label style="grid-column:1 / -1">E-mails destinatarios
          <input id="hitachiRecipients" placeholder="ex.: ariani.souza@mse.com.br, maria@mse.com.br">
        </label>
        <label style="grid-column:1 / -1">Assunto
          <input id="hitachiMailSubject" readonly>
        </label>
        <label style="grid-column:1 / -1">Resumo das pendencias
          <div class="pending-mail-list" id="hitachiPendenciasList"></div>
        </label>
        <label style="grid-column:1 / -1">Corpo do e-mail
          <textarea id="hitachiMailBody"></textarea>
        </label>
      </div>
      <div class="helper">O portal monta o texto automaticamente com base no mes selecionado. Depois voce pode abrir o e-mail ja preenchido.</div>
      <div class="helper" id="hitachiMailFeedback"></div>
      <footer>
        <button class="ghost" type="button" id="copyHitachiPendencias"><span data-icon="copy"></span>Copiar texto</button>
        <button class="ghost" type="button" id="refreshHitachiPendencias"><span data-icon="refresh"></span>Atualizar lista</button>
        <button class="primary" type="button" id="sendHitachiPendencias"><span data-icon="mail"></span>Abrir e-mail</button>
      </footer>
    </div>
  </div>
`

## 3. Estado inicial do modulo

`javascript
    let hitachiFilter = 'todos';
    let editingHitachiId = null;
    let editingHitachiCompanyId = null;
    let overviewEditingHitachiId = null;
    let overviewEditingHitachiCompanyId = null;
    let protectedAuthenticated = false;
    let currentModule = 'internet';
    let hitachiRecipients = '';
    const PROTECTED_USER = 'ADM';
    const PROTECTED_PASS = 'mse2026';
    const portalConfig = window.PORTAL_CONFIG || {};
    const supabaseConfig = portalConfig.supabase || {};
    const SUPABASE_URL = (supabaseConfig.url || '').replace(/\/+$/, '');
    const SUPABASE_ANON_KEY = supabaseConfig.anonKey || '';
    const REMOTE_ENABLED = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
    const LOCAL_CACHE_KEY = 'portal-mse-cache-v2';
    const monthPicker = document.getElementById('monthPicker');
    const monthOverrides = {};
    const monthLines = {};
    const contracts = [];
    const diaristaMasters = [];
    const diaristaMonthOverrides = {};
    const hitachiCollaborators = [];
    const hitachiCompanyDocs = [];
    const hMonthPicker = document.getElementById('hMonthPicker');

`

## 4. Helper de mes do modulo

`javascript
    function currentHitachiMonth() {
      return hMonthPicker.value || currentMonthKey() || defaultMonth();
    }
`

## 5. Logica completa do modulo

`javascript
    function statusTone(value) {
      if (value === 'OK') return 'ok';
      if (value === 'PENDENTE') return 'warn';
      return 'neutral';
    }

    function hitachiDocStatuses(row) {
      const docs = [
        row.holerite,
        row.comprovantePagamento,
        row.comprovanteAdiantamento
      ];
      if (row.situacao !== 'Ativo') docs.push(row.kitRescisao);
      return docs.filter(item => item && item !== 'N/A');
    }

    function hitachiRowsForMonth(monthKey = currentHitachiMonth()) {
      return hitachiCollaborators.filter(item => item.monthKey === monthKey);
    }

    function hitachiCompanyDocsForMonth(monthKey = currentHitachiMonth()) {
      return hitachiCompanyDocs.filter(item => item.monthKey === monthKey);
    }

    function hitachiMonthlySummary(monthKey = currentHitachiMonth()) {
      const rows = hitachiRowsForMonth(monthKey);
      const companyDocs = hitachiCompanyDocsForMonth(monthKey);
      let ok = 0;
      let pending = 0;

      rows.forEach(row => {
        hitachiDocStatuses(row).forEach(status => {
          if (status === 'OK') ok += 1;
          if (status === 'PENDENTE') pending += 1;
        });
      });

      companyDocs.forEach(item => {
        if (item.status === 'OK') ok += 1;
        if (item.status === 'PENDENTE') pending += 1;
      });

      return {
        rows,
        companyDocs,
        ok,
        pending,
        total: ok + pending
      };
    }

    function hitachiHistory() {
      const months = [...new Set([
        ...hitachiCollaborators.map(item => item.monthKey),
        ...hitachiCompanyDocs.map(item => item.monthKey)
      ])].filter(Boolean).sort((a, b) => monthIndex(b) - monthIndex(a));

      return months.map(monthKey => {
        const summary = hitachiMonthlySummary(monthKey);
        const pct = summary.total ? Math.round((summary.ok / summary.total) * 100) : 0;
        return {
          monthKey,
          pct,
          total: summary.total,
          pending: summary.pending
        };
      });
    }

    function brl(value) {
      return value == null ? 'R$ 0,00' : value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }

    function norm(value) {
      return (value || '').toString().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    }

    function filteredRows() {
      const rows = currentData();
      const q = norm(document.getElementById('q').value);
      return rows.filter(row => {
        const hay = norm([row.status, row.obra, row.empresa, row.contrato, row.contato, row.pedido, row.obs].join(' '));
        const queryOk = !q || hay.includes(q);
        const filterOk =
          filter === 'todos' ||
          (filter === 'ativos' && row.status === 'Ativo') ||
          (filter === 'vencendo' && Number(row.vencimento || 99) <= 20) ||
          (filter === 'sem-pedido' && (!row.pedido || row.pedido === '-'));
        return queryOk && filterOk;
      });
    }

    function kpiData(rows) {
      const active = rows.filter(row => row.status === 'Ativo').length;
      const totalValue = rows.reduce((sum, row) => sum + (row.valor || 0), 0);
      const operators = new Set(rows.map(row => row.empresa).filter(Boolean)).size;
      const nextDueValues = rows.map(row => Number(row.vencimento)).filter(v => Number.isFinite(v) && v > 0);
      const nextDue = nextDueValues.length ? Math.min(...nextDueValues) : null;
      const orders = rows.filter(row => row.pedido && row.pedido !== '-').length;
      return { active, totalValue, operators, nextDue, orders };
    }

    function renderKpis(rows) {
      const info = kpiData(rows);
      const lines = ensureMonthLines(currentMonthKey());
      document.getElementById('kActive').textContent = info.active;
      document.getElementById('kCost').textContent = brl(info.totalValue);
      document.getElementById('kOperators').textContent = info.operators;
      document.getElementById('kNext').textContent = info.nextDue || '-';
      document.getElementById('kOrders').textContent = info.orders;
      document.getElementById('kMonth').textContent = monthLabel(currentMonthKey());
      document.getElementById('miniIndicators').textContent = `${info.active} contratos ativos`;
      document.getElementById('pageSubtitle').textContent = `Mes de referencia: ${monthLabel(currentMonthKey())}. Cadastre tudo que voce precisa para este fechamento.`;
      document.getElementById('activeLinesCount').textContent = lines.length;
    }

    function renderBars(rows) {
      const grouped = {};
      rows.forEach(row => {
        const key = row.obra || 'Sem obra';
        grouped[key] = (grouped[key] || 0) + (row.valor || 0);
      });
      const entries = Object.entries(grouped).sort((a, b) => b[1] - a[1]);
      const max = entries.length ? entries[0][1] : 0;
      const container = document.getElementById('bars');
      if (!entries.length) {
        container.innerHTML = `<div class="empty-state"><b>Sem valores registrados.</b>Adicione contratos no mes para visualizar a distribuicao por obra.</div>`;
        return;
      }
      container.innerHTML = entries.map(([obra, total]) => `
        <div class="baritem">
          <div class="barlabel"><span>${obra}</span><b>${brl(total)}</b></div>
          <div class="track"><div class="fill" style="width:${max ? total / max * 100 : 0}%"></div></div>
        </div>
      `).join('');
    }

    function renderStatus(rows) {
      const total = rows.length;
      const active = rows.filter(row => row.status === 'Ativo').length;
      const inactive = rows.filter(row => row.status === 'Inativo').length;
      const canceled = rows.filter(row => row.status === 'Cancelado').length;
      const pct = total ? Math.round(active / total * 100) : 0;
      document.getElementById('donut').style.background = `conic-gradient(var(--green) 0deg ${pct * 3.6}deg,#edf1f5 ${pct * 3.6}deg 360deg)`;
      document.getElementById('donutPct').textContent = `${pct}%`;
      document.getElementById('legend').innerHTML = `
        <div class="leg"><span><span class="dot" style="background:var(--green)"></span>Ativos</span><b>${active}</b></div>
        <div class="leg"><span><span class="dot" style="background:var(--amber)"></span>Inativos</span><b>${inactive}</b></div>
        <div class="leg"><span><span class="dot" style="background:var(--slate)"></span>Cancelados</span><b>${canceled}</b></div>
      `;
    }

    function renderUpcoming(rows) {
      const container = document.getElementById('upcoming');
      const items = rows
        .filter(row => Number(row.vencimento))
        .sort((a, b) => Number(a.vencimento) - Number(b.vencimento))
        .slice(0, 4);
      if (!items.length) {
        container.innerHTML = `<div class="empty-state"><b>Sem vencimentos cadastrados.</b>Preencha o dia de vencimento para montar a agenda do mes.</div>`;
        return;
      }
      container.innerHTML = items.map(item => `
        <div class="li">
          <div style="display:flex;align-items:center;gap:12px">
            <div class="liday">${item.vencimento}</div>
            <div><b class="link">${item.obra || 'Sem obra'}</b><div class="lisub">${item.empresa || 'Empresa nao informada'}</div></div>
          </div>
          <div class="lisub">1 contrato</div>
        </div>
      `).join('');
    }

    function renderActiveLines(rows) {
      const lines = recalculateLinePercentages(currentMonthKey());
      const activeLines = lines.filter(line => (line.status || 'Ativo') === 'Ativo');
      const summary = document.getElementById('activeLines');
      const accessSummary = document.getElementById('activeSummary');
      const credentials = document.getElementById('credentialsList');
      const rateioBars = document.getElementById('lineRateioBars');
      document.getElementById('accessMonthLabel').textContent = monthLabel(currentMonthKey());
      if (!lines.length) {
        summary.innerHTML = `<div class="empty-state"><b>Sem linhas ativas cadastradas.</b>Cadastre as linhas diretamente nesta aba protegida.</div>`;
        accessSummary.innerHTML = `<div class="empty-state"><b>Nenhuma linha listada.</b>Cadastre linhas ativas para montar o resumo operacional.</div>`;
        rateioBars.innerHTML = `<div class="empty-state"><b>Sem rateio calculado.</b>Cadastre linhas ativas para visualizar a distribuicao por centro de custo.</div>`;
        credentials.innerHTML = `<div class="empty-state"><b>Nenhuma credencial registrada.</b>Preencha login e senha no registro mensal quando necessario.</div>`;
        return;
      }
      const centerCounts = {};
      activeLines.forEach(line => {
        normalizeCenters(line.centroCusto).forEach(center => {
          const key = center.toUpperCase();
          centerCounts[key] = (centerCounts[key] || 0) + 1;
        });
      });
      const rateioEntries = Object.entries(centerCounts).sort((a, b) => b[1] - a[1]);
      if (!rateioEntries.length) {
        rateioBars.innerHTML = `<div class="empty-state"><b>Sem linhas ativas no rateio.</b>As linhas cadastradas estao marcadas como inativas.</div>`;
      } else {
        const totalActiveLines = activeLines.length;
        rateioBars.innerHTML = rateioEntries.map(([center, count]) => {
          const pct = formatPercentNumber(totalActiveLines ? (count / totalActiveLines) * 100 : 0);
          return `
            <div class="baritem">
              <div class="barlabel"><span>${center}</span><b>${count} de ${totalActiveLines} linha(s) | ${pct}% do total</b></div>
              <div class="track"><div class="fill" style="width:${pct.replace(',', '.')}%"></div></div>
            </div>
          `;
        }).join('');
      }
      if (!activeLines.length) {
        summary.innerHTML = `<div class="empty-state"><b>Sem linhas ativas neste mes.</b>As linhas cadastradas estao marcadas como inativas.</div>`;
      } else {
        summary.innerHTML = activeLines.slice(0, 4).map(line => `
        <div class="li">
          <div>
            <b class="link">${line.numero}</b>
            <div class="lisub">${line.responsavel || 'Sem responsavel'} | ${line.centroCusto}</div>
          </div>
          <div class="tag ${line.status === 'Inativo' ? 'neutral' : 'ok'}">${line.percentual}</div>
        </div>
        `).join('');
      }
      accessSummary.innerHTML = lines.map((line, index) => `
        <div class="cred-item">
          <h4>Linha ${index + 1}</h4>
          <div class="cred-row"><span>Numero</span><b>${line.numero || '-'}</b></div>
          <div class="cred-row"><span>Responsavel</span><b>${line.responsavel || '-'}</b></div>
          <div class="cred-row"><span>Status</span><b>${line.status || 'Ativo'}</b></div>
          <div class="cred-row"><span>Centro de custo</span><b>${line.centroCusto || '-'}</b></div>
          <div class="cred-row"><span>Percentual</span><b>${line.percentual || '-'}</b></div>
          <div style="margin-top:10px;display:flex;justify-content:flex-end">
            <button class="inline-btn" type="button" onclick="editActiveLine(${line.id})">Editar linha</button>
          </div>
        </div>
      `).join('');
      const withCredentials = rows.filter(row => row.loginAcesso || row.senhaAcesso || row.obs);
      if (!withCredentials.length) {
        credentials.innerHTML = `<div class="empty-state"><b>Nenhuma credencial registrada.</b>Preencha login e senha no registro mensal quando necessario.</div>`;
        return;
      }
      credentials.innerHTML = withCredentials.map(row => `
        <div class="cred-item">
          <h4>${row.empresa}</h4>
          <div class="cred-row"><span>Login</span><b class="pwd">${row.loginAcesso || 'Nao informado'}</b></div>
          <div class="cred-row"><span>Senha</span><b class="pwd" data-secret="${row.id}">${maskPassword(row.senhaAcesso)}</b></div>
          <div class="cred-row"><span>Observacao</span><b>${row.obs || '-'}</b></div>
          <div style="margin-top:10px">
            <button class="inline-btn" type="button" onclick="togglePassword(${row.id})">${row.senhaAcesso ? 'Mostrar senha' : 'Sem senha'}</button>
          </div>
        </div>
      `).join('');
    }

    function populateContractOptions() {
      const select = document.getElementById('contractPreset');
      if (!select) return;
      const currentValue = select.value;
      select.innerHTML = `<option value="">Selecionar contrato salvo</option>` + contracts.map(contract => `
        <option value="${contract.id}">${contractLabel(contract)}</option>
      `).join('');
      if (contracts.some(contract => String(contract.id) === currentValue)) {
        select.value = currentValue;
      }
    }

    function renderContracts() {
      const list = document.getElementById('contractsList');
      const count = document.getElementById('contractCount');
      count.textContent = `${contracts.length} contrato${contracts.length === 1 ? '' : 's'}`;
      if (!contracts.length) {
        list.innerHTML = `<div class="empty-state"><b>Nenhum contrato cadastrado.</b>Cadastre a empresa e o contrato aqui para aproveitar o preenchimento automatico no novo registro.</div>`;
        populateContractOptions();
        return;
      }
      list.innerHTML = contracts.map(contract => `
        <div class="cred-item">
          <h4>${contract.empresa}</h4>
          <div class="cred-row"><span>Status</span><b>${contract.statusContrato}</b></div>
          <div class="cred-row"><span>Inicio</span><b>${monthLabel(contract.inicioContrato)}</b></div>
          <div class="cred-row"><span>Inativo em</span><b>${contract.fimContrato ? monthLabel(contract.fimContrato) : '-'}</b></div>
          <div class="cred-row"><span>Obra</span><b>${contract.obra}</b></div>
          <div class="cred-row"><span>Vencimento</span><b>${contract.vencimento}</b></div>
          <div class="cred-row"><span>Contrato</span><b>${contract.numeroContrato}</b></div>
          <div class="cred-row"><span>Observacao</span><b>${contract.obsContrato || '-'}</b></div>
          <div style="margin-top:10px;display:flex;justify-content:flex-end">
            <button class="inline-btn" type="button" onclick="editContract(${contract.id})">Editar contrato</button>
          </div>
        </div>
      `).join('');
      populateContractOptions();
    }

    function applyContractPreset(contractId) {
      const form = document.getElementById('form');
      const contract = contracts.find(item => String(item.id) === String(contractId));
      if (!form || !contract) return;
      form.elements.empresa.value = contract.empresa;
      form.elements.obra.value = contract.obra;
      form.elements.vencimento.value = contract.vencimento;
      form.elements.contrato.value = contract.numeroContrato;
    }

    function fillFormFromRow(row, monthKey) {
      const form = document.getElementById('form');
      if (!form || !row) return;
      form.elements.contratoBase.value = '';
      form.elements.mesReferencia.value = monthKey;
      form.elements.status.value = row.status || 'Ativo';
      form.elements.obra.value = row.obra || '';
      form.elements.empresa.value = row.empresa || '';
      form.elements.vencimento.value = row.vencimento || '';
      form.elements.contrato.value = row.contrato || '';
      form.elements.valor.value = row.valor != null ? String(row.valor).replace('.', ',') : '';
      form.elements.pedido.value = row.pedido === '-' ? '' : (row.pedido || '');
      form.elements.contato.value = row.contato === '-' ? '' : (row.contato || '');
      form.elements.loginAcesso.value = row.loginAcesso || '';
      form.elements.senhaAcesso.value = row.senhaAcesso || '';
      form.elements.aprovado.value = row.aprovado == null ? 'pendente' : row.aprovado ? 'sim' : 'nao';
      form.elements.s1.value = row.s1 == null ? 'pendente' : row.s1 ? 'sim' : 'nao';
      form.elements.obs.value = row.obs || '';
    }

    function fillContractForm(contract) {
      const form = document.getElementById('contractForm');
      form.elements.empresaContrato.value = contract.empresa || '';
      form.elements.obraContrato.value = contract.obra || '';
      form.elements.vencimentoContrato.value = contract.vencimento || '';
      form.elements.numeroContrato.value = contract.numeroContrato || '';
      form.elements.statusContrato.value = contract.statusContrato || 'Ativo';
      form.elements.inicioContrato.value = contract.inicioContrato || '';
      form.elements.fimContrato.value = contract.fimContrato || '';
      form.elements.contatoContrato.value = contract.contato || '';
      form.elements.obsContrato.value = contract.obsContrato || '';
    }

    function renderTable(rows) {
      const body = document.getElementById('rows');
      if (!rows.length) {
        body.innerHTML = `<tr><td colspan="11"><div class="empty-state"><b>Mes sem informacoes cadastradas.</b>Selecione o mes e use "Novo registro" para comecar do zero.</div></td></tr>`;
        return;
      }
      body.innerHTML = rows.map(row => `
        <tr>
          <td><span class="tag ${row.status === 'Ativo' ? 'ok' : row.status === 'Inativo' ? 'warn' : 'neutral'}"><span class="bullet"></span>${row.status}</span></td>
          <td><b class="link">${row.obra || '-'}</b></td>
          <td><span class="company">${row.empresa || '-'}</span></td>
          <td><b style="color:#2d8b57">${row.vencimento || '-'}</b></td>
          <td>${row.contrato || '-'}</td>
          <td>${row.contato || '-'}</td>
          <td><span class="${row.valor == null ? 'pending' : 'money'}">${row.valor != null ? brl(row.valor) : 'Pendente'}</span></td>
          <td><span class="${!row.pedido ? 'pending' : ''}">${row.pedido || 'Pendente'}</span></td>
          <td><span class="${row.aprovado == null ? 'pending' : ''}">${row.aprovado == null ? 'Pendente' : row.aprovado ? 'Sim' : 'Nao'}</span></td>
          <td><span class="${row.s1 == null ? 'pending' : ''}">${row.s1 == null ? 'Pendente' : row.s1 ? 'Sim' : 'Nao'}</span></td>
          <td class="actioncell">
            <div style="display:flex;justify-content:flex-end;gap:8px">
              <button class="rowact" title="Ver detalhe" aria-label="Ver detalhe" onclick="selectRow(${row.id})">${icon('eye')}</button>
              <button class="rowact" title="Editar linha" aria-label="Editar linha" onclick="editRow(${row.id})">${icon('edit')}</button>
            </div>
          </td>
        </tr>
      `).join('');
    }

    function renderDetails(row) {
      const detail = document.getElementById('detail');
      if (!row) {
        document.getElementById('detailTitle').textContent = 'Registro selecionado';
        document.getElementById('detailStatus').textContent = 'Aguardando';
        document.getElementById('detailStatus').className = 'tag neutral';
        detail.innerHTML = `<div class="empty-state"><b>Nenhum registro selecionado.</b>Clique no icone de visualizacao da tabela para abrir os detalhes do contrato do mes.</div>`;
        return;
      }
      document.getElementById('detailTitle').textContent = row.obra || 'Registro';
      document.getElementById('detailStatus').textContent = row.status;
      document.getElementById('detailStatus').className = `tag ${row.status === 'Ativo' ? 'ok' : row.status === 'Inativo' ? 'warn' : 'neutral'}`;
      detail.innerHTML = `
        <div class="ditem"><span>Empresa</span><b>${row.empresa || '-'}</b></div>
        <div class="ditem"><span>Contrato</span>${row.contrato || '-'}</div>
        <div class="ditem"><span>Contato</span>${row.contato || '-'}</div>
        <div class="ditem"><span>Valor mensal</span><b>${row.valor != null ? brl(row.valor) : '-'}</b></div>
        <div class="ditem"><span>Pedido</span>${row.pedido || '-'}</div>
        <div class="ditem"><span>Fluxo</span>Aprovado: ${row.aprovado ? 'sim' : 'nao'} | S1: ${row.s1 ? 'sim' : 'nao'}</div>
        <div class="note"><b style="display:block;color:var(--ink);margin-bottom:6px">Observacao</b>${row.obs || 'Sem observacao cadastrada.'}</div>
      `;
    }

    function renderDiarista() {
      const rows = currentDiaristaData().filter(row => {
        const q = norm(document.getElementById('dq').value);
        if (!q) return true;
        return norm([row.obra, row.nome, row.pedido, row.link].join(' ')).includes(q);
      });
      const allRows = currentDiaristaData();
      const totalValue = allRows.reduce((sum, row) => sum + (row.valor || 0), 0);
      const protocolados = allRows.filter(row => row.protocolado === 'sim').length;
      const pedidos = allRows.filter(row => row.pedido).length;
      document.getElementById('dMonthMirror').value = currentMonthKey();
      document.getElementById('dPageTitle').textContent = `Controle da Diarista | ${monthLabel(currentMonthKey())}`;
      document.getElementById('dPageSubtitle').textContent = `Cadastros ativos do mes: ${allRows.length}. Complete pedido, valor e protocolo.`;
      document.getElementById('dActive').textContent = allRows.length;
      document.getElementById('dCost').textContent = brl(totalValue);
      document.getElementById('dOrders').textContent = pedidos;
      document.getElementById('dProtocolado').textContent = protocolados;
      document.getElementById('dCountLabel').textContent = `${allRows.length} registros no mes`;
      document.getElementById('dFootCount').textContent = allRows.length;

      const body = document.getElementById('dRows');
      if (!rows.length) {
        body.innerHTML = `<tr><td colspan="7"><div class="empty-state"><b>Mes sem diaristas ativas.</b>Use o cadastro protegido para incluir obra e nome.</div></td></tr>`;
      } else {
        body.innerHTML = rows.map(row => `
          <tr>
            <td><b class="link">${row.obra || '-'}</b></td>
            <td><span class="company">${row.nome || '-'}</span></td>
            <td><span class="${!row.pedido ? 'pending' : ''}">${row.pedido || 'Pendente'}</span></td>
            <td><span class="${row.valor == null ? 'pending' : 'money'}">${row.valor != null ? brl(row.valor) : 'Pendente'}</span></td>
            <td><span class="${!row.protocolado ? 'pending' : ''}">${row.protocolado ? row.protocolado.toUpperCase() : 'Pendente'}</span></td>
            <td>${row.link || 'Pendente'}</td>
            <td class="actioncell">
              <button class="rowact" title="Editar diarista" aria-label="Editar diarista" onclick="editDiaristaMonth(${row.id})">${icon('edit')}</button>
            </td>
          </tr>
        `).join('');
      }

      const list = document.getElementById('dCadastroList');
      document.getElementById('dCadastroCount').textContent = `${diaristaMasters.length} cadastro${diaristaMasters.length === 1 ? '' : 's'}`;
      if (!diaristaMasters.length) {
        list.innerHTML = `<div class="empty-state"><b>Nenhum cadastro salvo.</b>Inclua obra e nome para montar o mes automaticamente.</div>`;
      } else {
        list.innerHTML = diaristaMasters.map(item => `
          <div class="cred-item">
            <h4>${item.obraDiarista}</h4>
            <div class="cred-row"><span>Nome</span><b>${item.nomeDiarista}</b></div>
            <div class="cred-row"><span>Status</span><b>${item.statusDiarista}</b></div>
            <div class="cred-row"><span>Inicio</span><b>${monthLabel(item.inicioDiarista)}</b></div>
            <div class="cred-row"><span>Inativo em</span><b>${item.fimDiarista ? monthLabel(item.fimDiarista) : '-'}</b></div>
            <div style="margin-top:10px;display:flex;justify-content:flex-end">
              <button class="inline-btn" type="button" onclick="editDiaristaCadastro(${item.id})">Editar cadastro</button>
            </div>
          </div>
        `).join('');
      }
    }

    function resetHitachiForm() {
      editingHitachiId = null;
      const form = document.getElementById('hitachiForm');
      form.reset();
      form.elements.monthKey.value = currentHitachiMonth();
      form.elements.empresa.value = 'MSE ENGENHARIA';
      form.elements.situacao.value = 'Ativo';
      form.elements.holerite.value = 'OK';
      form.elements.comprovantePagamento.value = 'OK';
      form.elements.comprovanteAdiantamento.value = 'OK';
      form.elements.kitRescisao.value = 'N/A';
      document.getElementById('saveHitachiBtn').innerHTML = `${icon('plus')}Salvar colaborador`;
      document.getElementById('cancelHitachiEdit').style.display = 'none';
    }

    function resetHitachiCompanyForm() {
      editingHitachiCompanyId = null;
      const form = document.getElementById('hitachiCompanyForm');
      form.reset();
      form.elements.monthKey.value = currentHitachiMonth();
      form.elements.empresa.value = 'MSE ENGENHARIA';
      form.elements.documento.value = 'FOLHA DE PAGAMENTO';
      form.elements.status.value = 'OK';
      document.getElementById('saveHitachiCompanyBtn').innerHTML = `${icon('plus')}Salvar documento`;
      document.getElementById('cancelHitachiCompanyEdit').style.display = 'none';
    }

    function openModalById(id) {
      document.getElementById(id).classList.add('open');
    }

    function closeModalById(id) {
      document.getElementById(id).classList.remove('open');
    }

    function populateHitachiEditForm(form, item) {
      form.elements.monthKey.value = item.monthKey || currentHitachiMonth();
      form.elements.empresa.value = item.empresa || 'MSE ENGENHARIA';
      form.elements.colaborador.value = item.colaborador || '';
      form.elements.situacao.value = item.situacao || 'Ativo';
      form.elements.holerite.value = item.holerite || 'OK';
      form.elements.comprovantePagamento.value = item.comprovantePagamento || 'OK';
      form.elements.comprovanteAdiantamento.value = item.comprovanteAdiantamento || 'OK';
      form.elements.kitRescisao.value = item.kitRescisao || 'N/A';
    }

    function populateHitachiCompanyEditForm(form, item) {
      form.elements.monthKey.value = item.monthKey || currentHitachiMonth();
      form.elements.empresa.value = item.empresa || 'MSE ENGENHARIA';
      form.elements.documento.value = item.documento || 'FOLHA DE PAGAMENTO';
      form.elements.status.value = item.status || 'OK';
    }

    async function saveHitachiCollaborator(payload) {
      const index = hitachiCollaborators.findIndex(item => item.id === payload.id);
      if (index >= 0) {
        hitachiCollaborators[index] = payload;
      } else {
        hitachiCollaborators.push(payload);
      }
      hMonthPicker.value = payload.monthKey;
      saveLocalCache();
      renderHitachi();
      try {
        await upsertHitachiRemote(payload);
        setSyncStatus(`Colaborador ${payload.colaborador} sincronizado no KPI Hitachi`);
      } catch (error) {
        console.error(error);
        setSyncStatus(`Falha ao sincronizar colaborador ${payload.colaborador}. Cache local mantido.`);
      }
    }

    async function saveHitachiCompanyDoc(payload) {
      const index = hitachiCompanyDocs.findIndex(item => item.id === payload.id);
      if (index >= 0) {
        hitachiCompanyDocs[index] = payload;
      } else {
        hitachiCompanyDocs.push(payload);
      }
      hMonthPicker.value = payload.monthKey;
      saveLocalCache();
      renderHitachi();
      try {
        await upsertHitachiCompanyDocRemote(payload);
        setSyncStatus(`Documento ${payload.documento} sincronizado no KPI Hitachi`);
      } catch (error) {
        console.error(error);
        setSyncStatus(`Falha ao sincronizar documento ${payload.documento}. Cache local mantido.`);
      }
    }

    function buildHitachiPendencias(monthKey = currentHitachiMonth()) {
      const summary = hitachiMonthlySummary(monthKey);
      const items = [];
      summary.rows.forEach(row => {
        if (row.holerite === 'PENDENTE') items.push({ tipo: 'Colaborador', empresa: row.empresa, nome: row.colaborador, campo: 'Holerite' });
        if (row.comprovantePagamento === 'PENDENTE') items.push({ tipo: 'Colaborador', empresa: row.empresa, nome: row.colaborador, campo: 'Comprovante de pagamento' });
        if (row.comprovanteAdiantamento === 'PENDENTE') items.push({ tipo: 'Colaborador', empresa: row.empresa, nome: row.colaborador, campo: 'Comprovante de adiantamento' });
        if (row.kitRescisao === 'PENDENTE') items.push({ tipo: 'Colaborador', empresa: row.empresa, nome: row.colaborador, campo: 'Kit rescisao' });
      });
      summary.companyDocs.forEach(row => {
        if (row.status === 'PENDENTE') items.push({ tipo: 'Empresa', empresa: row.empresa, nome: row.documento, campo: 'Documento da empresa' });
      });
      return items;
    }

    function buildHitachiMailBody(monthKey = currentHitachiMonth()) {
      const pendencias = buildHitachiPendencias(monthKey);
      if (!pendencias.length) {
        return `Prezados,\n\nNao ha pendencias documentais para a competencia ${monthLabel(monthKey)}.\n\nAtenciosamente,\nPortal MSE`;
      }
      const grouped = pendencias.reduce((acc, item) => {
        const key = `${item.empresa}||${item.nome}`;
        if (!acc[key]) acc[key] = { empresa: item.empresa, nome: item.nome, campos: [] };
        acc[key].campos.push(item.campo);
        return acc;
      }, {});
      const lines = Object.values(grouped).map(item => `- ${item.empresa} | ${item.nome}: ${item.campos.join(', ')}`);
      return `Prezados,\n\nSegue relacao de pendencias documentais da competencia ${monthLabel(monthKey)}:\n\n${lines.join('\n')}\n\nFavor verificar e retornar com a regularizacao.\n\nAtenciosamente,\nPortal MSE`;
    }

    function normalizeRecipients(raw = '') {
      return raw
        .split(/[;,]+/)
        .map(item => item.trim())
        .filter(Boolean)
        .join(';');
    }

    function setHitachiMailFeedback(message = '') {
      document.getElementById('hitachiMailFeedback').textContent = message;
    }

    function refreshHitachiPendenciasModal() {
      const monthKey = currentHitachiMonth();
      const pendencias = buildHitachiPendencias(monthKey);
      document.getElementById('hitachiMailSubject').value = `Pendencias documentais - KPI Hitachi - ${monthLabel(monthKey)}`;
      document.getElementById('hitachiMailBody').value = buildHitachiMailBody(monthKey);
      const recipientsInput = document.getElementById('hitachiRecipients');
      recipientsInput.value = hitachiRecipients;
      setHitachiMailFeedback('');
      document.getElementById('hitachiPendenciasList').innerHTML = pendencias.length ? pendencias.map(item => `
        <div class="pending-mail-item">
          <b>${item.empresa}</b>
          <ul>
            <li>${item.nome}</li>
            <li>${item.campo}</li>
          </ul>
        </div>
      `).join('') : `<div class="empty-state"><b>Sem pendencias neste mes.</b>O e-mail sera montado como informativo de status regular.</div>`;
    }

    function editHitachiRow(id) {
      const item = hitachiCollaborators.find(entry => entry.id === id);
      if (!item) return;
      overviewEditingHitachiId = id;
      populateHitachiEditForm(document.getElementById('hitachiEditForm'), item);
      openModalById('hitachiEditModal');
    }
    window.editHitachiRow = editHitachiRow;

    function editHitachiCompanyDoc(id) {
      const item = hitachiCompanyDocs.find(entry => entry.id === id);
      if (!item) return;
      overviewEditingHitachiCompanyId = id;
      populateHitachiCompanyEditForm(document.getElementById('hitachiCompanyEditForm'), item);
      openModalById('hitachiCompanyModal');
    }
    window.editHitachiCompanyDoc = editHitachiCompanyDoc;

    function renderHitachi() {
      const monthKey = currentHitachiMonth();
      const summary = hitachiMonthlySummary(monthKey);
      const q = norm(document.getElementById('hq').value);
      const filteredRows = summary.rows.filter(row => {
        const hasPending = hitachiDocStatuses(row).some(status => status === 'PENDENTE');
        const statusOk =
          hitachiFilter === 'todos' ||
          (hitachiFilter === 'ok' && !hasPending) ||
          (hitachiFilter === 'pendente' && hasPending) ||
          (hitachiFilter === 'rescindidos' && row.situacao !== 'Ativo');
        const queryOk = !q || norm([row.colaborador, row.empresa, row.situacao].join(' ')).includes(q);
        return statusOk && queryOk;
      });
      const pct = summary.total ? Math.round((summary.ok / summary.total) * 100) : 0;
      const history = hitachiHistory();
      const maxHistoryTotal = history.length ? Math.max(...history.map(item => item.total || 0), 1) : 1;
      const companyBoxes = ['MSE ENGENHARIA', 'MSE SERVICE'].reduce((acc, empresa) => {
        const rows = summary.rows.filter(row => row.empresa === empresa);
        const docs = summary.companyDocs.filter(row => row.empresa === empresa);
        let ok = 0;
        let pending = 0;
        rows.forEach(row => {
          hitachiDocStatuses(row).forEach(status => {
            if (status === 'OK') ok += 1;
            if (status === 'PENDENTE') pending += 1;
          });
        });
        docs.forEach(row => {
          if (row.status === 'OK') ok += 1;
          if (row.status === 'PENDENTE') pending += 1;
        });
        acc[empresa] = { rows, docs, ok, pending };
        return acc;
      }, {});

      hMonthPicker.value = monthKey;
      document.getElementById('hPageTitle').textContent = `KPI Hitachi | ${monthLabel(monthKey)}`;
      document.getElementById('hPageSubtitle').textContent = `Competencia ${monthLabel(monthKey)} com ${summary.rows.length} colaborador(es) e ${summary.companyDocs.length} documento(s) da empresa.`;
      document.getElementById('hCollaborators').textContent = summary.rows.length;
      document.getElementById('hOkPct').textContent = `${pct}%`;
      document.getElementById('hPendings').textContent = summary.pending;
      document.getElementById('hCompanyDocs').textContent = summary.companyDocs.length;
      document.getElementById('hCountLabel').textContent = `${summary.rows.length} colaboradores no mes`;
      document.getElementById('hFootCount').textContent = `${summary.rows.length} registros mensais`;
      document.getElementById('hDonut').style.background = `conic-gradient(var(--green) 0deg ${pct * 3.6}deg,#edf1f5 ${pct * 3.6}deg 360deg)`;
      document.getElementById('hDonutPct').textContent = `${pct}%`;
      document.getElementById('hLegend').innerHTML = `
        <div class="leg"><span><span class="dot" style="background:var(--green)"></span>OK</span><b>${summary.ok}</b></div>
        <div class="leg"><span><span class="dot" style="background:var(--amber)"></span>Pendentes</span><b>${summary.pending}</b></div>
        <div class="leg"><span><span class="dot" style="background:var(--slate)"></span>Total</span><b>${summary.total}</b></div>
      `;

      document.getElementById('hEvolution').innerHTML = history.length ? history.map(item => `
        <div class="li">
          <div>
            <b class="link">${monthLabel(item.monthKey)}</b>
            <div class="lisub">${item.total} documento(s) considerados</div>
          </div>
          <div class="tag ${item.pct === 100 ? 'ok' : item.pct >= 85 ? 'warn' : 'neutral'}">${item.pct}% OK</div>
        </div>
      `).join('') : `<div class="empty-state"><b>Sem historico.</b>Cadastre um mes para acompanhar a evolucao.</div>`;

      document.getElementById('hVolumeBars').innerHTML = history.length ? [...history].reverse().map(item => `
        <div class="baritem">
          <div class="barlabel"><span>${monthLabel(item.monthKey)}</span><b>${item.total} docs</b></div>
          <div class="track"><div class="fill" style="width:${maxHistoryTotal ? (item.total / maxHistoryTotal) * 100 : 0}%"></div></div>
        </div>
      `).join('') : `<div class="empty-state"><b>Sem volume mensal.</b>Os meses cadastrados aparecerao aqui.</div>`;

      document.getElementById('hEngineeringCard').innerHTML = companyBoxes['MSE ENGENHARIA'].rows.length || companyBoxes['MSE ENGENHARIA'].docs.length ? `
        <div class="cred-item">
          <h4>MSE ENGENHARIA</h4>
          <div class="cred-row"><span>Colaboradores</span><b>${companyBoxes['MSE ENGENHARIA'].rows.length}</b></div>
          <div class="cred-row"><span>Itens OK</span><b>${companyBoxes['MSE ENGENHARIA'].ok}</b></div>
          <div class="cred-row"><span>Pendentes</span><b>${companyBoxes['MSE ENGENHARIA'].pending}</b></div>
        </div>` : `<div class="empty-state"><b>Sem dados da engenharia.</b>Cadastre os colaboradores do mes.</div>`;
      document.getElementById('hServiceCard').innerHTML = companyBoxes['MSE SERVICE'].rows.length || companyBoxes['MSE SERVICE'].docs.length ? `
        <div class="cred-item">
          <h4>MSE SERVICE</h4>
          <div class="cred-row"><span>Colaboradores</span><b>${companyBoxes['MSE SERVICE'].rows.length}</b></div>
          <div class="cred-row"><span>Itens OK</span><b>${companyBoxes['MSE SERVICE'].ok}</b></div>
          <div class="cred-row"><span>Pendentes</span><b>${companyBoxes['MSE SERVICE'].pending}</b></div>
        </div>` : `<div class="empty-state"><b>Sem dados do service.</b>Cadastre os colaboradores do mes.</div>`;

      const rowsBody = document.getElementById('hRows');
      rowsBody.innerHTML = filteredRows.length ? filteredRows.map(row => `
        <tr>
          <td><span class="company">${row.colaborador}</span></td>
          <td>${row.empresa}</td>
          <td><span class="tag ${row.situacao === 'Ativo' ? 'ok' : 'warn'}">${row.situacao}</span></td>
          <td><span class="tag ${statusTone(row.holerite)}">${row.holerite}</span></td>
          <td><span class="tag ${statusTone(row.comprovantePagamento)}">${row.comprovantePagamento}</span></td>
          <td><span class="tag ${statusTone(row.comprovanteAdiantamento)}">${row.comprovanteAdiantamento}</span></td>
          <td><span class="tag ${statusTone(row.kitRescisao)}">${row.kitRescisao}</span></td>
          <td class="actioncell"><button class="rowact" title="Editar colaborador" aria-label="Editar colaborador" onclick="editHitachiRow(${row.id})">${icon('edit')}</button></td>
        </tr>
      `).join('') : `<tr><td colspan="8"><div class="empty-state"><b>Nenhum colaborador encontrado.</b>Ajuste os filtros ou cadastre o mes.</div></td></tr>`;

      const companyBody = document.getElementById('hCompanyRows');
      companyBody.innerHTML = summary.companyDocs.length ? summary.companyDocs.map(row => `
        <tr>
          <td>${row.empresa}</td>
          <td><b class="link">${row.documento}</b></td>
          <td><span class="tag ${statusTone(row.status)}">${row.status}</span></td>
          <td class="actioncell"><button class="rowact" title="Editar documento" aria-label="Editar documento" onclick="editHitachiCompanyDoc(${row.id})">${icon('edit')}</button></td>
        </tr>
      `).join('') : `<tr><td colspan="4"><div class="empty-state"><b>Nenhum documento da empresa cadastrado.</b>Cadastre a competencia mensal para montar o painel.</div></td></tr>`;

      document.getElementById('hCadastroCount').textContent = `${hitachiCollaborators.length} registros`;
      document.getElementById('hCadastroList').innerHTML = hitachiCollaborators.length ? hitachiCollaborators.slice().sort((a, b) => monthIndex(b.monthKey) - monthIndex(a.monthKey)).map(item => `
        <div class="cred-item">
          <h4>${item.colaborador}</h4>
          <div class="cred-row"><span>Competencia</span><b>${monthLabel(item.monthKey)}</b></div>
          <div class="cred-row"><span>Empresa</span><b>${item.empresa}</b></div>
          <div class="cred-row"><span>Situacao</span><b>${item.situacao}</b></div>
          <div style="margin-top:10px;display:flex;justify-content:flex-end">
            <button class="inline-btn" type="button" onclick="editHitachiRow(${item.id})">Editar colaborador</button>
          </div>
        </div>
      `).join('') : `<div class="empty-state"><b>Nenhum colaborador salvo.</b>Cadastre a competencia para montar o dashboard.</div>`;

      document.getElementById('hCompanyCadastroCount').textContent = `${hitachiCompanyDocs.length} registros`;
      document.getElementById('hCompanyCadastroList').innerHTML = hitachiCompanyDocs.length ? hitachiCompanyDocs.slice().sort((a, b) => monthIndex(b.monthKey) - monthIndex(a.monthKey)).map(item => `
        <div class="cred-item">
          <h4>${item.documento}</h4>
          <div class="cred-row"><span>Competencia</span><b>${monthLabel(item.monthKey)}</b></div>
          <div class="cred-row"><span>Empresa</span><b>${item.empresa}</b></div>
          <div class="cred-row"><span>Status</span><b>${item.status}</b></div>
          <div style="margin-top:10px;display:flex;justify-content:flex-end">
            <button class="inline-btn" type="button" onclick="editHitachiCompanyDoc(${item.id})">Editar documento</button>
          </div>
        </div>
      `).join('') : `<div class="empty-state"><b>Nenhum documento salvo.</b>Cadastre os documentos mensais da empresa.</div>`;

      if (document.getElementById('hitachiPendenciasModal').classList.contains('open')) {
        refreshHitachiPendenciasModal();
      }
    }
`

## 6. Eventos do modulo

`javascript
    document.getElementById('navHitachi').addEventListener('click', () => switchModule('hitachi'));
    document.getElementById('resetHitachi').addEventListener('click', async () => {
      const monthKey = currentHitachiMonth();
      const label = monthLabel(monthKey);
      if (!window.confirm(`Deseja zerar os registros HITACHI do mes ${label}?`)) return;
      for (let index = hitachiCollaborators.length - 1; index >= 0; index -= 1) {
        if (hitachiCollaborators[index].monthKey === monthKey) hitachiCollaborators.splice(index, 1);
      }
      for (let index = hitachiCompanyDocs.length - 1; index >= 0; index -= 1) {
        if (hitachiCompanyDocs[index].monthKey === monthKey) hitachiCompanyDocs.splice(index, 1);
      }
      saveLocalCache();
      renderHitachi();
      try {
        await Promise.all([
          resetRemoteMonth('hitachi_collaborators', monthKey),
          resetRemoteMonth('hitachi_company_docs', monthKey)
        ]);
        setSyncStatus(`KPI Hitachi de ${label} zerado no Supabase`);
      } catch (error) {
        console.error(error);
        setSyncStatus(`Falha ao zerar KPI Hitachi de ${label}. Cache local mantido.`);
      }
    });
    document.querySelectorAll('[data-h-filter]').forEach(button => {
      button.addEventListener('click', () => {
        document.querySelectorAll('[data-h-filter]').forEach(item => item.classList.remove('on'));
        button.classList.add('on');
        hitachiFilter = button.dataset.hFilter;
        renderHitachi();
      });
    });
    document.getElementById('cancelHitachiEdit').addEventListener('click', resetHitachiForm);
    document.getElementById('cancelHitachiCompanyEdit').addEventListener('click', resetHitachiCompanyForm);
    document.getElementById('openHitachiPendencias').addEventListener('click', () => {
      refreshHitachiPendenciasModal();
      openModalById('hitachiPendenciasModal');
    });
    document.getElementById('refreshHitachiPendencias').addEventListener('click', () => {
      hitachiRecipients = normalizeRecipients(document.getElementById('hitachiRecipients').value.trim());
      saveLocalCache();
      refreshHitachiPendenciasModal();
    });
    document.getElementById('copyHitachiPendencias').addEventListener('click', async () => {
      const recipients = normalizeRecipients(document.getElementById('hitachiRecipients').value.trim());
      const subject = document.getElementById('hitachiMailSubject').value;
      const body = document.getElementById('hitachiMailBody').value;
      const fullText = `Para: ${recipients || '-'}\nAssunto: ${subject}\n\n${body}`;
      try {
        await navigator.clipboard.writeText(fullText);
        hitachiRecipients = recipients;
        saveLocalCache();
        setHitachiMailFeedback('Texto copiado. Se o e-mail nao abrir no navegador, voce ja pode colar no Outlook.');
      } catch (error) {
        console.error(error);
        setHitachiMailFeedback('Nao foi possivel copiar automaticamente neste navegador.');
      }
    });
    document.getElementById('sendHitachiPendencias').addEventListener('click', () => {
      const recipients = normalizeRecipients(document.getElementById('hitachiRecipients').value.trim());
      if (!recipients) {
        setHitachiMailFeedback('Preencha ao menos um e-mail destinatario para abrir a mensagem.');
        return;
      }
      hitachiRecipients = recipients;
      saveLocalCache();
      const subject = document.getElementById('hitachiMailSubject').value;
      const body = document.getElementById('hitachiMailBody').value;
      const target = `mailto:${recipients}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
      setHitachiMailFeedback('Tentando abrir o aplicativo de e-mail...');
      const anchor = document.createElement('a');
      anchor.href = target;
      anchor.target = '_top';
      anchor.rel = 'noopener';
      anchor.style.display = 'none';
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      try {
        window.open(target, '_top');
      } catch (error) {
        console.error(error);
      }
      window.setTimeout(() => {
        setHitachiMailFeedback('Se o Outlook nao abrir, use "Copiar texto" e cole no seu e-mail manualmente.');
      }, 900);
    });
    document.getElementById('closeHitachiPendenciasModal').addEventListener('click', () => closeModalById('hitachiPendenciasModal'));
    document.getElementById('closeHitachiEditModal').addEventListener('click', () => closeModalById('hitachiEditModal'));
    document.getElementById('cancelHitachiEditModal').addEventListener('click', () => closeModalById('hitachiEditModal'));
    document.getElementById('closeHitachiCompanyModal').addEventListener('click', () => closeModalById('hitachiCompanyModal'));
    document.getElementById('cancelHitachiCompanyModal').addEventListener('click', () => closeModalById('hitachiCompanyModal'));
    document.getElementById('hitachiForm').addEventListener('submit', async event => {
      event.preventDefault();
      const formData = Object.fromEntries(new FormData(event.currentTarget).entries());
      const payload = {
        id: editingHitachiId || createId(),
        monthKey: formData.monthKey || currentHitachiMonth(),
        empresa: formData.empresa,
        colaborador: formData.colaborador,
        situacao: formData.situacao,
        holerite: formData.holerite,
        comprovantePagamento: formData.comprovantePagamento,
        comprovanteAdiantamento: formData.comprovanteAdiantamento,
        kitRescisao: formData.kitRescisao
      };
      resetHitachiForm();
      await saveHitachiCollaborator(payload);
    });
    document.getElementById('hitachiCompanyForm').addEventListener('submit', async event => {
      event.preventDefault();
      const formData = Object.fromEntries(new FormData(event.currentTarget).entries());
      const payload = {
        id: editingHitachiCompanyId || createId(),
        monthKey: formData.monthKey || currentHitachiMonth(),
        empresa: formData.empresa,
        documento: formData.documento,
        status: formData.status
      };
      resetHitachiCompanyForm();
      await saveHitachiCompanyDoc(payload);
    });
    document.getElementById('hitachiEditForm').addEventListener('submit', async event => {
      event.preventDefault();
      const formData = Object.fromEntries(new FormData(event.currentTarget).entries());
      const payload = {
        id: overviewEditingHitachiId,
        monthKey: formData.monthKey || currentHitachiMonth(),
        empresa: formData.empresa,
        colaborador: formData.colaborador,
        situacao: formData.situacao,
        holerite: formData.holerite,
        comprovantePagamento: formData.comprovantePagamento,
        comprovanteAdiantamento: formData.comprovanteAdiantamento,
        kitRescisao: formData.kitRescisao
      };
      await saveHitachiCollaborator(payload);
      overviewEditingHitachiId = null;
      closeModalById('hitachiEditModal');
    });
    document.getElementById('hitachiCompanyEditForm').addEventListener('submit', async event => {
      event.preventDefault();
      const formData = Object.fromEntries(new FormData(event.currentTarget).entries());
      const payload = {
        id: overviewEditingHitachiCompanyId,
        monthKey: formData.monthKey || currentHitachiMonth(),
        empresa: formData.empresa,
        documento: formData.documento,
        status: formData.status
      };
      await saveHitachiCompanyDoc(payload);
      overviewEditingHitachiCompanyId = null;
      closeModalById('hitachiCompanyModal');
`

## Dependencias compartilhadas do portal

O modulo usa alguns helpers globais do portal principal, como:

- icon()
- monthLabel()
- monthIndex()
- 
orm()
- createId()
- saveLocalCache()
- setSyncStatus()
- upsertHitachiRemote()
- upsertHitachiCompanyDocRemote()
- 
esetRemoteMonth()
- currentMonthKey()

Se voce quiser, no proximo passo eu posso transformar este modulo em um arquivo HTML/JS independente e pronto para plugar em outro projeto.
