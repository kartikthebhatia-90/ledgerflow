from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .database import get_company_profile, get_duckdb


DEPARTMENTS = [
    ("Executive", "General Manager"),
    ("Finance", "Finance Manager"),
    ("Sales", "Account Manager"),
    ("Operations", "Warehouse Supervisor"),
    ("Operations", "Inventory Coordinator"),
    ("Customer", "Customer Success Specialist"),
    ("Growth", "Marketing Specialist"),
    ("Technology", "Systems Administrator"),
    ("People", "People and Payroll Coordinator"),
]


def _stable_index(value: str, size: int) -> int:
    return int(hashlib.sha1(value.encode("utf-8")).hexdigest()[:8], 16) % size


def sync_employee_profiles() -> None:
    con = get_duckdb()
    try:
        employees = [
            str(row[0])
            for row in con.execute(
                "SELECT DISTINCT employee FROM payroll_records WHERE COALESCE(employee,'')<>'' ORDER BY employee"
            ).fetchall()
        ]
        synthetic = "synthetic demo" in str(get_company_profile().get("company_name") or "").lower()
        for index, employee in enumerate(employees):
            department, role = DEPARTMENTS[index % len(DEPARTMENTS)]
            employee_code = f"EMP-{index + 1:03d}"
            start_date = date(2021 + (index % 5), 1 + ((index * 3) % 12), 1 + ((index * 5) % 24))
            manager = "Amelia Hart" if employee != "Amelia Hart" else "Board"
            evidence_mode = "synthetic_demo_profile" if synthetic else "inferred_from_payroll"
            con.execute(
                """
                INSERT OR IGNORE INTO employee_profiles
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Melbourne', 'active', ?)
                """,
                [employee, employee_code, department, role, "Permanent", start_date, manager, evidence_mode],
            )
            annual = round(4.5 + (_stable_index(employee + "annual", 115) / 10), 1)
            personal = round(2 + (_stable_index(employee + "personal", 70) / 10), 1)
            leave_taken = round(_stable_index(employee + "taken", 55) / 10, 1)
            review_date = date.today() + timedelta(days=20 + _stable_index(employee, 140))
            con.execute(
                """
                INSERT OR IGNORE INTO employee_leave_balances
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [employee, annual, personal, leave_taken, review_date, evidence_mode],
            )
            training_due = date.today() + timedelta(days=(-15 if index % 5 == 0 else 25 + index * 9))
            completion = "overdue" if training_due < date.today() else "scheduled"
            con.execute(
                """
                INSERT OR IGNORE INTO employee_training
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    f"training-{hashlib.sha1(employee.encode()).hexdigest()[:14]}", employee,
                    ("WHS refresher" if department == "Operations" else "Privacy and cyber awareness"),
                    training_due, completion, evidence_mode,
                ],
            )
    finally:
        con.close()


