# ngspice — Complete Input-to-Output Data Flow

> This document traces exactly how ngspice reads a circuit netlist from disk,
> builds the internal simulation state, runs the analysis, and writes results to
> output files. Every subsystem, data structure, and key function is covered in
> call-stack order.

---

## 1. The Big Picture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DISK (input)                                                               │
│  circuit.cir  ─────►  1. READ & PRE-PROCESS  ─────►  2. PARSE             │
│  .lib / .inc files         (inpcom.c, inp.c)           (inppas1/2.c)       │
└─────────────────────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
                                                    CKTcircuit struct
                                                              │
                                          ┌───────────────────┴──────────────┐
                                          ▼                                  ▼
                                   3. SETUP                          Model table
                                  (cktsetup.c)                      (INPtables)
                                          │
                                          ▼
                                  Sparse MNA matrix
                                  State vectors
                                          │
                              ┌───────────┴──────────────┐
                              ▼                          ▼
                        4. ANALYSIS                  4a. TEMPERATURE
                    (dcop / dctran / acan …)         (ckttemp.c)
                              │
                        ┌─────┘
                        ▼
               5. NEWTON–RAPHSON LOOP  (niiter.c)
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
          CKTload   SMPluFac   NIconv
         (stamp)   (factor)  (check)
             │
        DEVload per device
        (dioload, bjtload, …)
                              │
                              ▼ accepted point
                        6. DATA RECORDING
                         (outitf.c: OUTdata)
                              │
               ┌──────────────┴─────────────────┐
               ▼                                ▼
      In-memory plot                     rawfile (disk)
      (dvec list)                       (rawfile.c: raw_write)
               │
               ▼
      7. POST-PROCESSING & OUTPUT
      (com_measure2, com_fft, plotting, gnuplot …)
               │
               ▼
     DISK (output)  ─────── .raw / .csv / .dat / screen plot
