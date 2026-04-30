---
type: summary
name: 6aa2dea1
sha: 6aa2dea1334bfd4f859f9c2f77141ff28f427f3b
created: 2026-04-30T03:37:18Z
updated: 2026-04-30T03:37:18Z
confidence: 1.00
sources: [6aa2dea1334bfd4f859f9c2f77141ff28f427f3b]
tier: episodic
---
# Commit 6aa2dea1

        **fase 3**

        This commit adds comprehensive tests for the `consolidate.py` module, which implements Ebbinghaus decay and fact/page tier promotion in the wiki, updates the `README.md` with usage instructions for `llmwikidoc` commands, and expands the `.gitignore` to include local generated directories.

        ## Changed Files
        - `.gitignore`
- `README.md`
- `tests/test_consolidate.py`

        ## Entities
        - **.gitignore** (file): Configuration file specifying intentionally untracked files that Git should ignore.
- **README.md** (file): The main documentation file for the project, providing setup and usage instructions.
- **tests/test_consolidate.py** (module): A new test module for the `consolidate.py` script, covering Ebbinghaus decay, tier promotion, and digest functionalities.
- **consolidate.py** (module): A module responsible for managing confidence decay, promoting facts and pages between knowledge tiers, and creating digests within the wiki.
- **ConfidenceStore** (class): Manages the storage and retrieval of facts and their associated confidence levels.
- **Fact** (class): Represents a single verifiable statement within the wiki, including its confidence, entity, and sources.
- **WikiManager** (class): Manages the wiki structure and content.
- **ConsolidationResult** (class): Stores the outcomes and metrics of a consolidation operation, such as facts decayed or promoted.
- **Ebbinghaus decay** (concept): A mechanism to model the natural decay of confidence in facts over time, similar to the forgetting curve.
- **tier promotion** (concept): The process of elevating facts or pages through different knowledge tiers (e.g., working, episodic, semantic, procedural) based on stability, age, and confidence.
- **digest** (concept): A summarized collection of information or changes within the wiki.
- **_apply_decay** (function): Applies the Ebbinghaus decay logic to facts in the ConfidenceStore, reducing their confidence based on age.
- **_promote_facts** (function): Promotes facts within the ConfidenceStore by adding a 'consolidated' source marker if they meet certain criteria (age, confidence, sources).
- **_fact_tier** (function): Determines the current knowledge tier of a fact based on its number of sources and confidence.
- **_compute_new_tier** (function): Calculates the potential new knowledge tier for a fact or page based on its current tier, confidence, sources, and age.
- **_tier_stability_multiplier** (function): Provides a multiplier that affects the decay rate of facts based on their current knowledge tier, with higher tiers having more stability.
- **GEMINI_API_KEY** (concept): An environment variable required for `llmwikidoc` to interact with the Gemini API.
- **llmwikidoc init** (command): A command to initialize `llmwikidoc` in a git project, installing necessary hooks and creating the wiki directory.
- **git commit hook** (mechanism): A git hook installed by `llmwikidoc init` that automatically runs `llmwikidoc ingest` after a commit to update the wiki.
- **llmwikidoc ingest** (command): A command (often run via a git hook) to process new code changes and update the project wiki.
- **llmwikidoc query** (command): A command to query the project wiki for information using natural language.
- **llmwikidoc status** (command): A command to check the current status of the `llmwikidoc` system or wiki.

        ## Stats
        - Author: ianache <ianache@crossnet.ws>
        - Timestamp: 2026-04-29T22:32:05-05:00
        - Files changed: 3
