from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from logic.cfg_parser import parse_cfg
from logic.cnf_converter import convert_to_cnf
from logic.generator import generate_strings
from logic.cyk import run_cyk, reconstruct_tree
from logic.tree_builder import flatten_tree

app = Flask(__name__)
CORS(app)

# Global stored grammar state
GLOBAL_ORIGINAL_CFG = None
GLOBAL_CNF = None
GLOBAL_START = None
GLOBAL_TERM_MAP = None
GLOBAL_NONTERM_MAP = None


# =====================================================================
#  HOME PAGE
# =====================================================================
@app.route("/")
def index():
    return render_template("index.html")


# =====================================================================
#  1. SET GRAMMAR
# =====================================================================
@app.route("/set_grammar", methods=["POST"])
def set_grammar():
    global GLOBAL_ORIGINAL_CFG, GLOBAL_CNF, GLOBAL_START, GLOBAL_TERM_MAP, GLOBAL_NONTERM_MAP

    data = request.json
    start_var = data.get("start", "").strip()
    productions = data.get("productions", [])

    try:
        # 1. Parse raw CFG
        original_cfg = parse_cfg(start_var, productions)

        # 2. Convert to CNF
        cnf_result = convert_to_cnf(original_cfg, start_var)

        GLOBAL_ORIGINAL_CFG = original_cfg
        GLOBAL_CNF = cnf_result["grammar"]
        GLOBAL_START = cnf_result["start"]
        GLOBAL_TERM_MAP = cnf_result["term_map"]
        GLOBAL_NONTERM_MAP = cnf_result["nonterm_map"]

        return jsonify({
            "success": True,
            "message": "Grammar successfully parsed and converted to CNF.",
            "cnf": GLOBAL_CNF
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Grammar Error: {str(e)}"
        })


# =====================================================================
#  2. GENERATE STRINGS
# =====================================================================
@app.route("/generate", methods=["POST"])
def generate():
    if GLOBAL_ORIGINAL_CFG is None:
        return jsonify({"success": False, "message": "Grammar is not set."})

    try:
        generated = list(generate_strings(GLOBAL_ORIGINAL_CFG, GLOBAL_START, max_strings=10))
        return jsonify({"success": True, "generated": generated})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


# =====================================================================
#  3. CYK VALIDATION
# =====================================================================
@app.route("/validate", methods=["POST"])
def validate():
    if GLOBAL_CNF is None:
        return jsonify({
            "success": False,
            "message": "Please set a grammar first."
        })

    data = request.json
    input_str = data.get("string", "").strip()
    tokens = [t for t in input_str.split() if t]

    # Empty input case – handled by checking epsilon rule in original CFG
    if len(tokens) == 0:
        epsilon_allowed = False

        if GLOBAL_ORIGINAL_CFG.get(GLOBAL_START):
            for rule in GLOBAL_ORIGINAL_CFG[GLOBAL_START]:
                if rule == ["ε"]:
                    epsilon_allowed = True

        if epsilon_allowed:
            return jsonify({
                "success": True,
                "valid": True,
                "message": "ε (empty string) is derivable.",
                "tree": {"name": "\"ε\""}
            })
        else:
            return jsonify({
                "success": True,
                "valid": False,
                "message": "Empty string is NOT derivable."
            })

    try:
        # Run CYK
        result = run_cyk(GLOBAL_CNF, GLOBAL_START, tokens)
        table = result["table"]
        accepted = result["success"]

        if not accepted:
            return jsonify({
                "success": True,
                "valid": False,
                "message": "String is NOT derivable."
            })

        # Build parse tree
        tree = reconstruct_tree(
            table,
            0,
            len(tokens) - 1,
            GLOBAL_START,
            GLOBAL_NONTERM_MAP
        )

        # Flatten for D3
        tree = flatten_tree(tree)

        return jsonify({
            "success": True,
            "valid": True,
            "message": "String is derivable.",
            "tree": tree
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Validation Error: {str(e)}"
        })


# =====================================================================
#  HEALTH CHECK
# =====================================================================
@app.route("/ping")
def ping():
    return jsonify({"status": "OK", "message": "Server running"})


# =====================================================================
#  RUN
# =====================================================================
if __name__ == "__main__":
    app.run(debug=True)