```

---

## 2. Stage 1: Input File Reading

### 2.1 Entry point

```
main()  →  ft_doreadcir()  →  inp_spsource()  →  inp_readall()
```

All in `src/frontend/inpcom.c` and `src/frontend/inp.c`.

### 2.2 `inp_readall()` — `src/frontend/inpcom.c`

**What it does:**

1. **Opens** the top-level `.cir` / `.sp` file with `fopen()`.
2. **Reads line by line** into `struct line` (also called `card`) linked list.
   - Continues lines that end with `+` (SPICE continuation syntax).
   - Strips comments (lines starting with `*`).
3. **Processes `.include`** directives — recursively reads the included file and
   splices the resulting deck into the current list.
4. **Processes `.lib`** directives — looks up the library file in the `libraries[]`
   array; if not yet loaded, reads it and caches it. Splices the requested section
   into the deck.
5. **Resolves `.param` and `.func`** — calls into `numparam/` to expand
   `{expression}` parameter substitutions throughout the deck.
6. Returns the fully expanded `struct line *deck`.

**Key data structure — `struct line` / `card`:**

```c
struct line {
    int   linenum;       /* original file line number for error messages */
    char *line;          /* expanded text of the line                    */
    char *error;         /* parse error string (NULL if OK)              */
    struct line *nextcard;
    struct line *actualLine;
};
```

### 2.3 `subckt.c` — Subcircuit flattening

Called immediately after `inp_readall()`:

```c
deck = inp_subcktexpand(deck);   /* src/frontend/subckt.c */
```

- Finds every subcircuit definition (`.subckt` … `.ends`).
- Finds every subcircuit call (`X…` element lines).
- **Replaces** each `X` line with a flat copy of the subcircuit body, renaming
  nodes using a `<instance>:<node>` mangling scheme.
- Result: a completely flat deck with no subcircuit calls remaining.

### 2.4 `dotcards.c` — Dot-card parsing

```c
inp_dodotcard(deck);   /* src/frontend/dotcards.c */
```

Walks the flat deck looking for control lines:

| Dot card | Action |
|----------|--------|
| `.tran` | Creates `TRANan` job struct; fills `TRANstep`, `TRANfinal`, `TRANmaxStep` |
| `.ac` | Creates `ACan` job struct; fills freq range, sweep type |
| `.dc` | Creates `DCTRCURVan` job struct |
| `.op` | Marks DC operating-point flag |
| `.options` | Calls `INPdoOptions()` → sets `CKToptions` fields (VNTOL, RELTOL, ABSTOL, GMIN, …) |
| `.ic` | Stores initial-condition node=value pairs |
| `.measure` | Registers a `.meas` task for post-processing |
| `.four` | Registers a Fourier analysis |
| `.save` | Registers which vectors to save to rawfile |
| `.probe` | Alias for `.save` |
| `.print` | Registers output columns |

---

## 3. Stage 2: Circuit Parsing (spicelib parser)

### 3.1 Interface call

```c
/* src/frontend/spiceif.c */
SPfrontEnd->IFnewCircuit(&ckt);
SPfrontEnd->IFloadCircuit(ckt, deck, tab);
```

`SPfrontEnd` is the `IFsimulator` vtable (defined in `src/include/ngspice/ifsim.h`)
that routes frontend calls to the spicelib back-end.

### 3.2 Pass 1 — Model registration (`inppas1.c`)

```c
INPpas1(ckt, deck, tab);
```

- Scans for every `.model <name> <type> (params…)` line.
- Calls `INPdomodel()` which allocates a `INPmodel` struct and stores it in
  `INPtables.INPmhead` hash table keyed by name.
- The model type string (`NPN`, `PNP`, `NMOS`, `D`, …) is resolved to a device
  type index into the global `DEVices[]` array.

### 3.3 Pass 2 — Element instantiation (`inppas2.c`)

```c
INPpas2(ckt, deck, tab, nodTab);
```

For each non-`.` line, the first character selects the parser:

| First char | Parser file | Device |
|-----------|------------|--------|
| `R` | `inp2r.c` | Resistor |
| `C` | `inp2c.c` | Capacitor |
| `L` | `inp2l.c` | Inductor |
| `D` | `inp2d.c` | Diode |
| `Q` | `inp2q.c` | BJT |
| `J` | `inp2j.c` | JFET |
| `M` | `inp2m.c` | MOSFET |
| `B` | `inp2b.c` | Nonlinear source |
| `V` | `inp2v.c` | Voltage source |
| `I` | `inp2i.c` | Current source |
| `E/F/G/H` | `inp2e/f/g/h.c` | Controlled sources |
| `T` | `inp2t.c` | Transmission line |
| `K` | `inp2k.c` | Mutual inductance |
| `X` | handled by subckt.c | (already expanded) |

Each `inp2X.c` calls:
1. `CKTmkNode()` — finds or creates nodes in the node table; assigns matrix row indices.
2. `IFnewInstance()` — calls `DEVices[type]->DEVnew()` to allocate the device-specific
   instance struct (e.g. `DIinstance` for diodes).
3. `IFsetParam()` — copies parsed parameter values into the instance struct.
4. `INPgetMod()` — looks up the model by name and links the instance to its model.

**Result:** `CKTcircuit` is fully populated:
- `ckt->CKTnodeTab[]` — all nodes with matrix indices
- `ckt->CKThead[devtype]` — linked lists of all instances per device type
- `ckt->CKTmods` — model parameter blocks

---

## 4. Stage 3: Circuit Setup

### 4.1 `CKTsetup()` — `src/spicelib/analysis/cktsetup.c`

Called once before the first analysis:

```c
error = CKTsetup(ckt);
```

**Steps:**

1. **Allocates state vectors:** `CKTstate0[]`, `CKTstate1[]`, … (used for
   integration history). Size = sum of state variable counts from all devices.
2. **Calls `DEVsetup` for every device:** Each device stamps its MNA matrix
   element indices (`SMPgetElement()`) to register which matrix locations it will
   write during `DEVload`. No values are written yet.
3. **Builds the sparse matrix:** After all elements are registered,
   `SMPpreOrder(ckt->CKTmatrix)` sets up the fill-in pattern for LU factorisation.
4. **Allocates RHS, solution, and old-solution vectors:** `CKTrhs[]`, `CKTrhsOld[]`.
5. **Calls `CKTtemp()` for initial temperature.**

### 4.2 `CKTtemp()` — `src/spicelib/analysis/ckttemp.c`

For every device type that registers `DEVtemperature`, calls it with the current
`ckt->CKTtemp` value. Devices recompute all temperature-dependent parameters
(saturation current `IS`, threshold voltage `VTH0`, etc.) and store them in the
instance struct.

---

## 5. Stage 4: Analysis Loop

### 5.1 Analysis dispatch

The job queue (`ckt->CKTcurJob`) is walked in `src/frontend/runcoms.c`. Each job
calls into its analysis driver via `IFrunAnalysis()`.

### 5.2 DC Operating Point (`dcop.c`)

```
DCop()
  └─ NIiter(ckt, ckt->CKTdcMaxIter)
       ├─ CKTload(ckt)              ← stamp all devices
       ├─ SMPluFac(ckt->CKTmatrix) ← LU factorise
       ├─ SMPsolve(…)               ← back-substitute → CKTrhs = solution
       └─ NIconv(ckt)              ← check convergence
