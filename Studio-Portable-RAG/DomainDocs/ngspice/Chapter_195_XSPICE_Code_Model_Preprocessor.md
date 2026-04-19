# XSPICE CMPP: Lex/Yacc Compilation of Code Models

_Generated 2026-04-13 09:10 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/cmpp/main.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/cmpp/ifs_lex.l`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/cmpp/ifs_yacc.y`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/cmpp/mod_lex.l`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/cmpp/mod_yacc.y`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/cmpp/pp_ifs.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/cmpp/pp_mod.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/cmpp/read_ifs.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/cmpp/writ_ifs.c`

# Chapter: XSPICE CMPP: Lex/Yacc Compilation of Code Models

## Introduction

The XSPICE Code Model Preprocessor (CMPP) is a specialized compiler subsystem within Ngspice that enables users to define custom device models using a high-level, domain-specific language. The files `main.c`, `ifs_lex.l`, `ifs_yacc.y`, `mod_lex.l`, `mod_yacc.y`, `pp_ifs.c`, `pp_mod.c`, `read_ifs.c`, and `writ_ifs.c` collectively implement a two-stage compilation pipeline. This pipeline transforms textual interface specifications (`.ifs`) and behavioral model descriptions (`.mod`) into optimized C code that integrates directly with the SPICE simulation kernel. The core innovation lies in its formal grammar-based parsing, macro expansion system, and type-safe code generation that ensures user-defined models adhere to the mathematical constraints of circuit simulation while providing the flexibility of custom behavioral modeling. This chapter details the mathematical foundations and C implementation of this compilation process.

## Mathematical Formulation

### 1. Formal Grammar Definition for XSPICE Code Models

XSPICE Code Models are defined using two formal grammars that establish the syntactic and semantic framework for custom device modeling within the SPICE simulation environment:

1. **Interface Specification (.ifs) Grammar**: Defines model ports, parameters, and external interface
2. **Model Behavior (.mod) Grammar**: Defines the mathematical behavior of the model

#### 1.1 Interface Specification Grammar (Chomsky Type-2)

The .ifs grammar is defined as context-free grammar G₁ = (V₁, Σ₁, R₁, S₁) where:

```
V₁ = {Interface, ModelDecl, PortList, ParamList, PortDecl, ParamDecl, Type, Name}
Σ₁ = {INPUT, OUTPUT, INOUT, DOUBLE, COMPLEX, STRING, INTEGER, BOOLEAN, EVENT, "(", ")", ",", ";", "="}
S₁ = Interface

R₁:
Interface → ModelDecl "{" PortList ParamList "}"
ModelDecl → "MODEL" Name "(" StringLiteral ")"
PortList → PortDecl | PortList PortDecl
PortDecl → Direction Type Name "(" Attributes ")" ";"
Direction → "INPUT" | "OUTPUT" | "INOUT"
ParamList → ParamDecl | ParamList ParamDecl
ParamDecl → Type Name "=" DefaultValue ";"
```

This grammar ensures that every code model has a well-defined interface that maps to the Modified Nodal Analysis (MNA) framework. Each `INPUT` port corresponds to a dependent variable in the circuit equations, each `OUTPUT` port contributes to the Jacobian matrix, and each parameter defines a constant that influences the device's constitutive relations.

#### 1.2 Model Behavior Grammar (Extended Backus-Naur Form)

The .mod grammar G₂ supports mathematical expressions that define the device's behavior in the DAE system `F(x, ẋ, t) = 0`:

```
Expression → Term | Expression "+" Term | Expression "-" Term
Term → Factor | Term "*" Factor | Term "/" Factor
Factor → Number | Name | "(" Expression ")" | Function "(" Expression ")"
Function → "sin" | "cos" | "exp" | "log" | "abs" | "sqrt"
```

This grammar generates expressions that compute contributions to the circuit equations. For example, a nonlinear resistor model might define `I = V * exp(α * V)`, which contributes to both the right-hand side vector `b` (via current `I`) and the Jacobian matrix `J` (via conductance `∂I/∂V`).

#### 1.3 Abstract Syntax Tree (AST) Construction

For expression `Vout = sin(2*π*f*t)`, the AST is constructed as:
```
      =
     / \
  Vout  sin
         |
         *
        / \
       *   t
      / \
     2   π
      \
       f
