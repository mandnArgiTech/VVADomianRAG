import { describe, it, expect } from "vitest";
import {
  detectRelevantTypes,
  resolveCatalogTypesForKeywords,
  validateAIResponse,
  buildInlineAIPrompt,
} from "./aiLibraryContext.js";

function fakeCache(partNumbers) {
  var typ = "DIODE";
  var topParts = {};
  topParts[typ] = partNumbers.map(function (pn) {
    return { part_number: pn, comp_type: typ, spice_payload: ".model " + pn + " D()" };
  });
  var flatIndex = partNumbers.map(function (pn, idx) {
    return { pnUpper: String(pn).toUpperCase(), type: typ, idx: idx, descLower: "", mfrLower: "" };
  });
  return {
    ready: true,
    types: [{ type: typ, count: partNumbers.length }],
    topParts: topParts,
    flatIndex: flatIndex,
  };
}

describe("detectRelevantTypes", function () {
  it("maps schottky to DIODE", function () {
    expect(detectRelevantTypes("add a schottky diode")).toContain("DIODE");
  });
  it("treats sic as MOSFET family", function () {
    expect(detectRelevantTypes("add a SiC mosfet")).toContain("MOSFET");
  });
});

describe("resolveCatalogTypesForKeywords", function () {
  it("maps MOSFET keyword to SiC_MOSFET catalog rows", function () {
    var rows = [
      { type: "SiC_MOSFET", count: 3 },
      { type: "RESISTOR", count: 1 },
    ];
    var out = resolveCatalogTypesForKeywords(["MOSFET"], rows);
    expect(out).toContain("SiC_MOSFET");
  });
});

describe("validateAIResponse", function () {
  it("ignores known catalog .model name", function () {
    var c = fakeCache(["1N5819"]);
    var r = validateAIResponse(".model 1N5819 D(IS=1e-12)", c);
    expect(r.warnings.length).toBe(0);
  });
  it("warns on unknown .model", function () {
    var c = fakeCache(["1N5819"]);
    var r = validateAIResponse(".model FAKE999 D(IS=1e-12)", c);
    expect(r.warnings.length).toBeGreaterThan(0);
  });
  it("ignores built-in NPN", function () {
    var c = fakeCache([]);
    var r = validateAIResponse(".model NPN (BF=200)", c);
    expect(r.warnings.length).toBe(0);
  });
  it("warns unknown device model token on instance line", function () {
    var c = fakeCache(["1N5819"]);
    var r = validateAIResponse("D1 a b NOTINLIB", c);
    expect(
      r.warnings.some(function (w) {
        return w.indexOf("NOTINLIB") >= 0;
      }),
    ).toBe(true);
  });
  it("does not warn R line with numeric value", function () {
    var c = fakeCache(["1N5819"]);
    var r = validateAIResponse("R1 n1 n2 10k", c);
    expect(r.warnings.length).toBe(0);
  });
});

describe("buildInlineAIPrompt", function () {
  it("includes library section and RULES", function () {
    var c = fakeCache(["AAA"]);
    var p = buildInlineAIPrompt({
      netlist: "V1 1 0 5\n",
      cursorLine: 1,
      userRequest: "add diode",
      libCache: c,
    });
    expect(p.indexOf("=== COMPONENT LIBRARY") >= 0).toBe(true);
    expect(p.indexOf("=== RULES ===") >= 0).toBe(true);
    expect(p.indexOf("=== USER REQUEST ===") >= 0).toBe(true);
    expect(p.indexOf("=== CURRENT NETLIST") >= 0).toBe(true);
  });
});
