// Curated domain knowledge layered on top of the Digikey-seeded parts.
// Safe to rerun: everything is MERGE. Run statements individually (Aura write-cypher
// takes one statement per call) or via cypher-shell/neo4j-mcp write-cypher in sequence.

// ---------- Footprints ----------
MERGE (:Footprint {name: 'MX'})
;
MERGE (:Footprint {name: 'Choc v1'})
;
MERGE (:Footprint {name: 'USB-C-16P'})
;
MERGE (:Footprint {name: 'QFN-56'})
;

// ---------- Interfaces ----------
MERGE (:Interface {name: 'USB-C'})
;
MERGE (:Interface {name: 'USB 2.0'})
;
MERGE (:Interface {name: 'I2C'})
;
MERGE (:Interface {name: 'SPI'})
;
MERGE (:Interface {name: 'MX'})
;
MERGE (:Interface {name: 'Choc'})
;

// ---------- Threads ----------
MERGE (:Thread {spec: 'M2x0.4'})
;
MERGE (:Thread {spec: 'M2.5x0.45'})
;

// ---------- Firmware ----------
MERGE (:Firmware {name: 'QMK'})
;
MERGE (:Firmware {name: 'ZMK'})
;
MERGE (:Firmware {name: 'VIA'})
;
MERGE (:Firmware {name: 'KMK'})
;

// ---------- Features ----------
MERGE (:Feature {name: 'RGB underglow', description: 'Addressable RGB LEDs under the switches/board', keywords: 'rgb led ws2812 underglow'})
;
MERGE (:Feature {name: 'Rotary encoder', description: 'Volume/scroll knob input', keywords: 'encoder knob volume rotary'})
;
MERGE (:Feature {name: 'OLED display', description: 'Small status display', keywords: 'oled ssd1306 display screen'})
;
MERGE (:Feature {name: 'Hotswap switches', description: 'Switches can be swapped without soldering', keywords: 'hotswap socket kailh'})
;
MERGE (:Feature {name: 'Wireless', description: 'Bluetooth or 2.4GHz wireless connectivity', keywords: 'bluetooth wireless nrf52'})
;
MERGE (:Feature {name: 'Battery powered', description: 'Runs off a rechargeable battery', keywords: 'battery lipo charger'})
;

// Feature dependencies
MATCH (oled:Feature {name: 'OLED display'}), (i2c:Feature {name: 'I2C bus'})
MERGE (oled)-[:DEPENDS_ON]->(i2c)
;
MERGE (:Feature {name: 'I2C bus'})
;
MATCH (oled:Feature {name: 'OLED display'}), (i2c:Feature {name: 'I2C bus'})
MERGE (oled)-[:DEPENDS_ON]->(i2c)
;
MATCH (w:Feature {name: 'Wireless'}), (b:Feature {name: 'Battery powered'})
MERGE (w)-[:DEPENDS_ON]->(b)
;

// ---------- Manually added parts absent from Digikey (hobbyist vendor items) ----------
MERGE (p:Part:HotswapSocket {partId: 'Kailh|CPG151101S11'})
  SET p.mpn = 'CPG151101S11', p.name = 'Kailh MX Hotswap Socket', p.source = 'manual',
      p.description = 'Solderless hotswap socket for MX-style switches', p.verified = true,
      p.ingestedAt = datetime(), p.lifecycle = 'Active'
;
MERGE (m:Manufacturer {name: 'Kailh'})
;
MATCH (p:Part {partId: 'Kailh|CPG151101S11'}), (m:Manufacturer {name: 'Kailh'})
MERGE (p)-[:MADE_BY]->(m)
;
MATCH (p:Part {partId: 'Kailh|CPG151101S11'}), (f:Footprint {name: 'MX'})
MERGE (p)-[:HAS_FOOTPRINT]->(f)
;

MERGE (p:Part:Stabilizer {partId: 'Cherry|MX-STAB-2U'})
  SET p.mpn = 'MX-STAB-2U', p.name = 'Cherry-style PCB-mount stabilizer, 2U', p.source = 'manual',
      p.description = 'Wire stabilizer for 2U keys (shift, backspace)', p.verified = true,
      p.ingestedAt = datetime(), p.lifecycle = 'Active'
;
MATCH (p:Part {partId: 'Cherry|MX-STAB-2U'}), (m:Manufacturer {name: 'Cherry Americas LLC'})
MERGE (p)-[:MADE_BY]->(m)
;

MERGE (p:Part:Stabilizer {partId: 'Cherry|MX-STAB-6.25U'})
  SET p.mpn = 'MX-STAB-6.25U', p.name = 'Cherry-style PCB-mount stabilizer, 6.25U', p.source = 'manual',
      p.description = 'Wire stabilizer for the spacebar', p.verified = true,
      p.ingestedAt = datetime(), p.lifecycle = 'Active'
;
MATCH (p:Part {partId: 'Cherry|MX-STAB-6.25U'}), (m:Manufacturer {name: 'Cherry Americas LLC'})
MERGE (p)-[:MADE_BY]->(m)
;

