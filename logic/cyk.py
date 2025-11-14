"""
CYK Algorithm Implementation
----------------------------
Matches the frontend CYK logic exactly:
- table[i][j] contains a list of entries.
- each entry is either:
    [Variable, Terminal]  for length-1 matches
    [Variable, split_k, left_entry, right_entry]  for combined matches

This preserves enough structure for reconstructing a full parse tree.
"""

from typing import Dict, List, Any


def is_variable(sym: str) -> bool:
    return sym and sym[0].isupper()


def run_cyk(cnf_grammar: Dict[str, List[List[str]]], start_var: str, tokens: List[str]):
    """
    Execute the CYK algorithm on a CNF grammar.

    Parameters
    ----------
    cnf_grammar: dict
        Example:
          { "S": [["NP","VP"], ...], "NP": [["X1","N"], ...], "X1": [["dog"]] }
    start_var: str
        Start variable after CNF conversion
    tokens: list[str]
        Tokenized input string

    Returns
    -------
    {
        "table": CYK_table,
        "success": bool
    }
    """

    n = len(tokens)
    if n == 0:
        # Handled by app logic (checking S → ε)
        return {"table": [], "success": False}

    # table[i][j] = list of parse entries
    # i = start index, j = end index
    table = [[[] for _ in range(n)] for _ in range(n)]

    # -------------------------------------------------------
    # Step 1: Initialize diagonal table cells with terminals
    # -------------------------------------------------------
    for i, tok in enumerate(tokens):
        for A, rules in cnf_grammar.items():
            for rule in rules:
                # rule must be A -> a
                if len(rule) == 1 and rule[0] == tok:
                    # store [A, tok]
                    table[i][i].append([A, tok])

    # -------------------------------------------------------
    # Step 2: CYK combination for substrings of length >= 2
    # -------------------------------------------------------
    for length in range(2, n + 1):            # substring length
        for i in range(0, n - length + 1):    # start
            j = i + length - 1                # end

            # split position k : (i..k) + (k+1..j)
            for k in range(i, j):

                left_cell = table[i][k]
                right_cell = table[k + 1][j]

                if not left_cell or not right_cell:
                    continue

                # Try all A → B C rules
                for A, rules in cnf_grammar.items():
                    for rule in rules:
                        if len(rule) != 2:
                            continue
                        B, C = rule

                        # find B in left cell
                        b_matches = [entry for entry in left_cell if entry[0] == B]
                        if not b_matches:
                            continue
                        # find C in right cell
                        c_matches = [entry for entry in right_cell if entry[0] == C]
                        if not c_matches:
                            continue

                        # For CYK we only need 1 combination per variable
                        # but store full pointers for tree reconstruction
                        existing = any(entry[0] == A for entry in table[i][j])
                        if not existing:
                            table[i][j].append(
                                [A, k, b_matches[0], c_matches[0]]
                            )

    # -------------------------------------------------------
    # Step 3: Accept if start_var is in table[0][n-1]
    # -------------------------------------------------------
    success = any(entry[0] == start_var for entry in table[0][n - 1])

    return {
        "table": table,
        "success": success
    }


def reconstruct_tree(table: List[List[List[Any]]], i: int, j: int, variable: str,
                     nonterm_map: Dict[str, str]):
    """
    Reconstruct a parse tree using the backpointer table.

    Mirrors the JS logic exactly.

    nonterm_map: dict
        Example {"X1": "dog"} meaning X1 → dog terminal wrapper
    """

    # entries whose variable matches
    candidates = [entry for entry in table[i][j] if entry[0] == variable]
    if not candidates:
        return {"name": f"ERROR:{variable}"}

    entry = candidates[0]

    # -------------------------------------------------------
    # Case 1: Terminal rule => [A, terminal]
    # -------------------------------------------------------
    if len(entry) == 2:
        A, terminal = entry
        # If A is a terminal-wrapper (e.g., X1 → dog)
        if A in nonterm_map:
            return {"name": f"\"{nonterm_map[A]}\""}

        # Normal terminal rule
        return {"name": A, "children": [{"name": f"\"{terminal}\""}]}

    # -------------------------------------------------------
    # Case 2: Binary rule => [A, k, leftEntry, rightEntry]
    # -------------------------------------------------------
    A, k, left_ent, right_ent = entry
    B = left_ent[0]
    C = right_ent[0]

    left_child = reconstruct_tree(table, i, k, B, nonterm_map)
    right_child = reconstruct_tree(table, k + 1, j, C, nonterm_map)

    # Flatten intermediate binarization variables (X_i)
    children = []

    def append_child(child):
        if child["name"].startswith("X") and child["name"] not in nonterm_map:
            # intermediate CNF binarization variable → flatten
            if "children" in child:
                for cc in child["children"]:
                    children.append(cc)
        else:
            children.append(child)

    append_child(left_child)
    append_child(right_child)

    return {"name": A, "children": children}


# -----------------------------------------------------------
# Manual test
# -----------------------------------------------------------
if __name__ == "__main__":
    # Example tiny grammar
    G = {
        "S": [["A", "B"]],
        "A": [["a"]],
        "B": [["b"]]
    }
    tokens = ["a", "b"]
    result = run_cyk(G, "S", tokens)
    print(result["success"])
    print(result["table"])