```

If not converged within `dcMaxIter`, source-stepping or GMIN-stepping is attempted
(`niniter.c`).

### 5.3 Transient Analysis (`dctran.c`)

```
DCTran()
  ├─ traninit(ckt)        ← set up breakpoint table, initial step
  ├─ Time loop:
  │    ├─ NIpred(ckt)     ← predictor: extrapolate state for next time
  │    ├─ NIiter(ckt, …)  ← Newton loop at current time point
  │    │    ├─ CKTload(ckt)
  │    │    ├─ SMPluFac / SMPsolve
  │    │    └─ NIconv
  │    ├─ CKTtrunc(ckt, &newDelta)   ← LTE: accept step or reduce Δt?
  │    ├─ if accepted:
  │    │    ├─ NIcomCof(ckt)          ← update integration coefficients
  │    │    ├─ OUTdata(runDesc, …)    ← record data point
  │    │    └─ advance time
  │    └─ repeat
  └─ OUTendPlot(runDesc)
```

**Time-step control (LTE):**
Each device's `DEVtrunc` computes the local truncation error for its state
variables and returns the maximum allowable `Δt`. `CKTtrunc()` takes the minimum
across all devices. If the proposed time step exceeds this limit, the step is
rejected and retried with the smaller `Δt`.

### 5.4 AC Analysis (`acan.c`)

```
ACan()
  ├─ DCop()                    ← find linearisation point
  ├─ Frequency loop:
  │    ├─ CKTacLoad(ckt, ω)    ← stamp complex AC conductances + sources
  │    ├─ SMPcLUfac(…)         ← complex LU factorisation
  │    ├─ SMPcSolve(…)         ← complex back-substitute
  │    └─ OUTdata(…)           ← record V(n), I(branch) at this frequency
  └─ OUTendPlot
