# Question Content Schema and Examples

Prepared 18 October 2026. **Proposed payload schema**, not generated OpenAPI or an implemented validator. All nine confirmed product formats are represented below. Examples illustrate shape/type rules; they are synthetic content, not imported curriculum/taxonomy or proof of academic review.

## Envelope and fixtures

A candidate/revision payload has schema_version, question_type, language, stem rich blocks, a typed answer, metadata and type-specific fields. Incomplete drafts may omit answer and required publication metadata; malformed supplied fields still produce findings. UUIDs below are fixture identities, not live database IDs. In this fixture registry class/subject/chapter/topic form one valid hierarchy and the primary concept belongs to that subject. Bloom is a stable catalogue key; localized labels live separately. Simple arithmetic is used to make structural examples easy to inspect, not to specify the production JEE curriculum.

Publication-ready examples mean content/metadata complete, **not** already QC-approved or directly publishable through an API without workflow evidence. Source/provenance, creator and authorization are assigned server-side and cannot be forged by payloads.

## Rich blocks

paragraph: Unicode text. equation: format (latex or mathml), source and optional renderer metadata; visual input produces a supported equation source. image: same-coaching immutable asset_id, caption/alt text. table: rectangular rows of supported blocks. HTML/script and arbitrary executable markup are not canonical storage. Preserve supplied equation source when conversion is unsupported. Optional solution uses the same blocks; optional video_solution_url is an external link. No numerical answer-unit field exists.

Option/item IDs are unique within a question revision. Numerical values are decimal strings with exactly two digits after the decimal; integers are JSON integers, excluding booleans. A new revision may change type only with a fully revalidated payload. No scoring or tolerance is implied by this schema.


## SCQ

Valid incomplete draft:

```json
{
  "schema_version": 1,
  "question_type": "SCQ",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "What is 2 + 3?"
    }
  ]
}
```

Content-ready fixture (workflow evidence still required):

```json
{
  "schema_version": 1,
  "question_type": "SCQ",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "What is 2 + 3?"
    }
  ],
  "answer": {
    "option_id": "B"
  },
  "metadata": {
    "class_id": "00000000-0000-4000-8000-000000000001",
    "subject_id": "00000000-0000-4000-8000-000000000002",
    "chapter_id": "00000000-0000-4000-8000-000000000003",
    "topic_id": "00000000-0000-4000-8000-000000000004",
    "subtopic_id": null,
    "primary_concept_id": "00000000-0000-4000-8000-000000000005",
    "secondary_concept_ids": [],
    "difficulty": 4,
    "bloom_level": "APPLY",
    "is_pyq": false
  },
  "options": [
    {
      "id": "A",
      "content": [
        {
          "kind": "paragraph",
          "text": "4"
        }
      ]
    },
    {
      "id": "B",
      "content": [
        {
          "kind": "paragraph",
          "text": "5"
        }
      ]
    },
    {
      "id": "C",
      "content": [
        {
          "kind": "paragraph",
          "text": "6"
        }
      ]
    },
    {
      "id": "D",
      "content": [
        {
          "kind": "paragraph",
          "text": "7"
        }
      ]
    }
  ]
}
```

Invalid replacement answer:

```json
{
  "answer": {
    "option_id": "Z"
  }
}
```

Expected finding: Answer references a nonexistent option.

## Multiple correct

Valid incomplete draft:

```json
{
  "schema_version": 1,
  "question_type": "MULTI_CORRECT",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "Which listed numbers are prime?"
    }
  ]
}
```

Content-ready fixture (workflow evidence still required):

```json
{
  "schema_version": 1,
  "question_type": "MULTI_CORRECT",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "Which listed numbers are prime?"
    }
  ],
  "answer": {
    "option_ids": [
      "A",
      "C"
    ]
  },
  "metadata": {
    "class_id": "00000000-0000-4000-8000-000000000001",
    "subject_id": "00000000-0000-4000-8000-000000000002",
    "chapter_id": "00000000-0000-4000-8000-000000000003",
    "topic_id": "00000000-0000-4000-8000-000000000004",
    "subtopic_id": null,
    "primary_concept_id": "00000000-0000-4000-8000-000000000005",
    "secondary_concept_ids": [],
    "difficulty": 4,
    "bloom_level": "APPLY",
    "is_pyq": false
  },
  "options": [
    {
      "id": "A",
      "content": [
        {
          "kind": "paragraph",
          "text": "2"
        }
      ]
    },
    {
      "id": "B",
      "content": [
        {
          "kind": "paragraph",
          "text": "4"
        }
      ]
    },
    {
      "id": "C",
      "content": [
        {
          "kind": "paragraph",
          "text": "3"
        }
      ]
    },
    {
      "id": "D",
      "content": [
        {
          "kind": "paragraph",
          "text": "6"
        }
      ]
    }
  ]
}
```

