# Assessment evidence plan

| Brief requirement | Evidence to produce |
|---|---|
| LTI 1.3 Advantage | Moodle tool configuration, launch log, NRPS response, AGS passback log |
| IP boundary | Architecture diagram plus a database/API review showing rubric and allocation data never enters Moodle |
| Double-blind allocation | Allocation specification, 50-user test output, and reviewer UI screenshots with identities hidden |
| No self-allocation / reciprocal pairs | Automated validator output and worked examples |
| Balanced reviewer loads | Load distribution table for the synthetic cohort |
| Rubric authoring | Data model, rubric versioning screenshots, and API tests |
| Moderation and flagging | Moderator workflow recording and audit-event examples |
| Multi-tenant isolation | Negative tests for cross-tenant access, row-level authorization checks, and tenant fixtures |
| Deployment | Environment variable catalogue, database migration steps, secrets/key-management procedure, rollback steps |
| End-to-end success | A timestamped run from Moodle sandbox through final gradebook result |

Do not include real student data. Use synthetic users and remove credentials, private keys, and Moodle access tokens from logs before submission.