// ---------- HAS_FOOTPRINT for switches ----------
MATCH (p:Part:Switch) WHERE p.mpn STARTS WITH 'MX'
MATCH (f:Footprint {name: 'MX'})
MERGE (p)-[:HAS_FOOTPRINT]->(f)
;
MATCH (p:Part:Switch) WHERE p.mpn IN ['5114', '5111']
MATCH (f:Footprint {name: 'Choc v1'})
MERGE (p)-[:HAS_FOOTPRINT]->(f)
;
MATCH (p:Part:Connector) WHERE p.name CONTAINS 'TYPE C' AND p.name CONTAINS '16'
MATCH (f:Footprint {name: 'USB-C-16P'})
MERGE (p)-[:HAS_FOOTPRINT]->(f)
;
MATCH (p:Part:Microcontroller) WHERE p.mpn = 'SC0914(13)'
MATCH (f:Footprint {name: 'QFN-56'})
MERGE (p)-[:HAS_FOOTPRINT]->(f)
;

// ---------- IMPLEMENTS interfaces ----------
MATCH (p:Part:Switch)
MATCH (i:Interface {name: 'MX'})
WHERE p.mpn STARTS WITH 'MX'
MERGE (p)-[:IMPLEMENTS]->(i)
;
MATCH (p:Part:Switch)
MATCH (i:Interface {name: 'Choc'})
WHERE p.mpn IN ['5114', '5111']
MERGE (p)-[:IMPLEMENTS]->(i)
;
MATCH (p:Part:Connector)
MATCH (i:Interface {name: 'USB-C'})
WHERE p.name CONTAINS 'TYPE C'
MERGE (p)-[:IMPLEMENTS]->(i)
;
MATCH (p:Part:Display)
MATCH (i:Interface {name: 'I2C'})
WHERE p.name CONTAINS 'OLED' OR p.description CONTAINS 'OLED'
MERGE (p)-[:IMPLEMENTS]->(i)
;
MATCH (p:Part:FlashMemory)
MATCH (i:Interface {name: 'SPI'})
MERGE (p)-[:IMPLEMENTS]->(i)
;

// ---------- SUPPORTED_BY firmware ----------
MATCH (p:Part:Microcontroller) WHERE p.mpn = 'SC0914(13)'
MATCH (fw:Firmware) WHERE fw.name IN ['QMK', 'ZMK', 'VIA', 'KMK']
MERGE (p)-[:SUPPORTED_BY]->(fw)
;
MATCH (p:Part:Microcontroller) WHERE p.mpn STARTS WITH 'ATMEGA32U4'
MATCH (fw:Firmware) WHERE fw.name IN ['QMK', 'VIA']
MERGE (p)-[:SUPPORTED_BY]->(fw)
;

// ---------- HAS_THREAD (fasteners <-> standoffs) ----------
MATCH (p:Part) WHERE (p:Fastener OR p:Standoff) AND (p.name CONTAINS 'M2 ' OR p.mpn CONTAINS 'M2' AND NOT p.mpn CONTAINS 'M2.5')
MATCH (t:Thread {spec: 'M2x0.4'})
MERGE (p)-[:HAS_THREAD]->(t)
;
MATCH (p:Part) WHERE (p:Fastener OR p:Standoff) AND (p.name CONTAINS 'M2.5' OR p.mpn CONTAINS 'M2.5')
MATCH (t:Thread {spec: 'M2.5x0.45'})
MERGE (p)-[:HAS_THREAD]->(t)
;

// ---------- PROVIDES (part -> feature) ----------
MATCH (p:Part:Led) WHERE p.mpn CONTAINS 'WS2812'
MATCH (f:Feature {name: 'RGB underglow'})
MERGE (p)-[:PROVIDES]->(f)
;
MATCH (p:Part:Encoder)
MATCH (f:Feature {name: 'Rotary encoder'})
MERGE (p)-[:PROVIDES]->(f)
;
MATCH (p:Part:Display)
MATCH (f:Feature {name: 'OLED display'})
MERGE (p)-[:PROVIDES]->(f)
;
MATCH (p:Part:HotswapSocket)
MATCH (f:Feature {name: 'Hotswap switches'})
MERGE (p)-[:PROVIDES]->(f)
;
MATCH (p:Part:Battery)
MATCH (f:Feature {name: 'Battery powered'})
MERGE (p)-[:PROVIDES]->(f)
;