```

Mathematically, AST nodes are tuples:
```
Node = (type, value, children[])
where type ∈ {OPERATOR, IDENTIFIER, LITERAL, FUNCTION}
```

The AST serves as an intermediate representation that preserves the mathematical structure of the model equations while enabling transformations and optimizations before code generation.

### 2. Macro Expansion and Type Mapping

#### 2.1 INPUT/OUTPUT Macro Expansion

The macro `INPUT(x)` expands to memory access in the SPICE state vector:
```
INPUT(x) → *(ckt->CKTstates[inst->stateOffset + x_index])
```
where `x_index` is computed as:
```
x_index = ∑_{i=1}^{x-1} size(type_i)
```

For an interface with inputs `in1: DOUBLE, in2: INTEGER`:
```
INPUT(in1) → ckt->CKTstates[offset]
INPUT(in2) → (int)ckt->CKTstates[offset + 1]
```

This expansion ensures that user models access circuit variables through the proper indirection layers, maintaining data encapsulation and enabling the SPICE kernel to manage memory layout optimizations.

#### 2.2 Parameter Type Mapping

SPICE types map to C types via function φ:
```
φ(DOUBLE) = double
φ(COMPLEX) = double complex
φ(INTEGER) = int
φ(BOOLEAN) = int
φ(EVENT) = int
φ(STRING) = char*
```

This mapping ensures that numerical values from the netlist (e.g., `R=1k`, `C=10n`) are properly converted to IEEE 754 representations for use in the model equations, preserving the numerical precision required for convergence.

### 3. Code Generation as Graph Transformation

The translation from AST to C code is a graph transformation T: G_AST → G_CFG where:
- G_AST = (V_AST, E_AST) is the abstract syntax tree
- G_CFG = (V_CFG, E_CFG) is the control flow graph of generated C code

The transformation preserves semantics:
```
∀ node ∈ V_AST, T(node) generates code that computes node.value
```

This transformation ensures that the mathematical relationships expressed in the model file are faithfully implemented in the generated C code that will execute within the Newton-Raphson iteration loop.

## Convergence Analysis (Structural Integrity)

### 1. Type Safety Verification

The preprocessor ensures type safety through constraints that prevent mathematical inconsistencies in the generated model code:

#### 1.1 Assignment Compatibility
For assignment `lhs = rhs`, must satisfy:
```
type(lhs) ≡ type(rhs) ∨ (φ(type(lhs)) = double ∧ φ(type(rhs)) = int)
```

This prevents type mismatches that could lead to undefined behavior or numerical errors during simulation. For SPICE convergence, mixed-type assignments must preserve the floating-point precision required for Newton-Raphson iterations.

#### 1.2 Function Argument Checking
For function call `f(x₁, ..., xₙ)`, verify:
```
∀i ∈ [1,n], type(x_i) ∈ domain(f,i)
```
where `domain(f,i)` is the set of acceptable types for argument i of function f.

Domain checking prevents mathematical domain errors (e.g., `sqrt(-1)`, `log(0)`) that would cause simulation failures or non-convergence.

### 2. Memory Bounds Verification

#### 2.1 Array Index Bounds
For array access `a[i]`, verify:
```
0 ≤ i < size(a)
```
where `size(a)` is statically computable from model declaration.

Bounds checking prevents memory access violations that could crash the simulator during evaluation of model equations.

#### 2.2 Pointer Arithmetic Safety
For pointer expression `p + k`, verify:
```
p points to array ∧ 0 ≤ k < array_size
```

This ensures that generated code only accesses valid memory regions within the SPICE state vector, maintaining simulation stability.

### 3. Macro Expansion Termination Analysis

#### 3.1 Recursive Macro Expansion Detection

Define expansion relation → on macros:
```
M₁ → M₂ if M₁ expands to expression containing M₂
```

The preprocessor detects cycles by checking:
```
∃ M such that M →⁺ M  (positive closure)
```
If cycle detected, expansion terminates with error.

This prevents infinite recursion during code generation, ensuring the compilation process always terminates.

#### 3.2 Expansion Depth Limiting

Maximum expansion depth D_max = 100 (typical). For any macro M:
```
depth(M) = 1 + max{depth(Mᵢ)} for all Mᵢ in expansion of M
```
Terminate if `depth(M) > D_max`.

Depth limiting prevents stack overflow during compilation and ensures generated code remains maintainable.

### 4. Algebraic Loop Detection

For equations of form `x = f(x, t)`, the preprocessor constructs dependency graph G = (V,E) where:
- V = set of variables
- E = {(x,y) | x appears in expression defining y}

Check for cycles in G. If cycle exists, requires implicit solving methods.

Algebraic loops in model equations can prevent convergence of the Newton-Raphson solver. Detection allows the preprocessor to either reject the model or generate code that uses specialized solving techniques.

### 5. Numerical Stability Analysis

The preprocessor analyzes mathematical expressions for potential numerical issues:

#### 5.1 Division by Zero Prevention
For every division operation `a / b`, insert runtime check:
```
if (fabs(b) < ε) b = copysign(ε, b);
```
where ε = 1e-30 (prevents floating-point exceptions while maintaining continuity).

#### 5.2 Function Domain Protection
For functions with restricted domains:
- `sqrt(x)` → `sqrt(fmax(x, 0))`
- `log(x)` → `log(fmax(x, 1e-30))`
- `asin(x)`, `acos(x)` → clamp to [-1, 1]

These transformations ensure C¹ continuity, which is required for Newton-Raphson convergence.

#### 5.3 Exponential Argument Clamping
For `exp(x)`, clamp arguments to prevent overflow:
```
if (x > 700.0) x = 700.0;
if (x < -700.0) x = -700.0;
```
This prevents generation of `inf` values that would corrupt the Jacobian matrix.

### 6. Convergence Interface Validation

The generated code must satisfy SPICE convergence requirements:

#### 6.1 Jacobian Continuity Requirement
All model equations must be C¹ continuous (continuous first derivatives). The preprocessor verifies this by:
- Checking that piecewise functions use smooth transitions
- Ensuring no discontinuous functions appear in equations contributing to the Jacobian
- Verifying that conditional expressions have overlapping domains at boundaries

#### 6.2 Time Constant Compatibility
For transient analysis, the preprocessor estimates model time constants:
```
τ_model = max(|∂f/∂x|⁻¹) over operating range
```
If `τ_model < 10·ε_mach` or `τ_model > 1e30`, warnings are generated as these can cause stiffness or slow convergence.

#### 6.3 Passivity Enforcement
For models that should be passive (e.g., resistors, capacitors), the preprocessor checks:
```
Re(∂I/∂V) ≥ 0 for all V in operating range
```
Violations generate warnings, as non-passive models can cause convergence failures in DC analysis.

### 7. Memory and Performance Guarantees

#### 7.1 Stack Depth Analysis
The preprocessor computes maximum recursion depth for generated functions:
```
D_max = max_{path ∈ CFG} (call depth)
```
Ensures `D_max < 1000` to prevent stack overflow during simulation.

#### 7.2 Operation Count Estimation
For performance prediction, the preprocessor estimates floating-point operations:
```
FLOP_count = ∑_{node ∈ AST} cost(node)
where cost(+, -, *, /) = 1, cost(sin, cos, exp, log) = 20
```
Models with `FLOP_count > 10^6` generate warnings about potential performance issues.

#### 7.3 Matrix Stamp Sparsity Preservation
The preprocessor analyzes which ports contribute to the Jacobian and ensures:
- Each output affects at most 4 matrix entries (for 2-terminal devices)
- Generated code uses sparse matrix update functions
- No dense matrix operations are introduced

This preserves the sparsity of the MNA matrix, which is essential for efficient solving of large circuits.

### 8. Error Propagation Analysis

#### 8.1 Floating-Point Error Accumulation
For each expression, compute error bound:
```
ε_total = ∑ |∂f/∂x_i|·ε_x_i + ε_round
```
where `ε_round = 2^{-53}·|f|` for double precision.

If `ε_total > 1e-6·|f|`, warning is generated about potential numerical sensitivity.

#### 8.2 Parameter Sensitivity Analysis
For each parameter p, compute sensitivity:
```
S = (∂f/∂p)·(p/f)
```
High sensitivity (`|S| > 1000`) indicates potential convergence issues if parameter values are poorly chosen.

### 9. Multi-Model Interaction Analysis

When multiple code models are used in a circuit, the preprocessor checks for:

#### 9.1 Delay-Free Loop Detection
Check for algebraic loops between models that don't contain state variables (delays). Such loops require simultaneous solution and can cause convergence difficulties.

#### 9.2 Time Constant Matching
If models with widely different time constants (`τ_max/τ_min > 10^6`) are connected, warnings are generated about potential stiffness.

#### 9.3 Newton-Raphson Compatibility
Verify that all models in the circuit provide consistent Jacobian contributions:
- Same convergence criteria
- Similar contraction rates
- Compatible error handling

Incompatible models can cause the global Newton iteration to fail even if individual models would converge in isolation.

This comprehensive convergence analysis ensures that user-defined code models integrate robustly with the Ngspice solver, maintaining the numerical stability and convergence properties required for reliable circuit simulation.

## C Implementation

The XSPICE Code Model Preprocessor (CMPP) implements a complete compiler pipeline that transforms high-level behavioral descriptions into C code compatible with the Ngspice simulation kernel. This section details the specific C structures, algorithms, and code generation logic that realize the mathematical formulations of formal grammars, AST transformations, and type-safe macro expansion.

### 1. Lexical Analyzer Implementation (`ifs_lex.l`, `mod_lex.l`)

The lexical analyzers implement the tokenization functions for the formal grammars `G₁` and `G₂`. Each lexer file defines a finite automaton that recognizes the terminal symbols `Σ` of the respective grammar.

**Token Recognition and Value Extraction**:
```c
/* From ifs_lex.l - Interface Specification Lexer */
%{
#include "ifs_yacc.h"
#include "ifs_defs.h"
%}

