export const FALLBACK = [
  {
    t: "Voltage Divider",
    c: "Basics",
    a: "op",
    net: ".title Voltage Divider\nV1 in 0 DC 12\nR1 in out 10k\nR2 out 0 10k\n.op\n.end",
  },
  {
    t: "RC Low-Pass Filter",
    c: "RC/RL/RLC",
    a: "ac",
    net: ".title RC Low-Pass Filter\nR1 in out 1k\nC1 out 0 100n\nV1 in 0 AC 1\n.ac dec 50 10 100k\n.end",
  },
  {
    t: "Half-Wave Rectifier",
    c: "Diode Circuits",
    a: "tran",
    net: ".title Half-Wave Rectifier\nV1 in 0 SIN(0 5 60)\nD1 in out D1N\n.model D1N D(IS=1e-14 N=1.0 BV=100)\nR1 out 0 1k\nC1 out 0 100u\n.tran 0.1m 50m\n.end",
  },
  {
    t: "CMOS Inverter VTC",
    c: "MOSFET",
    a: "dc",
    net: ".title CMOS Inverter\nVDD vdd 0 DC 5\nVIN in 0 DC 0\nM1 out in vdd vdd PMOD W=20u L=1u\nM2 out in 0 0 NMOD W=10u L=1u\n.model NMOD NMOS(VTO=0.7 KP=110u GAMMA=0.4 LAMBDA=0.04)\n.model PMOD PMOS(VTO=-0.7 KP=50u GAMMA=0.4 LAMBDA=0.05)\n.dc VIN 0 5 0.02\n.end",
  },
  {
    t: "CE Amplifier",
    c: "BJT Amplifiers",
    a: "ac",
    net: ".title CE Amplifier\nVCC vcc 0 DC 12\nR1 vcc base 100k\nR2 base 0 22k\nRC vcc col 4.7k\nRE emit 0 1k\nCE emit 0 100u\nQ1 col base emit NPN1\n.model NPN1 NPN(BF=200 IS=1e-14 VAF=100)\nVIN in 0 AC 1\nCIN in base 10u\n.ac dec 50 10 10Meg\n.end",
  },
  {
    t: "Wien Bridge Oscillator",
    c: "Analog",
    a: "tran",
    net: ".title Wien Bridge Oscillator\nR1 in fb 10k\nR2 fb 0 10k\nC1 in fb 10n\nC2 fb 0 10n\nE1 out 0 fb 0 3.1\nR3 out in 1\n.tran 0.01m 5m\n.end",
  },
  {
    t: "Hydraulic Pump + PRV",
    c: "Hydraulic",
    a: "op",
    net: ".title Hydraulic Pump + PRV\n* 1 bar=1V, 1 L/min=1A\nI_PUMP PUMP_OUT 0 DC 38.6\nD_PRV 0 PUMP_OUT PRV200\n.model PRV200 D(IS=1e-14 BV=200 IBV=10 RS=0.02)\nR_PIPE PUMP_OUT LOAD_IN 0.5\nR_LOAD LOAD_IN 0 5.0\n.op\n.end",
  },
];
