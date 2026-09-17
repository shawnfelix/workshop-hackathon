// PCB component graph — schema constraints and indexes
// Safe to rerun: all statements use IF NOT EXISTS.

// ---------- Uniqueness / key constraints ----------
CREATE CONSTRAINT part_id_key IF NOT EXISTS
  FOR (p:Part) REQUIRE p.partId IS NODE KEY;

CREATE CONSTRAINT manufacturer_name_unique IF NOT EXISTS
  FOR (m:Manufacturer) REQUIRE m.name IS UNIQUE;

CREATE CONSTRAINT supplier_name_unique IF NOT EXISTS
  FOR (s:Supplier) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT offer_id_key IF NOT EXISTS
  FOR (o:Offer) REQUIRE o.offerId IS NODE KEY;

CREATE CONSTRAINT category_path_unique IF NOT EXISTS
  FOR (c:Category) REQUIRE c.path IS UNIQUE;

CREATE CONSTRAINT footprint_name_unique IF NOT EXISTS
  FOR (f:Footprint) REQUIRE f.name IS UNIQUE;

CREATE CONSTRAINT package_name_unique IF NOT EXISTS
  FOR (p:Package) REQUIRE p.name IS UNIQUE;

CREATE CONSTRAINT interface_name_unique IF NOT EXISTS
  FOR (i:Interface) REQUIRE i.name IS UNIQUE;

CREATE CONSTRAINT thread_spec_unique IF NOT EXISTS
  FOR (t:Thread) REQUIRE t.spec IS UNIQUE;

CREATE CONSTRAINT firmware_name_unique IF NOT EXISTS
  FOR (f:Firmware) REQUIRE f.name IS UNIQUE;

CREATE CONSTRAINT design_id_key IF NOT EXISTS
  FOR (d:Design) REQUIRE d.designId IS NODE KEY;

CREATE CONSTRAINT feature_name_unique IF NOT EXISTS
  FOR (f:Feature) REQUIRE f.name IS UNIQUE;

CREATE CONSTRAINT ingestion_id_key IF NOT EXISTS
  FOR (i:Ingestion) REQUIRE i.ingestionId IS NODE KEY;

CREATE CONSTRAINT project_id_key IF NOT EXISTS
  FOR (pr:Project) REQUIRE pr.projectId IS NODE KEY;

// ---------- Existence / type constraints ----------
CREATE CONSTRAINT part_name_exists IF NOT EXISTS
  FOR (p:Part) REQUIRE p.name IS NOT NULL;

CREATE CONSTRAINT part_mpn_string IF NOT EXISTS
  FOR (p:Part) REQUIRE p.mpn IS :: STRING;

CREATE CONSTRAINT offer_price_float IF NOT EXISTS
  FOR (o:Offer) REQUIRE o.unitPrice IS :: FLOAT;

CREATE CONSTRAINT offer_stock_int IF NOT EXISTS
  FOR (o:Offer) REQUIRE o.stock IS :: INTEGER;

// ---------- Range indexes ----------
CREATE INDEX part_mpn_idx IF NOT EXISTS FOR (p:Part) ON (p.mpn);
CREATE INDEX part_lifecycle_idx IF NOT EXISTS FOR (p:Part) ON (p.lifecycle);
CREATE INDEX offer_sku_idx IF NOT EXISTS FOR (o:Offer) ON (o.sku);
CREATE INDEX offer_price_idx IF NOT EXISTS FOR (o:Offer) ON (o.unitPrice);
CREATE INDEX offer_stock_idx IF NOT EXISTS FOR (o:Offer) ON (o.stock);
CREATE INDEX category_name_idx IF NOT EXISTS FOR (c:Category) ON (c.name);
CREATE INDEX part_source_idx IF NOT EXISTS FOR (p:Part) ON (p.source);
CREATE INDEX ingestion_status_idx IF NOT EXISTS FOR (i:Ingestion) ON (i.status);

