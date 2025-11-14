import re
from typing import Dict, List, Set, Any

# Regular expression to detect a variable (non-terminal).
# Matches names that start with an uppercase letter and may include letters, digits, underscore,
# and optionally a trailing apostrophe (e.g., S, NP, Det, X1, S').
_VAR_RE = re.compile(r"^[A-Z][A-Za-z0-9_]*'?$")


def is_variable(token: str) -> bool:
    """Return True if token looks like a non-terminal (variable)."""
    return bool(_VAR_RE.match(token))


class CFGError(ValueError):
    """Raised when the CFG is invalid in some way."""


def _parse_rhs_string(rhs_str: str) -> List[List[str]]:
    """
    Parse a RHS string like "A B | a b | ε" into a list of rules:
    [['A', 'B'], ['a', 'b'], ['ε']]
    """
    if rhs_str is None:
        return []
    parts = [p.strip() for p in rhs_str.split("|")]
    rules = []
    for p in parts:
        if p == "":
            # treat empty alternative as epsilon
            rules.append(["ε"])
            continue
        symbols = [tok.strip() for tok in p.split() if tok.strip() != ""]
        if len(symbols) == 0:
            rules.append(["ε"])
        else:
            rules.append(symbols)
    return rules


def parse_cfg(start_variable: str, productions: Any) -> Dict[str, List[List[str]]]:
    """
    Parse and validate the grammar supplied by the frontend and return a cleaned grammar.

    Expected input shapes
    ---------------------
    - productions can be a mapping: { "S": [["NP","VP"], ["ε"]], "NP": [["Det","N"], ["N"]] }
      (i.e., already tokenized lists)
    - OR productions can be a list of dicts: [ { "lhs": "S", "rhs": "NP VP | ε" }, ... ]
      where rhs is a single string with pipe-separated alternatives.

    Returns
    -------
    A dictionary: { variable: [ [sym1, sym2], [sym1], ... ] }
    Where terminals are plain strings (not marked), and epsilon is literally 'ε'

    Raises
    ------
    CFGError on invalid grammar.
    """
    # Basic validations
    if not start_variable or not isinstance(start_variable, str):
        raise CFGError("Start variable must be a non-empty string.")

    start_variable = start_variable.strip()
    if not is_variable(start_variable):
        raise CFGError(f"Invalid start variable '{start_variable}'. Must start with an uppercase letter.")

    # Build preliminary productions map
    productions_map: Dict[str, List[List[str]]] = {}

    # Support two input formats
    if isinstance(productions, dict):
        # assume mapping lhs -> list-of-rules
        for lhs, rhs_list in productions.items():
            if not lhs or not isinstance(lhs, str):
                raise CFGError(f"Invalid LHS value: {lhs!r}")
            lhs = lhs.strip()
            if lhs == "":
                continue
            if not is_variable(lhs):
                raise CFGError(f"Invalid variable format on left-hand side: '{lhs}'. Variables must start with an uppercase letter (e.g., S, NP, Det).")
            if lhs not in productions_map:
                productions_map[lhs] = []

            # rhs_list must be list of lists or list of strings
            if not isinstance(rhs_list, list):
                raise CFGError(f"RHS for '{lhs}' must be a list (found {type(rhs_list).__name__}).")
            for rhs in rhs_list:
                if isinstance(rhs, str):
                    # treat as space-separated tokens
                    syms = [t for t in rhs.split() if t]
                    productions_map[lhs].append(syms if syms else ["ε"])
                elif isinstance(rhs, list):
                    symbols = [s.strip() for s in rhs if isinstance(s, str) and s.strip() != ""]
                    productions_map[lhs].append(symbols if symbols else ["ε"])
                else:
                    raise CFGError(f"Unsupported RHS entry type for '{lhs}': {type(rhs).__name__}")

    elif isinstance(productions, list):
        # a list of {lhs, rhs} dicts or already tokenized dicts
        for entry in productions:
            if not isinstance(entry, dict):
                raise CFGError("Each production entry must be an object/dict with 'lhs' and 'rhs'.")
            lhs = entry.get("lhs")
            rhs = entry.get("rhs")
            if not lhs or not isinstance(lhs, str):
                raise CFGError(f"Invalid or missing LHS in production: {entry!r}")
            lhs = lhs.strip()
            if lhs == "":
                continue
            if not is_variable(lhs):
                raise CFGError(f"Invalid variable format on left-hand side: '{lhs}'. Variables must start with an uppercase letter (e.g., S, NP, Det).")

            if lhs not in productions_map:
                productions_map[lhs] = []

            # rhs can be string like "A B | a b | ε" or a list like ["A", "B"]
            if isinstance(rhs, str):
                rules = _parse_rhs_string(rhs)
                productions_map[lhs].extend(rules)
            elif isinstance(rhs, list):
                # assume token list or list-of-lists
                if len(rhs) > 0 and all(isinstance(x, list) for x in rhs):
                    # list of rules (each a list)
                    for r in rhs:
                        symbols = [s.strip() for s in r if isinstance(s, str) and s.strip() != ""]
                        productions_map[lhs].append(symbols if symbols else ["ε"])
                else:
                    # single rule as list of tokens
                    symbols = [s.strip() for s in rhs if isinstance(s, str) and s.strip() != ""]
                    productions_map[lhs].append(symbols if symbols else ["ε"])
            else:
                raise CFGError(f"Unsupported RHS type for production {lhs!r}: {type(rhs).__name__}")

    else:
        raise CFGError("Unsupported productions type. Provide a dict or a list of production entries.")

    # Remove any blank LHS entries
    productions_map = {k: v for k, v in productions_map.items() if k and v}

    if len(productions_map) == 0:
        raise CFGError("No production rules defined. Add at least one rule.")

    # Collect declared variables (LHS)
    declared_vars: Set[str] = set(productions_map.keys())

    # Validate RHS tokens: variables must be declared (or will be allowed if later introduced?)
    # We'll enforce that any variable used on RHS must exist as LHS in the provided grammar.
    for lhs, rules in productions_map.items():
        for rule in rules:
            for sym in rule:
                if sym == "ε":
                    continue
                # terminals are tokens that are not variables
                if is_variable(sym) and sym not in declared_vars:
                    raise CFGError(f"Undeclared variable '{sym}' used on right-hand side in rule: \"{lhs} -> {' '.join(rule)}\"")

    # At this point we have a raw grammar; next apply "useful" (generative) filtering and reachable filtering
    grammar = productions_map

    # --- Find useful variables (those that can generate terminals) ---
    useful: Set[str] = set()
    changed = True
    while changed:
        changed = False
        for var in list(grammar.keys()):
            if var in useful:
                continue
            for rule in grammar[var]:
                # rule is useful if every symbol is either terminal or already useful
                rule_useful = True
                for sym in rule:
                    if sym == "ε":
                        continue
                    if is_variable(sym) and sym not in useful:
                        rule_useful = False
                        break
                if rule_useful:
                    useful.add(var)
                    changed = True
                    break

    if start_variable not in useful:
        raise CFGError(f"Start symbol '{start_variable}' cannot generate terminal strings (not useful). Check for non-terminating recursion or missing terminal rules.")

    # Filter out rules referencing non-useful variables
    useful_grammar: Dict[str, List[List[str]]] = {}
    for var in useful:
        useful_grammar[var] = []
        for rule in grammar[var]:
            valid_rule = True
            for sym in rule:
                if sym == "ε":
                    continue
                if is_variable(sym) and sym not in useful:
                    valid_rule = False
                    break
            if valid_rule:
                useful_grammar[var].append(rule)

    grammar = useful_grammar

    # --- Find reachable variables from start ---
    reachable: Set[str] = set()
    stack = [start_variable]
    reachable.add(start_variable)
    while stack:
        v = stack.pop()
        for rule in grammar.get(v, []):
            for sym in rule:
                if is_variable(sym) and sym not in reachable and sym in grammar:
                    reachable.add(sym)
                    stack.append(sym)

    if start_variable not in reachable:
        raise CFGError("Start symbol not reachable after filtering. No derivation possible.")

    # Filter grammar to reachable variables only
    final_grammar: Dict[str, List[List[str]]] = {}
    for var in reachable:
        # keep the rules we already filtered in useful stage
        final_grammar[var] = grammar.get(var, [])

    # Double-check final grammar non-empty and start exists
    if start_variable not in final_grammar:
        raise CFGError("After filtering, start variable is missing from grammar.")

    # Return final cleaned CFG
    return final_grammar


# Quick manual test (only runs if executed directly)
if __name__ == "__main__":
    # simple example (like your frontend example)
    example = [
        {"lhs": "S", "rhs": "NP VP"},
        {"lhs": "NP", "rhs": "Det Adj N | Det N | N"},
        {"lhs": "VP", "rhs": "V NP | V"},
        {"lhs": "Det", "rhs": "the | a"},
        {"lhs": "Adj", "rhs": "big | small | old"},
        {"lhs": "N", "rhs": "cat | cats | dog | dogs | man | men"},
        {"lhs": "V", "rhs": "runs | run | eats | eat | chased"},
    ]
    try:
        g = parse_cfg("S", example)
        import json
        print(json.dumps(g, indent=2))
    except Exception as e:
        print("ERROR:", e)
