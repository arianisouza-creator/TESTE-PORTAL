from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Portal Administrativo | Controle de Internet",
    page_icon=":globe_with_meridians:",
    layout="wide",
    initial_sidebar_state="expanded",
)


DB_FILE = Path(__file__).with_name("portal_data.db")
PROTECTED_USER = "ADM"
PROTECTED_PASS = "mse2026"
MONTH_NAMES = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                project TEXT NOT NULL,
                due_day INTEGER NOT NULL,
                contract_number TEXT NOT NULL,
                status TEXT NOT NULL,
                start_month TEXT NOT NULL,
                inactive_month TEXT,
                contact TEXT,
                login_name TEXT,
                password_value TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS active_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_ref TEXT NOT NULL,
                number_value TEXT NOT NULL,
                responsible TEXT NOT NULL,
                cost_centers TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS monthly_entries (
                contract_id INTEGER NOT NULL,
                month_ref TEXT NOT NULL,
                amount REAL,
                order_number TEXT,
                approved INTEGER,
                s1 INTEGER,
                notes TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (contract_id, month_ref),
                FOREIGN KEY (contract_id) REFERENCES contracts(id)
            );
            """
        )


def parse_month(value: str) -> date:
    year, month = value.split("-")
    return date(int(year), int(month), 1)


def month_key(value: date | datetime | None = None) -> str:
    base = value.date() if isinstance(value, datetime) else value or date.today()
    return base.strftime("%Y-%m")


def month_label(value: str) -> str:
    current = parse_month(value)
    return f"{MONTH_NAMES[current.month]}/{current.year}"


def month_to_int(value: str) -> int:
    current = parse_month(value)
    return current.year * 12 + current.month


def month_picker(label: str, key: str, value: str) -> str:
    default_date = parse_month(value)
    picked = st.date_input(
        label,
        value=default_date,
        format="DD/MM/YYYY",
        key=key,
    )
    return month_key(picked)


def format_currency(value: float | None) -> str:
    if value is None:
        return "Pendente"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def bool_label(value: int | None) -> str:
    if value is None:
        return "Pendente"
    return "Sim" if value == 1 else "Nao"


def auth_ok() -> bool:
    return st.session_state.get("cadastro_auth", False)


def logout() -> None:
    st.session_state["cadastro_auth"] = False


def render_auth_gate() -> bool:
    if auth_ok():
        return True

    st.markdown(
        """
        <div style="max-width:520px;padding:24px;border:1px solid #dbe3f0;border-radius:18px;background:#ffffff;box-shadow:0 12px 30px rgba(15,23,42,.08);margin:16px 0;">
          <div style="font-size:26px;font-weight:800;color:#17356c;margin-bottom:6px;">Area de cadastro protegida</div>
          <div style="color:#5f6c84;">Use este acesso apenas para contratos, linhas ativas e credenciais.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("protected_login"):
        cols = st.columns(2)
        username = cols[0].text_input("Usuario")
        password = cols[1].text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar", use_container_width=True)

    if submit:
        if username == PROTECTED_USER and password == PROTECTED_PASS:
            st.session_state["cadastro_auth"] = True
            st.rerun()
        st.error("Usuario ou senha invalidos.")

    st.caption("Acesso do cadastro: `ADM` / `mse2026`")
    return False