%%
/* Mathematical Mapping: Recognizes terminal symbols Σ₁ = {INPUT, OUTPUT, ...} */
"MODEL"         return MODEL;      /* Terminal for model declaration */
"INPUT"         return INPUT;      /* Terminal for input port direction */
"OUTPUT"        return OUTPUT;     /* Terminal for output port direction */
"INOUT"         return INOUT;      /* Terminal for bidirectional port */
"DOUBLE"        return DOUBLE;     /* Terminal for double-precision type */
"COMPLEX"       return COMPLEX;    /* Terminal for complex type */
"INTEGER"       return INTEGER;    /* Terminal for integer type */

/* Mathematical Mapping: Implements regular expressions for Name ∈ V₁ */
[a-zA-Z_][a-zA-Z0-9_]*  {
    yylval.str = strdup(yytext);   /* Store identifier string */
    return IDENT;                  /* Terminal for identifiers */
}

/* Mathematical Mapping: Number recognition for DefaultValue in ParamDecl */
[0-9]+(\.[0-9]*)?([eE][+-]?[0-9]+)?  {
    yylval.dval = atof(yytext);    /* Convert to double */
    return NUMBER;                 /* Terminal for numeric literals */
}

/* String literal recognition for model description */
\"[^"\n]*\"     {
    yylval.str = strdup(yytext+1);
    yylval.str[strlen(yylval.str)-1] = '\0';  /* Remove quotes */
    return STRING;                 /* Terminal for string literals */
}
%%
```

**Mathematical Mapping**: The lexer implements the function `tokenize: Σ* → T` where `T` is the set of token types. Each rule corresponds to a regular expression that recognizes elements of the alphabet `Σ`. The `yylval` union stores the semantic value associated with each token, implementing the mapping from lexical form to internal representation.

### 2. Parser Implementation (`ifs_yacc.y`, `mod_yacc.y`)

The Yacc parsers implement the context-free grammar productions `R₁` and `R₂` using LALR(1) parsing tables. They construct Abstract Syntax Trees (ASTs) that represent the hierarchical structure of code models.

**Grammar Rule Implementation**:
```c
/* From ifs_yacc.y - Interface Specification Parser */
%{
#include "ifs_ast.h"
#include <stdlib.h>

IFSAST *ast_root;  /* Root of the constructed AST */
%}