```

---

## 6. Stage 5: Newton–Raphson Inner Loop (detail)

### 6.1 `NIiter()` — `src/maths/ni/niiter.c`

```c
int NIiter(CKTcircuit *ckt, int maxIter)
{
    for (iterno = 0; iterno < maxIter; iterno++) {
        /* 1. Stamp the MNA matrix */
        CKTload(ckt);

        /* 2. Factorise: A = LU */
        SMPluFac(ckt->CKTmatrix, ckt->CKTpivotRelTol, ckt->CKTpivotAbsTol);

        /* 3. Solve: LU·x = b  →  x stored back in CKTrhs */
        SMPsolve(ckt->CKTmatrix, ckt->CKTrhs, ckt->CKTrhsSpare);

        /* 4. Check convergence */
        if (NIconv(ckt) == OK) return OK;

        /* 5. Swap old/new solution vectors */
        SWAP(ckt->CKTrhs, ckt->CKTrhsOld);
    }
    return E_ITERLIM;   /* too many iterations */
}
```

### 6.2 `CKTload()` — `src/spicelib/analysis/cktload.c`

```c
int CKTload(CKTcircuit *ckt)
{
    SMPclear(ckt->CKTmatrix);      /* zero the matrix */
    for (i = 0; i <= size; i++)
        ckt->CKTrhs[i] = 0;       /* zero the RHS */

    for (i = 0; i < DEVmaxnum; i++) {
        if (DEVices[i] && DEVices[i]->DEVload && ckt->CKThead[i])
            DEVices[i]->DEVload(ckt->CKThead[i], ckt);
    }
}
```

Each `DEVload` (e.g. `DIOload`, `BJTload`, `MOS1load`) reads the current node
voltages from `ckt->CKTrhs[]`, evaluates the device equations, and stamps:
- **Conductances / Jacobian entries** → `SMPaddElement(ptr, value)` into the matrix.
- **Current sources** → `ckt->CKTrhs[nodeIndex] += current`.

### 6.3 Diode load — `src/spicelib/devices/dio/dioload.c`

Representative example of a `DEVload` function:

```
DIOload(DIOinstance *here, CKTcircuit *ckt)
  │
  ├─ vd = CKTrhs[here->DIOposNode] - CKTrhs[here->DIOnegNode]
  │       + voltage across internal series resistance
  │
  ├─ DEVpnjlim(vd, &vd, vt, here->DIOtSatCur, …)   ← voltage limiter
  │   (prevents exp() overflow on first iterations)
  │
  ├─ id = IS * (exp(vd / (N * Vt)) - 1)             ← Shockley equation
  │
  ├─ gd = ∂id/∂vd = IS/(N*Vt) * exp(…)             ← conductance stamp
  │
  ├─ SMPaddElement(here->DIOposPosPtr, gd + Gcond)  ← matrix stamp
  ├─ SMPaddElement(here->DIOnegNegPtr, gd + Gcond)
  ├─ SMPaddElement(here->DIOposPosPtr, -gd - Gcond) ← off-diagonals
  ├─ SMPaddElement(here->DIOnegPosPtr, -gd - Gcond)
  │
  ├─ ckt->CKTrhs[here->DIOposNode] -= (id - gd*vd)  ← Norton RHS
  └─ ckt->CKTrhs[here->DIOnegNode] += (id - gd*vd)
```

**Voltage limiting (`DEVpnjlim`):**
Before computing the exponential, the new junction voltage `vd` is clipped relative
to the old value `vdold` using:

```
if (vd > vcrit) vd = vdold + Vt * log(1 + (vd - vdold)/Vt)
```

This prevents divergence on the first Newton steps where node voltages are
far from the solution.

### 6.4 Convergence test — `NIconv()` — `src/maths/ni/niconv.c`

For every node `i`:

```
diff = |CKTrhs[i] - CKTrhsOld[i]|
tol  = RELTOL * max(|CKTrhs[i]|, |CKTrhsOld[i]|) + ABSTOL
if diff > tol: not converged
```

Separate tests for voltage nodes (`VNTOL`) and current branches (`ABSTOL`).

---

## 7. Stage 6: Output Data Recording

### 7.1 `OUTbeginPlot()` — `src/frontend/outitf.c`

Called once per analysis before the first data point:

```c
OUTbeginPlot(ckt, job,
             analName,        /* "Transient Analysis" etc. */
             refName,         /* "time", "frequency", "v-sweep" */
             refType,         /* IFT_REAL, IFT_COMPLEX */
             numNames, names, /* vector names: V(1), I(R1), … */
             dataType,
             &runDesc);
```

**Internally:**
1. Allocates `runDesc` (a `struct runDesc`).
2. If a `-o outputfile` option was given: calls `fileInit(runDesc)` which opens the
   output file and writes the rawfile **header** (variable list, date, title).
3. Always creates an in-memory `struct plot *` and attaches `dvec` vectors for each
   named output.

**Rawfile header format (ASCII mode):**

```
Title: Circuit name from first line of netlist
Date: Mon Apr 20 10:30:00 2026
Plotname: Transient Analysis
Flags: real
No. Variables: 5
No. Points: 0          ← updated at OUTendPlot
Variables:
        0 time         time
        1 v(out)       voltage
        2 v(in)        voltage
        3 i(v1)        current
        4 v(net001)    voltage
