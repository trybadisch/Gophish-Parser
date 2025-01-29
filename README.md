# Gophish-Parser
Script to parse Gophish campaign results by position and filter false positive clicks.

False clicks are filtered through an invisible URL in the mail template including a canary parameter.
Also checks false input submissions when the user email is different from the form payload.

It requires both Gophish Results.csv and Events.csv as input.
It provides 3 outpus:
- users_at_risk.xlsx
- position_results.xlsx
- fake_input.json

## Usage:
```shell
./gophish-parser.py results.csv events.csv [click_canary]
```