Invalid replacement answer:

```json
{
  "answer": {
    "option_ids": []
  }
}
```

Expected finding: At least one correct option is required. A one-item answer set is valid.

## Integer

Valid incomplete draft:

```json
{
  "schema_version": 1,
  "question_type": "INTEGER",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "What is 499 + 500?"
    }
  ]
}
```

Content-ready fixture (workflow evidence still required):

```json
{
  "schema_version": 1,
  "question_type": "INTEGER",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "What is 499 + 500?"
    }
  ],
  "answer": {
    "value": 999
  },
  "metadata": {
    "class_id": "00000000-0000-4000-8000-000000000001",
    "subject_id": "00000000-0000-4000-8000-000000000002",
    "chapter_id": "00000000-0000-4000-8000-000000000003",
    "topic_id": "00000000-0000-4000-8000-000000000004",
    "subtopic_id": null,
    "primary_concept_id": "00000000-0000-4000-8000-000000000005",
    "secondary_concept_ids": [],
    "difficulty": 4,
    "bloom_level": "APPLY",
    "is_pyq": false
  }
}
```

Invalid replacement answer:

```json
{
  "answer": {
    "value": 1000
  }
}
```

Expected finding: Integer key must be in 0..999.

## Single digit

Valid incomplete draft:

```json
{
  "schema_version": 1,
  "question_type": "SINGLE_DIGIT",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "What is 2 + 3?"
    }
  ]
}
```

Content-ready fixture (workflow evidence still required):

```json
{
  "schema_version": 1,
  "question_type": "SINGLE_DIGIT",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "What is 2 + 3?"
    }
  ],
  "answer": {
    "value": 5
  },
  "metadata": {
    "class_id": "00000000-0000-4000-8000-000000000001",
    "subject_id": "00000000-0000-4000-8000-000000000002",
    "chapter_id": "00000000-0000-4000-8000-000000000003",
    "topic_id": "00000000-0000-4000-8000-000000000004",
    "subtopic_id": null,
    "primary_concept_id": "00000000-0000-4000-8000-000000000005",
    "secondary_concept_ids": [],
    "difficulty": 4,
    "bloom_level": "APPLY",
    "is_pyq": false
  }
}
```

Invalid replacement answer:

```json
{
  "answer": {
    "value": 10
  }
}
```

Expected finding: Single-digit key must be in 0..9.

## Numerical

Valid incomplete draft:

```json
{
  "schema_version": 1,
  "question_type": "NUMERICAL",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "A measurement is accepted between 9.79 and 9.81 inclusive. Give its numerical value."
    }
  ]
}
```

Content-ready fixture (workflow evidence still required):

```json
{
  "schema_version": 1,
  "question_type": "NUMERICAL",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "A measurement is accepted between 9.79 and 9.81 inclusive. Give its numerical value."
    }
  ],
  "answer": {
    "mode": "range",
    "lower": "9.79",
    "upper": "9.81"
  },
  "metadata": {
    "class_id": "00000000-0000-4000-8000-000000000001",
    "subject_id": "00000000-0000-4000-8000-000000000002",
    "chapter_id": "00000000-0000-4000-8000-000000000003",
    "topic_id": "00000000-0000-4000-8000-000000000004",
    "subtopic_id": null,
    "primary_concept_id": "00000000-0000-4000-8000-000000000005",
    "secondary_concept_ids": [],
    "difficulty": 4,
    "bloom_level": "APPLY",
    "is_pyq": false
  }
}
```

Invalid replacement answer:

```json
{
  "answer": {
    "mode": "exact",
    "value": "9.805"
  }
}
```

Expected finding: More than two decimal places: retain evidence and flag; do not round.

## Matching

Valid incomplete draft:

```json
{
  "schema_version": 1,
  "question_type": "MATCHING",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "Match each expression to every equal value in the right list."
    }
  ]
}
```

Content-ready fixture (workflow evidence still required):

