from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Expense:
    expense_id: int
    owner: str
    merchant: str
    amount: str
    description: str


EXPENSES = {
    1041: Expense(1041, "alex", "Metro Transit", "18.50", "Client-site travel"),
    1042: Expense(1042, "sam", "Northwind Hotel", "286.00", "Conference lodging"),
    1043: Expense(1043, "alex", "Corner Cafe", "24.75", "Project lunch"),
}


def find_expense(
    requesting_user: str,
    expense_id: int,
    mode: str,
) -> Expense | None:
    if mode not in {"vulnerable", "fixed"}:
        raise ValueError("QUIZ_MODE must be vulnerable or fixed")

    expense = EXPENSES.get(expense_id)
    if expense is None:
        return None

    if mode == "fixed" and expense.owner != requesting_user:
        return None

    # The vulnerable lesson intentionally omits the object-ownership check.
    return expense