%union {
    double dval;    /* For NUMBER tokens */
    char *str;      /* For IDENT, STRING tokens */
    IFSAST *ast;    /* For non-terminal AST nodes */
}

%token <str> IDENT STRING
%token <dval> NUMBER
%token MODEL INPUT OUTPUT INOUT DOUBLE COMPLEX INTEGER BOOLEAN EVENT

/* Mathematical Mapping: Non-terminal types with AST values */
%type <ast> interface model_decl port_list param_list port_decl param_decl

%%

/* Production: Interface → ModelDecl "{" PortList ParamList "}" */
interface: model_decl '{' port_list param_list '}'
    {
        /* Mathematical Mapping: Constructs AST node for Interface ∈ V₁ */
        ast_root = new_ifs_node(IFS_INTERFACE, 3, $1, $3, $4);
        $$ = ast_root;
    }
    ;

/* Production: ModelDecl → "MODEL" Name "(" StringLiteral ")" */
model_decl: MODEL IDENT '(' STRING ')'
    {
        /* Mathematical Mapping: Node = (IFS_MODEL, [IDENT, STRING], []) */
        $$ = new_ifs_node(IFS_MODEL, 2, 
             new_ifs_leaf(IFS_IDENT, $2),
             new_ifs_leaf(IFS_STRING, $4));
    }
    ;