```json
{
  "schema_version": 1,
  "question_type": "MATCHING",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "Match each expression to every equal value in the right list."
    }
  ],
  "answer": {
    "option_id": "A"
  },
  "metadata": {
    "class_id": "00000000-0000-4000-8000-000000000001",
    "subject_id": "00000000-0000-4000-8000-000000000002",
    "chapter_id": "00000000-0000-4000-8000-000000000003",
    "topic_id": "00000000-0000-4000-8000-000000000004",
    "subtopic_id": null,
    "primary_concept_id": "00000000-0000-4000-8000-000000000005",
    "secondary_concept_ids": [],
    "difficulty": 4,
    "bloom_level": "APPLY",
    "is_pyq": false
  },
  "left": [
    {
      "id": "L1",
      "content": [
        {
          "kind": "paragraph",
          "text": "1 + 1"
        }
      ]
    },
    {
      "id": "L2",
      "content": [
        {
          "kind": "paragraph",
          "text": "1 + 2"
        }
      ]
    }
  ],
  "right": [
    {
      "id": "R1",
      "content": [
        {
          "kind": "paragraph",
          "text": "2"
        }
      ]
    },
    {
      "id": "R2",
      "content": [
        {
          "kind": "paragraph",
          "text": "3"
        }
      ]
    },
    {
      "id": "R3",
      "content": [
        {
          "kind": "paragraph",
          "text": "2.0"
        }
      ]
    },
    {
      "id": "R4",
      "content": [
        {
          "kind": "paragraph",
          "text": "5"
        }
      ]
    }
  ],
  "options": [
    {
      "id": "A",
      "mapping": {
        "L1": [
          "R1",
          "R3"
        ],
        "L2": [
          "R2"
        ]
      }
    },
    {
      "id": "B",
      "mapping": {
        "L1": [
          "R2"
        ],
        "L2": [
          "R1"
        ]
      }
    },
    {
      "id": "C",
      "mapping": {
        "L1": [
          "R1"
        ],
        "L2": [
          "R1"
        ]
      }
    },
    {
      "id": "D",
      "mapping": {
        "L1": [
          "R4"
        ],
        "L2": [
          "R3"
        ]
      }
    }
  ]
}
```

Invalid replacement answer:

```json
{
  "answer": {
    "option_id": "C"
  }
}
```

Expected finding: The selected correct mapping shares R1 across two left items. This is forbidden for the correct answer; an incorrect distractor may display it.

## Assertion and reason

Valid incomplete draft:

```json
{
  "schema_version": 1,
  "question_type": "ASSERTION_REASON",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "Select the correct interpretation."
    }
  ]
}
```

Content-ready fixture (workflow evidence still required):

```json
{
  "schema_version": 1,
  "question_type": "ASSERTION_REASON",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "Select the correct interpretation."
    }
  ],
  "answer": {
    "option_id": "A"
  },
  "metadata": {
    "class_id": "00000000-0000-4000-8000-000000000001",
    "subject_id": "00000000-0000-4000-8000-000000000002",
    "chapter_id": "00000000-0000-4000-8000-000000000003",
    "topic_id": "00000000-0000-4000-8000-000000000004",
    "subtopic_id": null,
    "primary_concept_id": "00000000-0000-4000-8000-000000000005",
    "secondary_concept_ids": [],
    "difficulty": 4,
    "bloom_level": "APPLY",
    "is_pyq": false
  },
  "assertion": [
    {
      "kind": "paragraph",
      "text": "2 is even."
    }
  ],
  "reason": [
    {
      "kind": "paragraph",
      "text": "2 is divisible by 2."
    }
  ],
  "options": [
    {
      "id": "A",
      "content": [
        {
          "kind": "paragraph",
          "text": "Both are true and the reason explains the assertion."
        }
      ]
    },
    {
      "id": "B",
      "content": [
        {
          "kind": "paragraph",
          "text": "Both are true but the reason does not explain the assertion."
        }
      ]
    },
    {
      "id": "C",
      "content": [
        {
          "kind": "paragraph",
          "text": "Only the assertion is true."
        }
      ]
    },
    {
      "id": "D",
      "content": [
        {
          "kind": "paragraph",
          "text": "Only the reason is true."
        }
      ]
    }
  ]
}
```

Invalid replacement answer:

```json
{
  "answer": {
    "option_id": "E"
  }
}
```

Expected finding: Exactly one of the four supplied option IDs must be selected. Wording is question-specific.

## Multiple statement

Valid incomplete draft:

```json
{
  "schema_version": 1,
  "question_type": "MULTIPLE_STATEMENT",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "Choose the true statements."
    }
  ]
}
```

Content-ready fixture (workflow evidence still required):

```json
{
  "schema_version": 1,
  "question_type": "MULTIPLE_STATEMENT",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "Choose the true statements."
    }
  ],
  "answer": {
    "option_id": "A"
  },
  "metadata": {
    "class_id": "00000000-0000-4000-8000-000000000001",
    "subject_id": "00000000-0000-4000-8000-000000000002",
    "chapter_id": "00000000-0000-4000-8000-000000000003",
    "topic_id": "00000000-0000-4000-8000-000000000004",
    "subtopic_id": null,
    "primary_concept_id": "00000000-0000-4000-8000-000000000005",
    "secondary_concept_ids": [],
    "difficulty": 4,
    "bloom_level": "APPLY",
    "is_pyq": false
  },
  "statements": [
    {
      "id": "S1",
      "content": [
        {
          "kind": "paragraph",
          "text": "2 is prime."
        }
      ]
    },
    {
      "id": "S2",
      "content": [
        {
          "kind": "paragraph",
          "text": "4 is prime."
        }
      ]
    },
    {
      "id": "S3",
      "content": [
        {
          "kind": "paragraph",
          "text": "6 is even."
        }
      ]
    }
  ],
  "options": [
    {
      "id": "A",
      "content": [
        {
          "kind": "paragraph",
          "text": "S1 and S3 only"
        }
      ]
    },
    {
      "id": "B",
      "content": [
        {
          "kind": "paragraph",
          "text": "S1 and S2 only"
        }
      ]
    },
    {
      "id": "C",
      "content": [
        {
          "kind": "paragraph",
          "text": "S2 and S3 only"
        }
      ]
    },
    {
      "id": "D",
      "content": [
        {
          "kind": "paragraph",
          "text": "All three"
        }
      ]
    }
  ]
}
```