def list_contracts() -> list[dict[str, Any]]:
    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM contracts
            ORDER BY status DESC, company, project, contract_number
            """
        ).fetchall()
    return [dict(row) for row in rows]


def save_contract(data: dict[str, Any], contract_id: int | None = None) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with db_connect() as conn:
        if contract_id:
            conn.execute(
                """
                UPDATE contracts
                SET company = ?, project = ?, due_day = ?, contract_number = ?, status = ?,
                    start_month = ?, inactive_month = ?, contact = ?, login_name = ?,
                    password_value = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    data["company"],
                    data["project"],
                    data["due_day"],
                    data["contract_number"],
                    data["status"],
                    data["start_month"],
                    data["inactive_month"] or None,
                    data["contact"],
                    data["login_name"],
                    data["password_value"],
                    data["notes"],
                    now,
                    contract_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO contracts (
                    company, project, due_day, contract_number, status,
                    start_month, inactive_month, contact, login_name,
                    password_value, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["company"],
                    data["project"],
                    data["due_day"],
                    data["contract_number"],
                    data["status"],
                    data["start_month"],
                    data["inactive_month"] or None,
                    data["contact"],
                    data["login_name"],
                    data["password_value"],
                    data["notes"],
                    now,
                    now,
                ),
            )


def get_contract(contract_id: int) -> dict[str, Any] | None:
    with db_connect() as conn:
        row = conn.execute(
            "SELECT * FROM contracts WHERE id = ?",
            (contract_id,),
        ).fetchone()
    return dict(row) if row else None


def contract_visible_for_month(contract: dict[str, Any], selected_month: str) -> bool:
    current = month_to_int(selected_month)
    start = month_to_int(contract["start_month"])
    inactive = contract.get("inactive_month")
    end = month_to_int(inactive) if inactive else None

    if current < start:
        return False
    if contract["status"] == "Inativo" and end is not None and current >= end:
        return False
    return True


def list_lines(month_ref: str) -> list[dict[str, Any]]:
    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM active_lines
            WHERE month_ref = ?
            ORDER BY id
            """,
            (month_ref,),
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        centers = [part.strip() for part in item["cost_centers"].split(",") if part.strip()]
        count = len(centers) if centers else 1
        item["centers_list"] = centers or [item["cost_centers"]]
        item["percentage_each"] = round(100 / count, 2)
        items.append(item)
    return items


def save_line(month_ref: str, number_value: str, responsible: str, cost_centers: str) -> None:
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO active_lines (month_ref, number_value, responsible, cost_centers, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                month_ref,
                number_value,
                responsible,
                cost_centers,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )


def delete_line(line_id: int) -> None:
    with db_connect() as conn:
        conn.execute("DELETE FROM active_lines WHERE id = ?", (line_id,))


def load_monthly_entry(contract_id: int, month_ref: str) -> dict[str, Any] | None:
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM monthly_entries
            WHERE contract_id = ? AND month_ref = ?
            """,
            (contract_id, month_ref),
        ).fetchone()
    return dict(row) if row else None