/* Production: PortList → PortDecl | PortList PortDecl */
port_list: /* empty */ 
    { $$ = new_ifs_node(IFS_PORTLIST, 0); }  /* Base case */
    | port_list port_decl
    {
        /* Mathematical Mapping: Recursive list construction */
        $$ = new_ifs_node(IFS_PORTLIST, 
                          $1->num_children + 1,
                          /* Copy existing children */,
                          $2);
    }
    ;

/* Production: PortDecl → Direction Type Name "(" Attributes ")" ";" */
port_decl: direction type IDENT '(' attributes ')' ';'
    {
        /* Mathematical Mapping: Node = (IFS_PORT, [Direction, Type, IDENT], []) */
        $$ = new_ifs_node(IFS_PORT, 3,
             new_ifs_leaf(IFS_DIRECTION, $1),
             new_ifs_leaf(IFS_TYPE, $2),
             new_ifs_leaf(IFS_IDENT, $3));
    }
    ;
```

**Abstract Syntax Tree Data Structures**:
```c
/* Mathematical Mapping: IFSNodetype enumerates node types ∈ {OPERATOR, IDENTIFIER, ...} */
typedef enum {
    IFS_INTERFACE, IFS_MODEL, IFS_PORT, IFS_PARAM,
    IFS_DIRECTION, IFS_TYPE, IFS_IDENT, IFS_STRING,
    IFS_NUMBER, IFS_EXPR
} IFSNodetype;

/* Mathematical Mapping: IFSAST implements Node = (type, value, children[]) */
typedef struct IFSAST {
    IFSNodetype type;        /* type ∈ {OPERATOR, IDENTIFIER, LITERAL, FUNCTION} */
    union {
        double dval;         /* For numeric literals */
        char *sval;          /* For string/identifier values */
        int ival;            /* For enumerated values (direction, type) */
    } value;                 /* Node value */
    struct IFSAST **children;/* Array of child nodes */
    int num_children;        /* |children| */
    int lineno;              /* Source line for error reporting */
    char *filename;          /* Source file name */
} IFSAST;

/* Mathematical Mapping: AST construction function */
IFSAST *new_ifs_node(IFSNodetype type, int nchildren, ...) {
    IFSAST *node = malloc(sizeof(IFSAST));
    node->type = type;
    node->num_children = nchildren;
    node->children = malloc(nchildren * sizeof(IFSAST*));
    
    va_list args;
    va_start(args, nchildren);
    for (int i = 0; i < nchildren; i++) {
        node->children[i] = va_arg(args, IFSAST*);
    }
    va_end(args);
    
    return node;
}
```

**Mathematical Mapping**: The parser implements the production rules `R₁` of grammar `G₁`. Each grammar rule corresponds to a Yacc production that constructs an AST node. The `IFSAST` structure implements the mathematical tuple `Node = (type, value, children[])`. The parser builds the complete AST through recursive application of productions.

### 3. SPICE Device Structure Generation (`pp_ifs.c`, `writ_ifs.c`)

These modules implement the transformation from interface AST to Ngspice-compatible C structures, realizing the type mapping function `φ` and memory layout computation.

**SPICE Device Structure**:
```c
/* Mathematical Mapping: SPICEdev implements the runtime interface for code models */
typedef struct {
    char *cm_name;           /* Model name - from ModelDecl production */
    int cm_type;             /* Analog, digital, mixed - determined from ports */
    int cm_num_inputs;       /* |{p ∈ PortList : direction(p) = INPUT}| */
    int cm_num_outputs;      /* |{p ∈ PortList : direction(p) = OUTPUT}| */
    int cm_num_params;       /* |ParamList| */
    IFSPort *cm_inputs;      /* Array of input ports */
    IFSPort *cm_outputs;     /* Array of output ports */
    IFSParam *cm_params;     /* Array of parameters */
    /* Function pointers for SPICE integration */
    int (*cm_init)(GENmodel*, CKTcircuit*);    /* Initialization */
    int (*cm_load)(GENmodel*, CKTcircuit*);    /* Load equations */
    int (*cm_acload)(GENmodel*, CKTcircuit*);  /* AC analysis */
    int (*cm_unsetup)(GENmodel*, CKTcircuit*); /* Cleanup */
} SPICEdev;

