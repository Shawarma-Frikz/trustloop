import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import Ajv2020 from "ajv/dist/2020";
import type { Schema } from "ajv";

const CONTRACTS = join(import.meta.dirname, "..", "..", "contracts", "v1");
const FIXTURES = join(CONTRACTS, "fixtures");

// strictRequired is off: the schemas express status rules via if/then, where
// "required" legitimately names properties declared at the item level.
const ajv = new Ajv2020({ allErrors: true, strict: true, strictRequired: false });

function load(name: string): unknown {
  return JSON.parse(readFileSync(join(CONTRACTS, name), "utf8"));
}

interface ConstantsFile {
  contractVersion: string;
  constants: Record<string, number | string>;
  statuses: string[];
  engines: string[];
  evidenceQualityLevels: string[];
  reasonCodes: { code: string; scope: string }[];
  bands: { name: string; min: number; max: number }[];
  signals: { kind: string; direction: string }[];
}

interface SchemaFile {
  $defs?: {
    result?: { properties: Record<string, unknown> };
    signal?: { properties: { kind: { enum: string[] } } };
  };
  properties?: Record<string, any>;
}

const constants = load("constants.json") as ConstantsFile;

describe("contract v1 fixtures", () => {
  const fixtures = readdirSync(FIXTURES).filter((name) => name.endsWith(".json"));

  it.each(fixtures)("%s validates as its name promises", (name) => {
    const segments = name.split(".");
    const message = segments[0];
    const validate = ajv.compile(load(`${message}.schema.json`) as Schema);
    const valid = validate(load(join("fixtures", name)));

    if (segments[1].startsWith("valid")) {
      expect(validate.errors).toBeNull();
      expect(valid).toBe(true);
    } else {
      expect(valid).toBe(false);
    }
  });
});

describe("schemas stay in sync with constants.json", () => {
  it("analyze-request bounds come from constants", () => {
    const request = load("analyze-request.schema.json") as SchemaFile;
    expect(request.properties!.reviews.maxItems).toBe(constants.constants.MAX_REVIEWS_PER_REQUEST);
    expect(request.properties!.reviews.items.properties.text.maxLength).toBe(
      constants.constants.MAX_REVIEW_CHARS,
    );
  });

  it("analyze-response enums come from constants", () => {
    const response = load("analyze-response.schema.json") as SchemaFile;
    const resultProps = response.$defs!.result!.properties as Record<string, any>;

    expect(resultProps.status.enum).toEqual(constants.statuses);
    expect(resultProps.engine.enum).toEqual(constants.engines);
    expect(resultProps.evidenceQuality.enum).toEqual(constants.evidenceQualityLevels);
    expect(resultProps.verdict.enum).toEqual(constants.bands.map((b) => b.name));
    expect(resultProps.signals.maxItems).toBe(constants.constants.MAX_SIGNALS);
    expect(resultProps.reasonCode.enum).toEqual(
      constants.reasonCodes.filter((r) => r.scope === "result").map((r) => r.code),
    );
    expect(response.$defs!.signal!.properties.kind.enum).toEqual(
      constants.signals.map((s) => s.kind),
    );
  });

  it("version-response pins the model version format", () => {
    const version = load("version-response.schema.json") as SchemaFile;
    expect(version.properties!.expectedModelVersion.pattern).toBe(
      constants.constants.MODEL_VERSION_FORMAT,
    );
  });

  it("error-response uses only request-error reason codes", () => {
    const error = load("error-response.schema.json") as SchemaFile;
    expect(error.properties!.error.properties.code.enum).toEqual(
      constants.reasonCodes.filter((r) => r.scope === "request_error").map((r) => r.code),
    );
  });
});

describe("constants.json is complete and coherent", () => {
  it("has exactly 17 constants, 10 reason codes, 7 signals, 6 bands", () => {
    expect(Object.keys(constants.constants)).toHaveLength(17);
    expect(constants.reasonCodes).toHaveLength(10);
    expect(constants.signals).toHaveLength(7);
    expect(constants.bands).toHaveLength(6);
    expect(constants.constants.REQUEST_ID_HEADER).toBe("X-Request-Id");
  });

  it("bands cover 0-100 without gaps", () => {
    expect(constants.bands[0].min).toBe(0);
    expect(constants.bands.at(-1)!.max).toBe(100);
    for (let i = 1; i < constants.bands.length; i++) {
      expect(constants.bands[i].min).toBe(constants.bands[i - 1].max + 1);
    }
  });
});

describe("internal contract boundary", () => {
  it("internal result is the public result plus pOrganic and nothing else", () => {
    const publicSchema = load("analyze-response.schema.json") as SchemaFile;
    const internalSchema = load("score-response.schema.json") as SchemaFile;

    const publicKeys = Object.keys(publicSchema.$defs!.result!.properties).sort();
    const internalKeys = Object.keys(internalSchema.$defs!.result!.properties)
      .filter((key) => key !== "pOrganic")
      .sort();

    expect(internalKeys).toEqual(publicKeys);
  });
});