def save_monthly_entry(
    contract_id: int,
    month_ref: str,
    amount: float | None,
    order_number: str,
    approved: int | None,
    s1: int | None,
    notes: str,
) -> None:
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO monthly_entries (contract_id, month_ref, amount, order_number, approved, s1, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(contract_id, month_ref)
            DO UPDATE SET
                amount = excluded.amount,
                order_number = excluded.order_number,
                approved = excluded.approved,
                s1 = excluded.s1,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (
                contract_id,
                month_ref,
                amount,
                order_number or None,
                approved,
                s1,
                notes,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )


def month_rows(selected_month: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for contract in list_contracts():
        if not contract_visible_for_month(contract, selected_month):
            continue
        entry = load_monthly_entry(contract["id"], selected_month) or {}
        rows.append(
            {
                "id": contract["id"],
                "status": contract["status"],
                "project": contract["project"],
                "company": contract["company"],
                "due_day": contract["due_day"],
                "contract_number": contract["contract_number"],
                "contact": contract["contact"] or "-",
                "login_name": contract["login_name"] or "",
                "password_value": contract["password_value"] or "",
                "contract_notes": contract["notes"] or "",
                "month_notes": entry.get("notes") or "",
                "amount": entry.get("amount"),
                "order_number": entry.get("order_number") or "",
                "approved": entry.get("approved"),
                "s1": entry.get("s1"),
            }
        )
    return rows


def metric_card(label: str, value: str, help_text: str) -> None:
    st.markdown(
        f"""
        <div class="mse-card mse-metric-card">
          <div class="mse-eyebrow">{label}</div>
          <div class="mse-metric-value">{value}</div>
          <div class="mse-metric-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def pending_html(value: str, is_pending: bool) -> str:
    color = "#d92d20" if is_pending else "#1f2a37"
    return f"<span style='color:{color};font-weight:700;'>{value}</span>"


def empty_state(message: str) -> None:
    st.markdown(
        f"""
        <div class="mse-empty">
          <span>{message}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(selected_month: str) -> str:
    st.markdown(
        """
        <div class="nav-top-icon">&laquo;</div>
        <div class="nav-brand">Portal MSE</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="nav-month">Mes ativo: {month_label(selected_month)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-card-title">Administrativo</div>', unsafe_allow_html=True)
    page = st.radio(
        "Menu",
        options=["Visao Geral", "Linhas Ativas e Acessos", "Contratos"],
        label_visibility="collapsed",
        key="main_nav",
    )
    if not auth_ok():
        st.markdown('<div class="nav-protected">Cadastro protegido</div>', unsafe_allow_html=True)
    return page


def render_overview(selected_month: str) -> None:
    rows = month_rows(selected_month)
    active_lines = list_lines(selected_month)
    contracts_count = len(rows)
    total_amount = sum(row["amount"] or 0 for row in rows)
    operators = len({row["company"] for row in rows})
    next_due = min((row["due_day"] for row in rows), default="-")
    orders = len([row for row in rows if row["order_number"]])

    st.markdown('<div class="page-subtitle dark">Dashboard Executivo</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-caption dark">Visualizacao automatica dos contratos do mes com pendencias destacadas.</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Contratos ativos", str(contracts_count), "Visiveis neste mes")
    with c2:
        metric_card("Valor mensal", format_currency(total_amount if total_amount else 0), "Total preenchido")
    with c3:
        metric_card("Operadoras", str(operators), "Empresas distintas")
    with c4:
        metric_card("Proximo vencimento", str(next_due), "Dia mais proximo")
    with c5:
        metric_card("Linhas ativas", str(len(active_lines)), "Cadastro do mes")

    left, right = st.columns([1.5, 1])
    with left:
        st.markdown('<div class="section-title">Valor por obra</div>', unsafe_allow_html=True)
        if rows:
            chart_df = pd.DataFrame(
                {
                    "Obra": [row["project"] for row in rows],
                    "Valor": [row["amount"] or 0 for row in rows],
                }
            ).groupby("Obra", as_index=True).sum()
            st.bar_chart(chart_df)
        else:
            empty_state("Nenhum contrato ativo no mes selecionado.")

    with right:
        st.markdown('<div class="section-title">Pendencias do mes</div>', unsafe_allow_html=True)
        pending = [
            row
            for row in rows
            if row["amount"] is None or not row["order_number"] or row["approved"] is None or row["s1"] is None
        ]
        if not pending:
            st.markdown('<div class="mse-ok-box">Nao ha pendencias neste mes.</div>', unsafe_allow_html=True)
        else:
            for row in pending[:8]:
                fields = []
                if row["amount"] is None:
                    fields.append("Valor")
                if not row["order_number"]:
                    fields.append("Pedido")
                if row["approved"] is None:
                    fields.append("Aprovado")
                if row["s1"] is None:
                    fields.append("S1")
                st.markdown(f"**{row['company']}**  \n{row['project']}  \nPendente: {', '.join(fields)}")

    st.markdown('<div class="section-title" style="margin-top:28px;">Contratos do mes</div>', unsafe_allow_html=True)
    header = st.columns([1.0, 1.2, 2.1, 0.8, 1.2, 1.4, 1.1, 1.0, 0.9, 0.8, 0.8])
    labels = [
        "Status",
        "Obra",
        "Empresa",
        "Venc.",
        "Contrato",
        "Contato",
        "Valor",
        "Pedido",
        "Aprov.",
        "S1",
        "Acoes",
    ]
    for col, label in zip(header, labels):
        col.markdown(
            f"<div style='font-size:11px;color:#7b8ba3;font-weight:700;text-transform:uppercase;padding-bottom:6px;'>{label}</div>",
            unsafe_allow_html=True,
        )

    if not rows:
        empty_state("Nenhum contrato disponivel neste mes.")
        return

    for row in rows:
        cols = st.columns([1.0, 1.2, 2.1, 0.8, 1.2, 1.4, 1.1, 1.0, 0.9, 0.8, 0.8])
        cols[0].markdown(
            pending_html("ATIVO" if row["status"] == "Ativo" else "INATIVO", row["status"] != "Ativo"),
            unsafe_allow_html=True,
        )
        cols[1].write(row["project"])
        cols[2].write(row["company"])
        cols[3].write(str(row["due_day"]))
        cols[4].write(row["contract_number"])
        cols[5].write(row["contact"])
        cols[6].markdown(pending_html(format_currency(row["amount"]), row["amount"] is None), unsafe_allow_html=True)
        cols[7].markdown(pending_html(row["order_number"] or "Pendente", not row["order_number"]), unsafe_allow_html=True)
        cols[8].markdown(pending_html(bool_label(row["approved"]), row["approved"] is None), unsafe_allow_html=True)
        cols[9].markdown(pending_html(bool_label(row["s1"]), row["s1"] is None), unsafe_allow_html=True)
        if cols[10].button("Editar", key=f"edit_month_{row['id']}_{selected_month}"):
            st.session_state["edit_month_row"] = row["id"]
        st.divider()

    edit_id = st.session_state.get("edit_month_row")
    if not edit_id:
        return

    selected = next((item for item in rows if item["id"] == edit_id), None)
    if not selected:
        return

    st.markdown("### Atualizar pendencias do mes")
    with st.form("month_entry_form"):
        cols = st.columns(4)
        amount_raw = cols[0].text_input(
            "Valor",
            value="" if selected["amount"] is None else str(selected["amount"]).replace(".", ","),
            placeholder="Ex.: 1339,94",
        )
        order_number = cols[1].text_input("Pedido", value=selected["order_number"])
        approved = cols[2].selectbox(
            "Aprovado",
            options=["Pendente", "Sim", "Nao"],
            index=0 if selected["approved"] is None else 1 if selected["approved"] == 1 else 2,
        )
        s1 = cols[3].selectbox(
            "Aprovado no S1",
            options=["Pendente", "Sim", "Nao"],
            index=0 if selected["s1"] is None else 1 if selected["s1"] == 1 else 2,
        )
        notes = st.text_input("Observacao do mes", value=selected["month_notes"])
        save = st.form_submit_button("Salvar atualizacao", use_container_width=True)

    if save:
        amount = None
        if amount_raw.strip():
            amount = float(amount_raw.replace(".", "").replace(",", "."))
        save_monthly_entry(
            contract_id=selected["id"],
            month_ref=selected_month,
            amount=amount,
            order_number=order_number,
            approved=None if approved == "Pendente" else 1 if approved == "Sim" else 0,
            s1=None if s1 == "Pendente" else 1 if s1 == "Sim" else 0,
            notes=notes,
        )
        st.session_state["edit_month_row"] = None
        st.success("Registro mensal atualizado.")
        st.rerun()


def render_lines_page(selected_month: str) -> None:
    st.markdown("## Linhas Ativas")
    st.caption("Cadastre aqui as linhas do mes e o rateio automatico por centro de custo.")

    with st.form("line_form"):
        cols = st.columns(3)
        number_value = cols[0].text_input("Numero", placeholder="43 99999-0000")
        responsible = cols[1].text_input("Responsavel", placeholder="Nome do responsavel")
        cost_centers = cols[2].text_input("Centro de custo", placeholder="ADM, MKT, DTE")
        submit = st.form_submit_button("Adicionar linha", use_container_width=True)

    if submit:
        if number_value and responsible and cost_centers:
            save_line(selected_month, number_value, responsible, cost_centers)
            st.success("Linha cadastrada com sucesso.")
            st.rerun()
        st.error("Preencha numero, responsavel e centro de custo.")

    lines = list_lines(selected_month)
    st.markdown("### Linhas cadastradas no mes")
    if not lines:
        st.info("Nenhuma linha cadastrada para este mes.")
    else:
        head = st.columns([1.1, 1.2, 2.2, 1.0, 0.8])
        titles = ["Numero", "Responsavel", "Centros de custo", "Percentual", "Acoes"]
        for col, title in zip(head, titles):
            col.markdown(
                f"<div style='font-size:11px;color:#7b8ba3;font-weight:700;text-transform:uppercase;padding-bottom:6px;'>{title}</div>",
                unsafe_allow_html=True,
            )

        for line in lines:
            cols = st.columns([1.1, 1.2, 2.2, 1.0, 0.8])
            cols[0].write(line["number_value"])
            cols[1].write(line["responsible"])
            cols[2].write(", ".join(line["centers_list"]))
            cols[3].write(f"{line['percentage_each']:.2f}% por C.C")
            if cols[4].button("Remover", key=f"remove_line_{line['id']}"):
                delete_line(line["id"])
                st.rerun()
            st.divider()

    st.markdown("### Credenciais dos contratos ativos")
    contract_rows = month_rows(selected_month)
    if not contract_rows:
        st.info("Sem contratos ativos neste mes.")
    else:
        for row in contract_rows:
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"**{row['company']}**")
                    st.write(f"Obra: {row['project']}")
                    st.write(f"Contrato: {row['contract_number']}")
                    st.write(f"Contato: {row['contact']}")
                with c2:
                    st.write(f"Login: {row['login_name'] or '-'}")
                    st.write(f"Senha: {row['password_value'] or '-'}")
                if row["contract_notes"]:
                    st.caption(f"Observacao: {row['contract_notes']}")


def render_contracts_page(selected_month: str) -> None:
    st.markdown("## Cadastro de Contratos")
    st.caption("A base mestra gera automaticamente os registros de cada mes a partir do mes de inicio.")

    contract_rows = list_contracts()
    edit_id = st.session_state.get("edit_contract_id")
    editing = get_contract(edit_id) if edit_id else None

    with st.form("contract_form"):
        row1 = st.columns(4)
        company = row1[0].text_input("Empresa", value=editing["company"] if editing else "", placeholder="Ex.: VIVO")
        project = row1[1].text_input("Obra", value=editing["project"] if editing else "", placeholder="Ex.: Sede")
        due_day = row1[2].number_input(
            "Vencimento",
            min_value=1,
            max_value=31,
            value=int(editing["due_day"]) if editing else 1,
        )
        contract_number = row1[3].text_input(
            "Numero do contrato",
            value=editing["contract_number"] if editing else "",
            placeholder="Ex.: 285704686",
        )

        row2 = st.columns(4)
        status = row2[0].selectbox(
            "Status",
            options=["Ativo", "Inativo"],
            index=0 if not editing or editing["status"] == "Ativo" else 1,
        )
        with row2[1]:
            start_month = month_picker(
                "Mes de inicio",
                key="contract_start_month",
                value=editing["start_month"] if editing else selected_month,
            )
        with row2[2]:
            inactive_month = month_picker(
                "Mes/ano inativo",
                key="contract_inactive_month",
                value=editing["inactive_month"] if editing and editing["inactive_month"] else selected_month,
            )
        contact = row2[3].text_input("Contato", value=editing["contact"] if editing else "", placeholder="Telefone ou WhatsApp")

        row3 = st.columns(2)
        login_name = row3[0].text_input("Login", value=editing["login_name"] if editing else "")
        password_value = row3[1].text_input("Senha", value=editing["password_value"] if editing else "", type="password")
        notes = st.text_area("Observacao", value=editing["notes"] if editing else "", height=100)

        save = st.form_submit_button("Salvar contrato", use_container_width=True)

    if save:
        if not all([company.strip(), project.strip(), contract_number.strip()]):
            st.error("Preencha empresa, obra e numero do contrato.")
        else:
            save_contract(
                {
                    "company": company.strip(),
                    "project": project.strip(),
                    "due_day": int(due_day),
                    "contract_number": contract_number.strip(),
                    "status": status,
                    "start_month": start_month,
                    "inactive_month": inactive_month if status == "Inativo" else "",
                    "contact": contact.strip(),
                    "login_name": login_name.strip(),
                    "password_value": password_value,
                    "notes": notes.strip(),
                },
                contract_id=edit_id,
            )
            st.session_state["edit_contract_id"] = None
            st.success("Contrato salvo com sucesso.")
            st.rerun()

    st.markdown("### Contratos cadastrados")
    if not contract_rows:
        st.info("Nenhum contrato cadastrado ainda.")
        return

    head = st.columns([1.7, 1.2, 0.9, 1.0, 1.0, 0.9])
    labels = ["Empresa / Obra", "Contrato", "Status", "Inicio", "Inativo em", "Acoes"]
    for col, label in zip(head, labels):
        col.markdown(
            f"<div style='font-size:11px;color:#7b8ba3;font-weight:700;text-transform:uppercase;padding-bottom:6px;'>{label}</div>",
            unsafe_allow_html=True,
        )

    for contract in contract_rows:
        cols = st.columns([1.7, 1.2, 0.9, 1.0, 1.0, 0.9])
        cols[0].write(f"{contract['company']} | {contract['project']}")
        cols[1].write(contract["contract_number"])
        cols[2].write(contract["status"])
        cols[3].write(month_label(contract["start_month"]))
        cols[4].write(month_label(contract["inactive_month"]) if contract["inactive_month"] else "-")
        if cols[5].button("Editar", key=f"edit_contract_{contract['id']}"):
            st.session_state["edit_contract_id"] = contract["id"]
            st.rerun()
        st.divider()


def main() -> None:
    init_db()

    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
          :root{
            --bg:#e8eaee; --card:#fff; --line:#e4e7ec; --line-2:#eef0f3; --chip:#eef0f3;
            --navy:#16243c; --navy-2:#1f3a63; --ink:#192231; --body:#4d5868; --mut:#98a1b0; --mut-2:#aab2bf;
            --blue:#2563eb; --green:#1f9d57; --amber:#d9911a; --red:#d23b3b;
            --r:14px; --shadow:0 1px 2px rgba(16,24,40,.05),0 1px 3px rgba(16,24,40,.04); --maxw:1440px;
          }
          html, body, [class*="css"]  { font-family: "IBM Plex Sans", sans-serif; }
          .stApp { background: var(--bg); }
          [data-testid="stAppViewContainer"] { background:var(--bg); }
          [data-testid="stHeader"] { background: transparent; }
          [data-testid="stToolbar"] { right: 18px; top: 18px; }
          [data-testid="stSidebar"] { display:none !important; }
          .block-container { padding-top: 0; padding-bottom: 2rem; max-width: 100%; padding-left: 0; padding-right: 0; }
          div[data-testid="stForm"] { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; box-shadow:var(--shadow); }
          label, [data-testid="stWidgetLabel"] p, .stNumberInput label p, .stTextInput label p, .stDateInput label p, .stSelectbox label p, .stTextArea label p {
            font-family:"IBM Plex Mono", monospace !important;
            text-transform:uppercase;
            letter-spacing:2px;
            font-size:10px !important;
            color:var(--mut) !important;
            font-weight:500 !important;
          }
          .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input, .stSelectbox [data-baseweb="select"] > div {
            border:1px solid var(--line) !important;
            border-radius:10px !important;
            background:#fff !important;
            color:var(--ink) !important;
            box-shadow:none !important;
          }
          .stButton button, .stDownloadButton button, .stForm button[kind="primary"] {
            border-radius:10px !important;
            border:1px solid var(--line) !important;
            box-shadow:var(--shadow) !important;
            font-weight:600 !important;
          }
          .stButton button[kind="primary"], .stForm button[kind="primary"] {
            background:var(--blue) !important;
            color:#fff !important;
            border-color:var(--blue) !important;
          }
          .main-left-col {
            background:linear-gradient(180deg,#213f76 0%,#2a4a84 100%);
            border-radius:0;
            padding:22px 20px 26px;
            min-height:calc(100vh - 24px);
          }
          .top-shell {
            height:74px;
            background:#15181f;
            display:flex;
            align-items:center;
            justify-content:flex-end;
            padding:0 28px;
            border-radius:0;
            margin-bottom:0;
          }
          .top-shell span {
            color:#f8fafc;
            font-size:14px;
            font-weight:600;
            opacity:.92;
          }
          .hero-shell {
            background: radial-gradient(640px 360px at 85% -30%, rgba(64,120,210,.5), transparent 62%), linear-gradient(118deg,#13223b,#193053 68%,#1f3a63);
            padding:28px 28px 30px;
            margin-bottom:0;
          }
          .content-shell {
            padding:28px;
          }
          .month-shell {
            background:#242732;
            border-radius:10px;
            padding:12px 16px 8px;
            width:280px;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,.03);
          }
          .month-shell label, .month-shell div, .month-shell p, .month-shell input { color:#ffffff !important; }
          .month-shell input {
            background:#242732 !important;
            border:0 !important;
            font-family:"IBM Plex Mono", monospace !important;
            font-size:18px !important;
            font-weight:600 !important;
          }
          .hero-header { display:flex; align-items:flex-start; justify-content:space-between; gap:24px; }
          .page-title {
            font-size:54px;
            line-height:1;
            font-weight:800;
            color:#f3f6fb;
            margin:38px 0 10px;
          }
          .page-subtitle {
            font-size:32px;
            font-weight:800;
            color:#192231;
            margin-top:18px;
          }
          .page-subtitle.dark { color:#ffffff; margin-top:14px; }
          .page-caption {
            color:#667085;
            margin:8px 0 24px;
            font-size:14px;
          }
          .page-caption.dark { color:rgba(255,255,255,.76); }
          .section-title {
            font-size:26px;
            font-weight:800;
            color:#192231;
            margin:10px 0 14px;
          }
          .mse-card {
            background:var(--card);
            border:1px solid var(--line);
            border-radius:16px;
            box-shadow:var(--shadow);
          }
          .mse-metric-card {
            padding:18px 18px 16px;
            min-height:112px;
          }
          .mse-eyebrow {
            font-family:"IBM Plex Mono", monospace;
            text-transform:uppercase;
            letter-spacing:1.6px;
            font-size:10px;
            color:#6d7a8d;
            font-weight:600;
          }
          .mse-metric-value {
            font-size:24px;
            font-weight:700;
            color:#17356c;
            margin-top:16px;
          }
          .mse-metric-help {
            font-size:13px;
            color:#738198;
            margin-top:8px;
          }
          .mse-empty {
            border:1px dashed #bdd5f6;
            background:#dcebff;
            color:#3384ff;
            border-radius:10px;
            padding:16px 18px;
            font-size:14px;
          }
          .mse-ok-box {
            border-radius:10px;
            background:rgba(31,157,87,.10);
            color:#28bf5b;
            padding:16px 18px;
            font-size:14px;
          }
          div[data-testid="stVerticalBlock"] div[data-testid="stMarkdownContainer"] p {
            color:var(--body);
          }
          [data-testid="stAlert"] p { margin:0; }
          [data-testid="stAlert"] {
            border-radius:12px;
            border:0;
          }
          [data-testid="column"] { position:relative; min-width:0; }
          .nav-top-icon {
            text-align:right;
            font-size:34px;
            line-height:1;
            color:#ffffff;
            font-weight:800;
            margin-bottom:56px;
          }
          .nav-brand {
            color:#ffffff;
            font-size:28px;
            font-weight:800;
            margin-bottom:18px;
          }
          .nav-month {
            color:rgba(255,255,255,.78);
            font-size:14px;
            margin-bottom:24px;
          }
          .nav-card-title {
            background:#1f232d;
            color:#ffffff;
            padding:14px 16px;
            border:1px solid rgba(255,255,255,.14);
            border-bottom:none;
            border-radius:12px 12px 0 0;
            font-size:15px;
            font-weight:700;
          }
          .stRadio > div {
            background:#232834;
            border:1px solid rgba(255,255,255,.14);
            border-radius:0 0 12px 12px;
            padding:16px 14px;
          }
          .stRadio label {
            padding:10px 8px;
            border-radius:10px;
          }
          .stRadio label:hover { background:rgba(255,255,255,.05); }
          .stRadio p {
            color:#ffffff !important;
            letter-spacing:1.6px !important;
          }
          .nav-button .stButton button {
            margin-top:14px;
            background:#1f232d !important;
            color:#ffffff !important;
            border:1px solid rgba(255,255,255,.14) !important;
          }
          .nav-protected {
            color:rgba(255,255,255,.68);
            font-size:14px;
            margin-top:14px;
          }
          .overview-table-head {
            font-family:"IBM Plex Mono", monospace;
            text-transform:uppercase;
            letter-spacing:1.4px;
            color:#98a1b0;
            font-size:10px;
            font-weight:600;
            padding-bottom:8px;
          }
          .table-row {
            background:#ffffff;
            border:1px solid var(--line);
            border-radius:14px;
            box-shadow:var(--shadow);
            padding:10px 12px;
            margin-bottom:10px;
          }
          hr { border-color:var(--line-2); }
        </style>
        """,
        unsafe_allow_html=True,
    )
    left_col, right_col = st.columns([0.95, 5.05], gap="small")
    selected_month = st.session_state.get("selected_month", month_key())

    with left_col:
        st.markdown('<div class="main-left-col">', unsafe_allow_html=True)
        page = render_sidebar(selected_month)
        st.markdown('<div class="nav-button">', unsafe_allow_html=True)
        if auth_ok():
            st.button("Sair do cadastro", on_click=logout, use_container_width=True, key="logout_main_nav_bottom")
        st.markdown('</div></div>', unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="top-shell"><span>Share &nbsp;&nbsp; ☆ &nbsp;&nbsp; ✎ &nbsp;&nbsp; GitHub</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-shell">', unsafe_allow_html=True)
        hero_cols = st.columns([1.15, 3.85], gap="large")
        with hero_cols[0]:
            st.markdown('<div class="month-shell">', unsafe_allow_html=True)
            selected_month = month_picker(
                "Mes de referencia",
                key="selected_month_picker",
                value=st.session_state.get("selected_month", month_key()),
            )
            st.markdown('</div>', unsafe_allow_html=True)
        st.session_state["selected_month"] = selected_month
        with hero_cols[1]:
            st.markdown('<div class="page-title">Controle de Internet</div>', unsafe_allow_html=True)
            st.markdown('<div class="page-subtitle dark">Painel Administrativo MSE</div>', unsafe_allow_html=True)
            st.markdown('<div class="page-caption dark">Acompanhamento mensal de contratos, linhas ativas e credenciais.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="content-shell">', unsafe_allow_html=True)

        if page == "Visao Geral":
            render_overview(selected_month)
        else:
            if render_auth_gate():
                if page == "Linhas Ativas e Acessos":
                    render_lines_page(selected_month)
                else:
                    render_contracts_page(selected_month)

        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