Binary:                ← or "Values:" for ASCII
```

### 7.2 `OUTdata()` — `src/frontend/outitf.c`

Called by the analysis driver at every accepted simulation point:

```c
OUTdata(runDesc, refValue, dataType, dataValues);
```

**Routing:**

```
OUTdata()
  ├─ if runDesc->fd != NULL (rawfile open):
  │    ├─ fileStartPoint(fp, binary, pointNum)
  │    ├─ for each variable:
  │    │    ├─ fileAddRealValue(fp, binary, val)    ← or Complex
  │    └─ fileEndPoint(fp, binary)
  │
  └─ if runDesc->plot != NULL (in-memory):
       ├─ for each dvec:
       │    dvec->v_realdata[pointIndex] = val      ← extends the array
       └─ pointIndex++
```

**Binary rawfile point format:**

One block per time point: N doubles (8 bytes each) written sequentially.
The reference variable (time or frequency) is always first.

**ASCII rawfile point format:**

```
 9.000000000000000e-09
 +4.999941022000000e+00
 +0.000000000000000e+00
 -1.000000000000000e-05
 +4.999941022000000e+00
```

### 7.3 `OUTendPlot()` — `src/frontend/outitf.c`

```c
OUTendPlot(runDesc);
```

1. Flushes and **closes** the output file.
2. Goes back to the start of the file and **rewrites the "No. Points:" header** line
   with the actual count (since it was unknown at `OUTbeginPlot` time).
3. Frees `rowbuf`.
4. Links the in-memory `dvec` plot into the global `plot_list` so CP commands like
   `plot`, `print`, `measure` can access the data.

### 7.4 `raw_write()` — `src/frontend/rawfile.c`

Called when the user issues the `write` CP command or `--rawfile` CLI flag after
simulation is complete. Serialises the entire in-memory plot:

```c
void raw_write(char *name, struct plot *pl, bool app, bool binary)
{
    /* Open file (append or overwrite) */
    fp = fopen(name, app ? "ab" : "wb");

    /* Write header */
    fprintf(fp, "Title: %s\n", pl->pl_title);
    fprintf(fp, "Date: %s\n", datestring());
    fprintf(fp, "Plotname: %s\n", pl->pl_name);
    fprintf(fp, "Flags: %s\n", realflag ? "real" : "complex");
    fprintf(fp, "No. Variables: %d\n", nvars);
    fprintf(fp, "No. Points: %d\n", length);
    fprintf(fp, "Variables:\n");
    for each dvec v:
        fprintf(fp, "\t%d %s %s\n", index, v->v_name, typenames[v->v_type]);

    if (binary) fprintf(fp, "Binary:\n");
    else        fprintf(fp, "Values:\n");

    /* Write data points */
    for (j = 0; j < length; j++) {
        for each dvec v:
            if binary: fwrite(&v->v_realdata[j], sizeof(double), 1, fp);
            else:      fprintf(fp, "\t%.15e\n", v->v_realdata[j]);
    }
    fclose(fp);
}
```

---

## 8. Stage 7: Post-Processing

### 8.1 `.measure` — `src/frontend/com_measure2.c`

After `OUTendPlot()`, each registered `.meas` statement is evaluated against the
in-memory `dvec` data:

| Measurement | Function |
|-------------|---------|
| `TRIG … TARG` | Find crossing times, compute difference |
| `RISE` / `FALL` | `trise()` / `tfall()` — cross a threshold level |
| `MAX` / `MIN` | Scan the vector, find extreme value |
| `AVG` | Integrate and divide by interval |
| `INTEG` | Trapezoidal integration over the interval |
| `DERIV` | Numerical derivative at a point |
| `FIND … WHEN` | Find the value of one variable when another crosses |

Results are printed to `stdout` and also stored as CP variables (accessible via
`print meas_result` in scripts).

### 8.2 Fourier analysis — `src/frontend/fourier.c`

Called when `.four` is in the deck:

```
com_fourier()
  ├─ Extracts the time-domain waveform dvec for the requested node
  ├─ Calls maths/fft/ for DFT
  └─ Prints THD and harmonic table to stdout
```

### 8.3 Gnuplot output — `src/frontend/plotting/gnuplot.c`

```
com_gnuplot()
  ├─ Writes a .data file with columns of numbers
  ├─ Writes a .plt gnuplot script
  └─ Optionally forks gnuplot subprocess
