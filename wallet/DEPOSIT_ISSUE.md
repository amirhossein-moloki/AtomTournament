# Zibal deposit verification issue and fix

## What was wrong
- The verification task only treated Zibal result code `100` as success and ignored `201` ("already verified"), so wallets stayed unchanged when Zibal returned 201 for a transaction that had already been confirmed.
- Wallet rows were updated without a database lock, so concurrent operations could overwrite balance changes and leave deposits unapplied in some race conditions.

## How it was fixed
- The task now treats both `100` and `201` as successful verification outcomes and updates the transaction record accordingly.
- It locks both the `Transaction` and its `Wallet` rows with `select_for_update()` inside a single atomic transaction before applying balance changes, ensuring wallet totals are increased exactly once.
- Saves now specify the exact fields being updated for clearer persistence of status, reference number, description, and wallet balances.

## Where to look
See `verify_deposit_task` in `wallet/tasks.py` for the updated verification, locking, and save logic.