// ---------- REQUIRES (bill-of-material dependencies) ----------
// RP2040 needs a 12MHz crystal and 16Mbit QSPI flash
MATCH (mcu:Part:Microcontroller {mpn: 'SC0914(13)'})
MATCH (xtal:Part:Crystal {mpn: 'STDCRG1-12M'})
MERGE (mcu)-[:REQUIRES {qty: 1, note: '12MHz crystal for USB timing'}]->(xtal)
;
MATCH (mcu:Part:Microcontroller {mpn: 'SC0914(13)'})
MATCH (flash:Part:FlashMemory {mpn: 'W25Q16JVSSIQ'})
MERGE (mcu)-[:REQUIRES {qty: 1, note: 'external QSPI flash for firmware storage'}]->(flash)
;
// ATMEGA32U4 boards commonly pair with a crystal too
MATCH (mcu:Part:Microcontroller) WHERE mcu.mpn STARTS WITH 'ATMEGA32U4'
MATCH (xtal:Part:Crystal {mpn: 'STDCRG1-12M'})
MERGE (mcu)-[:REQUIRES {qty: 1, note: '12MHz crystal'}]->(xtal)
;
// USB-C receptacle needs 2x 5.1k CC pull-down resistors
MATCH (usb:Part:Connector) WHERE usb.name CONTAINS 'TYPE C'
MATCH (r:Part:Resistor {mpn: 'ERJ-3EKF5101V'})
MERGE (usb)-[:REQUIRES {qty: 2, note: 'CC1/CC2 pull-down resistors, 5.1k 1%'}]->(r)
;
// LDO regulator needs input/output decoupling caps
MATCH (reg:Part:VoltageRegulator {mpn: 'AP2112K-3.3TRG1'})
MATCH (cap:Part:Capacitor) WHERE cap.name CONTAINS '1UF' OR cap.description CONTAINS '1uF'
WITH reg, cap LIMIT 1
MERGE (reg)-[:REQUIRES {qty: 2, note: 'input + output decoupling capacitor'}]->(cap)
;
// ESD protection recommended alongside the USB-C connector
MATCH (usb:Part:Connector) WHERE usb.name CONTAINS 'TYPE C'
MATCH (esd:Part:EsdProtection {mpn: 'USBLC6-2SC6'})
MERGE (usb)-[:REQUIRES {qty: 1, note: 'ESD protection on D+/D-'}]->(esd)
;
// Switches need a diode per key for the key matrix
MATCH (sw:Part:Switch) WHERE sw.mpn STARTS WITH 'MX'
MATCH (d:Part:Diode {mpn: '1N4148W'})
MERGE (sw)-[:REQUIRES {qty: 1, note: '1N4148 diode per switch for matrix scanning'}]->(d)
;
// Hotswap sockets are used with (not instead of) the switch footprint
MATCH (sock:Part:HotswapSocket {mpn: 'CPG151101S11'})
MATCH (sw:Part:Switch) WHERE sw.mpn STARTS WITH 'MX'
MERGE (sock)-[:COMPATIBLE_WITH {reason: 'both use the MX footprint', source: 'curated'}]->(sw)
;
// Fasteners <-> standoffs of matching thread are compatible
MATCH (t:Thread)<-[:HAS_THREAD]-(f:Part:Fastener)
MATCH (t)<-[:HAS_THREAD]-(s:Part:Standoff)
MERGE (f)-[:COMPATIBLE_WITH {reason: 'matching thread spec ' + t.spec, source: 'derived'}]->(s)
;

// ---------- Sample Design ----------
MERGE (d:Design {designId: 'demo-60pct-wireless'})
  SET d.name = '60% Wireless Keyboard Demo', d.layout = '60%', d.revision = 1
;
MATCH (d:Design {designId: 'demo-60pct-wireless'})
MATCH (mcu:Part:Microcontroller {mpn: 'SC0914(13)'})
MERGE (d)-[:USES {qty: 1, refDes: 'U1'}]->(mcu)
;
MATCH (d:Design {designId: 'demo-60pct-wireless'})
MATCH (usb:Part:Connector) WHERE usb.name CONTAINS 'TYPE C'
WITH d, usb LIMIT 1
MERGE (d)-[:USES {qty: 1, refDes: 'J1'}]->(usb)
;
MATCH (d:Design {designId: 'demo-60pct-wireless'})
MATCH (f:Feature {name: 'RGB underglow'})
MERGE (d)-[:WANTS]->(f)
;
MATCH (d:Design {designId: 'demo-60pct-wireless'})
MATCH (f:Feature {name: 'Wireless'})
MERGE (d)-[:WANTS]->(f)
;

// ---------- McMaster-Carr supplier + offers for fasteners/standoffs ----------
MERGE (:Supplier {name: 'McMaster-Carr', website: 'https://www.mcmaster.com'})
;
MATCH (p:Part) WHERE (p:Fastener OR p:Standoff) AND NOT (p)-[:OFFERED_AS]->()
MATCH (s:Supplier {name: 'McMaster-Carr'})
MERGE (o:Offer {offerId: 'mcmaster:' + p.partId})
  SET o.sku = 'MCM-' + toString(id(p)), o.url = 'https://www.mcmaster.com', o.unitPrice = 0.10,
      o.currency = 'USD', o.moq = 1, o.stock = 1000, o.lastCheckedAt = datetime()
MERGE (p)-[:OFFERED_AS]->(o)
MERGE (o)-[:SOLD_BY]->(s)
;