```

### 8.4 Additional output formats

| Command | File | Output |
|---------|------|--------|
| `write filename.raw` | `rawfile.c` | Binary or ASCII rawfile |
| `write filename.csv` | `rawfile.c` | (with `-f` format flag) |
| `hardcopy` | `com_hardcopy.c` + `postsc.c` | PostScript plot |
| `asciiplot` | `com_asciiplot.c` | Text-art waveform on terminal |
| `gnuplot` | `plotting/gnuplot.c` | External gnuplot rendering |
| `display` | `com_display.c` | List available vectors |
| `print` | `com_dump.c` | Print vector values to stdout |

---

## 9. Complete Call Stack — Transient Analysis

```
main()                                            [src/frontend/main.c]
 └─ ft_doreadcir(filename)
     └─ inp_readall(fp)                           [inpcom.c]
         ├─ reads lines, processes .include/.lib
         └─ returns struct line *deck

 └─ inp_subcktexpand(deck)                        [subckt.c]
     └─ flattens all X-elements
 
 └─ inp_dodotcard(deck)                           [dotcards.c]
     └─ creates TRANan, .options etc.
 
 └─ SPC_parseSpice(deck)                          [spicelib/parser/]
     ├─ INPpas1(ckt, deck, tab)                   [inppas1.c]  ← .model
     └─ INPpas2(ckt, deck, tab, nodTab)           [inppas2.c]  ← elements

 └─ CKTsetup(ckt)                                 [analysis/cktsetup.c]
     ├─ DEVsetup() for each device type
     ├─ SMPpreOrder(matrix)
     └─ CKTtemp(ckt)                              [analysis/ckttemp.c]

 └─ IFrunAnalysis(ckt, tranJob)
     └─ DCTran(ckt)                               [analysis/dctran.c]
         ├─ traninit(ckt)                         [analysis/traninit.c]
         ├─ OUTbeginPlot(…, &run)                 [frontend/outitf.c]
         │   └─ fileInit(run)                     ← writes rawfile header
         │
         └─ TIME LOOP:
             ├─ NIpred(ckt)                       [maths/ni/nipred.c]
             │
             ├─ NIiter(ckt, maxIter)              [maths/ni/niiter.c]
             │   ├─ CKTload(ckt)                  [analysis/cktload.c]
             │   │   └─ DIOload / BJTload / …     [devices/*/xxxload.c]
             │   │       ├─ DEVpnjlim()           ← voltage clamp
             │   │       └─ SMPaddElement()       ← matrix stamp
             │   ├─ SMPluFac(matrix)              [maths/sparse/]
             │   ├─ SMPsolve(matrix, rhs)
             │   └─ NIconv(ckt)                   [maths/ni/niconv.c]
             │
             ├─ CKTtrunc(ckt, &newDelta)          [analysis/ckttrunc.c]
             │   └─ DEVtrunc() per device         ← LTE check
             │
             ├─ NIcomCof(ckt)                     [maths/ni/nicomcof.c]
             │
             └─ OUTdata(run, &time, …, &vals)     [frontend/outitf.c]
                 ├─ fileAddRealValue(fp, …)        ← append to rawfile
                 └─ plotAddRealValue(dvec, …)      ← append to memory

         └─ OUTendPlot(run)                       [frontend/outitf.c]
             ├─ fseek → rewrite "No. Points:" header
             └─ fclose(rawfile)

 └─ Post-processing:
     ├─ com_measure2()                            [frontend/com_measure2.c]
     ├─ com_fourier()                             [frontend/fourier.c]
     └─ com_gnuplot() / raw_write()               [plotting/gnuplot.c / rawfile.c]
```

---

## 10. Key Data Structures — Field Reference

### `CKTcircuit` (`src/include/ngspice/cktdefs.h`)

```c
struct CKTcircuit {
    SMPmatrix  *CKTmatrix;     /* sparse MNA matrix */
    double     *CKTrhs;        /* current solution vector (node voltages + branch currents) */
    double     *CKTrhsOld;     /* previous iteration solution */
    double     *CKTstate0;     /* current time-point state variables */
    double     *CKTstate1;     /* previous time-point state variables */
    double     *CKTstate2;     /* t-2 state variables (Gear-2) */
    CKTnode    *CKTnodeTab;    /* node table: name → matrix index */
    void       *CKThead[MAXNUMDEVS]; /* per-device instance list heads */
    void       *CKTmods;       /* model list */
    double      CKTtime;       /* current simulation time */
    double      CKTdelta;      /* current time step Δt */
    double      CKTvt;         /* thermal voltage kT/q */
    double      CKTtemp;       /* circuit temperature (Kelvin) */
    double      CKTgmin;       /* minimum conductance (convergence aid) */
    double      CKTvntol;      /* voltage Newton tolerance */
    double      CKTreltol;     /* relative tolerance */
    double      CKTabstol;     /* absolute tolerance */
    int         CKTmode;       /* mode flags: MODEDCOP, MODETRAN, MODEAC … */
    int         CKTnoncon;     /* nonconvergence counter */
    CKTnode    *CKTtroubleNode;/* node causing nonconvergence */
    CKTstat    *CKTstat;       /* timing / iteration statistics */
};
```

### `dvec` (`src/include/ngspice/dvec.h`)

```c
struct dvec {
    char       *v_name;        /* "v(out)", "time", "i(v1)" */
    int         v_type;        /* SV_VOLTAGE, SV_CURRENT, SV_TIME … */
    int         v_flags;       /* VF_REAL, VF_COMPLEX, VF_PERMANENT */
    double     *v_realdata;    /* real sample array [0..v_length-1] */
    ngcomplex_t *v_compdata;   /* complex sample array (AC only) */
    int         v_length;      /* number of points stored so far */
    int         v_alloc_length;/* allocated size */
    struct plot *v_plot;       /* owning plot */
    struct dvec *v_next;       /* next vector in plot */
};
```

### `runDesc` (internal to `outitf.c`)

```c
typedef struct {
    char    *name;        /* analysis name */
    int      numData;     /* number of output variables */
    dataDesc *data;       /* array of variable descriptors */
    FILE    *fd;          /* output rawfile FILE pointer (NULL = memory only) */
    bool     binary;      /* binary rawfile format? */
    int      pointCount;  /* data points written so far */
    struct plot *plot;    /* in-memory plot for CP access */
    long     headerPos;   /* file position of "No. Points:" for rewrite */
} runDesc;
```

---

## 11. Output File Formats

### 11.1 Binary rawfile (`.raw`)

```
[ASCII header text terminated by "Binary:\n"]
[N doubles × M variables × P points, little-endian IEEE 754]
```

Used by ngspice, LTspice, WaveView, Python `spyci` / `ltspice` libraries.

### 11.2 ASCII rawfile

```
[ASCII header as above but "Values:\n"]
[For each point: N lines each with one floating-point value]
```

### 11.3 Reading the rawfile back

```c
raw_read(filename, &plots, &datasets);
/* src/frontend/rawfile.c — raw_read() */
```

Returns a linked list of `struct plot *`, each with its `dvec *` chain.
Used by the `load` CP command to read back previously saved results.

---

## 12. Environment Variables and `.options` Parameters Affecting I/O

| Parameter | Default | Effect |
|-----------|---------|--------|
| `VNTOL` | `1e-6 V` | Voltage convergence tolerance in `NIconv()` |
| `ABSTOL` | `1e-12 A` | Current convergence tolerance |
| `RELTOL` | `0.001` | Relative convergence tolerance |
| `GMIN` | `1e-12 S` | Minimum conductance stamped at every node |
| `TNOM` | `27 °C` | Nominal temperature for model parameters |
| `RAWFMT` | `binary` | `ascii` or `binary` rawfile output |
| `NOPADDING` | off | Suppress zero-padding in binary rawfile |
| `MAXSTEP` | `TRANstop/100` | Maximum time step (transient) |
| `ITL1` | `100` | Max DC operating-point iterations |
| `ITL2` | `50` | Max DC transfer curve iterations |
| `ITL4` | `10` | Max transient time-point iterations |
| `ITL5` | `5000` | Max total transient iterations |
