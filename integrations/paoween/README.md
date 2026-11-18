# Paoween integration snapshot

This folder contains the Shopping-specific host integration snapshot used with the separate Paoween application: the host chat server and its existing UI script, plus synthetic regression tests. These files depend on the rest of Paoween, including its finance provider and existing dashboard assets; this directory is not a standalone application.

The Shopping Skill is in `.agents/skills/shopping-agent` at the repository root. Integrate the host files only after reviewing them against the target Paoween version; replacing modified host files blindly can discard local changes. Keep financial data and local state in the user's private installation, never in this repository. No ledger, profile, receipt, or goal database is included.

Current limitations: logical reservations are stored separately from savings goals, but the daily spending and purchase engines do not yet fully reconcile partially spent reservations with recorded transactions. The host reports monthly results as estimates and does not establish an account balance from salary. The standalone dashboard in this repository is a separate synthetic demo; it is not the Paoween dashboard.

To validate the integration, place it alongside the matching Paoween application and run the synthetic tests in its `tests` directory, without copying personal data into fixtures. The Shopping suite's host-routing tests skip when this host is absent.
