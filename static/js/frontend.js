// frontend.js
// Full frontend logic for CFG Analysis Toolkit (generator + CYK + CNF conversion + D3 tree)
// Drop into your project and include with: <script src="frontend.js"></script>

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const mainGrid = document.getElementById('main-grid'); // Get the main grid
    const startVariableInput = document.getElementById('start-variable-input');
    const productionsList = document.getElementById('productions-list');
    const addProductionBtn = document.getElementById('add-production-btn');
    const autofillBtn = document.getElementById('autofill-btn');
    const productionRowTemplate = document.getElementById('production-row-template');

    const setGrammarBtn = document.getElementById('set-grammar-btn');
    const grammarMessage = document.getElementById('grammar-message');

    const actionsSection = document.getElementById('actions-section');
    const cnfOutput = document.getElementById('cnf-output');

    const generateBtn = document.getElementById('generate-btn');
    const generatorOutput = document.getElementById('generator-output');

    const validateInput = document.getElementById('validate-input');
    const validateBtn = document.getElementById('validate-btn');
    const validatorOutput = document.getElementById('validator-output');

    // Modal & tree
    const treeModal = document.getElementById('tree-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalSvgContainer = document.getElementById('modal-svg-container');
    const saveTreeBtn = document.getElementById('save-tree-btn');

    // --- Global State ---
    let originalCFG = null;
    let cnfGrammar = null;
    let cnfTerminals = null; // term -> var
    let cnfNonTerminals = null; // var -> term
    let startVariable = null;
    let lastValidTree = null; // Store last parsed tree for modal

    // --- Event Listeners ---
    setGrammarBtn.addEventListener('click', handleSetGrammar);
    generateBtn.addEventListener('click', handleGenerate);
    validateBtn.addEventListener('click', handleValidate);
    addProductionBtn.addEventListener('click', addNewProductionRow);
    autofillBtn.addEventListener('click', handleAutofill);

    // --- Production Row Management ---
    function addNewProductionRow() {
        const rowClone = productionRowTemplate.content.cloneNode(true);
        const row = rowClone.querySelector('.production-row');
        const lhsInput = row.querySelector('.lhs-input');
        const rhsInput = row.querySelector('.rhs-input');

        // Add delete functionality
        row.querySelector('.delete-row-btn').addEventListener('click', () => {
            row.remove();
        });

        // Enter on LHS jumps to RHS
        lhsInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                rhsInput.focus();
            }
        });

        // Enter on RHS adds a new row
        rhsInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addNewProductionRow();
            }
        });

        productionsList.appendChild(rowClone);
        lhsInput.focus();
    }

    // Initialise UI with one row
    addNewProductionRow();
    startVariableInput.value = "S";
    const firstLhs = productionsList.querySelector('.lhs-input');
    if (firstLhs) firstLhs.value = "S";

    // --- Autofill Example ---
    function handleAutofill(e) {
        e && e.preventDefault();
        const exampleGrammar = [
            { lhs: 'S', rhs: 'NP VP' },
            { lhs: 'NP', rhs: 'Det Adj N | Det N | N' },
            { lhs: 'VP', rhs: 'V NP | V' },
            { lhs: 'Det', rhs: 'the | a' },
            { lhs: 'Adj', rhs: 'big | small | old' },
            { lhs: 'N', rhs: 'cat | cats | dog | dogs | man | men' },
            { lhs: 'V', rhs: 'runs | run | eats | eat | chased' }
        ];

        productionsList.innerHTML = '';
        startVariableInput.value = 'S';

        for (const rule of exampleGrammar) {
            addNewProductionRow();
            const newRow = productionsList.lastElementChild;
            if (newRow) {
                newRow.querySelector('.lhs-input').value = rule.lhs;
                newRow.querySelector('.rhs-input').value = rule.rhs;
            }
        }

        clearMessage(grammarMessage);
        actionsSection.classList.add('hidden');
    }

    // --- Message Helpers ---
    function showMessage(element, message, isError = true) {
        element.textContent = message;
        if (isError) {
            element.className = 'mt-4 text-sm rounded-xl p-3 bg-red-100 text-red-700 border border-red-300';
        } else {
            element.className = 'mt-4 text-sm rounded-xl p-3 bg-green-100 text-green-700 border border-green-300';
        }
    }

    function clearMessage(element) {
        element.textContent = '';
        element.className = 'mt-4 text-sm rounded-xl p-3';
    }

    // Generator output helper
    function showGeneratorOutput(title, contentList) {
        let content = contentList.map(s => `"${s}"`).join('\n');
        generatorOutput.innerHTML = `
            <div class="rounded-xl p-4 bg-gray-100 border border-green-300">
                <h4 class="font-bold text-green-600 mb-2">${title}</h4>
                <pre class="text-sm text-gray-700 font-mono whitespace-pre-wrap overflow-x-auto">${content}</pre>
            </div>
        `;
    }

    // Validator output helper
    function showValidatorOutput(title, message, derivationData = null, isError = false) {
        const titleColor = isError ? 'text-red-600' : 'text-green-600';
        const borderColor = isError ? 'border-red-300' : 'border-green-300';

        let derivationHTML = '';
        if (derivationData) {
            derivationHTML = `
                <div class="flex items-center gap-4 mt-2">
                    <a href="#" id="derivation-link" class="text-sm text-blue-600 hover:text-blue-500 hover:underline">See Parse Tree</a>
                    <button id="enlarge-tree-btn" class="hidden text-sm text-gray-600 hover:text-black transition-colors py-1 px-3 rounded-lg bg-gray-200/50 border border-gray-300">Enlarge View</button>
                    <button id="save-inline-tree-btn" class="hidden text-sm text-gray-600 hover:text-black transition-colors py-1 px-3 rounded-lg bg-gray-200/50 border border-gray-300">Save as PNG</button>
                </div>
                <div id="derivation-content" class="hidden mt-3 bg-white rounded-xl p-4 border border-gray-200" style="min-height: 200px; max-height: 400px; overflow: auto; resize: vertical;">
                    <div id="derivation-svg-container" class="w-full"></div>
                </div>
            `;
        }

        validatorOutput.innerHTML = `
            <div class="rounded-xl p-4 bg-gray-100 border ${borderColor}">
                <h4 class="font-bold ${titleColor} mb-1">${title}</h4>
                <p class="text-gray-700">${message}</p>
                ${derivationHTML}
            </div>
        `;

        if (derivationData) {
            const link = document.getElementById('derivation-link');
            const enlargeBtn = document.getElementById('enlarge-tree-btn');
            const saveInlineBtn = document.getElementById('save-inline-tree-btn');
            const content = document.getElementById('derivation-content');

            link.addEventListener('click', (e) => {
                e.preventDefault();
                content.classList.toggle('hidden');
                enlargeBtn.classList.toggle('hidden');
                saveInlineBtn.classList.toggle('hidden');
                link.textContent = content.classList.contains('hidden') ? 'See Parse Tree' : 'Hide Parse Tree';

                if (!content.classList.contains('hidden') && !content.dataset.drawn) {
                    drawTree(derivationData, '#derivation-svg-container');
                    content.dataset.drawn = "true";
                }
            });

            enlargeBtn.addEventListener('click', openTreeModal);
            saveInlineBtn.addEventListener('click', () => saveTreeAsPNG('#derivation-svg-container'));
        }
    }

    // --- Grammar Parsing & Validation (Step 2) ---
    function handleSetGrammar() {
        clearMessage(grammarMessage);
        actionsSection.classList.add('hidden');

        // Keep layout single-column centered
        mainGrid.classList.remove('lg:grid-cols-2');
        mainGrid.classList.add('justify-items-center');

        cnfOutput.innerHTML = '<pre class="text-sm text-gray-700 font-mono">Awaiting valid grammar input...</pre>';
        originalCFG = null;
        cnfGrammar = null;
        startVariable = null;
        cnfTerminals = null;
        cnfNonTerminals = null;

        try {
            const startVar = startVariableInput.value.trim();
            if (!startVar) throw new Error("Please enter a Start Variable.");

            const variables = new Set();
            const productions = {};
            const productionRows = productionsList.querySelectorAll('.production-row');

            if (productionRows.length === 0) throw new Error("Please add at least one production rule.");

            // Discover LHS variables
            for (const row of productionRows) {
                const lhs = row.querySelector('.lhs-input').value.trim();
                if (lhs === "") continue;
                if (!isVariable(lhs)) throw new Error(`Invalid variable format on left-hand side: '${lhs}'. Variables must start with an uppercase letter (e.g., S, NP, Det).`);
                if (!variables.has(lhs)) {
                    variables.add(lhs);
                    productions[lhs] = [];
                }
            }

            if (variables.size === 0) throw new Error("No production rules defined.");
            if (!variables.has(startVar)) throw new Error(`Start variable '${startVar}' is not defined in any production rule's left-hand side.`);

            startVariable = startVar;

            // Parse RHS rules
            for (const row of productionRows) {
                const lhs = row.querySelector('.lhs-input').value.trim();
                if (lhs === "") continue;

                const rhsString = row.querySelector('.rhs-input').value.trim();

                if (rhsString === "") {
                    productions[lhs].push(['ε']);
                    continue;
                }

                const rhsRules = rhsString.split('|').map(r => r.trim());

                for (const rule of rhsRules) {
                    const symbols = rule.split(' ').map(s => s.trim()).filter(s => s);
                    if (symbols.length === 0) {
                        productions[lhs].push(['ε']);
                        continue;
                    }

                    for (const symbol of symbols) {
                        if (symbol === 'ε') continue;
                        if (isVariable(symbol) && !variables.has(symbol)) {
                            throw new Error(`Undeclared variable '${symbol}' used on right-hand side in rule: "${lhs} -> ${rule}"`);
                        }
                    }
                    productions[lhs].push(symbols);
                }
            }

            originalCFG = productions;

            // --- Clean Grammar (useful & reachable) ---
            let grammar = productions;
            let currentVariables = variables;

            // Useful (generative)
            const useful = new Set();
            let grammarChanged = true;
            while (grammarChanged) {
                grammarChanged = false;
                for (const variable of currentVariables) {
                    if (useful.has(variable)) continue;
                    for (const rule of grammar[variable]) {
                        const ruleIsUseful = rule.every(sym => !isVariable(sym) || useful.has(sym));
                        if (ruleIsUseful) {
                            useful.add(variable);
                            grammarChanged = true;
                            break;
                        }
                    }
                }
            }

            if (!useful.has(startVar)) {
                throw new Error(`Start symbol '${startVar}' cannot generate any terminal strings (is not useful). Check for non-terminating recursion.`);
            }

            const usefulGrammar = {};
            const usefulVariables = new Set();
            for (const variable of useful) {
                usefulGrammar[variable] = [];
                usefulVariables.add(variable);
                for (const rule of grammar[variable]) {
                    if (rule.every(sym => !isVariable(sym) || useful.has(sym))) {
                        usefulGrammar[variable].push(rule);
                    }
                }
            }
            grammar = usefulGrammar;
            currentVariables = usefulVariables;

            // Reachable
            const reachable = new Set([startVar]);
            const worklist = [startVar];
            while (worklist.length > 0) {
                const V = worklist.pop();
                if (!grammar[V]) continue;
                for (const rule of grammar[V]) {
                    for (const symbol of rule) {
                        if (isVariable(symbol) && currentVariables.has(symbol) && !reachable.has(symbol)) {
                            reachable.add(symbol);
                            worklist.push(symbol);
                        }
                    }
                }
            }

            const finalGrammar = {};
            if (currentVariables.size !== reachable.size) {
                const unreachable = [...currentVariables].filter(v => !reachable.has(v));
                console.warn("Unreachable variables found and removed:", unreachable);
            }
            for (const variable of reachable) {
                finalGrammar[variable] = grammar[variable];
            }

            originalCFG = finalGrammar;

            // --- CNF Conversion (background) ---
            const cnfResult = convertToCNF(JSON.parse(JSON.stringify(originalCFG)), startVariable);
            cnfGrammar = cnfResult.grammar;
            cnfTerminals = cnfResult.termMap;
            cnfNonTerminals = cnfResult.nonTermMap;
            startVariable = cnfResult.startVar;

            // Display CNF internally (we keep it hidden from UI but for debug we set it)
            displayCNF(cnfGrammar);

            showMessage(grammarMessage, "Grammar successfully parsed, cleaned and converted to CNF. Analysis tools enabled.", false);
            actionsSection.classList.remove('hidden');

        } catch (error) {
            showMessage(grammarMessage, `Grammar Error: ${error.message}`, true);
            console.error(error);
        }
    }

    function isVariable(s) {
        return /^[A-Z][A-Za-z0-9_]*'?$/.test(s);
    }

    function displayCNF(grammar) {
        let cnfString = `Start Variable: ${startVariable}\n\n`;
        cnfString += "--- Non-Terminal Rules (A → B C) ---\n";
        for (const variable in grammar) {
            for (const rule of grammar[variable]) {
                if (rule.length === 2 && isVariable(rule[0]) && isVariable(rule[1])) {
                    cnfString += `${variable} → ${rule[0]} ${rule[1]}\n`;
                }
            }
        }
        cnfString += "\n--- Terminal Rules (A → a) ---\n";
        for (const variable in grammar) {
            for (const rule of grammar[variable]) {
                if (rule.length === 1 && !isVariable(rule[0])) {
                    cnfString += `${variable} → ${rule[0] === 'ε' ? 'ε (Lambda)' : rule[0]}\n`;
                }
            }
        }
        // Keep hidden in UI; but place in element for possible debug (element is hidden by CSS)
        cnfOutput.innerHTML = `<pre class="text-sm text-gray-700 font-mono">${cnfString}</pre>`;
    }

    // --- CNF Conversion Logic (mirrors detailed JS converter) ---
    function convertToCNF(grammar, startVar) {
        let newVarCounter = 1;
        const termMap = {}; // 'a' -> 'X_a'
        const nonTermMap = {}; // 'X_a' -> 'a'
        let currentStartVar = startVar;

        function getNewVar() {
            let newVar = `X${newVarCounter++}`;
            while (grammar.hasOwnProperty(newVar)) {
                newVar = `X${newVarCounter++}`;
            }
            return newVar;
        }

        function getTermVar(term) {
            if (!termMap[term]) {
                const newVar = getNewVar();
                termMap[term] = newVar;
                nonTermMap[newVar] = term;
            }
            return termMap[term];
        }

        // Step 1: Find nullable variables
        let nullable = new Set();
        let changed = true;
        while (changed) {
            changed = false;
            for (const variable in grammar) {
                if (nullable.has(variable)) continue;
                for (const rule of grammar[variable]) {
                    if (rule.length === 1 && rule[0] === 'ε') {
                        nullable.add(variable);
                        changed = true;
                        break;
                    } else if (rule.length > 0 && rule.every(sym => nullable.has(sym))) {
                        nullable.add(variable);
                        changed = true;
                        break;
                    }
                }
            }
        }

        // Step 2: Remove epsilon rules via subsets
        let newGrammar = {};
        for (const variable in grammar) {
            newGrammar[variable] = [];
            for (const rule of grammar[variable]) {
                if (rule.length === 1 && rule[0] === 'ε') continue;

                let subsets = [[]];
                for (const symbol of rule) {
                    let newSubsets = [];
                    for (const subset of subsets) {
                        newSubsets.push([...subset, symbol]);
                        if (nullable.has(symbol)) {
                            newSubsets.push([...subset]);
                        }
                    }
                    subsets = newSubsets;
                }

                for (const newRule of subsets) {
                    if (newRule.length > 0) {
                        if (!newGrammar[variable].some(r => r.join(' ') === newRule.join(' '))) {
                            newGrammar[variable].push(newRule);
                        }
                    }
                }
            }
        }
        grammar = newGrammar;

        if (nullable.has(startVar)) {
            const newStartVar = `${startVar}'`;
            grammar[newStartVar] = grammar[startVar] ? [[startVar], ['ε']] : [['ε']];
            currentStartVar = newStartVar;
        }

        // Step 3: Eliminate unit productions
        let loop = true;
        while (loop) {
            loop = false;
            let copyG = JSON.parse(JSON.stringify(grammar));
            for (const variable in grammar) {
                let rulesToAdd = [];
                let rulesToRemove = [];
                for (const rule of grammar[variable]) {
                    if (rule.length === 1 && isVariable(rule[0])) {
                        rulesToRemove.push(rule);
                        if (variable !== rule[0]) {
                            if (grammar[rule[0]]) {
                                for (const newRule of grammar[rule[0]]) {
                                    if (newRule.length > 1 || !isVariable(newRule[0])) {
                                        if (!copyG[variable].some(r => r.join(' ') === newRule.join(' '))) {
                                            rulesToAdd.push(newRule);
                                            loop = true;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                copyG[variable] = copyG[variable].filter(rule => !rulesToRemove.some(r => r.join(' ') === rule.join(' '))).concat(rulesToAdd);

                // dedupe
                const uniqueRules = new Set(copyG[variable].map(r => r.join(' ')));
                copyG[variable] = Array.from(uniqueRules).map(s => s.split(' '));
            }
            grammar = copyG;
        }

        // Step 4: Binarize & create terminal wrappers
        newGrammar = {};
        for (const variable in grammar) newGrammar[variable] = [];

        for (const variable in grammar) {
            for (const rule of grammar[variable]) {
                if (rule.length === 1) {
                    newGrammar[variable].push(rule);
                } else if (rule.length === 2) {
                    const sym1 = isVariable(rule[0]) ? rule[0] : getTermVar(rule[0]);
                    const sym2 = isVariable(rule[1]) ? rule[1] : getTermVar(rule[1]);
                    newGrammar[variable].push([sym1, sym2]);
                } else {
                    let currentVar = variable;
                    const chain = [...rule];
                    while (chain.length > 2) {
                        const s = chain.shift();
                        const sym = isVariable(s) ? s : getTermVar(s);
                        const newVar = getNewVar();
                        newGrammar[currentVar].push([sym, newVar]);
                        if (!newGrammar[newVar]) newGrammar[newVar] = [];
                        currentVar = newVar;
                    }
                    const left = isVariable(chain[0]) ? chain[0] : getTermVar(chain[0]);
                    const right = isVariable(chain[1]) ? chain[1] : getTermVar(chain[1]);
                    newGrammar[currentVar].push([left, right]);
                }
            }
        }

        // Add terminal wrapper rules
        for (const newVar in nonTermMapFrom(termMapTo(nonTerm = null, termMap))) {
            // placeholder - real nonTermMap is constructed below; we'll add terminal rules after building nonTermMap
        }

        // Build nonTermMap correctly from termMap
        const nonterm_map = {};
        for (const t in termMap) {
            nonterm_map[termMap[t]] = t;
        }

        // Attach terminal rules
        for (const v in nonterm_map) {
            newGrammar[v] = newGrammar[v] || [];
            newGrammar[v].push([nonterm_map[v]]);
        }

        // Cleanup: remove empty sets and unit-only leftover
        for (const variable in newGrammar) {
            newGrammar[variable] = newGrammar[variable].filter(rule => {
                if (rule.length === 1 && isVariable(rule[0])) return false;
                return true;
            });
            if (newGrammar[variable].length === 0) delete newGrammar[variable];
        }

        // Return consistent mapping
        return { grammar: newGrammar, termMap: termMap, nonTermMap: nonterm_map, startVar: currentStartVar };

        // helper shims (kept local to avoid polluting global scope)
        function termMapTo(nonTerm, termMapInner) { return termMapInner; }
        function nonTermMapFrom(x) { return {}; }
    }

    // --- Generator Logic ---
    function handleGenerate() {
        if (!originalCFG || !startVariable) {
            showGeneratorOutput("Error", ["Please set a valid grammar first."]);
            return;
        }

        const generatedStrings = new Set();
        const originalStartVar = startVariableInput.value.trim();
        const maxAttempts = 50;
        const maxStrings = 10;

        try {
            for (let i = 0; i < maxAttempts && generatedStrings.size < maxStrings; i++) {
                const { string } = generateString(originalCFG, originalStartVar);
                if (string.length > 0 && string.length < 50) {
                    generatedStrings.add(string);
                }
            }

            if (generatedStrings.size === 0) {
                let epsilonGenerated = false;
                try {
                    const { string } = generateString(originalCFG, originalStartVar, 1);
                    if (string === "") {
                        if (originalCFG[originalStartVar] && originalCFG[originalStartVar].some(rule => rule.length === 1 && rule[0] === 'ε')) {
                            generatedStrings.add("ε");
                            epsilonGenerated = true;
                        }
                    }
                } catch (e) { /* ignore */ }

                if (generatedStrings.size === 0 && !epsilonGenerated) {
                    throw new Error("Could not generate any strings. The grammar might be very restrictive or only produce the empty string.");
                }
            }

            showGeneratorOutput(
                `Generated ${generatedStrings.size} Unique Strings:`,
                Array.from(generatedStrings)
            );

        } catch (error) {
            showGeneratorOutput("Generation Error", [error.message]);
            console.error(error);
        }
    }

    function generateString(grammar, symbol, maxDepth = 15, currentDepth = 0) {
        if (currentDepth > maxDepth) {
            return { string: "[...]" };
        }

        if (!isVariable(symbol)) {
            return { string: symbol };
        }

        if (!grammar[symbol] || grammar[symbol].length === 0) {
            return { string: "" };
        }

        const rules = grammar[symbol];
        const randomRule = rules[Math.floor(Math.random() * rules.length)];

        if (randomRule.length === 1 && randomRule[0] === 'ε') {
            return { string: "" };
        }

        const childStrings = [];
        for (const sym of randomRule) {
            const result = generateString(grammar, sym, maxDepth, currentDepth + 1);
            if (result.string === "[...]") return result;
            if (result.string !== "") childStrings.push(result.string);
        }

        return { string: childStrings.join(' ') };
    }

    // --- Validator (CYK) Logic ---
    function handleValidate() {
        if (!cnfGrammar || !startVariable) {
            showValidatorOutput("Error", "Please define and process a valid grammar first (Step 2).", null, true);
            return;
        }

        const originalStartVar = startVariableInput.value.trim();
        const inputString = validateInput.value.trim();
        const inputTerminals = inputString.split(' ').map(s => s.trim()).filter(s => s);

        if (inputString === "") {
            let epsilonValid = false;
            if (originalCFG[originalStartVar]) {
                epsilonValid = originalCFG[originalStartVar].some(rule => rule.length === 1 && rule[0] === 'ε');
            }
            if (startVariable !== originalStartVar) {
                epsilonValid = epsilonValid || (cnfGrammar[startVariable] && cnfGrammar[startVariable].some(rule => rule.length === 1 && rule[0] === 'ε'));
            }
            if (epsilonValid) {
                showValidatorOutput("Result: VALID", "The empty string 'ε' is a valid member of the language.", null, false);
            } else {
                showValidatorOutput("Result: INVALID", "The empty string 'ε' is not derivable from the start symbol.", null, true);
            }
            return;
        }

        if (inputTerminals.length > 30) {
            showValidatorOutput("Input Too Long", "The CYK algorithm is computationally expensive. Please use an input string with 30 or fewer tokens.", null, true);
            return;
        }

        try {
            const { table, success } = runCYK(cnfGrammar, startVariable, inputTerminals);

            if (success) {
                const tree = reconstructCYKTree(table, 0, inputTerminals.length - 1, startVariable);
                lastValidTree = tree;
                showValidatorOutput("Result: VALID", `The string "${inputString}" is derivable. Parse tree is available below.`, tree, false);
            } else {
                lastValidTree = null;
                showValidatorOutput("Result: INVALID", `The string "${inputString}" cannot be derived by the grammar.`, null, true);
            }
        } catch (error) {
            lastValidTree = null;
            showValidatorOutput("Validation Error", `A critical error occurred: ${error.message}`, null, true);
            console.error(error);
        }
    }

    function runCYK(grammar, startVar, inputTerminals) {
        const n = inputTerminals.length;
        const table = Array(n).fill(null).map(() => Array(n).fill(null).map(() => []));

        // base case
        for (let i = 0; i < n; i++) {
            const terminal = inputTerminals[i];
            for (const variable in grammar) {
                for (const rule of grammar[variable]) {
                    if (rule.length === 1 && rule[0] === terminal) {
                        table[i][i].push([variable, terminal]);
                    }
                }
            }
        }

        // inductive step
        for (let len = 2; len <= n; len++) {
            for (let i = 0; i <= n - len; i++) {
                const j = i + len - 1;
                for (let k = i; k < j; k++) {
                    for (const variable in grammar) {
                        for (const rule of grammar[variable]) {
                            if (rule.length === 2) {
                                const B = rule[0];
                                const C = rule[1];
                                const bEntries = table[i][k].filter(entry => entry[0] === B);
                                const cEntries = table[k + 1][j].filter(entry => entry[0] === C);
                                if (bEntries.length > 0 && cEntries.length > 0) {
                                    const existing = table[i][j].find(entry => entry[0] === variable);
                                    if (!existing) {
                                        table[i][j].push([variable, k, bEntries[0], cEntries[0]]);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        const success = table[0][n - 1] && table[0][n - 1].some(entry => entry[0] === startVar);
        return { table, success };
    }

    function reconstructCYKTree(table, i, j, variable) {
        const entries = table[i][j].filter(entry => entry[0] === variable);
        if (entries.length === 0) {
            return { name: `ERROR: ${variable}` };
        }

        const entry = entries[0];

        if (entry.length === 2) {
            const varSymbol = entry[0];
            const terminalVal = entry[1];

            const originalTerminal = cnfNonTerminals && cnfNonTerminals[varSymbol];
            if (originalTerminal) {
                return { name: `"${originalTerminal}"` };
            } else {
                return { name: varSymbol, children: [{ name: `"${terminalVal}"` }] };
            }
        } else {
            const [A, k, bEntry, cEntry] = entry;
            const B = bEntry[0];
            const C = cEntry[0];

            const leftChild = reconstructCYKTree(table, i, k, B);
            const rightChild = reconstructCYKTree(table, k + 1, j, C);

            let finalChildren = [];

            if (leftChild.name.startsWith('X') && leftChild.name.length > 1 && !(cnfNonTerminals && cnfNonTerminals[leftChild.name])) {
                if (leftChild.children) finalChildren.push(...leftChild.children);
            } else {
                finalChildren.push(leftChild);
            }

            if (rightChild.name.startsWith('X') && rightChild.name.length > 1 && !(cnfNonTerminals && cnfNonTerminals[rightChild.name])) {
                if (rightChild.children) finalChildren.push(...rightChild.children);
            } else {
                finalChildren.push(rightChild);
            }

            return { name: A, children: finalChildren };
        }
    }

    // --- D3 Tree Drawing Logic ---
    function drawTree(treeData, targetSelector = '#derivation-svg-container', allowZoom = false) {
        try {
            const margin = { top: 40, right: 40, bottom: 40, left: 40 };
            const container = d3.select(targetSelector);
            container.select("svg").remove();

            const rootForWidth = d3.hierarchy(treeData);
            let maxDepth = 0;
            let maxWidth = 0;
            rootForWidth.each(d => { if (d.depth > maxDepth) maxDepth = d.depth; });
            for (let i = 0; i <= maxDepth; i++) {
                const widthAtDepth = rootForWidth.descendants().filter(d => d.depth === i).length;
                if (widthAtDepth > maxWidth) maxWidth = widthAtDepth;
            }

            const height = maxDepth * 120 + 80;
            const width = Math.max(600, maxWidth * 100);
            const viewWidth = width + margin.left + margin.right;
            const viewHeight = height + margin.top + margin.bottom;

            const root = d3.hierarchy(treeData);
            const treeLayout = d3.tree().size([width, height]);
            treeLayout(root);

            const svg = container.append("svg")
                .attr("viewBox", `0 0 ${viewWidth} ${viewHeight}`)
                .attr("preserveAspectRatio", "xMidYMid meet")
                .style("max-width", "100%")
                .style("height", "auto")
                .style("background-color", "white");

            const g = svg.append("g").attr("transform", `translate(${margin.left}, ${margin.top})`);

            g.selectAll('.link')
                .data(root.links())
                .enter().append('path')
                .attr('class', 'link')
                .attr('d', d3.linkVertical().x(d => d.x).y(d => d.y))
                .style('fill', 'none')
                .style('stroke', '#9ca3af')
                .style('stroke-width', '2px');

            const node = g.selectAll('.node')
                .data(root.descendants())
                .enter().append('g')
                .attr('class', d => `node ${!d.children ? 'node--leaf' : 'node--internal'}`)
                .attr('transform', d => `translate(${d.x}, ${d.y})`);

            node.append('circle').attr('r', 16)
                .style('fill', d => !d.children ? '#ecfeff' : '#eef2ff')
                .style('stroke', d => !d.children ? '#0891b2' : '#4f46e5')
                .style('stroke-width', '2px');

            node.append('text')
                .attr('dy', '0.35em')
                .style('text-anchor', 'middle')
                .text(d => d.data.name.replace(/"/g, ''))
                .style('font-family', '"Inter", sans-serif')
                .style('font-size', '14px')
                .style('paint-order', 'stroke')
                .style('stroke', '#ffffff')
                .style('stroke-width', '3px')
                .style('stroke-linecap', 'butt')
                .style('stroke-linejoin', 'miter')
                .style('fill', d => !d.children ? '#155e75' : '#312e81');

            if (allowZoom) {
                const zoom = d3.zoom().scaleExtent([0.1, 8]).on('zoom', (event) => {
                    g.attr('transform', event.transform.toString());
                });
                const initialTransform = d3.zoomIdentity.translate((viewWidth - width) / 2, margin.top);
                svg.call(zoom).call(zoom.transform, initialTransform);
            }
        } catch (error) {
            console.error("Error drawing tree:", error);
            d3.select(targetSelector).text("Error drawing parse tree. Check console for details.");
        }
    }

    // --- Modal & Save Logic ---
    function openTreeModal() {
        if (lastValidTree) {
            drawTree(lastValidTree, '#modal-svg-container', true);
            treeModal.classList.remove('hidden');
        }
    }

    function closeTreeModal() {
        modalSvgContainer.innerHTML = '';
        treeModal.classList.add('hidden');
    }

    function saveTreeAsPNG(svgContainerSelector) {
        try {
            const svgContainer = document.querySelector(svgContainerSelector);
            if (!svgContainer) {
                console.error('Error: Could not find SVG container.');
                return;
            }
            const svgNode = svgContainer.querySelector('svg');
            if (!svgNode) {
                console.error('Error: Could not find SVG element to save.');
                return;
            }

            const viewBox = svgNode.getAttribute('viewBox');
            let width, height;
            if (viewBox) {
                const parts = viewBox.split(' ');
                width = parseFloat(parts[2]);
                height = parseFloat(parts[3]);
            } else {
                width = svgNode.clientWidth;
                height = svgNode.clientHeight;
            }

            if (!width || !height) {
                width = 1200;
                height = 800;
            }

            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');

            const svgData = new XMLSerializer().serializeToString(svgNode);
            const svgUrl = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
            const img = new Image();
            img.src = svgUrl;

            img.onload = () => {
                ctx.fillStyle = 'white';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0);
                const link = document.createElement('a');
                link.href = canvas.toDataURL('image/png');
                link.download = 'parse-tree.png';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            };

            img.onerror = (e) => {
                console.error("Error loading SVG into image:", e);
            };
        } catch (error) {
            console.error("Error saving tree as PNG:", error);
        }
    }

    modalCloseBtn.addEventListener('click', closeTreeModal);
    saveTreeBtn.addEventListener('click', () => saveTreeAsPNG('#modal-svg-container'));
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeTreeModal(); });
    treeModal.addEventListener('click', (e) => { if (e.target === treeModal) closeTreeModal(); });

});