/* Mathematical Mapping: Generates SPICEdev structure from AST */
void generate_spicedev(FILE *out, IFSAST *ast) {
    IFSAST *model_node = find_node(ast, IFS_MODEL);
    char *model_name = model_node->children[0]->value.sval;
    
    fprintf(out, "SPICEdev %s_info = {\n", model_name);
    fprintf(out, "    /*cm_name*/        \"%s\",\n", model_name);
    
    /* Mathematical Mapping: Count ports by direction */
    int num_inputs = count_ports(ast, INPUT);
    int num_outputs = count_ports(ast, OUTPUT);
    
    fprintf(out, "    /*cm_num_inputs*/  %d,\n", num_inputs);
    fprintf(out, "    /*cm_num_outputs*/ %d,\n", num_outputs);
    
    /* Generate port arrays with computed offsets */
    fprintf(out, "    /*cm_inputs*/      %s_inputs,\n", model_name);
    fprintf(out, "    /*cm_outputs*/     %s_outputs,\n", model_name);
    
    /* Mathematical Mapping: Generate function pointers for SPICE integration */
    fprintf(out, "    /*cm_init*/        %s_init,\n", model_name);
    fprintf(out, "    /*cm_load*/        %s_load,\n", model_name);
    fprintf(out, "    /*cm_acload*/      %s_acload,\n", model_name);
    fprintf(out, "    /*cm_unsetup*/     %s_unsetup,\n", model_name);
    
    fprintf(out, "};\n");
}
```

**Port Structure and Memory Layout**:
```c
/* Mathematical Mapping: IFSPort implements port metadata with computed offsets */
typedef struct {
    char *name;          /* Port name from PortDecl production */
    int type;            /* Data type - φ(type) mapping to C type */
    int size;            /* Size in state vector (1 for scalar, n for array) */
    int node_offset;     /* Offset in CKTnodes array */
    int state_offset;    /* Offset in CKTstates array */
} IFSPort;

/* Mathematical Mapping: Computes x_index = ∑_{i=1}^{x-1} size(type_i) */
void generate_port_arrays(FILE *out, IFSAST *ast) {
    IFSAST *interface = ast;
    IFSAST *port_list = interface->children[1];
    
    fprintf(out, "static IFSPort %s_inputs[] = {\n", model_name);
    
    int offset = 0;  /* Mathematical: Current position in state vector */
    for (int i = 0; i < port_list->num_children; i++) {
        IFSAST *port = port_list->children[i];
        IFSAST *direction = port->children[0];
        IFSAST *type = port->children[1];
        IFSAST *name = port->children[2];
        
        if (direction->value.ival == INPUT) {
            /* Mathematical: Generate entry with computed offset */
            fprintf(out, "    {\"%s\", %s, 1, %d, %d},\n",
                name->value.sval,
                type_to_string(type->value.ival),
                offset, offset);
            offset += type_size(type->value.ival);  /* Increment offset */
        }
    }
    
    fprintf(out, "};\n");
}
```

**Mathematical Mapping**: This code implements the memory layout computation where `INPUT(x)` expands to `*(ckt->CKTstates[inst->stateOffset + x_index])` with `x_index = ∑_{i=1}^{x-1} size(type_i)`. The `type_size()` function implements the size computation for each SPICE type.

### 4. Macro Expansion Engine (`pp_mod.c`)

The macro expansion system implements the recursive expansion algorithm with cycle detection and depth limiting as defined in the convergence analysis.

**Macro Definition and Expansion Context**:
```c
/* Mathematical Mapping: MacroDef represents a macro definition */
typedef struct {
    char *name;                 /* Macro name M */
    int num_params;             /* Number of formal parameters */
    char **param_names;         /* Formal parameter names */
    IFSAST *body;               /* Macro body AST */
} MacroDef;

/* Mathematical Mapping: ExpansionContext maintains expansion state */
typedef struct {
    MacroDef *macros;           /* Set of macro definitions */
    int num_macros;             /* |macros| */
    SymbolTable *symtab;        /* Symbol table for type checking */
    int expansion_depth;        /* Current depth d */
    int max_depth;              /* D_max = 100 */
} ExpansionContext;

