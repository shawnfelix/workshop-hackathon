"""What to pull from Digikey: keyboard-PCB categories -> keyword queries.

`limit` is the total number of distinct parts kept per category (spread across its queries).
"""

CATALOG: list[dict] = [
    {"kind": "Switch", "limit": 30, "queries": [
        "Cherry MX keyswitch", "Kailh Choc key switch", "Kailh mechanical keyboard switch",
    ]},
    {"kind": "HotswapSocket", "limit": 20, "queries": [
        "CPG151101S11", "CPG135001S30", "Kailh socket", "keyswitch socket", "hot swap socket",
    ]},
    {"kind": "Stabilizer", "limit": 20, "queries": [
        "keyswitch stabilizer", "MX stabilizer", "Cherry stabilizer 2U",
    ]},
    {"kind": "Diode", "limit": 30, "queries": [
        "1N4148W SOD-123", "1N4148 DO-35 switching diode", "1N4148WS SOD-323",
    ]},
    {"kind": "Microcontroller", "limit": 30, "queries": [
        "RP2040", "ATMEGA32U4-AU", "ATMEGA32U4-MU", "nRF52840", "STM32F072CBT6", "STM32F411CEU6",
    ]},
    {"kind": "FlashMemory", "limit": 20, "queries": [
        "W25Q16JVUXIQ", "W25Q128JVSIQ", "W25Q32JVSSIQ", "W25Q64JVSSIQ", "GD25Q16", "W25Q16JV",
    ]},
    {"kind": "Crystal", "limit": 25, "queries": [
        "12MHz crystal 3225", "16MHz crystal 3225", "ABM8-12.000MHZ", "32.768kHz crystal 3215",
    ]},
    {"kind": "Connector", "limit": 30, "queries": [
        "USB Type-C receptacle 16 position SMD", "USB4105-GF-A", "USB-C mid mount receptacle",
        "TRRS 3.5mm jack PJ-320A", "JST SH 4 position 1.0mm", "Kailh hot swap USB connector",
    ]},
    {"kind": "Resistor", "limit": 30, "queries": [
        "5.1k ohm 0603 1%", "10k ohm 0603 1%", "22 ohm 0603 1%", "1k ohm 0603 1%", "4.7k ohm 0603 1%",
    ]},
    {"kind": "Capacitor", "limit": 30, "queries": [
        "0.1uF 0603 X7R 50V", "1uF 0603 X5R 16V", "10uF 0805 X5R 10V", "15pF 0603 C0G 50V", "4.7uF 0805 X5R",
    ]},
    {"kind": "Led", "limit": 30, "queries": [
        "WS2812B", "SK6812MINI-E", "SK6812 MINI", "LED 0603 white", "LED 0805 red", "APA102",
    ]},
    {"kind": "VoltageRegulator", "limit": 25, "queries": [
        "AP2112K-3.3TRG1", "XC6206P332MR", "LDO 3.3V 500mA SOT-23-5", "MIC5219-3.3YM5",
    ]},
    {"kind": "EsdProtection", "limit": 20, "queries": [
        "USBLC6-2SC6", "TPD2E001", "PRTR5V0U2X", "SRV05-4",
    ]},
    {"kind": "Encoder", "limit": 20, "queries": [
        "EC11 rotary encoder", "EC11E rotary encoder push", "PEC11R rotary encoder",
    ]},
    {"kind": "Display", "limit": 20, "queries": [
        "SSD1306 OLED 0.91", "OLED display 128x32 I2C", "OLED display 128x64 I2C",
    ]},
    {"kind": "TactileSwitch", "limit": 20, "queries": [
        "SKQG tactile switch", "TL3342", "PTS645", "B3U-1000P", "EVQP7", "TL1105",
    ]},
    {"kind": "Battery", "limit": 20, "queries": [
        "MCP73831T-2ACI/OT", "MCP73831", "TP4056", "BQ24075", "LP503562", "LiPo 3.7V",
    ]},
    {"kind": "Fastener", "limit": 25, "queries": [
        "M2 machine screw phillips", "M2 screw", "M2.5 screw", "M2 x 4mm screw", "M2 x 6mm pan head",
    ]},
    {"kind": "Standoff", "limit": 25, "queries": [
        "M2 standoff hex brass female", "M2 standoff 6mm", "M2.5 standoff hex female",
    ]},
]
