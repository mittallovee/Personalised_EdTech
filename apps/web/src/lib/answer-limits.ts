/**
 * The answer limits a coaching can change (M3 design note §5.4, D-03), as the admin screen shows
 * them. The server decides what is allowed (bounds, a minimum above a maximum, the exam); this only
 * turns what is typed into the values to send, and a stored value into text for a box. Decimals are
 * kept as text with two decimals, never as floats.
 */

export type Setting = {
  name: string;
  label: string;
  kind: "int" | "decimal";
  group: string;
};

const GROUPS = {
  integer: "Integer answers",
  digit: "Single-digit answers",
  numeric: "Numerical answers",
  matching: "Matching: items in each list",
  statements: "Multiple statements: number of statements",
};

export const SETTINGS: Setting[] = [
  { name: "integer_min", label: "Lowest key", kind: "int", group: GROUPS.integer },
  { name: "integer_max", label: "Highest key", kind: "int", group: GROUPS.integer },
  { name: "digit_min", label: "Lowest digit", kind: "int", group: GROUPS.digit },
  { name: "digit_max", label: "Highest digit", kind: "int", group: GROUPS.digit },
  { name: "numeric_min", label: "Lowest key", kind: "decimal", group: GROUPS.numeric },
  { name: "numeric_max", label: "Highest key", kind: "decimal", group: GROUPS.numeric },
  { name: "matching_min_items", label: "Fewest", kind: "int", group: GROUPS.matching },
  { name: "matching_max_items", label: "Most", kind: "int", group: GROUPS.matching },
  { name: "statements_min", label: "Fewest", kind: "int", group: GROUPS.statements },
  { name: "statements_max", label: "Most", kind: "int", group: GROUPS.statements },
];

/** The groups in the order they are shown, each with its settings. */
export const GROUP_LIST: { title: string; settings: Setting[] }[] = Object.values(GROUPS).map(
  (title) => ({ title, settings: SETTINGS.filter((s) => s.group === title) }),
);

type Values = Record<string, number | string>;

/** The text for each box: the saved value, else the fallback (what it would be otherwise), else empty. */
export function formFrom(values: Values, fallback: Values = {}): Record<string, string> {
  return Object.fromEntries(
    SETTINGS.map((s) => [s.name, String(values[s.name] ?? fallback[s.name] ?? "")]),
  );
}

const INT = /^-?[0-9]+$/;
const DECIMAL = /^-?[0-9]{1,6}(\.[0-9]{1,2})?$/;

function twoDecimals(text: string): string {
  const [whole, fraction = ""] = text.split(".");
  return `${whole}.${fraction.padEnd(2, "0")}`;
}

/**
 * The values to send for what was typed. A blank box is left out (it keeps the value it would have
 * had); so is a value equal to `builtIn`, because only what differs is sent. A box that is not a
 * number in the right form is named in `problems` and left out.
 */
export function valuesFrom(
  form: Record<string, string>,
  builtIn: Values = {},
): { values: Values; problems: Record<string, string> } {
  const values: Values = {};
  const problems: Record<string, string> = {};
  for (const setting of SETTINGS) {
    const text = (form[setting.name] ?? "").trim();
    if (text === "") continue;
    let value: number | string;
    if (setting.kind === "int") {
      if (!INT.test(text)) {
        problems[setting.name] = "Use a whole number, like 999.";
        continue;
      }
      value = Number(text);
    } else {
      if (!DECIMAL.test(text)) {
        problems[setting.name] = "Use a number with at most two decimals, like 999.00.";
        continue;
      }
      value = twoDecimals(text);
    }
    const same = setting.name in builtIn && sameNumber(builtIn[setting.name]!, value);
    if (!same) values[setting.name] = value;
  }
  return { values, problems };
}

function sameNumber(a: number | string, b: number | string): boolean {
  return Number(a) === Number(b);
}
