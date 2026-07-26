from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timezone
from typing import Any

from .database import get_company_profile, get_duckdb


def _snapshot_cutoff(source_files: list[str]) -> date | None:
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    candidates: list[date] = []
    for source in source_files:
        match = re.search(r"(\d{1,2})(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{4})", source, re.I)
        if not match:
            continue
        try:
            candidates.append(date(int(match.group(3)), months[match.group(2).lower()], int(match.group(1))))
        except ValueError:
            continue
    return max(candidates) if candidates else None


def _ensure_settings(con: Any) -> None:
    rows = con.execute(
        "SELECT sku, name, quantity FROM inventory WHERE COALESCE(sku,'')<>'' ORDER BY sku"
    ).fetchall()
    for index, (sku, _name, quantity) in enumerate(rows):
        current = float(quantity or 0)
        # The demo deliberately includes a few watch items so the replenishment
        # workflow can be seen. User-provided settings are never overwritten.
        reorder = round(current * (1.12 if index % 7 == 0 else 0.28), 2)
        target = round(max(current * 1.35, reorder * 1.8), 2)
        lead_time = (14, 21, 30)[index % 3]
        con.execute(
            """
            INSERT OR IGNORE INTO inventory_reorder_settings
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [str(sku), reorder, target, lead_time, "Use supplier master", datetime.now(timezone.utc)],
        )


def _record_structured_invoice_movements(con: Any, cutoff: date | None) -> None:
    columns = {str(row[1]) for row in con.execute("PRAGMA table_info('invoices')").fetchall()}
    if not {"sku", "quantity", "unit_cost"}.issubset(columns):
        return
    rows = con.execute(
        """
        SELECT id, invoice_number, invoice_date, invoice_kind, sku, quantity,
               unit_cost, description, source_file
        FROM invoices
        WHERE COALESCE(sku,'')<>'' AND COALESCE(quantity,0)<>0
        """
    ).fetchall()
    for row in rows:
        invoice_id, invoice_number, invoice_date, kind, sku, quantity, unit_cost, description, source_file = row
        movement_id = f"invoice-movement-{invoice_id}"
        signed_quantity = abs(float(quantity or 0)) * (-1 if str(kind) == "sales" else 1)
        movement_type = "sale" if signed_quantity < 0 else "purchase"
        applied = cutoff is None or (invoice_date is not None and invoice_date > cutoff)
        existing = con.execute(
            "SELECT signed_quantity, applied_to_stock FROM inventory_movements WHERE id=?",
            [movement_id],
        ).fetchone()
        con.execute(
            """
            INSERT OR REPLACE INTO inventory_movements
            VALUES (?, ?, ?, COALESCE((SELECT name FROM inventory WHERE sku=? LIMIT 1), ?),
                    ?, ?, ?, ?, ?, 'invoice_line', ?, ?)
            """,
            [
                movement_id, invoice_date, str(sku), str(sku), str(description or sku),
                movement_type, signed_quantity, float(unit_cost or 0), str(invoice_number),
                str(source_file or ""), applied,
                "Applied after the latest inventory snapshot." if applied else "Already represented in the latest inventory snapshot.",
            ],
        )
        if applied and not existing:
            item = con.execute(
                "SELECT quantity, unit_cost, name, location, status, source_file FROM inventory WHERE sku=?",
                [str(sku)],
            ).fetchone()
            if item:
                old_qty, old_cost, name, location, status, inventory_source = item
                next_qty = float(old_qty or 0) + signed_quantity
                next_cost = float(unit_cost or old_cost or 0)
                con.execute(
                    """
                    UPDATE inventory
                    SET quantity=?, unit_cost=?, total_value=?
                    WHERE sku=?
                    """,
                    [next_qty, next_cost, next_qty * next_cost, str(sku)],
                )
            elif signed_quantity > 0:
                con.execute(
                    """
                    INSERT INTO inventory
                    VALUES (?, ?, ?, ?, ?, ?, 'Unassigned', 'active', ?)
                    """,
                    [
                        f"inventory-{hashlib.sha1(str(sku).encode()).hexdigest()[:16]}",
                        str(sku), str(description or sku), signed_quantity,
                        float(unit_cost or 0), signed_quantity * float(unit_cost or 0),
                        str(source_file or ""),
                    ],
                )


def _seed_synthetic_invoice_history(con: Any, cutoff: date | None) -> None:
    profile = get_company_profile()
    if "synthetic demo" not in str(profile.get("company_name") or "").lower():
        return
    if int(con.execute("SELECT COUNT(*) FROM inventory_movements").fetchone()[0]) > 0:
        return
    items = con.execute(
        "SELECT sku, name, unit_cost, source_file FROM inventory WHERE COALESCE(sku,'')<>'' ORDER BY sku"
    ).fetchall()
    invoices = con.execute(
        """
        SELECT invoice_number, invoice_date, invoice_kind, amount, source_file
        FROM invoices
        WHERE validation_status='approved'
        ORDER BY invoice_date, invoice_number
        """
    ).fetchall()
    if not items or not invoices:
        return
    for index, invoice in enumerate(invoices[:18]):
        invoice_number, invoice_date, kind, amount, source_file = invoice
        sku, name, unit_cost, _inventory_source = items[index % len(items)]
        base_units = max(1, round(abs(float(amount or 0)) / max(float(unit_cost or 1) * 8, 1)))
        signed_quantity = float(base_units) * (-1 if str(kind) == "sales" else 1)
        movement_type = "sale" if signed_quantity < 0 else "purchase"
        con.execute(
            """
            INSERT INTO inventory_movements
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE, ?)
            """,
            [
                f"demo-movement-{index + 1:03d}", invoice_date, str(sku), str(name),
                movement_type, signed_quantity, float(unit_cost or 0), str(invoice_number),
                str(source_file or ""), "synthetic_demo_inferred",
                "Illustrative invoice-to-stock history; already included in the 30 June inventory snapshot.",
            ],
        )


def sync_inventory_from_invoices() -> None:
    con = get_duckdb()
    try:
        source_files = [
            str(row[0] or "")
            for row in con.execute("SELECT DISTINCT source_file FROM inventory").fetchall()
        ]
        cutoff = _snapshot_cutoff(source_files)
        _ensure_settings(con)
        _record_structured_invoice_movements(con, cutoff)
        _seed_synthetic_invoice_history(con, cutoff)
    finally:
        con.close()


def inventory_dashboard() -> dict[str, Any]:
    sync_inventory_from_invoices()
    con = get_duckdb()
    try:
        rows = con.execute(
            """
            SELECT i.sku, i.name, i.quantity, i.unit_cost, i.total_value, i.location,
                   i.status, i.source_file,
                   COALESCE(r.reorder_point,0), COALESCE(r.target_stock,0),
                   COALESCE(r.lead_time_days,0), COALESCE(r.preferred_supplier,'')
            FROM inventory i
            LEFT JOIN inventory_reorder_settings r ON r.sku=i.sku
            ORDER BY i.total_value DESC, i.sku
            """
        ).fetchall()
        movements = con.execute(
            """
            SELECT movement_date, sku, item_name, movement_type, signed_quantity,
                   unit_cost, source_invoice, source_file, evidence_mode,
                   applied_to_stock, note
            FROM inventory_movements
            ORDER BY movement_date DESC, id DESC
            LIMIT 80
            """
        ).fetchall()
    finally:
        con.close()

    items: list[dict[str, Any]] = []
    for row in rows:
        sku, name, quantity, unit_cost, total_value, location, status, source_file, reorder, target, lead_time, supplier = row
        qty = float(quantity or 0)
        reorder_point = float(reorder or 0)
        stock_state = "reorder" if qty <= reorder_point else "watch" if qty <= reorder_point * 1.35 else "healthy"
        items.append({
            "sku": str(sku or ""), "name": str(name or ""), "quantity": round(qty, 2),
            "unit_cost": round(float(unit_cost or 0), 2), "total_value": round(float(total_value or 0), 2),
            "location": str(location or ""), "status": str(status or ""), "source_file": str(source_file or ""),
            "reorder_point": round(reorder_point, 2), "target_stock": round(float(target or 0), 2),
            "lead_time_days": int(lead_time or 0), "preferred_supplier": str(supplier or ""),
            "stock_state": stock_state, "suggested_order": round(max(0, float(target or 0) - qty), 2),
        })
    movement_records = [
        {
            "movement_date": str(row[0] or ""), "sku": str(row[1] or ""),
            "item_name": str(row[2] or ""), "movement_type": str(row[3] or ""),
            "signed_quantity": round(float(row[4] or 0), 2), "unit_cost": round(float(row[5] or 0), 2),
            "source_invoice": str(row[6] or ""), "source_file": str(row[7] or ""),
            "evidence_mode": str(row[8] or ""), "applied_to_stock": bool(row[9]),
            "note": str(row[10] or ""),
        }
        for row in movements
    ]
    total_value = sum(float(item["total_value"]) for item in items)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "sku_count": len(items),
            "units_on_hand": round(sum(float(item["quantity"]) for item in items), 2),
            "inventory_value": round(total_value, 2),
            "reorder_count": sum(1 for item in items if item["stock_state"] == "reorder"),
            "invoice_linked_movements": sum(1 for item in movement_records if item["source_invoice"]),
            "auto_applied_movements": sum(1 for item in movement_records if item["applied_to_stock"]),
        },
        "items": items,
        "movements": movement_records,
        "value_by_category": [
            {"label": item["name"], "value": item["total_value"], "sku": item["sku"]}
            for item in items[:8]
        ],
        "method": (
            "Structured invoice lines containing SKU and quantity update stock automatically when dated after the latest inventory snapshot. "
            "Earlier invoice movements remain traceable but are not double-counted."
        ),
    }