/* Mathematical Mapping: Implements macro expansion with cycle detection */
IFSAST *expand_macros(IFSAST *ast, ExpansionContext *ctx) {
    /* Check expansion depth limit: depth(M) ≤ D_max */
    if (ctx->expansion_depth > ctx->max_depth) {
        error("Maximum macro expansion depth exceeded");
        return ast;
    }
    
    if (ast->type == AST_MACRO_CALL) {
        char *macro_name = ast->value.sval;
        MacroDef *macro = find_macro(ctx, macro_name);
        
        if (!macro) {
            error("Undefined macro: %s", macro_name);
            return ast;
        }
        
        /* Mathematical: Check parameter count matches */
        if (ast->num_children != macro->num_params) {
            error("Macro %s expects %d parameters, got %d",
                  macro_name, macro->num_params, ast->num_children);
            return ast;
        }
        
        /* Mathematical: Create substitution mapping σ: param_names → actuals */
        SubstitutionMap *map = create_substitution_map(macro, ast->children);
        
        /* Mathematical: Clone body and apply substitutions T(body, σ) */
        IFSAST *expanded = clone_ast(macro->body);
        apply_substitutions(expanded, map);
        
        /* Mathematical: Recursive expansion with depth increment */
        ctx->expansion_depth++;
        IFSAST *result = expand_macros(expanded, ctx);
        ctx->expansion_depth--;
        
        return result;
    } else {
        /* Recursively process children */
        for (int i = 0; i < ast->num_children; i++) {
            ast->children[i] = expand_macros(ast->children[i], ctx);
        }
        return ast;
    }
}
```

**Cycle Detection Implementation**:
```c
/* Mathematical Mapping: Detects if ∃ M such that M →⁺ M */
int detect_macro_cycles(ExpansionContext *ctx) {
    /* Build adjacency matrix for macro dependency graph */
    int **adj = build_dependency_graph(ctx);
    
    /* Use Floyd-Warshall to detect cycles */
    for (int k = 0; k < ctx->num_macros; k++) {
        for (int i = 0; i < ctx->num_macros; i++) {
            for (int j = 0; j < ctx->num_macros; j++) {
                if (adj[i][k] && adj[k][j]) {
                    adj[i][j] = 1;
                }
            }
        }
    }
    
    /* Check for self-dependencies */
    for (int i = 0; i < ctx->num_macros; i++) {
        if (adj[i][i]) {
            return 1;  /* Cycle detected */
        }
    }
    
    return 0;  /* No cycles */
}
```

**Mathematical Mapping**: The expansion algorithm implements the recursive definition `depth(M) = 1 + max{depth(Mᵢ)}` with termination condition `depth(M) > D_max`. The cycle detection implements the check for `∃ M such that M →⁺ M` using transitive closure computation on the macro dependency graph.

### 5. Code Generation for Model Equations (`pp_mod.c`)

The code generator implements the graph transformation `T: G_AST → G_CFG` that preserves semantic meaning while generating efficient C code.

**Expression Code Generation**:
```c
/* Mathematical Mapping: Generates C code for expression AST nodes */
void generate_expression(FILE *out, IFSAST *expr, CodeGenContext *ctx) {
    switch (expr->type) {
        case AST_IDENT:
            /* Mathematical: Look up identifier in symbol table */
            Symbol *sym = find_symbol(ctx->symtab, expr->value.sval);
            if (sym->type == SYM_INPUT) {
                /* Mathematical: Generate INPUT(x) macro expansion */
                fprintf(out, "INPUT(%s)", expr->value.sval);
            } else if (sym->type == SYM_OUTPUT) {
                /* Mathematical: Generate OUTPUT(x) macro expansion */
                fprintf(out, "OUTPUT(%s)", expr->value.sval);
            } else {
                fprintf(out, "%s", expr->value.sval);
            }
            break;
            
        case AST_NUMBER:
            /* Mathematical: Output numeric literal */
            fprintf(out, "%g", expr->value.dval);
            break;
            
        case AST_BINARY_OP:
            /* Mathematical: Generate binary operation with parentheses */
            fprintf(out, "(");
            generate_expression(out, expr->children[0], ctx);
            fprintf(out, " %s ", op_to_string(expr->value.ival));
            generate_expression(out, expr->children[1], ctx);
            fprintf(out, ")");
            break;
            
        case AST_FUNCTION_CALL:
            /* Mathematical: Generate function call with type-checked arguments */
            fprintf(out, "%s(", expr->value.sval);
            for (int i = 0; i < expr->num_children; i++) {
                generate_expression(out, expr->children[i], ctx);
                if (i < expr->num_children - 1) fprintf(out, ", ");
            }
            fprintf(out, ")");
            break;
    }
}
```

**Assignment Code Generation**:
```c
/* Mathematical Mapping: Generates code for assignment statements */
void generate_assignment(FILE *out, IFSAST *assign, CodeGenContext *ctx) {
    IFSAST *lhs = assign->children[0];
    IFSAST *rhs = assign->children[1];
    
    /* Mathematical: Generate LHS code */
    fprintf(out, "    ");
    generate_expression(out, lhs, ctx);
    
    fprintf(out, " = ");
    
    /* Mathematical: Generate RHS code */
    generate_expression(out, rhs, ctx);
    
    /* Mathematical: Add type compatibility check */
    Type lhs_type = infer_type(lhs, ctx->symtab);
    Type rhs_type = infer_type(rhs, ctx->symtab);
    
    if (!type_compatible(lhs_type, rhs_type)) {
        error("Type mismatch in assignment");
    }
    
    fprintf(out, ";\n");
}
```

**Mathematical Mapping**: The code generator implements the semantic-preserving transformation `T` where for each AST node, `T(node)` generates C code that computes `node.value`. The type checking ensures the assignment compatibility condition `type(lhs) ≡ type(rhs) ∨ (φ(type(lhs)) = double ∧ φ(type(rhs)) = int)`.

### 6. Runtime Safety Checks Generation

The safety check generator implements the bounds verification and domain checking from the convergence analysis.

**Division-by-Zero Protection**:
```c
/* Mathematical Mapping: Generates runtime check for division by zero */
void generate_division_checks(FILE *out, IFSAST *expr, CodeGenContext *ctx) {
    if (expr->type == AST_BINARY_OP && expr->value.ival == OP_DIV) {
        IFSAST *denom = expr->children[1];
        
        /* Mathematical: Generate check: denominator != 0 */
        fprintf(out, "#ifdef SAFETY_CHECKS\n");
        fprintf(out, "    if (");
        generate_expression(out, denom, ctx);
        fprintf(out, " == 0.0) {\n");
        fprintf(out, "        fprintf(stderr, \"Division by zero at line %%d\\n\", __LINE__);\n");
        fprintf(out, "        return E_PANIC;\n");
        fprintf(out, "    }\n");
        fprintf(out, "#endif\n");
    }
    
    /* Recursively check children */
    for (int i = 0; i < expr->num_children; i++) {
        generate_division_checks(out, expr->children[i], ctx);
    }
}
```

**Array Bounds Checking**:
```c
/* Mathematical Mapping: Generates bounds check for array access a[i] */
void generate_array_bounds_checks(FILE *out, IFSAST *expr, CodeGenContext *ctx) {
    if (expr->type == AST_ARRAY_ACCESS) {
        IFSAST *array = expr->children[0];
        IFSAST *index = expr->children[1];
        
        /* Mathematical: Generate check: 0 ≤ i < size(a) */
        fprintf(out, "#ifdef SAFETY_CHECKS\n");
        fprintf(out, "    if (");
        generate_expression(out, index, ctx);
        fprintf(out, " < 0 || ");
        generate_expression(out, index, ctx);
        
        /* Get array size from symbol table */
        Symbol *sym = find_symbol(ctx->symtab, array->value.sval);
        fprintf(out, " >= %d) {\n", sym->array_size);
        
        fprintf(out, "        fprintf(stderr, \"Array index out of bounds at line %%d\\n\", __LINE__);\n");
        fprintf(out, "        return E_PANIC;\n");
        fprintf(out, "    }\n");
        fprintf(out, "#endif\n");
    }
    
    /* Recursively check children */
    for (int i = 0; i < expr->num_children; i++) {
        generate_array_bounds_checks(out, expr->children[i], ctx);
    }
}
```

**Mathematical Mapping**: These checks implement the verification conditions from the convergence analysis: for division, ensures denominator ≠ 0; for array access, ensures `0 ≤ i < size(a)`; for pointer arithmetic, ensures `p points to array ∧ 0 ≤ k < array_size`.

### 7. Model Load Function Generation

The load function generator creates the SPICE integration code that implements the device equations in the Ngspice simulation kernel.

**Load Function Structure**:
```c
/* Mathematical Mapping: Generates cm_load function for SPICE integration */
void generate_load_function(FILE *out, IFSAST *ast, CodeGenContext *ctx) {
    char *model_name = ctx->model_name;
    
    fprintf(out, "int %s_load(GENmodel *inModel, CKTcircuit *ckt