Invalid replacement answer:

```json
{
  "answer": {
    "option_ids": [
      "A",
      "B"
    ]
  }
}
```

Expected finding: This format requires one option_id, not a multiple-correct answer set.

## Passage-based child

Valid incomplete draft:

```json
{
  "schema_version": 1,
  "question_type": "SCQ",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "What distance is travelled?"
    }
  ],
  "context": {
    "passage_revision_id": "00000000-0000-4000-8000-00000000001e",
    "ordinal": 1
  }
}
```

Content-ready fixture (workflow evidence still required):

```json
{
  "schema_version": 1,
  "question_type": "SCQ",
  "language": "en",
  "stem": [
    {
      "kind": "paragraph",
      "text": "What distance is travelled?"
    }
  ],
  "answer": {
    "option_id": "C"
  },
  "metadata": {
    "class_id": "00000000-0000-4000-8000-000000000001",
    "subject_id": "00000000-0000-4000-8000-000000000002",
    "chapter_id": "00000000-0000-4000-8000-000000000003",
    "topic_id": "00000000-0000-4000-8000-000000000004",
    "subtopic_id": null,
    "primary_concept_id": "00000000-0000-4000-8000-000000000005",
    "secondary_concept_ids": [],
    "difficulty": 4,
    "bloom_level": "APPLY",
    "is_pyq": false
  },
  "options": [
    {
      "id": "A",
      "content": [
        {
          "kind": "paragraph",
          "text": "2 m"
        }
      ]
    },
    {
      "id": "B",
      "content": [
        {
          "kind": "paragraph",
          "text": "3 m"
        }
      ]
    },
    {
      "id": "C",
      "content": [
        {
          "kind": "paragraph",
          "text": "6 m"
        }
      ]
    },
    {
      "id": "D",
      "content": [
        {
          "kind": "paragraph",
          "text": "9 m"
        }
      ]
    }
  ],
  "context": {
    "passage_revision_id": "00000000-0000-4000-8000-00000000001e",
    "ordinal": 1
  }
}
```

Invalid replacement answer:

```json
{
  "answer": {
    "option_id": "Z"
  }
}
```

Expected finding: Child obeys SCQ rules and must pin an accessible immutable passage revision.

## Passage grouping and other boundary cases

The ninth format is shared context, not a second answer discriminator. The passage fixture above pins passage revision 00000000-0000-4000-8000-00000000001e containing: "A body travels at constant speed 2 m/s for 3 s." Each child receives its own master/global code when materialized. Another child may be INTEGER with stem "How many seconds does it travel?", answer {"value":3}, context pointing to the same passage revision with ordinal 2. This demonstrates mixed child types without nested passages. Parent passage has no public question code requirement. Editing context creates a new passage revision; existing published children keep the original.

Additional required boundaries: integer 0/999 accepted and -1/1000/fractions rejected; single digit 0/9 accepted and -1/10 rejected. Numerical exact {"mode":"exact","value":"999.00"} is valid, as is 0.00. Reject 999.01, negative values, reversed bounds, disjoint ranges and answer-unit attributes. Range endpoints are inclusive. Short numerical UI input may be explicitly normalized to two-decimal display only when its value is already exactly representable; imported extra precision is flagged, never silently rounded.

Multiple-correct may use ["A"] as its answer option_ids. Matching permits unused right R4 in the example. Only the selected correct option mapping must satisfy the confirmed no-shared-right rule; distractors can intentionally violate it.

PYQ metadata adds exam_id/exam_year; missing either blocks publication when is_pyq is true. Optional subtopic/secondary concepts/solution/video/PYQ date/shift/paper code may be absent. Chapter/topic are singular IDs; valid secondary concepts need not share the primary chapter/topic.

## Verification boundary

Documentation checks parse these JSON fences and inspect their illustrated type/range/cardinality relationships. They are not application schema tests, subject-matter QC or engine benchmarks. Real typed validators, rendering tests and representative content fixtures are implementation work.
