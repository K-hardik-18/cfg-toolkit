"""
generator.py

Stochastic generator for Context-Free Grammars (CFGs).

Expected grammar shape (same as cfg_parser.py output):
    {
      "S": [["NP","VP"], ["ε"]],
      "NP": [["Det","N"], ["N"]],
      "Det": [["the"], ["a"]],
      ...
    }

Functions:
- generate_one(grammar, symbol, max_depth=15, current_depth=0)
    Recursively expand `symbol` and return a dict { "string": str }.
    - If symbol is a terminal, returns it directly.
    - If symbol is a variable, randomly picks a production and expands it.
    - Epsilon productions are represented as the empty string "".
    - If recursion exceeds max_depth, returns {"string": "[...]"} (a truncation marker).

- generate_strings(grammar, start_symbol, max_strings=10, max_attempts=50, max_depth=15)
    Repeatedly calls generate_one to collect up to `max_strings` unique strings,
    trying up to `max_attempts` times.

Notes:
- The generator uses Python's random module. If you want reproducible output,
  call `random.seed(...)` before using generate_strings.
- The function returns strings joined by single spaces; epsilon is returned as an
  empty string "" (presentation layer may render it as "ε").
"""

from typing import Dict, List, Set
import random

def is_variable(sym: str) -> bool:
    """Rudimentary check for variables (non-terminals): starts with uppercase letter."""
    return bool(sym) and sym[0].isupper()


def generate_one(grammar: Dict[str, List[List[str]]], symbol: str,
                 max_depth: int = 15, current_depth: int = 0) -> dict:
    """
    Recursively generate a string for `symbol` using `grammar`.

    Returns: {"string": str}
      - normal string for a terminal expansion (may be empty for epsilon).
      - returns {"string": "[...]"} if max_depth is exceeded (truncation marker).

    Behavior:
    - If `symbol` is a terminal (not a variable), return it as the string.
    - If `symbol` is a variable:
        * If grammar lacks productions for it, return empty string (fallback).
        * Choose one production at random and expand recursively.
    - If a production is ['ε'] treat as epsilon -> "".
    """
    if current_depth > max_depth:
        # Indicate truncation (mirrors JS behavior "[...]")
        return {"string": "[...]"}

    # Terminal: return directly
    if not is_variable(symbol):
        return {"string": symbol}

    # Missing variable: fallback to empty string (shouldn't happen if grammar has been cleaned)
    if symbol not in grammar or not grammar[symbol]:
        return {"string": ""}

    rules = grammar[symbol]
    rule = random.choice(rules)

    # Epsilon production
    if len(rule) == 1 and rule[0] == "ε":
        return {"string": ""}

    parts: List[str] = []
    for sym in rule:
        res = generate_one(grammar, sym, max_depth=max_depth, current_depth=current_depth + 1)
        s = res.get("string", "")
        if s == "[...]":
            # propagate truncation immediately
            return {"string": "[...]"}
        if s != "":
            parts.append(s)

    # Join with space between terminals
    return {"string": " ".join(parts)}


def generate_strings(grammar: Dict[str, List[List[str]]], start_symbol: str,
                     max_strings: int = 10, max_attempts: int = 50, max_depth: int = 15) -> Set[str]:
    """
    Generate up to `max_strings` unique strings from `grammar` starting at `start_symbol`.

    - Tries up to `max_attempts` times to find unique strings.
    - Filters out strings that are empty or longer than a safety limit (50 chars by default).
    - Returns a set of generated strings. Epsilon (empty string) will be present as "".

    Note: Caller (e.g., frontend) may display empty string as "ε".
    """
    if start_symbol is None:
        return set()

    generated: Set[str] = set()
    attempts = 0

    while attempts < max_attempts and len(generated) < max_strings:
        attempts += 1
        try:
            res = generate_one(grammar, start_symbol, max_depth=max_depth, current_depth=0)
            s = res.get("string", "")
            # Accept epsilon as empty string, but do not accept overly long strings.
            if s == "[...]":
                # truncated — skip adding but continue attempts
                continue
            if len(s) == 0:
                # include epsilon only if grammar explicitly allows it from the start variable
                # safe to include; caller can interpret it
                generated.add(s)
            elif len(s) < 200 and len(s.split()) <= 40:
                # keep bounds generous but safe (JS used 50 chars; here token-limit is safer)
                generated.add(s)
            # otherwise skip because it's too long
        except RecursionError:
            # extremely deep recursion — treat as truncation
            continue

    # If nothing generated, attempt one final deterministic expansion (allow epsilon)
    if len(generated) == 0:
        try:
            res = generate_one(grammar, start_symbol, max_depth=max_depth, current_depth=0)
            s = res.get("string", "")
            if s == "":
                generated.add(s)  # epsilon
        except Exception:
            pass

    return generated


# -------------------
# Quick manual test
# -------------------
if __name__ == "__main__":
    # Example grammar (same as example CFG)
    example = {
        "S": [["NP", "VP"]],
        "NP": [["Det", "Adj", "N"], ["Det", "N"], ["N"]],
        "VP": [["V", "NP"], ["V"]],
        "Det": [["the"], ["a"]],
        "Adj": [["big"], ["small"], ["old"]],
        "N": [["cat"], ["cats"], ["dog"], ["dogs"], ["man"], ["men"]],
        "V": [["runs"], ["run"], ["eats"], ["eat"], ["chased"]],
    }

    # deterministic outputs for testing
    random.seed(42)

    gens = generate_strings(example, "S", max_strings=10, max_attempts=100, max_depth=20)
    print("Generated strings (showing ε as empty string):")
    for s in sorted(gens):
        if s == "":
            print("ε")
        else:
            print(s)
