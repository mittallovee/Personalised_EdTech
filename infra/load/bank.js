// K-08: load test of the bank on the 100,000-question synthetic coaching (M4 design note §7.3).
//
// Five people at once (VUS), each signed in as a different member of the load-test coaching, each
// doing a mix of: the plain list, the list with filters and its total, a lookup by code, and a
// search (exact words, phrases, typos, Hindi). The thresholds are the targets from the design note:
// p95 under 300 ms for list, filter and code, under 800 ms for search. See
// docs/operations/load-tests.md for how to run it; the numbers are recorded there.

import http from "k6/http";
import { check, fail } from "k6";

const BASE = __ENV.BASE_URL || "http://host.docker.internal:8090";
const ORIGIN = __ENV.ORIGIN || "http://localhost:3000";
const PASSWORD = __ENV.LOAD_TEST_PASSWORD;
// Written by infra/load/serve-load-api.sh (tests/load/seed_bank.py): the seeded members' emails.
const SEEDED = JSON.parse(open(__ENV.USERS_FILE || "/load/load-users.json"));

export const options = {
  // Each person signs in once and keeps the session cookie, as a browser does (k6 would otherwise
  // forget cookies after every iteration).
  noCookiesReset: true,
  scenarios: {
    bank: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || 5),
      duration: __ENV.DURATION || "2m",
    },
  },
  thresholds: {
    "http_req_duration{name:list}": ["p(95)<300"],
    "http_req_duration{name:filter}": ["p(95)<300"],
    "http_req_duration{name:code}": ["p(95)<300"],
    "http_req_duration{name:search}": ["p(95)<800"],
    checks: ["rate>0.99"],
  },
  summaryTrendStats: ["avg", "med", "p(90)", "p(95)", "p(99)", "max"],
};

// Words that are in most questions, in few, typed with a typo, as a phrase, and in Hindi.
const SEARCHES = [
  "velocity",
  "block",
  "the",
  "pendulum friction",
  "momentum conservation",
  "capacitor energy",
  '"smooth incline"',
  "torque -rod",
  "acceleratoin",
  "velocty",
  "pendulm",
  "frequncy",
  "त्वरण",
  "घर्षण बल",
  "frac",
];

function signIn(email) {
  const response = http.post(
    `${BASE}/api/v1/auth/login`,
    JSON.stringify({ email, password: PASSWORD }),
    { headers: { "Content-Type": "application/json", Origin: ORIGIN }, tags: { name: "login" } },
  );
  if (response.status !== 200) {
    fail(`sign-in failed for ${email}: ${response.status} ${response.body}`);
  }
}

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

// Once, before the people start: codes and labels that really exist, to ask for.
export function setup() {
  if (!PASSWORD) {
    fail("Set LOAD_TEST_PASSWORD.");
  }
  const owner = SEEDED.users.find((user) => user.name === "owner");
  signIn(owner.email);
  const page = http.get(`${BASE}/api/v1/bank/questions?limit=100`).json();
  const rows = page.data;
  return {
    codes: rows.map((row) => row.code),
    subjects: [...new Set(rows.map((row) => row.subject_id))],
    chapters: [...new Set(rows.map((row) => row.chapter_id))],
    concepts: [...new Set(rows.flatMap((row) => row.concept_ids))],
  };
}

export default function (data) {
  if (__ITER === 0) {
    signIn(SEEDED.users[(__VU - 1) % SEEDED.users.length].email);
  }
  const what = Math.random();
  let response;
  if (what < 0.25) {
    response = http.get(`${BASE}/api/v1/bank/questions?limit=50`, { tags: { name: "list" } });
  } else if (what < 0.5) {
    const filters = [
      `subject_id=${pick(data.subjects)}`,
      `difficulty=${1 + Math.floor(Math.random() * 10)}`,
      Math.random() < 0.5 ? `chapter_id=${pick(data.chapters)}` : `concept_id=${pick(data.concepts)}`,
      Math.random() < 0.3 ? "is_pyq=true" : "has_solution=true",
    ];
    const chosen = filters.slice(0, 1 + Math.floor(Math.random() * filters.length));
    response = http.get(`${BASE}/api/v1/bank/questions?limit=50&${chosen.join("&")}`, {
      tags: { name: "filter" },
    });
  } else if (what < 0.7) {
    response = http.get(`${BASE}/api/v1/bank/questions/by-code/${pick(data.codes)}`, {
      tags: { name: "code" },
    });
  } else {
    const q = encodeURIComponent(pick(SEARCHES));
    response = http.get(`${BASE}/api/v1/bank/questions?limit=50&q=${q}`, {
      tags: { name: "search" },
    });
  }
  // Only a lookup by code may be 404 (a code of someone else's private draft); everything else must
  // be a 200, so fast error answers can never pass for a measurement.
  const lookup = response.request.url.includes("/by-code/");
  check(response, {
    answered: (r) => r.status === 200 || (lookup && r.status === 404),
  });
}