// ---------- Fulltext search ----------
CREATE FULLTEXT INDEX part_search IF NOT EXISTS
  FOR (p:Part) ON EACH [p.name, p.mpn, p.description];

CREATE FULLTEXT INDEX feature_search IF NOT EXISTS
  FOR (f:Feature) ON EACH [f.name, f.description, f.keywords];

// ---------- Model reference ----------
// Nodes
//   (:Part {partId, mpn, name, description, datasheetUrl, lifecycle, ...kind-specific specs})
//     secondary labels: Switch, Diode, Microcontroller, Connector, HotswapSocket, Stabilizer,
//       Resistor, Capacitor, Led, Crystal, VoltageRegulator, Fastener, Standoff, Plate, Case, Keycap
//   (:Manufacturer {name, website})
//   (:Supplier {name, website})                       Digikey, McMaster-Carr, LCSC, Mouser
//   (:Offer {offerId, sku, url, unitPrice, currency, moq, stock, lastCheckedAt})
//   (:Category {name, path})                          hierarchical, e.g. "Connectors/USB/USB-C"
//   (:Footprint {name, description})                  MX, Choc v1, SOT-23, 0805, USB-C-16P, QFN-56
//   (:Package {name})                                 e.g. SOD-123, 0603, QFN-56
//   (:Interface {name, version})                      USB-C, USB 2.0, I2C, SPI, MX, Choc
//   (:Thread {spec})                                  M2x0.4, M2.5x0.45, #4-40
//   (:Firmware {name})                                QMK, ZMK, VIA, KMK
//   (:Design {designId, name, layout, revision})
//   (:Feature {name, description, keywords})          user-facing capability: "RGB underglow",
//                                                     "rotary encoder", "OLED display", "wireless"
//   (:Ingestion {ingestionId, query, status, startedAt, finishedAt, agentNotes})
//                                                     audit trail of a runtime agent run against Digikey
//
// Part provenance properties
//   p.source        'seed' | 'digikey-agent' | 'manual'
//   p.digikeyPn     Digikey part number when sourced via API/MCP
//   p.ingestedAt    datetime
//   p.verified      false until a human confirms agent-added compatibility edges
//
// Relationships
//   (Part)-[:MADE_BY]->(Manufacturer)
//   (Part)-[:IN_CATEGORY]->(Category)
//   (Category)-[:SUBCATEGORY_OF]->(Category)
//   (Part)-[:HAS_FOOTPRINT]->(Footprint)               shared footprint => derived compatibility
//   (Part)-[:HAS_PACKAGE]->(Package)
//   (Part)-[:IMPLEMENTS]->(Interface)
//   (Part)-[:HAS_THREAD]->(Thread)                     fasteners <-> standoffs
//   (Part:Microcontroller)-[:SUPPORTED_BY]->(Firmware)
//   (Part)-[:OFFERED_AS]->(Offer)-[:SOLD_BY]->(Supplier)
//   (Part)-[:REQUIRES {qty, note}]->(Part)             e.g. MCU -> crystal, USB-C -> 5.1k resistors
//   (Part)-[:COMPATIBLE_WITH {reason, source}]->(Part) curated, when not derivable from footprint
//   (Part)-[:CONFLICTS_WITH {reason}]->(Part)
//   (Part)-[:ALTERNATIVE_TO]->(Part)
//   (Part:Connector)-[:MATES_WITH]->(Part:Connector)
//   (Design)-[:USES {qty, refDes}]->(Part)
//   (Design)-[:WANTS]->(Feature)                       requested by user, may be unfulfilled
//   (Part)-[:PROVIDES]->(Feature)                      a part that satisfies a feature
//   (Feature)-[:DEPENDS_ON]->(Feature)                 e.g. "OLED display" -> "I2C bus"
//   (Ingestion)-[:TRIGGERED_BY]->(Design)
//   (Ingestion)-[:FOR_FEATURE]->(Feature)
//   (Ingestion)-[:CREATED]->(Part)                     which parts/offers the agent added
//   (Ingestion)-[:CREATED]->(Offer)
