"""
CNF Converter
-------------
Converts a cleaned CFG (from cfg_parser.py) into Chomsky Normal Form (CNF).

This module mirrors the exact behavior of the frontend JS CNF converter:
- Eliminates epsilon productions
- Eliminates unit productions
- Binarizes long RHS rules
- Lifts terminals (A -> a becomes A -> X_a ; X_a -> a)
- Introduces fresh variables (X1, X2, X3, ...)
- Introduces new start symbol S' if original start is nullable
"""

import itertools
from typing import Dict, List, Tuple


def is_variable(sym: str) -> bool:
    return sym and sym[0].isupper()


class CNFError(Exception):
    pass


def convert_to_cnf(grammar: Dict[str, List[List[str]]], start_var: str):
    """
    Perform full CNF conversion.

    Parameters
    ----------
    grammar : dict
        Example: { "S": [["NP", "VP"], ["ε"]], "NP": [["Det","N"], ...] }
    start_var : str
        Start variable of original grammar

    Returns
    -------
    {
        "grammar": <cnf dict>,
        "start_var": <new start variable>,
        "term_map": { "dog": "X1", "runs": "X2", ... },
        "nonterm_map": { "X1": "dog", "X2": "runs", ... }
    }
    """

    # Work on a deep copy
    import copy
    grammar = copy.deepcopy(grammar)

    # ---------------------------------------------------------
    # Step 1: Collect all existing variable names
    # ---------------------------------------------------------
    all_vars = set(grammar.keys())

    # ---------------------------------------------------------
    # Fresh variable generator (X1, X2, X3, ...)
    # Ensures names never collide with grammar variables
    # ---------------------------------------------------------
    counter = itertools.count(1)

    def fresh_var():
        while True:
            v = f"X{next(counter)}"
            if v not in all_vars:
                all_vars.add(v)
                return v

    # ---------------------------------------------------------
    # Collect nullable variables (epsilon-producers)
    # ---------------------------------------------------------
    nullable = set()

    changed = True
    while changed:
        changed = False
        for A, rules in grammar.items():
            if A in nullable:
                continue
            for rule in rules:
                # If rule is epsilon
                if rule == ["ε"]:
                    nullable.add(A)
                    changed = True
                    break
                # If all symbols are nullable variables
                if all((sym in nullable) for sym in rule if is_variable(sym)):
                    nullable.add(A)
                    changed = True
                    break

    # ---------------------------------------------------------
    # Step 2: Remove epsilon rules (except possibly S → ε)
    # Generate all nullable subsets
    # ---------------------------------------------------------
    new_grammar = {A: [] for A in grammar}

    for A, rules in grammar.items():
        for rule in rules:

            # skip raw ε productions (handled later)
            if rule == ["ε"]:
                continue

            # Generate subsets of rule by removing nullable variables
            subsets = [[]]

            for sym in rule:
                new_sub = []
                for s in subsets:
                    # Keep symbol
                    new_s = s + [sym]
                    new_sub.append(new_s)

                    # Drop symbol if nullable
                    if is_variable(sym) and sym in nullable:
                        new_sub.append(s)
                subsets = new_sub

            # We add every subset except the empty one (unless A is the start)
            for s in subsets:
                if len(s) == 0:
                    continue
                if s not in new_grammar[A]:
                    new_grammar[A].append(s)

    grammar = new_grammar

    # ---------------------------------------------------------
    # Introduce new start variable S' if original is nullable
    # ---------------------------------------------------------
    current_start = start_var
    if start_var in nullable:
        S_new = f"{start_var}'"
        while S_new in grammar:
            S_new += "'"
        grammar[S_new] = [[start_var], ["ε"]]
        current_start = S_new
        all_vars.add(S_new)

    # ---------------------------------------------------------
    # Step 3: Eliminate unit productions A → B
    # ---------------------------------------------------------
    def is_unit(rule):
        return len(rule) == 1 and is_variable(rule[0])

    changed = True
    while changed:
        changed = False
        new_prod = {A: list(rules) for A, rules in grammar.items()}
        for A, rules in grammar.items():
            for rule in rules:
                if is_unit(rule):
                    B = rule[0]
                    if B == A:
                        continue  # skip A → A

                    # Bring all non-unit rules of B into A
                    for rB in grammar.get(B, []):
                        if not is_unit(rB) or (len(rB) == 1 and not is_variable(rB[0])):
                            if rB not in new_prod[A]:
                                new_prod[A].append(rB)
                                changed = True

                    # Remove A → B
                    if rule in new_prod[A]:
                        new_prod[A].remove(rule)
                        changed = True

        grammar = new_prod

    # ---------------------------------------------------------
    # Step 4: Terminal lifting (A → a becomes A → X_a, X_a → a)
    # ---------------------------------------------------------
    term_map = {}      # "dog" → "X1"
    nonterm_map = {}   # "X1" → "dog"

    def get_term_var(t):
        if t not in term_map:
            v = fresh_var()
            term_map[t] = v
            nonterm_map[v] = t
        return term_map[t]

    # ---------------------------------------------------------
    # Step 5: Binarization
    # ---------------------------------------------------------
    final = {}

    for A, rules in grammar.items():
        final[A] = []
        for rule in rules:

            # Rule length 1 (terminal)
            if len(rule) == 1 and not is_variable(rule[0]):
                t = rule[0]
                final[A].append([t])
                continue

            # Rule length 2
            if len(rule) == 2:
                s1, s2 = rule

                if not is_variable(s1):
                    s1 = get_term_var(s1)
                if not is_variable(s2):
                    s2 = get_term_var(s2)

                final[A].append([s1, s2])
                continue

            # Rule length >= 3 → binarize
            current = A
            chain = rule[:]

            # Process the first n-2 symbols
            while len(chain) > 2:
                s = chain.pop(0)

                if not is_variable(s):
                    s = get_term_var(s)

                new_var = fresh_var()
                final.setdefault(current, []).append([s, new_var])
                final.setdefault(new_var, [])
                current = new_var

            # Now chain has exactly 2 symbols left
            left, right = chain

            if not is_variable(left):
                left = get_term_var(left)
            if not is_variable(right):
                right = get_term_var(right)

            final[current].append([left, right])

    # ---------------------------------------------------------
    # Step 6: Add X_a → a rules to final grammar
    # ---------------------------------------------------------
    for v, t in nonterm_map.items():
        if v not in final:
            final[v] = []
        final[v].append([t])

    # Remove any empty rule lists
    final = {A: rules for A, rules in final.items() if len(rules) > 0}

    return {
        "grammar": final,
        "start_var": current_start,
        "term_map": term_map,
        "nonterm_map": nonterm_map
    }


# -------------------------------------------------------------
# Manual test
# -------------------------------------------------------------
if __name__ == "__main__":
    # Example grammar:
    G = {
        "S": [["NP", "VP"]],
        "NP": [["Det", "N"], ["N"]],
        "Det": [["the"], ["a"]],
        "N": [["dog"], ["man"]],
        "VP": [["V", "NP"]],
        "V": [["eats"]],
    }

    result = convert_to_cnf(G, "S")

    import json
    print(json.dumps(result, indent=2))