def hr_dashboard() -> dict[str, Any]:
    sync_employee_profiles()
    con = get_duckdb()
    try:
        latest_month = con.execute("SELECT MAX(substr(pay_period,1,7)) FROM payroll_records").fetchone()[0]
        payroll_rows = con.execute(
            """
            SELECT p.employee, e.employee_code, e.department, e.role_title,
                   e.employment_type, e.start_date, e.manager, e.location, e.status,
                   SUM(p.gross_pay), SUM(p.payg_withholding), SUM(p.superannuation),
                   SUM(p.net_pay), MAX(p.currency), MAX(p.source_file),
                   l.annual_leave_days, l.personal_leave_days, l.leave_taken_days,
                   l.next_review_date, t.course_name, t.due_date, t.completion_status,
                   e.evidence_mode
            FROM payroll_records p
            LEFT JOIN employee_profiles e ON e.employee=p.employee
            LEFT JOIN employee_leave_balances l ON l.employee=p.employee
            LEFT JOIN employee_training t ON t.employee=p.employee
            WHERE substr(p.pay_period,1,7)=?
            GROUP BY p.employee, e.employee_code, e.department, e.role_title,
                     e.employment_type, e.start_date, e.manager, e.location, e.status,
                     l.annual_leave_days, l.personal_leave_days, l.leave_taken_days,
                     l.next_review_date, t.course_name, t.due_date, t.completion_status,
                     e.evidence_mode
            ORDER BY e.department, p.employee
            """,
            [latest_month or ""],
        ).fetchall()
    finally:
        con.close()

    employees: list[dict[str, Any]] = []
    for row in payroll_rows:
        (
            employee, employee_code, department, role, employment_type, start_date,
            manager, location, status, gross, payg, super_amount, net, currency,
            source_file, annual_leave, personal_leave, leave_taken, next_review,
            course, due_date, completion_status, evidence_mode,
        ) = row
        ote = float(gross or 0)
        expected_super = round(ote * 0.12, 2)
        super_gap = round(float(super_amount or 0) - expected_super, 2)
        employees.append({
            "employee": str(employee), "employee_code": str(employee_code or ""),
            "department": str(department or "Unassigned"), "role_title": str(role or ""),
            "employment_type": str(employment_type or ""), "start_date": str(start_date or ""),
            "manager": str(manager or ""), "location": str(location or ""), "status": str(status or ""),
            "gross_pay": round(float(gross or 0), 2), "payg_withholding": round(float(payg or 0), 2),
            "superannuation": round(float(super_amount or 0), 2), "expected_super": expected_super,
            "super_gap": super_gap, "net_pay": round(float(net or 0), 2),
            "currency": str(currency or "AUD"), "source_file": str(source_file or ""),
            "annual_leave_days": round(float(annual_leave or 0), 1),
            "personal_leave_days": round(float(personal_leave or 0), 1),
            "leave_taken_days": round(float(leave_taken or 0), 1),
            "next_review_date": str(next_review or ""), "training": str(course or ""),
            "training_due": str(due_date or ""), "training_status": str(completion_status or ""),
            "evidence_mode": str(evidence_mode or ""),
        })
    departments: dict[str, dict[str, float]] = {}
    for employee in employees:
        bucket = departments.setdefault(employee["department"], {"gross_pay": 0.0, "headcount": 0.0})
        bucket["gross_pay"] += float(employee["gross_pay"])
        bucket["headcount"] += 1
    department_costs = [
        {"department": name, "gross_pay": round(values["gross_pay"], 2), "headcount": int(values["headcount"])}
        for name, values in sorted(departments.items(), key=lambda item: item[1]["gross_pay"], reverse=True)
    ]
    actions = []
    for employee in employees:
        if employee["training_status"] == "overdue":
            actions.append({
                "type": "training", "severity": "medium", "employee": employee["employee"],
                "detail": f"{employee['training']} is overdue.", "due_date": employee["training_due"],
            })
        if abs(float(employee["super_gap"])) > 0.02:
            actions.append({
                "type": "super", "severity": "high", "employee": employee["employee"],
                "detail": f"Super differs from the 12% planning check by {employee['super_gap']:.2f}.",
                "due_date": "",
            })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": str(latest_month or ""),
        "summary": {
            "headcount": len(employees),
            "gross_pay": round(sum(float(item["gross_pay"]) for item in employees), 2),
            "net_pay": round(sum(float(item["net_pay"]) for item in employees), 2),
            "payg_withholding": round(sum(float(item["payg_withholding"]) for item in employees), 2),
            "superannuation": round(sum(float(item["superannuation"]) for item in employees), 2),
            "annual_leave_days": round(sum(float(item["annual_leave_days"]) for item in employees), 1),
            "open_actions": len(actions),
        },
        "employees": employees,
        "department_costs": department_costs,
        "actions": actions,
        "disclaimer": (
            "Payroll values come from uploaded payroll evidence. Department, role, leave and training fields are synthetic demo profiles "
            "until connected to an HR master file."
        ),
    }
