def minimize_debts(expenses):
    balances = {}

    for exp in expenses:
        payer = exp["payer"]
        amount = exp["amount"]
        shared_by = exp["shared_by"]

        if not shared_by:
            continue

        split_amount = amount / len(shared_by)
        balances[payer] = balances.get(payer, 0) + amount

        for person in shared_by:
            balances[person] = balances.get(person, 0) - split_amount

    debtors = []   
    creditors = [] 

    for person, balance in balances.items():
        balance = round(balance) 
        if balance < 0:
            debtors.append([person, -balance]) 
        elif balance > 0:
            creditors.append([person, balance])

    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    transactions = []
    i, j = 0, 0

    while i < len(debtors) and j < len(creditors):
        debtor_name, debt_amount = debtors[i]
        creditor_name, credit_amount = creditors[j]

        settle_amount = min(debt_amount, credit_amount)
        transactions.append(f"💸 {debtor_name} 需轉帳給 {creditor_name} {settle_amount} 元")

        debtors[i][1] -= settle_amount
        creditors[j][1] -= settle_amount

        if debtors[i][1] == 0: i += 1
        if creditors[j][1] == 0: j += 1

    if not transactions:
        return ["目前帳務完美平衡，互不相欠！"]

    return transactions