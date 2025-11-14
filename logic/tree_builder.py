# logic/tree_builder.py
"""
Utility functions to clean, simplify, and convert a CYK reconstructed parse tree
into a D3-compatible JSON format.
"""


# -------------------------------------------------------
# 1. Simplify CNF helper variables (X1, X2…)
# -------------------------------------------------------

def simplify_node(node):
    """
    Remove CNF intermediate variables (X_1, X_2…) from the tree
    and simplify their children.
    """
    if not isinstance(node, dict):
        return node

    name = node.get("name", "")
    children = node.get("children", [])

    # If intermediate CNF variable → flatten it
    if name.startswith("X") and any(c.isdigit() for c in name[1:]):
        if children:
            # If only one child → return child directly
            if len(children) == 1:
                return simplify_node(children[0])

            # Otherwise simplify each child
            return [simplify_node(c) for c in children]

    # Normal case: recursively simplify children
    new_children = []
    for child in children:
        new_children.append(simplify_node(child))

    return {
        "name": name,
        "children": new_children
    }


# -------------------------------------------------------
# 2. Convert into clean D3 hierarchical format
# -------------------------------------------------------

def flatten_tree(node):
    """
    Convert simplified tree into the clean D3 hierarchical structure.

    Output format:
    {
        "name": "S",
        "children": [ ... ]
    }
    """
    if node is None:
        return {"name": "?"}

    # Terminal node (string)
    if isinstance(node, str):
        return {"name": node}

    name = node.get("name", "")

    children = node.get("children", [])
    if children:
        return {
            "name": name,
            "children": [flatten_tree(child) for child in children]
        }

    return {"name": name}


# -------------------------------------------------------
# 3. Main public function
# -------------------------------------------------------

def build_tree_for_d3(tree):
    """
    Fully prepare any raw CYK parse tree for D3 visualization:
        raw CYK tree → simplified → flattened → D3 JSON tree
    """
    simplified = simplify_node(tree)
    flattened = flatten_tree(simplified)
    return flattened


__all__ = ["simplify_node", "flatten_tree", "build_tree_for_d3"]
